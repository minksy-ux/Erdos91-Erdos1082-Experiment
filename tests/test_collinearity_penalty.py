from __future__ import annotations

import math

import numpy as np
import pytest

from erdos_distance_explorer import collinearity_penalty


Array2D = np.ndarray


def collinearity_penalty_loop(points: Array2D, beta: float = 12.0) -> float:
    n, dim = points.shape
    penalty = 0.0
    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                v1 = points[j] - points[i]
                v2 = points[k] - points[i]
                if dim == 2:
                    area2 = abs(v1[0] * v2[1] - v1[1] * v2[0])
                elif dim == 3:
                    area2 = np.linalg.norm(np.cross(v1, v2))
                else:
                    raise ValueError("collinearity_penalty supports only dim=2 or dim=3")
                penalty += math.exp(-beta * area2)
    return penalty


def test_collinearity_penalty_matches_loop_in_2d() -> None:
    rng = np.random.default_rng(2026)
    points = rng.uniform(-1.0, 1.0, size=(12, 2))

    loop_val = collinearity_penalty_loop(points, beta=12.0)
    vec_val = collinearity_penalty(points, beta=12.0)

    assert vec_val == pytest.approx(loop_val, rel=1e-12, abs=1e-12)


def test_collinearity_penalty_matches_loop_in_3d() -> None:
    rng = np.random.default_rng(2027)
    points = rng.uniform(-1.0, 1.0, size=(10, 3))

    loop_val = collinearity_penalty_loop(points, beta=8.5)
    vec_val = collinearity_penalty(points, beta=8.5)

    assert vec_val == pytest.approx(loop_val, rel=1e-12, abs=1e-12)


def test_collinearity_penalty_trivial_case() -> None:
    points = np.array([[0.0, 0.0], [1.0, 1.0]])
    assert collinearity_penalty(points) == 0.0
