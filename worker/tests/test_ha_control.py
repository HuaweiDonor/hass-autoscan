import json

import pytest

from app.ha_control import HAControl
from app.live_config import ROI, LiveConfig


class FakeMsg:
    def __init__(self, payload: bytes):
        self.payload = payload


class FakeMQTTClient:
    def __init__(self):
        self.callbacks = {}
        self.subscribed = []
        self.published = []
        self.on_connect = None

    def message_callback_add(self, topic, callback):
        self.callbacks[topic] = callback

    def subscribe(self, topic, qos=0):
        self.subscribed.append(topic)

    def publish(self, topic, payload=None, qos=0, retain=False):
        self.published.append(
            {"topic": topic, "payload": payload, "qos": qos, "retain": retain}
        )

    def simulate_connect(self):
        self.on_connect(self, None, None, 0)

    def simulate_message(self, topic, payload: bytes):
        self.callbacks[topic](self, None, FakeMsg(payload))


def make_control():
    client = FakeMQTTClient()
    live_config = LiveConfig(
        rtsp_url="rtsp://initial", roi=ROI(0.0, 0.0, 1.0, 1.0)
    )
    reconnects = []
    control = HAControl(
        client,
        live_config,
        on_rtsp_url_changed=lambda: reconnects.append(True),
        mqtt_client_id="autoscan-worker-test",
    )
    return client, live_config, reconnects, control


def test_start_registers_callbacks_for_all_command_topics():
    client, _, _, control = make_control()

    control.start()

    assert "autoscan/autoscan-worker-test/rtsp_url/set" in client.callbacks
    assert "autoscan/autoscan-worker-test/roi_x_min/set" in client.callbacks
    assert "autoscan/autoscan-worker-test/roi_y_min/set" in client.callbacks
    assert "autoscan/autoscan-worker-test/roi_x_max/set" in client.callbacks
    assert "autoscan/autoscan-worker-test/roi_y_max/set" in client.callbacks


def test_on_connect_subscribes_to_all_command_topics():
    client, _, _, control = make_control()
    control.start()

    client.simulate_connect()

    assert set(client.subscribed) == {
        "autoscan/autoscan-worker-test/rtsp_url/set",
        "autoscan/autoscan-worker-test/roi_x_min/set",
        "autoscan/autoscan-worker-test/roi_y_min/set",
        "autoscan/autoscan-worker-test/roi_x_max/set",
        "autoscan/autoscan-worker-test/roi_y_max/set",
    }


def test_on_connect_publishes_discovery_and_current_state_retained():
    client, _, _, control = make_control()
    control.start()

    client.simulate_connect()

    discovery_msgs = [
        m for m in client.published if "/config" in m["topic"]
    ]
    state_msgs = [m for m in client.published if "/state" in m["topic"]]

    assert len(discovery_msgs) == 5  # 1 text + 4 number
    assert len(state_msgs) == 5
    assert all(m["retain"] is True for m in discovery_msgs)
    assert all(m["retain"] is True for m in state_msgs)

    rtsp_state = next(
        m
        for m in state_msgs
        if m["topic"] == "autoscan/autoscan-worker-test/rtsp_url/state"
    )
    assert rtsp_state["payload"] == "rtsp://initial"


def test_discovery_payload_for_text_entity_has_expected_fields():
    client, _, _, control = make_control()
    control.start()
    client.simulate_connect()

    payload = json.loads(
        next(
            m["payload"]
            for m in client.published
            if m["topic"]
            == "homeassistant/text/autoscan-worker-test/rtsp_url/config"
        )
    )

    assert payload["unique_id"] == "autoscan-worker-test_rtsp_url"
    assert payload["command_topic"] == "autoscan/autoscan-worker-test/rtsp_url/set"
    assert payload["state_topic"] == "autoscan/autoscan-worker-test/rtsp_url/state"
    assert payload["retain"] is True
    assert payload["device"]["identifiers"] == ["autoscan-worker-test"]


def test_discovery_payload_for_number_entity_has_expected_fields():
    client, _, _, control = make_control()
    control.start()
    client.simulate_connect()

    payload = json.loads(
        next(
            m["payload"]
            for m in client.published
            if m["topic"]
            == "homeassistant/number/autoscan-worker-test/roi_x_min/config"
        )
    )

    assert payload["unique_id"] == "autoscan-worker-test_roi_x_min"
    assert payload["min"] == 0
    assert payload["max"] == 1
    assert payload["step"] == 0.01
    assert payload["retain"] is True


def test_handle_rtsp_url_command_updates_live_config_and_publishes_state_and_reconnects():
    client, live_config, reconnects, control = make_control()
    control.start()
    client.simulate_connect()
    client.published.clear()

    client.simulate_message(
        "autoscan/autoscan-worker-test/rtsp_url/set", b"rtsp://new-camera/stream"
    )

    assert live_config.rtsp_url == "rtsp://new-camera/stream"
    assert reconnects == [True]
    state_msg = next(
        m
        for m in client.published
        if m["topic"] == "autoscan/autoscan-worker-test/rtsp_url/state"
    )
    assert state_msg["payload"] == "rtsp://new-camera/stream"
    assert state_msg["retain"] is True


def test_handle_roi_command_updates_only_that_field_and_does_not_reconnect():
    client, live_config, reconnects, control = make_control()
    control.start()
    client.simulate_connect()
    client.published.clear()

    client.simulate_message(
        "autoscan/autoscan-worker-test/roi_x_min/set", b"0.35"
    )

    assert live_config.roi == ROI(x_min=0.35, y_min=0.0, x_max=1.0, y_max=1.0)
    assert reconnects == []  # ROI changes don't need a camera reconnect
    state_msg = next(
        m
        for m in client.published
        if m["topic"] == "autoscan/autoscan-worker-test/roi_x_min/state"
    )
    assert state_msg["payload"] == "0.35"
