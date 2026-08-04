from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout

import numpy as np
import pytest

from erdos_distance_explorer import (
    generate_candidates,
    main,
    optimize_candidate,
    random_uniform_points,
    seed_points,
)


def test_optimize_candidate_rejects_non_2d_input() -> None:
    with pytest.raises(ValueError, match="2D"):
        optimize_candidate(np.array([0.0, 1.0]), method="hillclimb", steps=1)


def test_optimize_candidate_rejects_non_positive_steps() -> None:
    points = np.array([[0.0, 0.0], [1.0, 0.0]])

    with pytest.raises(ValueError, match="steps"):
        optimize_candidate(points, method="hillclimb", steps=0)


def test_seed_points_rejects_unknown_seed_type() -> None:
    with pytest.raises(ValueError, match="Unknown seed type"):
        seed_points(4, seed_type="not-a-real-seed", dim=2)


def test_seed_points_rejects_invalid_dimension() -> None:
    with pytest.raises(ValueError, match="dim"):
        seed_points(4, seed_type="uniform", dim=4)


def test_main_rejects_invalid_cluster_tolerance() -> None:
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        with pytest.raises(SystemExit):
            main(["--cluster-tol", "0"])


def test_main_rejects_invalid_n() -> None:
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        with pytest.raises(SystemExit):
            main(["--n", "0"])


def test_random_uniform_points_rejects_invalid_dimension() -> None:
    with pytest.raises(ValueError, match="dim"):
        random_uniform_points(4, dim=4)


def test_generate_candidates_rejects_invalid_trials() -> None:
    with pytest.raises(ValueError, match="trials"):
        generate_candidates(4, trials=0)
