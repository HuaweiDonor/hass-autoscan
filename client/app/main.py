import argparse
import logging

from app.config import load_config, validate_for_production
from app.cooldown import CooldownManager
from app.eventlog import EventLogger
from app.ha_client import HAClient
from app.message import MessageParseError, parse_detection_payload
from app.mqtt_subscriber import MQTTSubscriber
from app.normalize import normalize_plate
from app.whitelist import Whitelist

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _build_mqtt_client(cfg):
    import paho.mqtt.client as mqtt

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=cfg.mqtt_client_id,
        clean_session=False,
    )
    if cfg.mqtt_username:
        client.username_pw_set(cfg.mqtt_username, cfg.mqtt_password)
    client.connect(cfg.mqtt_broker_host, cfg.mqtt_broker_port)
    return client


def run(config_path: str, db_path: str, snapshots_dir: str) -> None:
    cfg = load_config(config_path)
    validate_for_production(cfg)

    whitelist = Whitelist(cfg.allowed_plates)
    cooldown = CooldownManager(cooldown_seconds=cfg.cooldown_seconds)
    ha_client = HAClient(
        base_url=cfg.ha_url,
        token=cfg.ha_token,
        domain=cfg.ha_domain,
        service=cfg.ha_service,
        entity_id=cfg.ha_entity_id,
    )
    event_logger = EventLogger(db_path=db_path, snapshots_dir=snapshots_dir)

    def handle_message(payload: bytes) -> None:
        try:
            msg = parse_detection_payload(payload)
        except MessageParseError as exc:
            logger.warning("Dropping invalid detection message: %s", exc)
            return

        plate_normalized = normalize_plate(msg.plate_raw)
        matched = msg.confidence >= cfg.confidence_threshold and (
            whitelist.is_allowed(plate_normalized)
        )

        ha_call_result = None
        if matched and cooldown.should_trigger(plate_normalized):
            if cfg.dry_run:
                logger.info("[dry_run] would open gate for %s", plate_normalized)
            else:
                ha_call_result = ha_client.call_gate()
                logger.info(
                    "Opened gate for %s (ha_call_result=%s)",
                    plate_normalized,
                    ha_call_result,
                )

        event_logger.log_event(
            plate_raw=msg.plate_raw,
            plate_normalized=plate_normalized,
            confidence=msg.confidence,
            matched=matched,
            snapshot_bytes=msg.snapshot_bytes,
            ha_call_result=ha_call_result,
        )

    mqtt_client = _build_mqtt_client(cfg)
    subscriber = MQTTSubscriber(mqtt_client, topic=cfg.mqtt_topic)

    logger.info("Starting autoscan client (dry_run=%s)", cfg.dry_run)
    subscriber.run_forever(handle_message)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--db", default="data/events.sqlite3")
    parser.add_argument("--snapshots", default="data/snapshots")
    args = parser.parse_args()
    run(args.config, args.db, args.snapshots)


if __name__ == "__main__":
    main()
