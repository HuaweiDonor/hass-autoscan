import argparse
import logging
import time

import cv2

from app.anpr import NomeroffANPR, load_pipeline
from app.camera import FrameReader
from app.config import load_config, validate_for_production
from app.ha_control import HAControl
from app.live_config import ROI, LiveConfig
from app.mqtt_publisher import MQTTPublisher
from app.roi import crop_roi
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
        cropped = crop_roi(frame, cfg.roi_x_min, cfg.roi_y_min, cfg.roi_x_max, cfg.roi_y_max)
        for detection in anpr.detect(cropped):
            logger.info(
                "[debug] plate=%s confidence=%.2f", detection.text, detection.confidence
            )
            _, encoded = cv2.imencode(".jpg", cropped)
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
    return client


def _connect_mqtt_client(client, cfg) -> None:
    # Connect only after on_connect/message_callback_add are registered
    # (see run()) so HAControl's subscribe-on-connect isn't racing a
    # CONNACK that arrives before it's wired up.
    client.connect(cfg.mqtt_broker_host, cfg.mqtt_broker_port)
    client.loop_start()


def run(config_path: str, snapshots_dir: str, debug: bool = False) -> None:
    cfg = load_config(config_path)

    if debug:
        _run_debug(cfg, snapshots_dir)
        return

    validate_for_production(cfg)

    live_config = LiveConfig(
        rtsp_url=cfg.rtsp_url,
        roi=ROI(cfg.roi_x_min, cfg.roi_y_min, cfg.roi_x_max, cfg.roi_y_max),
    )

    reader = FrameReader(
        capture_factory=lambda: cv2.VideoCapture(live_config.rtsp_url, cv2.CAP_FFMPEG),
        sample_fps=cfg.sample_fps,
    )
    anpr = NomeroffANPR(pipeline_fn=load_pipeline())

    mqtt_client = _build_mqtt_client(cfg)
    publisher = MQTTPublisher(mqtt_client, topic=cfg.mqtt_topic)

    if cfg.ha_discovery_enabled:
        ha_control = HAControl(
            mqtt_client,
            live_config,
            on_rtsp_url_changed=reader.request_reconnect,
            mqtt_client_id=cfg.mqtt_client_id,
            discovery_prefix=cfg.ha_discovery_prefix,
        )
        ha_control.start()

    _connect_mqtt_client(mqtt_client, cfg)

    logger.info("Starting autoscan worker, publishing to %s", cfg.mqtt_topic)
    for frame in reader.frames():
        roi = live_config.roi
        cropped = crop_roi(frame, roi.x_min, roi.y_min, roi.x_max, roi.y_max)
        for detection in anpr.detect(cropped):
            _, encoded = cv2.imencode(".jpg", cropped)
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
