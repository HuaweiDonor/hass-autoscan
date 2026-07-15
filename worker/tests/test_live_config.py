import pytest

from app.live_config import ROI, LiveConfig


def test_initial_rtsp_url_and_roi():
    cfg = LiveConfig(
        rtsp_url="rtsp://camera.local/stream",
        roi=ROI(x_min=0.0, y_min=0.0, x_max=1.0, y_max=1.0),
    )

    assert cfg.rtsp_url == "rtsp://camera.local/stream"
    assert cfg.roi == ROI(x_min=0.0, y_min=0.0, x_max=1.0, y_max=1.0)


def test_set_rtsp_url_updates_value():
    cfg = LiveConfig(rtsp_url="rtsp://old", roi=ROI(0.0, 0.0, 1.0, 1.0))

    cfg.set_rtsp_url("rtsp://new")

    assert cfg.rtsp_url == "rtsp://new"


def test_set_roi_field_updates_only_that_field():
    cfg = LiveConfig(rtsp_url="rtsp://x", roi=ROI(0.0, 0.0, 1.0, 1.0))

    cfg.set_roi_field("x_min", 0.2)

    assert cfg.roi == ROI(x_min=0.2, y_min=0.0, x_max=1.0, y_max=1.0)


def test_set_roi_field_rejects_unknown_field():
    cfg = LiveConfig(rtsp_url="rtsp://x", roi=ROI(0.0, 0.0, 1.0, 1.0))

    with pytest.raises(TypeError):
        cfg.set_roi_field("not_a_field", 0.5)
