from dataclasses import dataclass, field

import yaml

_REQUIRED_FIELDS = ["rtsp_url"]

_PRODUCTION_REQUIRED_FIELDS = [
    "ha_url",
    "ha_token",
    "ha_domain",
    "ha_service",
    "ha_entity_id",
]

_DEFAULTS = {
    "ha_url": None,
    "ha_token": None,
    "ha_domain": None,
    "ha_service": None,
    "ha_entity_id": None,
    "cooldown_seconds": 60,
    "confidence_threshold": 0.85,
    "sample_fps": 3,
    "dry_run": True,
}


class ConfigError(Exception):
    pass


@dataclass
class Config:
    rtsp_url: str
    ha_url: str
    ha_token: str
    ha_domain: str
    ha_service: str
    ha_entity_id: str
    cooldown_seconds: float
    confidence_threshold: float
    sample_fps: float
    dry_run: bool
    allowed_plates: list = field(default_factory=list)


def load_config(path: str) -> Config:
    with open(path) as f:
        raw = yaml.safe_load(f) or {}

    for field_name in _REQUIRED_FIELDS:
        if field_name not in raw:
            raise ConfigError(f"Missing required config field: {field_name}")

    merged = {**_DEFAULTS, **raw}
    merged.setdefault("allowed_plates", [])
    return Config(**{f: merged[f] for f in Config.__dataclass_fields__})


def validate_for_production(cfg: Config) -> None:
    missing = [f for f in _PRODUCTION_REQUIRED_FIELDS if not getattr(cfg, f)]
    if not cfg.allowed_plates:
        missing.append("allowed_plates")
    if missing:
        raise ConfigError(
            "Missing required config fields for non-debug mode: "
            + ", ".join(missing)
        )
