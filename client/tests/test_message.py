import base64
import json

import pytest

from app.message import MessageParseError, parse_detection_payload


def _valid_payload(**overrides):
    payload = {
        "schema_version": 1,
        "ts": 1752500000.123456,
        "plate_raw": "А123ВС777",
        "confidence": 0.93,
        "snapshot_jpeg_b64": base64.b64encode(b"fake-jpeg-bytes").decode("ascii"),
    }
    payload.update(overrides)
    return json.dumps(payload).encode("utf-8")


def test_parses_valid_payload():
    msg = parse_detection_payload(_valid_payload())

    assert msg.plate_raw == "А123ВС777"
    assert msg.confidence == 0.93
    assert msg.ts == 1752500000.123456
    assert msg.snapshot_bytes == b"fake-jpeg-bytes"


def test_raises_on_invalid_json():
    with pytest.raises(MessageParseError):
        parse_detection_payload(b"not json")


def test_raises_on_missing_schema_version():
    payload = json.loads(_valid_payload())
    del payload["schema_version"]

    with pytest.raises(MessageParseError, match="schema_version"):
        parse_detection_payload(json.dumps(payload).encode("utf-8"))


def test_raises_on_unsupported_schema_version():
    with pytest.raises(MessageParseError, match="schema_version"):
        parse_detection_payload(_valid_payload(schema_version=99))


def test_raises_on_missing_required_field():
    payload = json.loads(_valid_payload())
    del payload["plate_raw"]

    with pytest.raises(MessageParseError, match="plate_raw"):
        parse_detection_payload(json.dumps(payload).encode("utf-8"))


def test_raises_on_invalid_base64_snapshot():
    with pytest.raises(MessageParseError):
        parse_detection_payload(_valid_payload(snapshot_jpeg_b64="not-valid-base64!!!"))
