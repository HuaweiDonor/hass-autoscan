import sqlite3

from app.eventlog import EventLogger, write_snapshot


def test_creates_db_schema_on_init(tmp_path):
    db_path = tmp_path / "events.sqlite3"
    EventLogger(db_path=str(db_path), snapshots_dir=str(tmp_path / "snapshots"))

    conn = sqlite3.connect(str(db_path))
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert "events" in tables


def test_logs_event_and_persists_row(tmp_path):
    db_path = tmp_path / "events.sqlite3"
    logger = EventLogger(db_path=str(db_path), snapshots_dir=str(tmp_path / "snapshots"))

    event_id = logger.log_event(
        plate_raw="А123ВС777",
        plate_normalized="A123BC777",
        confidence=0.92,
        matched=True,
        snapshot_bytes=b"fake-jpeg-bytes",
        ha_call_result=True,
    )

    conn = sqlite3.connect(str(db_path))
    row = conn.execute(
        "SELECT id, plate_raw, plate_normalized, confidence, matched, "
        "snapshot_path, ha_call_result FROM events WHERE id = ?",
        (event_id,),
    ).fetchone()

    assert row[0] == event_id
    assert row[1] == "А123ВС777"
    assert row[2] == "A123BC777"
    assert row[3] == 0.92
    assert row[4] == 1
    assert row[5]  # snapshot_path is set
    assert row[6] == 1


def test_writes_snapshot_file_to_disk(tmp_path):
    db_path = tmp_path / "events.sqlite3"
    snapshots_dir = tmp_path / "snapshots"
    logger = EventLogger(db_path=str(db_path), snapshots_dir=str(snapshots_dir))

    logger.log_event(
        plate_raw="A123BC777",
        plate_normalized="A123BC777",
        confidence=0.5,
        matched=False,
        snapshot_bytes=b"fake-jpeg-bytes",
        ha_call_result=None,
    )

    saved_files = list(snapshots_dir.glob("*.jpg"))
    assert len(saved_files) == 1
    assert saved_files[0].read_bytes() == b"fake-jpeg-bytes"


def test_logs_unmatched_event_with_null_ha_result(tmp_path):
    db_path = tmp_path / "events.sqlite3"
    logger = EventLogger(db_path=str(db_path), snapshots_dir=str(tmp_path / "snapshots"))

    event_id = logger.log_event(
        plate_raw="Z999ZZ999",
        plate_normalized="Z999ZZ999",
        confidence=0.4,
        matched=False,
        snapshot_bytes=b"fake-jpeg-bytes",
        ha_call_result=None,
    )

    conn = sqlite3.connect(str(db_path))
    row = conn.execute(
        "SELECT matched, ha_call_result FROM events WHERE id = ?", (event_id,)
    ).fetchone()
    assert row[0] == 0
    assert row[1] is None


def test_write_snapshot_creates_dir_and_writes_file(tmp_path):
    snapshots_dir = tmp_path / "snapshots"

    path = write_snapshot(str(snapshots_dir), "A123BC777", b"fake-jpeg-bytes")

    assert snapshots_dir.exists()
    saved = list(snapshots_dir.glob("*.jpg"))
    assert len(saved) == 1
    assert saved[0].read_bytes() == b"fake-jpeg-bytes"
    assert path == str(saved[0])


def test_write_snapshot_filenames_are_unique_per_call(tmp_path):
    snapshots_dir = tmp_path / "snapshots"

    path1 = write_snapshot(str(snapshots_dir), "A123BC777", b"one")
    path2 = write_snapshot(str(snapshots_dir), "A123BC777", b"two")

    assert path1 != path2
    assert len(list(snapshots_dir.glob("*.jpg"))) == 2
