from dataclasses import dataclass

import yaml

_REQUIRED_FIELDS = ["rtsp_url"]

_PRODUCTION_REQUIRED_FIELDS = ["mqtt_broker_host"]

_DEFAULTS = {
    "sample_fps": 3,
    "mqtt_broker_host": None,
    "mqtt_broker_port": 1883,
    "mqtt_username": None,
    "mqtt_password": None,
    "mqtt_topic": "autoscan/plates/detections",
    "mqtt_client_id": "autoscan-worker",
    "roi_x_min": 0.0,
    "roi_y_min": 0.0,
    "roi_x_max": 1.0,
    "roi_y_max": 1.0,
    "ha_discovery_enabled": True,
    "ha_discovery_prefix": "homeassistant",
}


class ConfigError(Exception):
    pass


@dataclass
class Config:
    rtsp_url: str
    sample_fps: float
    mqtt_broker_host: str
    mqtt_broker_port: int
    mqtt_username: str
    mqtt_password: str
    mqtt_topic: str
    mqtt_client_id: str
    roi_x_min: float
    roi_y_min: float
    roi_x_max: float
    roi_y_max: float
    ha_discovery_enabled: bool
    ha_discovery_prefix: str


def load_config(path: str) -> Config:
    with open(path) as f:
        raw = yaml.safe_load(f) or {}

    for field_name in _REQUIRED_FIELDS:
        if field_name not in raw:
            raise ConfigError(f"Missing required config field: {field_name}")

    merged = {**_DEFAULTS, **raw}
    return Config(**{f: merged[f] for f in Config.__dataclass_fields__})


def validate_for_production(cfg: Config) -> None:
    missing = [f for f in _PRODUCTION_REQUIRED_FIELDS if not getattr(cfg, f)]
    if missing:
        raise ConfigError(
            "Missing required config fields for non-debug mode: "
            + ", ".join(missing)
        )
