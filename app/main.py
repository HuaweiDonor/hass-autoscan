import argparse
import logging

import cv2

from app.anpr import NomeroffANPR, load_pipeline
from app.camera import FrameReader
from app.config import load_config, validate_for_production
from app.cooldown import CooldownManager
from app.eventlog import EventLogger, write_snapshot
from app.ha_client import HAClient
from app.normalize import normalize_plate
from app.whitelist import Whitelist

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _run_debug(cfg, snapshots_dir: str) -> None:
    anpr = NomeroffANPR(pipeline_fn=load_pipeline())
    reader = FrameReader(
        capture_factory=lambda: cv2.VideoCapture(cfg.rtsp_url, cv2.CAP_FFMPEG),
        sample_fps=cfg.sample_fps,
    )

    logger.info("Starting autoscan in debug mode (RTSP + ANPR only, no HA calls)")
    for frame in reader.frames():
        for detection in anpr.detect(frame):
            plate_normalized = normalize_plate(detection.text)
            logger.info(
                "[debug] plate=%s confidence=%.2f", plate_normalized, detection.confidence
            )
            _, encoded = cv2.imencode(".jpg", frame)
            write_snapshot(snapshots_dir, plate_normalized, encoded.tobytes())


def run(config_path: str, db_path: str, snapshots_dir: str, debug: bool = False) -> None:
    cfg = load_config(config_path)

    if debug:
        _run_debug(cfg, snapshots_dir)
        return

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
    anpr = NomeroffANPR(pipeline_fn=load_pipeline())
    reader = FrameReader(
        capture_factory=lambda: cv2.VideoCapture(cfg.rtsp_url, cv2.CAP_FFMPEG),
        sample_fps=cfg.sample_fps,
    )

    logger.info("Starting autoscan (dry_run=%s)", cfg.dry_run)
    for frame in reader.frames():
        for detection in anpr.detect(frame):
            plate_normalized = normalize_plate(detection.text)
            matched = detection.confidence >= cfg.confidence_threshold and (
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

            _, encoded = cv2.imencode(".jpg", frame)
            event_logger.log_event(
                plate_raw=detection.text,
                plate_normalized=plate_normalized,
                confidence=detection.confidence,
                matched=matched,
                snapshot_bytes=encoded.tobytes(),
                ha_call_result=ha_call_result,
            )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--db", default="data/events.sqlite3")
    parser.add_argument("--snapshots", default="data/snapshots")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Only analyze the RTSP stream and log detected plates; no whitelist/cooldown/HA calls.",
    )
    args = parser.parse_args()
    run(args.config, args.db, args.snapshots, debug=args.debug)


if __name__ == "__main__":
    main()
