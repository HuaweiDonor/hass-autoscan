import json
from typing import Callable

_ROI_FIELDS = ["x_min", "y_min", "x_max", "y_max"]


class HAControl:
    """Exposes rtsp_url and the ROI as Home Assistant MQTT Discovery
    entities (1 `text` + 4 `number`), so they can be changed live from the
    HA UI. Command topics are published by HA with `retain: true`, so a
    fresh subscribe (e.g. after this worker restarts) immediately receives
    the last value HA had set, without needing separate local storage.
    """

    def __init__(
        self,
        client,
        live_config,
        on_rtsp_url_changed: Callable[[], None],
        mqtt_client_id: str,
        discovery_prefix: str = "homeassistant",
        device_name: str = "Autoscan Worker",
    ):
        self._client = client
        self._live_config = live_config
        self._on_rtsp_url_changed = on_rtsp_url_changed
        self._mqtt_client_id = mqtt_client_id
        self._discovery_prefix = discovery_prefix
        self._device_name = device_name
        self._base = f"autoscan/{mqtt_client_id}"

    def _rtsp_url_command_topic(self) -> str:
        return f"{self._base}/rtsp_url/set"

    def _rtsp_url_state_topic(self) -> str:
        return f"{self._base}/rtsp_url/state"

    def _roi_command_topic(self, field: str) -> str:
        return f"{self._base}/roi_{field}/set"

    def _roi_state_topic(self, field: str) -> str:
        return f"{self._base}/roi_{field}/state"

    def start(self) -> None:
        self._client.message_callback_add(
            self._rtsp_url_command_topic(), self._handle_rtsp_url
        )
        for roi_field in _ROI_FIELDS:
            self._client.message_callback_add(
                self._roi_command_topic(roi_field), self._make_roi_handler(roi_field)
            )
        self._client.on_connect = self._on_connect

    def _on_connect(self, client, userdata, flags, rc, properties=None) -> None:
        client.subscribe(self._rtsp_url_command_topic())
        for roi_field in _ROI_FIELDS:
            client.subscribe(self._roi_command_topic(roi_field))
        self._publish_discovery()
        self._publish_current_state()

    def _device(self) -> dict:
        return {"identifiers": [self._mqtt_client_id], "name": self._device_name}

    def _publish_discovery(self) -> None:
        text_payload = {
            "name": "RTSP URL",
            "unique_id": f"{self._mqtt_client_id}_rtsp_url",
            "command_topic": self._rtsp_url_command_topic(),
            "state_topic": self._rtsp_url_state_topic(),
            "retain": True,
            "device": self._device(),
        }
        self._client.publish(
            f"{self._discovery_prefix}/text/{self._mqtt_client_id}/rtsp_url/config",
            json.dumps(text_payload),
            qos=1,
            retain=True,
        )

        for roi_field in _ROI_FIELDS:
            number_payload = {
                "name": f"ROI {roi_field}",
                "unique_id": f"{self._mqtt_client_id}_roi_{roi_field}",
                "command_topic": self._roi_command_topic(roi_field),
                "state_topic": self._roi_state_topic(roi_field),
                "min": 0,
                "max": 1,
                "step": 0.01,
                "mode": "slider",
                "retain": True,
                "device": self._device(),
            }
            self._client.publish(
                f"{self._discovery_prefix}/number/{self._mqtt_client_id}/roi_{roi_field}/config",
                json.dumps(number_payload),
                qos=1,
                retain=True,
            )

    def _publish_current_state(self) -> None:
        self._client.publish(
            self._rtsp_url_state_topic(),
            self._live_config.rtsp_url,
            qos=1,
            retain=True,
        )
        roi = self._live_config.roi
        for roi_field in _ROI_FIELDS:
            self._client.publish(
                self._roi_state_topic(roi_field),
                str(getattr(roi, roi_field)),
                qos=1,
                retain=True,
            )

    def _handle_rtsp_url(self, client, userdata, msg) -> None:
        url = msg.payload.decode("utf-8")
        self._live_config.set_rtsp_url(url)
        client.publish(self._rtsp_url_state_topic(), url, qos=1, retain=True)
        self._on_rtsp_url_changed()

    def _make_roi_handler(self, field: str):
        def handler(client, userdata, msg) -> None:
            value = float(msg.payload.decode("utf-8"))
            self._live_config.set_roi_field(field, value)
            client.publish(
                self._roi_state_topic(field), str(value), qos=1, retain=True
            )

        return handler
