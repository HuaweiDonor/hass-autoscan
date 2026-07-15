import json

from app.mqtt_publisher import MQTTPublisher


class FakeMQTTClient:
    def __init__(self):
        self.published = []

    def publish(self, topic, payload, qos, retain):
        self.published.append(
            {"topic": topic, "payload": payload, "qos": qos, "retain": retain}
        )


def test_publish_detection_sends_to_configured_topic():
    client = FakeMQTTClient()
    publisher = MQTTPublisher(client, topic="autoscan/plates/detections")

    publisher.publish_detection(
        plate_raw="A123BC777", confidence=0.9, ts=1.0, snapshot_bytes=b"jpeg"
    )

    assert len(client.published) == 1
    assert client.published[0]["topic"] == "autoscan/plates/detections"


def test_publish_detection_uses_qos_1_and_retain_false_by_default():
    client = FakeMQTTClient()
    publisher = MQTTPublisher(client, topic="t")

    publisher.publish_detection(
        plate_raw="A123BC777", confidence=0.9, ts=1.0, snapshot_bytes=b"jpeg"
    )

    assert client.published[0]["qos"] == 1
    assert client.published[0]["retain"] is False


def test_publish_detection_payload_matches_build_detection_payload():
    client = FakeMQTTClient()
    publisher = MQTTPublisher(client, topic="t")

    publisher.publish_detection(
        plate_raw="A123BC777", confidence=0.9, ts=1.0, snapshot_bytes=b"jpeg"
    )

    decoded = json.loads(client.published[0]["payload"])
    assert decoded["plate_raw"] == "A123BC777"
    assert decoded["confidence"] == 0.9
    assert decoded["ts"] == 1.0


def test_publish_detection_respects_custom_qos_and_retain():
    client = FakeMQTTClient()
    publisher = MQTTPublisher(client, topic="t", qos=0, retain=True)

    publisher.publish_detection(
        plate_raw="A123BC777", confidence=0.9, ts=1.0, snapshot_bytes=b"jpeg"
    )

    assert client.published[0]["qos"] == 0
    assert client.published[0]["retain"] is True
