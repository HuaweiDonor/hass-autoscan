import os
import tempfile
from dataclasses import dataclass
from typing import Any, Callable

import cv2
import numpy as np


@dataclass
class PlateDetection:
    text: str
    confidence: float
    bbox: Any


def _to_scalar_confidence(confidence) -> float:
    if isinstance(confidence, (list, tuple)):
        return sum(confidence) / len(confidence)
    return float(confidence)


class NomeroffANPR:
    """Wraps Nomeroff-Net's number_plate_detection_and_reading pipeline.

    `pipeline_fn` takes a list of image file paths and returns the raw
    unzip(...) tuple documented at
    https://github.com/ria-com/nomeroff-net (images, images_bboxs,
    images_points, images_zones, region_ids, region_names, count_lines,
    confidences, texts). Injected so this class is testable without a
    GPU or the real model loaded.
    """

    def __init__(self, pipeline_fn: Callable[[list], tuple]):
        self._pipeline_fn = pipeline_fn

    def detect(self, frame: np.ndarray) -> list[PlateDetection]:
        fd, path = tempfile.mkstemp(suffix=".jpg")
        os.close(fd)
        try:
            cv2.imwrite(path, frame)
            raw = self._pipeline_fn([path])
        finally:
            os.remove(path)
        return self._parse(raw)

    @staticmethod
    def _parse(raw: tuple) -> list[PlateDetection]:
        (
            _images,
            images_bboxs,
            _images_points,
            _images_zones,
            _region_ids,
            _region_names,
            _count_lines,
            confidences,
            texts,
        ) = raw

        if not texts:
            return []

        image_texts = texts[0]
        image_confidences = confidences[0]
        image_bboxs = images_bboxs[0]

        return [
            PlateDetection(
                text=text,
                confidence=_to_scalar_confidence(image_confidences[i]),
                bbox=image_bboxs[i] if i < len(image_bboxs) else None,
            )
            for i, text in enumerate(image_texts)
        ]


def load_pipeline():
    """Builds the real Nomeroff-Net pipeline_fn for NomeroffANPR.

    Requires nomeroff-net and a CUDA-enabled torch install, and downloads
    model weights on first run — only exercised on the GPU target machine,
    not in this dev environment. Verify this against the installed
    nomeroff-net version's actual output shape (see project plan, task:
    validate anpr.py against real Nomeroff-Net on GPU machine) before
    trusting NomeroffANPR._parse's assumptions in production.
    """
    from nomeroff_net import pipeline

    return pipeline("number_plate_detection_and_reading", image_loader="opencv")
