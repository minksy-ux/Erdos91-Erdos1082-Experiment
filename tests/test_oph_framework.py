from __future__ import annotations

import numpy as np

from oph_framework import (
    ConfigurationAsSeamGraph,
    ConfigurationPatch,
    DistanceSeam,
    verify_metric_space,
)


def test_count_distinct_seams_empty_graph_returns_zero() -> None:
    points = np.array([[0.0, 0.0]])
    config = ConfigurationAsSeamGraph(points)

    assert config.count_distinct_seam_oscillations() == 0


def test_count_distinct_seams_groups_close_distances() -> None:
    points = np.array([[0.0, 0.0], [1.0, 0.0], [2.0 + 1e-7, 0.0]])
    config = ConfigurationAsSeamGraph(points)

    assert config.count_distinct_seam_oscillations(tolerance=1e-6) == 2


def test_patch_overlap_consistency_handles_zero_distance() -> None:
    points = np.array([[0.0, 0.0], [0.0, 0.0], [1.0, 0.0]])
    config = ConfigurationAsSeamGraph(points)

    patch_a = ConfigurationPatch(patch_id=1, point_indices={0, 1, 2})
    patch_b = ConfigurationPatch(patch_id=2, point_indices={0, 1})
    patch_a.extract_local_seams(config)
    patch_b.extract_local_seams(config)

    assert patch_a.verify_overlap_consistency(patch_b)


def test_verify_metric_space_accepts_valid_triangle() -> None:
    seams = {
        (0, 1): DistanceSeam(0, 1, 3.0),
        (1, 2): DistanceSeam(1, 2, 4.0),
        (0, 2): DistanceSeam(0, 2, 5.0),
    }

    assert verify_metric_space(seams)


def test_verify_metric_space_rejects_triangle_inequality_violation() -> None:
    seams = {
        (0, 1): DistanceSeam(0, 1, 1.0),
        (1, 2): DistanceSeam(1, 2, 1.0),
        (0, 2): DistanceSeam(0, 2, 3.5),
    }

    assert not verify_metric_space(seams)
