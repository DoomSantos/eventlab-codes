"""SQLite store for timing board API."""

from __future__ import annotations

import hashlib
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parent / "timing.db"

# Abuse / product defaults (see docs/PRODUCT_BRIEF.md)
UPLOADS_PER_HOUR = 60
PRESENCE_MIN_INTERVAL_S = 5
PRESENCE_EXPIRE_S = 45
BOARD_WINDOW_H = 24
MIN_LAP_S = 0.001
MAX_LAP_S = 30 * 60


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso(dt: datetime | None = None) -> str:
    value = dt or utc_now()
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class Device:
    id: int
    display_name: str
    token_hash: str
    created_at: str


@dataclass(frozen=True, slots=True)
class LapRow:
    id: int
    device_id: int
    display_name: str
    track: str
    lap_time_s: float
    class_name: str
    car_pi: int
    car_ordinal: int
    integrity: str
    stream_gaps: int
    client_lap_id: str | None
    submitted_at: str


@dataclass(frozen=True, slots=True)
class PresenceRow:
    device_id: int
    display_name: str
    track: str
    class_pi: str
    car: str
    racing: bool
    updated_at: str


class TimingStore:
    def __init__(self, db_path: Path | str = DEFAULT_DB) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._migrate()

    def close(self) -> None:
        self._conn.close()

    def _migrate(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS invites (
                code TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                used_at TEXT,
                used_by_device_id INTEGER
            );

            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                display_name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                token_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS laps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id INTEGER NOT NULL REFERENCES devices(id),
                track TEXT NOT NULL,
                lap_time_s REAL NOT NULL,
                class_name TEXT NOT NULL,
                car_pi INTEGER NOT NULL,
                car_ordinal INTEGER NOT NULL,
                integrity TEXT NOT NULL,
                stream_gaps INTEGER NOT NULL DEFAULT 0,
                client_lap_id TEXT,
                submitted_at TEXT NOT NULL,
                UNIQUE(device_id, client_lap_id)
            );

            CREATE INDEX IF NOT EXISTS laps_board_idx
            ON laps (submitted_at, integrity, track);

            CREATE TABLE IF NOT EXISTS presence (
                device_id INTEGER PRIMARY KEY REFERENCES devices(id),
                track TEXT NOT NULL,
                class_pi TEXT NOT NULL,
                car TEXT NOT NULL DEFAULT '',
                racing INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    def create_invite(self, code: str | None = None) -> str:
        invite = (code or secrets.token_urlsafe(8)).strip()
        if not invite:
            raise ValueError("invite code empty")
        self._conn.execute(
            "INSERT INTO invites (code, created_at) VALUES (?, ?)",
            (invite, utc_iso()),
        )
        self._conn.commit()
        return invite

    def claim_invite(self, *, invite_code: str, display_name: str) -> tuple[Device, str]:
        name = display_name.strip()
        if len(name) < 2 or len(name) > 24:
            raise ValueError("display_name must be 2–24 characters")
        if any(ch in name for ch in "<>\"'\n\r\t"):
            raise ValueError("display_name has invalid characters")

        row = self._conn.execute(
            "SELECT * FROM invites WHERE code = ?", (invite_code.strip(),)
        ).fetchone()
        if row is None:
            raise LookupError("invalid invite")
        if row["used_at"] is not None:
            raise PermissionError("invite already used")

        token = secrets.token_urlsafe(32)
        token_h = hash_token(token)
        now = utc_iso()
        try:
            cur = self._conn.execute(
                """
                INSERT INTO devices (display_name, token_hash, created_at)
                VALUES (?, ?, ?)
                """,
                (name, token_h, now),
            )
            device_id = int(cur.lastrowid)
            updated = self._conn.execute(
                """
                UPDATE invites
                SET used_at = ?, used_by_device_id = ?
                WHERE code = ? AND used_at IS NULL
                """,
                (now, device_id, invite_code.strip()),
            )
            if updated.rowcount != 1:
                self._conn.rollback()
                raise PermissionError("invite already used")
            self._conn.commit()
        except sqlite3.IntegrityError as exc:
            self._conn.rollback()
            raise ValueError("display_name already taken") from exc
        device = Device(id=device_id, display_name=name, token_hash=token_h, created_at=now)
        return device, token

    def device_from_token(self, token: str) -> Device | None:
        row = self._conn.execute(
            "SELECT * FROM devices WHERE token_hash = ?",
            (hash_token(token),),
        ).fetchone()
        if row is None:
            return None
        return Device(
            id=row["id"],
            display_name=row["display_name"],
            token_hash=row["token_hash"],
            created_at=row["created_at"],
        )

    def _uploads_last_hour(self, device_id: int) -> int:
        since = utc_iso(utc_now() - timedelta(hours=1))
        row = self._conn.execute(
            """
            SELECT COUNT(*) AS n FROM laps
            WHERE device_id = ? AND submitted_at >= ?
            """,
            (device_id, since),
        ).fetchone()
        return int(row["n"])

    def insert_lap(
        self,
        *,
        device: Device,
        track: str,
        lap_time_s: float,
        class_name: str,
        car_pi: int,
        car_ordinal: int,
        integrity: str,
        stream_gaps: int = 0,
        client_lap_id: str | None = None,
        known_tracks: set[str] | None = None,
    ) -> LapRow:
        integrity_n = integrity.strip().lower()
        if integrity_n not in {"clean", "paused", "rewound"}:
            raise ValueError("integrity must be clean, paused, or rewound")
        if not (MIN_LAP_S < lap_time_s <= MAX_LAP_S):
            raise ValueError("lap_time_s out of range")
        track_n = track.strip()
        if known_tracks is not None and track_n not in known_tracks:
            raise ValueError("unknown track")
        if self._uploads_last_hour(device.id) >= UPLOADS_PER_HOUR:
            raise PermissionError("upload rate limit")

        if client_lap_id:
            existing = self._conn.execute(
                """
                SELECT laps.*, devices.display_name
                FROM laps JOIN devices ON devices.id = laps.device_id
                WHERE laps.device_id = ? AND laps.client_lap_id = ?
                """,
                (device.id, client_lap_id),
            ).fetchone()
            if existing is not None:
                return self._lap_from_row(existing)

        now = utc_iso()
        cur = self._conn.execute(
            """
            INSERT INTO laps (
                device_id, track, lap_time_s, class_name, car_pi, car_ordinal,
                integrity, stream_gaps, client_lap_id, submitted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                device.id,
                track_n,
                float(lap_time_s),
                class_name.strip().upper(),
                int(car_pi),
                int(car_ordinal),
                integrity_n,
                int(stream_gaps),
                client_lap_id,
                now,
            ),
        )
        self._conn.commit()
        row = self._conn.execute(
            """
            SELECT laps.*, devices.display_name
            FROM laps JOIN devices ON devices.id = laps.device_id
            WHERE laps.id = ?
            """,
            (cur.lastrowid,),
        ).fetchone()
        return self._lap_from_row(row)

    def board(
        self,
        *,
        track: str | None = None,
        class_pi: str | None = None,
        window_h: int = BOARD_WINDOW_H,
        limit: int = 100,
    ) -> list[LapRow]:
        since = utc_iso(utc_now() - timedelta(hours=window_h))
        sql = """
            SELECT laps.*, devices.display_name
            FROM laps JOIN devices ON devices.id = laps.device_id
            WHERE laps.integrity = 'clean' AND laps.submitted_at >= ?
        """
        params: list[object] = [since]
        if track:
            sql += " AND laps.track = ?"
            params.append(track)
        if class_pi:
            sql += " AND (laps.class_name || ' ' || laps.car_pi) = ?"
            params.append(class_pi)
        sql += " ORDER BY laps.lap_time_s ASC LIMIT ?"
        params.append(max(1, min(limit, 500)))
        return [self._lap_from_row(r) for r in self._conn.execute(sql, params).fetchall()]

    def history(self, *, player: str, limit: int = 50) -> list[LapRow]:
        rows = self._conn.execute(
            """
            SELECT laps.*, devices.display_name
            FROM laps JOIN devices ON devices.id = laps.device_id
            WHERE devices.display_name = ? COLLATE NOCASE
            ORDER BY laps.submitted_at DESC
            LIMIT ?
            """,
            (player.strip(), max(1, min(limit, 200))),
        ).fetchall()
        return [self._lap_from_row(r) for r in rows]

    def upsert_presence(
        self,
        *,
        device: Device,
        track: str,
        class_pi: str,
        car: str = "",
        racing: bool = True,
    ) -> PresenceRow:
        now = utc_now()
        existing = self._conn.execute(
            "SELECT updated_at FROM presence WHERE device_id = ?",
            (device.id,),
        ).fetchone()
        if existing is not None:
            prev = datetime.fromisoformat(existing["updated_at"].replace("Z", "+00:00"))
            if (now - prev).total_seconds() < PRESENCE_MIN_INTERVAL_S:
                # Soft-ignore: return current row without update
                row = self._conn.execute(
                    """
                    SELECT presence.*, devices.display_name
                    FROM presence JOIN devices ON devices.id = presence.device_id
                    WHERE presence.device_id = ?
                    """,
                    (device.id,),
                ).fetchone()
                return self._presence_from_row(row)

        stamp = utc_iso(now)
        self._conn.execute(
            """
            INSERT INTO presence (device_id, track, class_pi, car, racing, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(device_id) DO UPDATE SET
                track = excluded.track,
                class_pi = excluded.class_pi,
                car = excluded.car,
                racing = excluded.racing,
                updated_at = excluded.updated_at
            """,
            (
                device.id,
                track.strip(),
                class_pi.strip(),
                car.strip(),
                1 if racing else 0,
                stamp,
            ),
        )
        self._conn.commit()
        row = self._conn.execute(
            """
            SELECT presence.*, devices.display_name
            FROM presence JOIN devices ON devices.id = presence.device_id
            WHERE presence.device_id = ?
            """,
            (device.id,),
        ).fetchone()
        return self._presence_from_row(row)

    def live(self, *, expire_s: int = PRESENCE_EXPIRE_S) -> list[PresenceRow]:
        since = utc_iso(utc_now() - timedelta(seconds=expire_s))
        rows = self._conn.execute(
            """
            SELECT presence.*, devices.display_name
            FROM presence JOIN devices ON devices.id = presence.device_id
            WHERE presence.racing = 1 AND presence.updated_at >= ?
            ORDER BY presence.updated_at DESC
            """,
            (since,),
        ).fetchall()
        return [self._presence_from_row(r) for r in rows]

    @staticmethod
    def _lap_from_row(row: sqlite3.Row) -> LapRow:
        return LapRow(
            id=row["id"],
            device_id=row["device_id"],
            display_name=row["display_name"],
            track=row["track"],
            lap_time_s=row["lap_time_s"],
            class_name=row["class_name"],
            car_pi=row["car_pi"],
            car_ordinal=row["car_ordinal"],
            integrity=row["integrity"],
            stream_gaps=row["stream_gaps"],
            client_lap_id=row["client_lap_id"],
            submitted_at=row["submitted_at"],
        )

    @staticmethod
    def _presence_from_row(row: sqlite3.Row) -> PresenceRow:
        return PresenceRow(
            device_id=row["device_id"],
            display_name=row["display_name"],
            track=row["track"],
            class_pi=row["class_pi"],
            car=row["car"],
            racing=bool(row["racing"]),
            updated_at=row["updated_at"],
        )
