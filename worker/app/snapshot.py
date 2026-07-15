import os
import time
import uuid


def write_snapshot(snapshots_dir: str, plate_text: str, snapshot_bytes: bytes) -> str:
    os.makedirs(snapshots_dir, exist_ok=True)
    filename = f"{time.time():.6f}_{plate_text}_{uuid.uuid4().hex[:8]}.jpg"
    path = os.path.join(snapshots_dir, filename)
    with open(path, "wb") as f:
        f.write(snapshot_bytes)
    return path
