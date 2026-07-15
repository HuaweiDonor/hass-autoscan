import threading
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class ROI:
    x_min: float
    y_min: float
    x_max: float
    y_max: float


class LiveConfig:
    """Thread-safe holder for settings that can change at runtime (e.g. via
    Home Assistant MQTT commands arriving on paho's network thread) while
    the camera capture loop reads them on the main thread.
    """

    def __init__(self, rtsp_url: str, roi: ROI):
        self._lock = threading.Lock()
        self._rtsp_url = rtsp_url
        self._roi = roi

    @property
    def rtsp_url(self) -> str:
        with self._lock:
            return self._rtsp_url

    def set_rtsp_url(self, url: str) -> None:
        with self._lock:
            self._rtsp_url = url

    @property
    def roi(self) -> ROI:
        with self._lock:
            return self._roi

    def set_roi_field(self, field: str, value: float) -> None:
        with self._lock:
            self._roi = replace(self._roi, **{field: value})
