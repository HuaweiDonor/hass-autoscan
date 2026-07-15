import numpy as np

from app.roi import crop_roi


def _labeled_frame(height=10, width=20):
    # Each pixel's value encodes its (row, col) so crop correctness can be
    # checked exactly, not just by shape.
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    for r in range(height):
        for c in range(width):
            frame[r, c] = (r, c, 0)
    return frame


def test_crops_to_relative_rectangle():
    frame = _labeled_frame(height=10, width=20)

    cropped = crop_roi(frame, x_min=0.25, y_min=0.5, x_max=0.75, y_max=1.0)

    # width 20 * [0.25, 0.75] -> cols [5:15); height 10 * [0.5, 1.0] -> rows [5:10)
    assert cropped.shape == (5, 10, 3)
    assert tuple(cropped[0, 0]) == (5, 5, 0)  # top-left corner of the crop


def test_full_roi_returns_full_frame():
    frame = _labeled_frame()

    cropped = crop_roi(frame, x_min=0.0, y_min=0.0, x_max=1.0, y_max=1.0)

    assert cropped.shape == frame.shape
    assert np.array_equal(cropped, frame)


def test_clamps_out_of_range_values():
    frame = _labeled_frame(height=10, width=20)

    cropped = crop_roi(frame, x_min=-0.5, y_min=-1.0, x_max=1.5, y_max=2.0)

    assert cropped.shape == frame.shape
    assert np.array_equal(cropped, frame)


def test_falls_back_to_full_frame_when_x_range_degenerate():
    frame = _labeled_frame()

    cropped = crop_roi(frame, x_min=0.8, y_min=0.0, x_max=0.2, y_max=1.0)

    assert cropped.shape == frame.shape
    assert np.array_equal(cropped, frame)


def test_falls_back_to_full_frame_when_y_range_degenerate():
    frame = _labeled_frame()

    cropped = crop_roi(frame, x_min=0.0, y_min=0.9, x_max=1.0, y_max=0.1)

    assert cropped.shape == frame.shape
    assert np.array_equal(cropped, frame)
