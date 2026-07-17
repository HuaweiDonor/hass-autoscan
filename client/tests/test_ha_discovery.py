import json

from app.ha_discovery import HADiscovery


class FakeMQTTClient:
    def __init__(self):
        self.published = []

    def publish(self, topic, payload=None, qos=0, retain=False):
        self.published.append(
            {"topic": topic, "payload": payload, "qos": qos, "retain": retain}
        )


def make_discovery():
    client = FakeMQTTClient()
    discovery = HADiscovery(client, mqtt_client_id="autoscan-client-test")
    return client, discovery


def test_publish_discovery_publishes_two_sensors_and_a_camera_retained():
    client, discovery = make_discovery()

    discovery.publish_discovery()

    config_msgs = [m for m in client.published if "/config" in m["topic"]]
    assert len(config_msgs) == 3
    assert all(m["retain"] is True for m in config_msgs)
    topics = {m["topic"] for m in config_msgs}
    assert topics == {
        "homeassistant/sensor/autoscan-client-test/last_plate/config",
        "homeassistant/sensor/autoscan-client-test/last_detection_time/config",
        "homeassistant/camera/autoscan-client-test/last_snapshot/config",
    }


def test_last_plate_discovery_payload_has_expected_fields():
    client, discovery = make_discovery()

    discovery.publish_discovery()

    payload = json.loads(
        next(
            m["payload"]
            for m in client.published
            if m["topic"]
            == "homeassistant/sensor/autoscan-client-test/last_plate/config"
        )
    )
    assert payload["unique_id"] == "autoscan-client-test_last_plate"
    assert payload["state_topic"] == "autoscan/autoscan-client-test/last_plate/state"
    assert (
        payload["json_attributes_topic"]
        == "autoscan/autoscan-client-test/last_plate/attributes"
    )
    assert payload["device"]["identifiers"] == ["autoscan-client-test"]


def test_last_detection_time_discovery_payload_has_timestamp_device_class():
    client, discovery = make_discovery()

    discovery.publish_discovery()

    payload = json.loads(
        next(
            m["payload"]
            for m in client.published
            if m["topic"]
            == "homeassistant/sensor/autoscan-client-test/last_detection_time/config"
        )
    )
    assert payload["device_class"] == "timestamp"
    assert (
        payload["state_topic"]
        == "autoscan/autoscan-client-test/last_detection_time/state"
    )


def test_snapshot_discovery_payload_points_at_snapshot_topic():
    client, discovery = make_discovery()

    discovery.publish_discovery()

    payload = json.loads(
        next(
            m["payload"]
            for m in client.published
            if m["topic"]
            == "homeassistant/camera/autoscan-client-test/last_snapshot/config"
        )
    )
    assert payload["topic"] == "autoscan/autoscan-client-test/last_snapshot"


def test_publish_detection_publishes_state_attributes_and_snapshot_retained():
    client, discovery = make_discovery()

    discovery.publish_detection(
        ts=1721296800.0,
        plate_raw="H491BY135",
        plate_normalized="H491BY125",
        confidence=0.97,
        matched=True,
        snapshot_bytes=b"\xff\xd8fakejpeg",
    )

    by_topic = {m["topic"]: m for m in client.published}

    plate_state = by_topic["autoscan/autoscan-client-test/last_plate/state"]
    assert plate_state["payload"] == "H491BY125"
    assert plate_state["retain"] is True

    time_state = by_topic["autoscan/autoscan-client-test/last_detection_time/state"]
    assert time_state["payload"] == "2024-07-18T10:00:00+00:00"
    assert time_state["retain"] is True

    attrs = json.loads(
        by_topic["autoscan/autoscan-client-test/last_plate/attributes"]["payload"]
    )
    assert attrs == {"plate_raw": "H491BY135", "confidence": 0.97, "matched": True}

    snapshot_msg = by_topic["autoscan/autoscan-client-test/last_snapshot"]
    assert snapshot_msg["payload"] == b"\xff\xd8fakejpeg"
    assert snapshot_msg["retain"] is True
