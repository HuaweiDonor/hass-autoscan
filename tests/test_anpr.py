import os

import numpy as np

from app.anpr import NomeroffANPR


def _raw_result(texts, confidences, bboxes):
    # Matches nomeroff_net's unzip(...) tuple order for a single image:
    # (images, images_bboxs, images_points, images_zones, region_ids,
    #  region_names, count_lines, confidences, texts)
    return (
        [None],  # images
        [bboxes],  # images_bboxs
        [None],  # images_points
        [None],  # images_zones
        [None],  # region_ids
        [None],  # region_names
        [None],  # count_lines
        [confidences],
        [texts],
    )


def test_detect_returns_empty_list_when_no_plates_found():
    anpr = NomeroffANPR(pipeline_fn=lambda paths: _raw_result([], [], []))

    result = anpr.detect(np.zeros((10, 10, 3), dtype=np.uint8))

    assert result == []


def test_detect_parses_single_plate_detection():
    anpr = NomeroffANPR(
        pipeline_fn=lambda paths: _raw_result(
            ["A123BC777"], [0.93], [(10, 10, 50, 20)]
        )
    )

    result = anpr.detect(np.zeros((10, 10, 3), dtype=np.uint8))

    assert len(result) == 1
    assert result[0].text == "A123BC777"
    assert result[0].confidence == 0.93
    assert result[0].bbox == (10, 10, 50, 20)


def test_detect_parses_multiple_plates_in_one_frame():
    anpr = NomeroffANPR(
        pipeline_fn=lambda paths: _raw_result(
            ["A123BC777", "K777XA777"],
            [0.9, 0.8],
            [(0, 0, 1, 1), (2, 2, 3, 3)],
        )
    )

    result = anpr.detect(np.zeros((10, 10, 3), dtype=np.uint8))

    assert [d.text for d in result] == ["A123BC777", "K777XA777"]


def test_detect_averages_per_character_confidence_list():
    anpr = NomeroffANPR(
        pipeline_fn=lambda paths: _raw_result(
            ["A123BC777"], [[0.9, 0.95, 0.85]], [(0, 0, 1, 1)]
        )
    )

    result = anpr.detect(np.zeros((10, 10, 3), dtype=np.uint8))

    assert result[0].confidence == 0.9


def test_detect_writes_frame_to_temp_file_and_cleans_up():
    seen_paths = []

    def fake_pipeline(paths):
        seen_paths.extend(paths)
        assert os.path.exists(paths[0])
        return _raw_result(["A123BC777"], [0.9], [(0, 0, 1, 1)])

    anpr = NomeroffANPR(pipeline_fn=fake_pipeline)
    anpr.detect(np.zeros((10, 10, 3), dtype=np.uint8))

    assert len(seen_paths) == 1
    assert not os.path.exists(seen_paths[0])
