from app.message import build_detection_payload


class MQTTPublisher:
    """`client` is injected (duck-typed like paho.mqtt.client.Client) so
    this is testable with a fake that just records publish() calls, no
    real broker needed.
    """

    def __init__(self, client, topic: str, qos: int = 1, retain: bool = False):
        self._client = client
        self._topic = topic
        self._qos = qos
        self._retain = retain

    def publish_detection(
        self, plate_raw: str, confidence: float, ts: float, snapshot_bytes: bytes
    ) -> None:
        payload = build_detection_payload(plate_raw, confidence, ts, snapshot_bytes)
        self._client.publish(
            self._topic, payload, qos=self._qos, retain=self._retain
        )
