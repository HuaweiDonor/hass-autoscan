import base64
import json

SCHEMA_VERSION = 1


def build_detection_payload(
    plate_raw: str, confidence: float, ts: float, snapshot_bytes: bytes
) -> bytes:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "ts": ts,
        "plate_raw": plate_raw,
        "confidence": confidence,
        "snapshot_jpeg_b64": base64.b64encode(snapshot_bytes).decode("ascii"),
    }
    return json.dumps(payload).encode("utf-8")
