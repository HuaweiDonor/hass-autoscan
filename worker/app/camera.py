import threading
import time
from typing import Callable, Iterator

import cv2


class FrameReader:
    """Pulls frames from an RTSP source, reconnecting on failure.

    `capture_factory` is injected so this is testable without a real
    camera/RTSP stream; production wiring passes
    `lambda: cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)`.
    """

    def __init__(
        self,
        capture_factory: Callable[[], "cv2.VideoCapture"],
        sample_fps: float = 3,
        initial_backoff_seconds: float = 1,
        max_backoff_seconds: float = 30,
        sleep=time.sleep,
    ):
        self._capture_factory = capture_factory
        self._frame_interval = 1 / sample_fps
        self._initial_backoff = initial_backoff_seconds
        self._max_backoff = max_backoff_seconds
        self._sleep = sleep
        self._reconnect_requested = threading.Event()

    def request_reconnect(self) -> None:
        """Force the next loop iteration to drop the current capture and
        reconnect, even if it's still reading successfully. Safe to call
        from another thread (e.g. an MQTT callback delivering a new
        RTSP URL).
        """
        self._reconnect_requested.set()

    def frames(self) -> Iterator:
        backoff = self._initial_backoff
        capture = None
        while True:
            if capture is None:
                capture = self._capture_factory()
                if not capture.isOpened():
                    capture.release()
                    capture = None
                    self._sleep(backoff)
                    backoff = min(backoff * 2, self._max_backoff)
                    continue

            if self._reconnect_requested.is_set():
                self._reconnect_requested.clear()
                capture.release()
                capture = None
                continue

            ret, frame = capture.read()
            if not ret:
                capture.release()
                capture = None
                self._sleep(backoff)
                backoff = min(backoff * 2, self._max_backoff)
                continue

            backoff = self._initial_backoff
            yield frame
            self._sleep(self._frame_interval)
