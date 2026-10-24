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

# Time Attack session day (docs/TIME_ATTACK.md)
AEST = timezone(timedelta(hours=10))
VALID_WINDOWS = frozenset({"today", "24h", "7d", "30d", "365d", "all"})
WINDOW_ALIASES = {
    "anytime": "all",
    "week": "7d",
    "month": "30d",
    "year": "365d",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso(dt: datetime | None = None) -> str:
    value = dt or utc_now()
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def aest_now(now: datetime | None = None) -> datetime:
    return (now or utc_now()).astimezone(AEST)


def aest_day_start(now: datetime | None = None) -> datetime:
    local = aest_now(now).replace(hour=0, minute=0, second=0, microsecond=0)
    return local


def aest_day_end(now: datetime | None = None) -> datetime:
    return aest_day_start(now) + timedelta(days=1)


def normalize_window(window: str | None) -> str:
    raw = (window or "24h").strip().lower()
    raw = WINDOW_ALIASES.get(raw, raw)
    if raw not in VALID_WINDOWS:
        raise ValueError("window must be today, 24h, 7d, 30d, 365d, or all")
    return raw


def window_since_iso(window: str | None, *, now: datetime | None = None) -> str | None:
    """Lower bound (UTC ISO) for submitted_at, or None for all-time."""
    key = normalize_window(window)
    current = now or utc_now()
    if key == "all":
        return None
    if key == "today":
        return utc_iso(aest_day_start(current).astimezone(timezone.utc))
    if key == "24h":
        return utc_iso(current - timedelta(hours=BOARD_WINDOW_H))
    if key == "7d":
        return utc_iso(current - timedelta(days=7))
    if key == "30d":
        return utc_iso(current - timedelta(days=30))
    if key == "365d":
        return utc_iso(current - timedelta(days=365))
    raise ValueError("window must be today, 24h, 7d, 30d, 365d, or all")


def session_meta(now: datetime | None = None) -> dict[str, str]:
    """AEST session day + countdown end for Live Timing."""
    current = now or utc_now()
    start = aest_day_start(current)
    end = aest_day_end(current)
    return {
        "tz": "AEST",
        "day": start.strftime("%Y-%m-%d"),
        "starts_at": utc_iso(start.astimezone(timezone.utc)),
        "ends_at": utc_iso(end.astimezone(timezone.utc)),
    }


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
    mode: str = ""


VALID_MODES = frozenset({"", "time_attack"})
BOARD_MODE_DEFAULT = "time_attack"

@dataclass(frozen=True, slots=True)
class PresenceRow:
    device_id: int
    display_name: str
    track: str
    class_pi: str
    car: str
    racing: bool
    updated_at: str
    mode: str = ""


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
                mode TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            );
            """
        )
        cols = {
            row[1]
            for row in self._conn.execute("PRAGMA table_info(laps)").fetchall()
        }
        if "mode" not in cols:
            self._conn.execute(
                "ALTER TABLE laps ADD COLUMN mode TEXT NOT NULL DEFAULT ''"
            )
        invite_cols = {
            row[1]
            for row in self._conn.execute("PRAGMA table_info(invites)").fetchall()
        }
        if "reclaim_device_id" not in invite_cols:
            self._conn.execute(
                "ALTER TABLE invites ADD COLUMN reclaim_device_id INTEGER"
            )
        presence_cols = {
            row[1]
            for row in self._conn.execute("PRAGMA table_info(presence)").fetchall()
        }
        if "mode" not in presence_cols:
            self._conn.execute(
                "ALTER TABLE presence ADD COLUMN mode TEXT NOT NULL DEFAULT ''"
            )
        self._conn.execute(
            """
            CREATE INDEX IF NOT EXISTS laps_board_mode_idx
            ON laps (submitted_at, integrity, mode, track)
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

    def device_by_name(self, display_name: str) -> Device | None:
        row = self._conn.execute(
            "SELECT * FROM devices WHERE display_name = ? COLLATE NOCASE",
            (display_name.strip(),),
        ).fetchone()
        if row is None:
            return None
        return Device(
            id=row["id"],
            display_name=row["display_name"],
            token_hash=row["token_hash"],
            created_at=row["created_at"],
        )

    def create_reclaim_invite(self, display_name: str) -> tuple[str, str]:
        """Mint an invite that reattaches a new PC to an existing display name."""
        device = self.device_by_name(display_name)
        if device is None:
            raise LookupError("no player with that display name")
        invite = secrets.token_urlsafe(8)
        self._conn.execute(
            """
            INSERT INTO invites (code, created_at, reclaim_device_id)
            VALUES (?, ?, ?)
            """,
            (invite, utc_iso(), device.id),
        )
        self._conn.commit()
        return invite, device.display_name

    def list_players(self) -> list[dict[str, object]]:
        rows = self._conn.execute(
            """
            SELECT devices.display_name AS display_name,
                   devices.created_at AS created_at,
                   COUNT(laps.id) AS lap_count
            FROM devices
            LEFT JOIN laps ON laps.device_id = devices.id
            GROUP BY devices.id
            ORDER BY devices.display_name COLLATE NOCASE
            """
        ).fetchall()
        return [
            {
                "display_name": row["display_name"],
                "created_at": row["created_at"],
                "lap_count": int(row["lap_count"]),
            }
            for row in rows
        ]

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
        reclaim_id = row["reclaim_device_id"]
        if reclaim_id:
            existing = self._conn.execute(
                "SELECT * FROM devices WHERE id = ?",
                (int(reclaim_id),),
            ).fetchone()
            if existing is None:
                raise LookupError("invalid invite")
            if name.casefold() != str(existing["display_name"]).casefold():
                raise ValueError(
                    f"use your existing display name: {existing['display_name']}"
                )
            try:
                self._conn.execute(
                    "UPDATE devices SET token_hash = ? WHERE id = ?",
                    (token_h, int(reclaim_id)),
                )
                updated = self._conn.execute(
                    """
                    UPDATE invites
                    SET used_at = ?, used_by_device_id = ?
                    WHERE code = ? AND used_at IS NULL
                    """,
                    (now, int(reclaim_id), invite_code.strip()),
                )
                if updated.rowcount != 1:
                    self._conn.rollback()
                    raise PermissionError("invite already used")
                self._conn.commit()
            except sqlite3.IntegrityError as exc:
                self._conn.rollback()
                raise ValueError("could not reattach display name") from exc
            return (
                Device(
                    id=int(existing["id"]),
                    display_name=str(existing["display_name"]),
                    token_hash=token_h,
                    created_at=str(existing["created_at"]),
                ),
                token,
            )

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
        mode: str | None = None,
        known_tracks: set[str] | None = None,
    ) -> LapRow:
        integrity_n = integrity.strip().lower()
        if integrity_n not in {"clean", "paused", "rewound"}:
            raise ValueError("integrity must be clean, paused, or rewound")
        mode_n = (mode or "").strip().lower()
        if mode_n not in VALID_MODES:
            raise ValueError("mode must be empty or time_attack")
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
                integrity, stream_gaps, client_lap_id, submitted_at, mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                mode_n,
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

    def retag_laps(
        self,
        *,
        ids: list[object],
        track: str,
        known_tracks: set[str] | None = None,
    ) -> list[LapRow]:
        track_n = track.strip()
        if not track_n:
            raise ValueError("track required")
        if known_tracks is not None and track_n not in known_tracks:
            raise ValueError("unknown track")
        clean_ids: list[int] = []
        for raw in ids:
            try:
                n = int(raw)
            except (TypeError, ValueError) as exc:
                raise ValueError("ids must be integers") from exc
            if n <= 0:
                raise ValueError("ids must be positive")
            clean_ids.append(n)
        if not clean_ids:
            raise ValueError("ids required")
        placeholders = ",".join("?" * len(clean_ids))
        self._conn.execute(
            f"UPDATE laps SET track = ? WHERE id IN ({placeholders})",
            (track_n, *clean_ids),
        )
        self._conn.commit()
        rows = self._conn.execute(
            f"""
            SELECT laps.*, devices.display_name
            FROM laps JOIN devices ON devices.id = laps.device_id
            WHERE laps.id IN ({placeholders})
            ORDER BY laps.id
            """,
            clean_ids,
        ).fetchall()
        return [self._lap_from_row(r) for r in rows]

    def delete_laps(self, ids: list[object]) -> int:
        clean_ids: list[int] = []
        for raw in ids:
            try:
                n = int(raw)
            except (TypeError, ValueError) as exc:
                raise ValueError("ids must be integers") from exc
            if n <= 0:
                raise ValueError("ids must be positive")
            clean_ids.append(n)
        if not clean_ids:
            raise ValueError("ids required")
        placeholders = ",".join("?" * len(clean_ids))
        cur = self._conn.execute(
            f"DELETE FROM laps WHERE id IN ({placeholders})",
            clean_ids,
        )
        self._conn.commit()
        return int(cur.rowcount)

    def delete_player(self, display_name: str) -> dict[str, object]:
        device = self.device_by_name(display_name)
        if device is None:
            raise LookupError("no player with that display name")
        laps = self._conn.execute(
            "DELETE FROM laps WHERE device_id = ?", (device.id,)
        )
        self._conn.execute(
            "DELETE FROM presence WHERE device_id = ?", (device.id,)
        )
        self._conn.execute(
            "DELETE FROM invites WHERE reclaim_device_id = ?", (device.id,)
        )
        self._conn.execute("DELETE FROM devices WHERE id = ?", (device.id,))
        self._conn.commit()
        return {
            "display_name": device.display_name,
            "laps_removed": int(laps.rowcount),
        }

    def board(
        self,
        *,
        track: str | None = None,
        class_pi: str | None = None,
        class_name: str | None = None,
        mode: str | None = BOARD_MODE_DEFAULT,
        window: str = "24h",
        window_h: int | None = None,
        limit: int = 100,
    ) -> list[LapRow]:
        # Legacy window_h still supported for older callers.
        if window_h is not None:
            since: str | None = utc_iso(utc_now() - timedelta(hours=window_h))
        else:
            window_key = normalize_window(window)
            since = window_since_iso(window_key)

        sql = """
            SELECT laps.*, devices.display_name
            FROM laps JOIN devices ON devices.id = laps.device_id
            WHERE laps.integrity = 'clean'
        """
        params: list[object] = []
        if since is not None:
            sql += " AND laps.submitted_at >= ?"
            params.append(since)
        if mode and mode != "all":
            sql += " AND laps.mode = ?"
            params.append(mode.strip().lower())
        if track:
            sql += " AND laps.track = ?"
            params.append(track)
        if class_name:
            sql += " AND laps.class_name = ?"
            params.append(class_name.strip().upper())
        if class_pi:
            sql += " AND (laps.class_name || ' ' || laps.car_pi) = ?"
            params.append(class_pi)
        sql += " ORDER BY laps.lap_time_s ASC LIMIT ?"
        params.append(max(1, min(limit, 500)))
        return [self._lap_from_row(r) for r in self._conn.execute(sql, params).fetchall()]

    def leaderboard(
        self,
        *,
        track: str | None = None,
        class_name: str | None = None,
        mode: str | None = BOARD_MODE_DEFAULT,
        window: str = "all",
        limit: int = 100,
    ) -> list[LapRow]:
        """One best Clean lap per player × track × class_name."""
        window_key = normalize_window(window)
        since = window_since_iso(window_key)
        sql = """
            WITH ranked AS (
                SELECT
                    laps.*,
                    devices.display_name,
                    ROW_NUMBER() OVER (
                        PARTITION BY laps.device_id, laps.track, laps.class_name
                        ORDER BY laps.lap_time_s ASC, laps.submitted_at ASC
                    ) AS rn
                FROM laps
                JOIN devices ON devices.id = laps.device_id
                WHERE laps.integrity = 'clean'
        """
        params: list[object] = []
        if since is not None:
            sql += " AND laps.submitted_at >= ?"
            params.append(since)
        if mode and mode != "all":
            sql += " AND laps.mode = ?"
            params.append(mode.strip().lower())
        if track:
            sql += " AND laps.track = ?"
            params.append(track)
        if class_name:
            sql += " AND laps.class_name = ?"
            params.append(class_name.strip().upper())
        sql += """
            )
            SELECT * FROM ranked
            WHERE rn = 1
            ORDER BY lap_time_s ASC
            LIMIT ?
        """
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
            (player.strip(), max(1, min(limit, 500))),
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
        mode: str = "",
    ) -> PresenceRow:
        cleaned_mode = (mode or "").strip()
        if cleaned_mode not in VALID_MODES:
            raise ValueError("mode must be empty or time_attack")
        now = utc_now()
        existing = self._conn.execute(
            "SELECT track, class_pi, car, racing, mode, updated_at FROM presence WHERE device_id = ?",
            (device.id,),
        ).fetchone()
        if existing is not None:
            prev = datetime.fromisoformat(existing["updated_at"].replace("Z", "+00:00"))
            racing_i = 1 if racing else 0
            unchanged = (
                existing["track"] == track.strip()
                and existing["class_pi"] == class_pi.strip()
                and existing["car"] == car.strip()
                and int(existing["racing"]) == racing_i
                and str(existing["mode"] or "") == cleaned_mode
            )
            if unchanged and (now - prev).total_seconds() < PRESENCE_MIN_INTERVAL_S:
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
            INSERT INTO presence (device_id, track, class_pi, car, racing, mode, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(device_id) DO UPDATE SET
                track = excluded.track,
                class_pi = excluded.class_pi,
                car = excluded.car,
                racing = excluded.racing,
                mode = excluded.mode,
                updated_at = excluded.updated_at
            """,
            (
                device.id,
                track.strip(),
                class_pi.strip(),
                car.strip(),
                1 if racing else 0,
                cleaned_mode,
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
            WHERE presence.racing = 1
              AND presence.mode = 'time_attack'
              AND presence.updated_at >= ?
            ORDER BY presence.updated_at DESC
            """,
            (since,),
        ).fetchall()
        return [self._presence_from_row(r) for r in rows]

    @staticmethod
    def _lap_from_row(row: sqlite3.Row) -> LapRow:
        keys = row.keys()
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
            mode=str(row["mode"]) if "mode" in keys else "",
        )

    @staticmethod
    def _presence_from_row(row: sqlite3.Row) -> PresenceRow:
        keys = row.keys()
        return PresenceRow(
            device_id=row["device_id"],
            display_name=row["display_name"],
            track=row["track"],
            class_pi=row["class_pi"],
            car=row["car"],
            racing=bool(row["racing"]),
            updated_at=row["updated_at"],
            mode=str(row["mode"]) if "mode" in keys else "",
        )
