import pytest

from app.config import ConfigError, load_config, validate_for_production

FULL_YAML = """
rtsp_url: rtsp://camera.local/stream
sample_fps: 5
mqtt_broker_host: mqtt.local
mqtt_broker_port: 8883
mqtt_username: worker-user
mqtt_password: worker-pass
mqtt_topic: autoscan/plates/detections
mqtt_client_id: autoscan-worker
"""


def test_loads_with_only_rtsp_url_for_debug_mode(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("rtsp_url: rtsp://camera.local/stream\n")

    cfg = load_config(str(path))

    assert cfg.rtsp_url == "rtsp://camera.local/stream"
    assert cfg.mqtt_broker_host is None
    assert cfg.mqtt_username is None
    assert cfg.mqtt_password is None


def test_applies_defaults_when_optional_fields_omitted(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("rtsp_url: rtsp://camera.local/stream\n")

    cfg = load_config(str(path))

    assert cfg.sample_fps == 3
    assert cfg.mqtt_broker_port == 1883
    assert cfg.mqtt_topic == "autoscan/plates/detections"
    assert cfg.mqtt_client_id == "autoscan-worker"


def test_loads_full_config(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(FULL_YAML)

    cfg = load_config(str(path))

    assert cfg.rtsp_url == "rtsp://camera.local/stream"
    assert cfg.sample_fps == 5
    assert cfg.mqtt_broker_host == "mqtt.local"
    assert cfg.mqtt_broker_port == 8883
    assert cfg.mqtt_username == "worker-user"
    assert cfg.mqtt_password == "worker-pass"
    assert cfg.mqtt_topic == "autoscan/plates/detections"
    assert cfg.mqtt_client_id == "autoscan-worker"


def test_raises_clear_error_when_rtsp_url_missing(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("sample_fps: 5\n")

    with pytest.raises(ConfigError, match="rtsp_url"):
        load_config(str(path))


def test_validate_for_production_passes_when_mqtt_broker_host_present(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(FULL_YAML)
    cfg = load_config(str(path))

    validate_for_production(cfg)  # should not raise


def test_validate_for_production_raises_when_mqtt_broker_host_missing(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("rtsp_url: rtsp://camera.local/stream\n")
    cfg = load_config(str(path))

    with pytest.raises(ConfigError, match="mqtt_broker_host"):
        validate_for_production(cfg)
