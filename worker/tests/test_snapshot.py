from app.snapshot import write_snapshot


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
