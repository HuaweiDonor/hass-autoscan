import pytest

from app.config import ConfigError, load_config, validate_for_production

REQUIRED_YAML = """
rtsp_url: rtsp://camera.local/stream
ha_url: http://homeassistant.local:8123
ha_token: secret-token
ha_domain: switch
ha_service: turn_on
ha_entity_id: switch.gate_relay
allowed_plates:
  - A123BC777
"""


def test_loads_required_fields(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(REQUIRED_YAML)

    cfg = load_config(str(path))

    assert cfg.rtsp_url == "rtsp://camera.local/stream"
    assert cfg.ha_url == "http://homeassistant.local:8123"
    assert cfg.ha_token == "secret-token"
    assert cfg.ha_domain == "switch"
    assert cfg.ha_service == "turn_on"
    assert cfg.ha_entity_id == "switch.gate_relay"
    assert cfg.allowed_plates == ["A123BC777"]


def test_applies_defaults_when_optional_fields_omitted(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(REQUIRED_YAML)

    cfg = load_config(str(path))

    assert cfg.cooldown_seconds == 60
    assert cfg.confidence_threshold == 0.85
    assert cfg.sample_fps == 3
    assert cfg.dry_run is True


def test_optional_fields_can_be_overridden(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(
        REQUIRED_YAML
        + """
cooldown_seconds: 30
confidence_threshold: 0.9
sample_fps: 5
dry_run: false
"""
    )

    cfg = load_config(str(path))

    assert cfg.cooldown_seconds == 30
    assert cfg.confidence_threshold == 0.9
    assert cfg.sample_fps == 5
    assert cfg.dry_run is False


def test_raises_clear_error_when_rtsp_url_missing(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("cooldown_seconds: 30\n")

    with pytest.raises(ConfigError, match="rtsp_url"):
        load_config(str(path))


def test_loads_with_only_rtsp_url_for_debug_mode(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("rtsp_url: rtsp://camera.local/stream\n")

    cfg = load_config(str(path))

    assert cfg.rtsp_url == "rtsp://camera.local/stream"
    assert cfg.ha_url is None
    assert cfg.ha_token is None
    assert cfg.ha_domain is None
    assert cfg.ha_service is None
    assert cfg.ha_entity_id is None
    assert cfg.allowed_plates == []


def test_validate_for_production_passes_when_all_fields_present(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(REQUIRED_YAML)
    cfg = load_config(str(path))

    validate_for_production(cfg)  # should not raise


def test_validate_for_production_raises_listing_missing_fields(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("rtsp_url: rtsp://camera.local/stream\n")
    cfg = load_config(str(path))

    with pytest.raises(ConfigError, match="ha_url"):
        validate_for_production(cfg)
