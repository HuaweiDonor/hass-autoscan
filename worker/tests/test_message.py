import base64
import json

from app.message import build_detection_payload


def test_builds_json_payload_with_expected_keys():
    payload = build_detection_payload(
        plate_raw="А123ВС777",
        confidence=0.93,
        ts=1752500000.123456,
        snapshot_bytes=b"fake-jpeg-bytes",
    )

    decoded = json.loads(payload)

    assert decoded["schema_version"] == 1
    assert decoded["ts"] == 1752500000.123456
    assert decoded["plate_raw"] == "А123ВС777"
    assert decoded["confidence"] == 0.93
    assert decoded["snapshot_jpeg_b64"] == base64.b64encode(b"fake-jpeg-bytes").decode(
        "ascii"
    )


def test_payload_is_bytes():
    payload = build_detection_payload(
        plate_raw="A123BC777", confidence=0.9, ts=1.0, snapshot_bytes=b"x"
    )

    assert isinstance(payload, bytes)


def test_snapshot_bytes_round_trip_through_base64():
    original = bytes(range(256))  # exercise all byte values, not just ascii-ish jpeg
    payload = build_detection_payload(
        plate_raw="A123BC777", confidence=0.9, ts=1.0, snapshot_bytes=original
    )

    decoded = json.loads(payload)
    assert base64.b64decode(decoded["snapshot_jpeg_b64"]) == original
