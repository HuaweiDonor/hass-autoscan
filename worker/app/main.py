import argparse
import logging
import time

import cv2

from app.anpr import NomeroffANPR, load_pipeline
from app.camera import FrameReader
from app.config import load_config, validate_for_production
from app.mqtt_publisher import MQTTPublisher
from app.snapshot import write_snapshot

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _run_debug(cfg, snapshots_dir: str) -> None:
    anpr = NomeroffANPR(pipeline_fn=load_pipeline())
    reader = FrameReader(
        capture_factory=lambda: cv2.VideoCapture(cfg.rtsp_url, cv2.CAP_FFMPEG),
        sample_fps=cfg.sample_fps,
    )

    logger.info("Starting autoscan worker in debug mode (RTSP + ANPR only, no MQTT)")
    for frame in reader.frames():
        for detection in anpr.detect(frame):
            logger.info(
                "[debug] plate=%s confidence=%.2f", detection.text, detection.confidence
            )
            _, encoded = cv2.imencode(".jpg", frame)
            write_snapshot(snapshots_dir, detection.text, encoded.tobytes())


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
    client.loop_start()
    return client


def run(config_path: str, snapshots_dir: str, debug: bool = False) -> None:
    cfg = load_config(config_path)

    if debug:
        _run_debug(cfg, snapshots_dir)
        return

    validate_for_production(cfg)

    mqtt_client = _build_mqtt_client(cfg)
    publisher = MQTTPublisher(mqtt_client, topic=cfg.mqtt_topic)
    anpr = NomeroffANPR(pipeline_fn=load_pipeline())
    reader = FrameReader(
        capture_factory=lambda: cv2.VideoCapture(cfg.rtsp_url, cv2.CAP_FFMPEG),
        sample_fps=cfg.sample_fps,
    )

    logger.info("Starting autoscan worker, publishing to %s", cfg.mqtt_topic)
    for frame in reader.frames():
        for detection in anpr.detect(frame):
            _, encoded = cv2.imencode(".jpg", frame)
            publisher.publish_detection(
                plate_raw=detection.text,
                confidence=detection.confidence,
                ts=time.time(),
                snapshot_bytes=encoded.tobytes(),
            )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--snapshots", default="data/snapshots")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Only analyze the RTSP stream and log detected plates locally; no MQTT publish.",
    )
    args = parser.parse_args()
    run(args.config, args.snapshots, debug=args.debug)


if __name__ == "__main__":
    main()
