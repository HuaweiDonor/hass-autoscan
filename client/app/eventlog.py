import os
import sqlite3
import time
import uuid

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    plate_raw TEXT NOT NULL,
    plate_normalized TEXT NOT NULL,
    confidence REAL NOT NULL,
    matched INTEGER NOT NULL,
    snapshot_path TEXT NOT NULL,
    ha_call_result INTEGER
)
"""


def write_snapshot(snapshots_dir: str, plate_normalized: str, snapshot_bytes: bytes) -> str:
    os.makedirs(snapshots_dir, exist_ok=True)
    filename = f"{time.time():.6f}_{plate_normalized}_{uuid.uuid4().hex[:8]}.jpg"
    path = os.path.join(snapshots_dir, filename)
    with open(path, "wb") as f:
        f.write(snapshot_bytes)
    return path


class EventLogger:
    def __init__(self, db_path: str, snapshots_dir: str, clock=time.time):
        self._db_path = db_path
        self._snapshots_dir = snapshots_dir
        self._clock = clock
        os.makedirs(self._snapshots_dir, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(_SCHEMA)

    def log_event(
        self,
        plate_raw: str,
        plate_normalized: str,
        confidence: float,
        matched: bool,
        snapshot_bytes: bytes,
        ha_call_result: bool | None,
    ) -> int:
        ts = self._clock()
        snapshot_path = write_snapshot(
            self._snapshots_dir, plate_normalized, snapshot_bytes
        )

        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO events "
                "(ts, plate_raw, plate_normalized, confidence, matched, "
                "snapshot_path, ha_call_result) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    ts,
                    plate_raw,
                    plate_normalized,
                    confidence,
                    int(matched),
                    snapshot_path,
                    None if ha_call_result is None else int(ha_call_result),
                ),
            )
            return cursor.lastrowid
