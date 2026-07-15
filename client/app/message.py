import base64
import json
from dataclasses import dataclass

SCHEMA_VERSION = 1

_REQUIRED_FIELDS = ["schema_version", "ts", "plate_raw", "confidence", "snapshot_jpeg_b64"]


class MessageParseError(Exception):
    pass


@dataclass
class DetectionMessage:
    plate_raw: str
    confidence: float
    ts: float
    snapshot_bytes: bytes


def parse_detection_payload(payload: bytes) -> DetectionMessage:
    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise MessageParseError(f"Invalid JSON payload: {exc}") from exc

    missing = [f for f in _REQUIRED_FIELDS if f not in data]
    if missing:
        raise MessageParseError(f"Missing required field(s): {', '.join(missing)}")

    if data["schema_version"] != SCHEMA_VERSION:
        raise MessageParseError(
            f"Unsupported schema_version: {data['schema_version']} "
            f"(expected {SCHEMA_VERSION})"
        )

    try:
        snapshot_bytes = base64.b64decode(data["snapshot_jpeg_b64"], validate=True)
    except (ValueError, TypeError) as exc:
        raise MessageParseError(f"Invalid base64 snapshot: {exc}") from exc

    return DetectionMessage(
        plate_raw=data["plate_raw"],
        confidence=data["confidence"],
        ts=data["ts"],
        snapshot_bytes=snapshot_bytes,
    )
