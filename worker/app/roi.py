import numpy as np


def crop_roi(
    frame: np.ndarray, x_min: float, y_min: float, x_max: float, y_max: float
) -> np.ndarray:
    x_min = min(max(x_min, 0.0), 1.0)
    y_min = min(max(y_min, 0.0), 1.0)
    x_max = min(max(x_max, 0.0), 1.0)
    y_max = min(max(y_max, 0.0), 1.0)

    if x_min >= x_max or y_min >= y_max:
        return frame

    height, width = frame.shape[:2]
    left = int(round(x_min * width))
    right = int(round(x_max * width))
    top = int(round(y_min * height))
    bottom = int(round(y_max * height))

    if right <= left or bottom <= top:
        return frame

    return frame[top:bottom, left:right]
