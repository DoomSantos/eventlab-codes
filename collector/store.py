"""SQLite storage for submitted laps."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parent / "laps.db"


@dataclass(frozen=True, slots=True)
class LapRecord:
    id: int
    track: str
    player_name: str
    lap_time_s: float
    class_name: str
    car_pi: int
    car_ordinal: int
    created_at: str
    suspect_rewind: int = 0
    stream_gaps: int = 0

    @property
    def class_pi_label(self) -> str:
        return f"{self.class_name} {self.car_pi}"

    @property
    def integrity_label(self) -> str:
        return "Suspect" if self.suspect_rewind else "Clean"


class LapStore:
    def __init__(self, db_path: Path | str = DEFAULT_DB) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._migrate()

    def _migrate(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS laps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track TEXT NOT NULL,
                player_name TEXT NOT NULL,
                lap_time_s REAL NOT NULL,
                class_name TEXT NOT NULL,
                car_pi INTEGER NOT NULL,
                car_ordinal INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                suspect_rewind INTEGER NOT NULL DEFAULT 0,
                stream_gaps INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        cols = {
            row["name"]
            for row in self._conn.execute("PRAGMA table_info(laps)").fetchall()
        }
        if "suspect_rewind" not in cols:
            self._conn.execute(
                "ALTER TABLE laps ADD COLUMN suspect_rewind INTEGER NOT NULL DEFAULT 0"
            )
        if "stream_gaps" not in cols:
            self._conn.execute(
                "ALTER TABLE laps ADD COLUMN stream_gaps INTEGER NOT NULL DEFAULT 0"
            )
        self._conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS laps_best_bucket
            ON laps (track, player_name, class_name, car_pi)
            """
        )
        self._conn.commit()

    def upsert_best(
        self,
        *,
        track: str,
        player_name: str,
        lap_time_s: float,
        class_name: str,
        car_pi: int,
        car_ordinal: int,
        suspect_rewind: bool = False,
        stream_gaps: int = 0,
    ) -> tuple[LapRecord, bool]:
        """Insert or replace if this lap is faster for the same bucket.

        Returns (record, improved).
        """
        existing = self._conn.execute(
            """
            SELECT * FROM laps
            WHERE track = ? AND player_name = ? AND class_name = ? AND car_pi = ?
            """,
            (track, player_name, class_name, car_pi),
        ).fetchone()

        now = datetime.now(timezone.utc).isoformat()
        suspect_i = 1 if suspect_rewind else 0

        if existing and float(existing["lap_time_s"]) <= lap_time_s:
            return self._row_to_record(existing), False

        if existing:
            self._conn.execute(
                """
                UPDATE laps
                SET lap_time_s = ?, car_ordinal = ?, created_at = ?,
                    suspect_rewind = ?, stream_gaps = ?
                WHERE id = ?
                """,
                (
                    lap_time_s,
                    car_ordinal,
                    now,
                    suspect_i,
                    stream_gaps,
                    existing["id"],
                ),
            )
            row_id = int(existing["id"])
        else:
            cur = self._conn.execute(
                """
                INSERT INTO laps (
                    track, player_name, lap_time_s, class_name, car_pi, car_ordinal,
                    created_at, suspect_rewind, stream_gaps
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    track,
                    player_name,
                    lap_time_s,
                    class_name,
                    car_pi,
                    car_ordinal,
                    now,
                    suspect_i,
                    stream_gaps,
                ),
            )
            row_id = int(cur.lastrowid)

        self._conn.commit()
        row = self._conn.execute("SELECT * FROM laps WHERE id = ?", (row_id,)).fetchone()
        return self._row_to_record(row), True

    def _row_to_record(self, row: sqlite3.Row) -> LapRecord:
        data = dict(row)
        data.setdefault("suspect_rewind", 0)
        data.setdefault("stream_gaps", 0)
        return LapRecord(**data)

    def all_laps(self) -> list[LapRecord]:
        rows = self._conn.execute(
            """
            SELECT * FROM laps
            ORDER BY track ASC, class_name ASC, car_pi ASC, lap_time_s ASC
            """
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def close(self) -> None:
        self._conn.close()
