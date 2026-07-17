import json
from datetime import datetime, timezone


class HADiscovery:
    """Publishes the last plate detection (time, plate, snapshot) as Home
    Assistant MQTT Discovery entities (2 sensors + 1 camera), so the last
    scan is visible in the HA UI without reading client logs/sqlite.

    Unlike worker's HAControl, these entities have no command_topic -
    they're read-only, so there's nothing to subscribe to; call
    publish_discovery() from the MQTT client's on_connect (it must be
    republished on every reconnect since the broker may not have retained
    it, e.g. after a broker restart) and publish_detection() per event.
    """

    def __init__(
        self,
        client,
        mqtt_client_id: str,
        discovery_prefix: str = "homeassistant",
        device_name: str = "Autoscan Client",
    ):
        self._client = client
        self._mqtt_client_id = mqtt_client_id
        self._discovery_prefix = discovery_prefix
        self._device_name = device_name
        self._base = f"autoscan/{mqtt_client_id}"

    def _plate_state_topic(self) -> str:
        return f"{self._base}/last_plate/state"

    def _plate_attributes_topic(self) -> str:
        return f"{self._base}/last_plate/attributes"

    def _detection_time_state_topic(self) -> str:
        return f"{self._base}/last_detection_time/state"

    def _snapshot_topic(self) -> str:
        return f"{self._base}/last_snapshot"

    def _device(self) -> dict:
        return {"identifiers": [self._mqtt_client_id], "name": self._device_name}

    def publish_discovery(self) -> None:
        plate_payload = {
            "name": "Last Scanned Plate",
            "unique_id": f"{self._mqtt_client_id}_last_plate",
            "state_topic": self._plate_state_topic(),
            "json_attributes_topic": self._plate_attributes_topic(),
            "device": self._device(),
        }
        self._client.publish(
            f"{self._discovery_prefix}/sensor/{self._mqtt_client_id}/last_plate/config",
            json.dumps(plate_payload),
            qos=1,
            retain=True,
        )

        time_payload = {
            "name": "Last Detection Time",
            "unique_id": f"{self._mqtt_client_id}_last_detection_time",
            "state_topic": self._detection_time_state_topic(),
            "device_class": "timestamp",
            "device": self._device(),
        }
        self._client.publish(
            f"{self._discovery_prefix}/sensor/{self._mqtt_client_id}/last_detection_time/config",
            json.dumps(time_payload),
            qos=1,
            retain=True,
        )

        camera_payload = {
            "name": "Last Plate Snapshot",
            "unique_id": f"{self._mqtt_client_id}_last_snapshot",
            "topic": self._snapshot_topic(),
            "device": self._device(),
        }
        self._client.publish(
            f"{self._discovery_prefix}/camera/{self._mqtt_client_id}/last_snapshot/config",
            json.dumps(camera_payload),
            qos=1,
            retain=True,
        )

    def publish_detection(
        self,
        ts: float,
        plate_raw: str,
        plate_normalized: str,
        confidence: float,
        matched: bool,
        snapshot_bytes: bytes,
    ) -> None:
        iso_ts = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()

        self._client.publish(
            self._detection_time_state_topic(), iso_ts, qos=1, retain=True
        )
        self._client.publish(
            self._plate_state_topic(), plate_normalized, qos=1, retain=True
        )
        self._client.publish(
            self._plate_attributes_topic(),
            json.dumps(
                {
                    "plate_raw": plate_raw,
                    "confidence": confidence,
                    "matched": matched,
                }
            ),
            qos=1,
            retain=True,
        )
        self._client.publish(
            self._snapshot_topic(), snapshot_bytes, qos=1, retain=True
        )
