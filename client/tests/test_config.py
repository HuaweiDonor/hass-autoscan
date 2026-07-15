import pytest

from app.config import ConfigError, load_config, validate_for_production

FULL_YAML = """
mqtt_broker_host: mqtt.local
mqtt_broker_port: 8883
mqtt_username: client-user
mqtt_password: client-pass
mqtt_topic: autoscan/plates/detections
mqtt_client_id: autoscan-client
ha_url: http://homeassistant.local:8123
ha_token: secret-token
ha_domain: switch
ha_service: turn_on
ha_entity_id: switch.gate_relay
allowed_plates:
  - A123BC777
"""


def test_loads_full_config(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(FULL_YAML)

    cfg = load_config(str(path))

    assert cfg.mqtt_broker_host == "mqtt.local"
    assert cfg.mqtt_broker_port == 8883
    assert cfg.mqtt_username == "client-user"
    assert cfg.mqtt_password == "client-pass"
    assert cfg.mqtt_topic == "autoscan/plates/detections"
    assert cfg.mqtt_client_id == "autoscan-client"
    assert cfg.ha_url == "http://homeassistant.local:8123"
    assert cfg.ha_token == "secret-token"
    assert cfg.ha_domain == "switch"
    assert cfg.ha_service == "turn_on"
    assert cfg.ha_entity_id == "switch.gate_relay"
    assert cfg.allowed_plates == ["A123BC777"]


def test_applies_defaults_when_optional_fields_omitted(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("mqtt_broker_host: mqtt.local\n")

    cfg = load_config(str(path))

    assert cfg.mqtt_broker_port == 1883
    assert cfg.mqtt_topic == "autoscan/plates/detections"
    assert cfg.mqtt_client_id == "autoscan-client"
    assert cfg.cooldown_seconds == 60
    assert cfg.confidence_threshold == 0.85
    assert cfg.dry_run is True
    assert cfg.allowed_plates == []
    assert cfg.ha_url is None


def test_raises_clear_error_when_mqtt_broker_host_missing(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("cooldown_seconds: 30\n")

    with pytest.raises(ConfigError, match="mqtt_broker_host"):
        load_config(str(path))


def test_validate_for_production_passes_when_all_fields_present(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(FULL_YAML)
    cfg = load_config(str(path))

    validate_for_production(cfg)  # should not raise


def test_validate_for_production_raises_listing_missing_fields(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("mqtt_broker_host: mqtt.local\n")
    cfg = load_config(str(path))

    with pytest.raises(ConfigError, match="ha_url"):
        validate_for_production(cfg)
