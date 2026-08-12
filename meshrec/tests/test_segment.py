"""Step 2, prima parte: outlier statistici e ritaglio a box."""

import numpy as np
import pytest

from meshrec.core import config, segment, synth

SIZE = (100.0, 40.0, 200.0)
SPACING = 5.0


def test_isolated_points_are_removed():
    points = synth.sample_box_surface(SIZE, SPACING)
    strays = np.array([[500.0, 500.0, 500.0], [-400.0, -400.0, -400.0]])
    dirty = np.vstack([points, strays])

    clean, metrics = segment.remove_outliers(dirty, config.SegmentConfig())

    assert metrics["outliers_removed"] >= 2
    assert clean.max() < 400.0


def test_crop_box_keeps_only_the_points_inside():
    points = synth.sample_box_surface(SIZE, SPACING)
    cfg = config.SegmentConfig(crop_min=(0.0, 0.0, 0.0), crop_max=(100.0, 40.0, 100.0))

    cropped, metrics = segment.crop_box(points, cfg)

    assert cropped[:, 2].max() <= 100.0
    assert len(cropped) < len(points)
    assert metrics["points_after"] == len(cropped)


def test_crop_without_bounds_is_a_no_op():
    points = synth.sample_box_surface(SIZE, SPACING)
    cropped, metrics = segment.crop_box(points, config.SegmentConfig())
    assert len(cropped) == len(points)
    assert metrics["cropped"] is False


def test_crop_that_empties_the_cloud_raises():
    points = synth.sample_box_surface(SIZE, SPACING)
    cfg = config.SegmentConfig(crop_min=(1000.0, 1000.0, 1000.0), crop_max=(2000.0, 2000.0, 2000.0))
    with pytest.raises(ValueError, match="nessun punto"):
        segment.crop_box(points, cfg)


def test_segment_cloud_in_crop_mode_chains_both_operations():
    points = synth.sample_box_surface(SIZE, SPACING)
    dirty = np.vstack([points, [[500.0, 500.0, 500.0]]])
    cfg = config.SegmentConfig(
        method="crop", crop_min=(0.0, 0.0, 0.0), crop_max=(100.0, 40.0, 100.0)
    )

    result, metrics = segment.segment_cloud(dirty, cfg, SPACING)

    assert result[:, 2].max() <= 100.0
    assert metrics["method"] == "crop"
    assert metrics["outliers_removed"] >= 1
    assert metrics["points_after"] == len(result)


def test_auto_mode_is_not_available_yet():
    points = synth.sample_box_surface(SIZE, SPACING)
    with pytest.raises(NotImplementedError):
        segment.segment_cloud(points, config.SegmentConfig(method="auto"), SPACING)


def test_crop_box_with_inverted_bounds_raises():
    points = synth.sample_box_surface(SIZE, SPACING)
    cfg = config.SegmentConfig(crop_min=(100.0, 0.0, 0.0), crop_max=(0.0, 40.0, 100.0))
    with pytest.raises(ValueError, match="non e maggiore"):
        segment.crop_box(points, cfg)


def test_remove_outliers_that_empties_the_cloud_raises():
    points = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    cfg = config.SegmentConfig(outlier_neighbors=1, outlier_std_ratio=1e-9)
    with pytest.raises(ValueError, match="svuotato"):
        segment.remove_outliers(points, cfg)


def test_segment_cloud_reports_original_points_before_not_intermediate():
    points = synth.sample_box_surface(SIZE, SPACING)
    dirty = np.vstack([points, [[500.0, 500.0, 500.0]]])
    cfg = config.SegmentConfig(
        method="crop", crop_min=(0.0, 0.0, 0.0), crop_max=(100.0, 40.0, 100.0)
    )

    result, metrics = segment.segment_cloud(dirty, cfg, SPACING)

    assert metrics["points_before"] == len(dirty)
    assert metrics["points_after"] == len(result)
