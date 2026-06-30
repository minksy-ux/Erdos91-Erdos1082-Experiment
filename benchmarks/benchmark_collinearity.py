#!/usr/bin/env python3
from __future__ import annotations

import time
from typing import Callable
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from erdos_distance_explorer import collinearity_penalty, no_three_collinear


Array2D = np.ndarray


def no_three_collinear_loop(points: Array2D, tol: float = 1e-8) -> bool:
    n, dim = points.shape
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
                    raise ValueError("no_three_collinear supports only dim=2 or dim=3")
                if area2 <= tol:
                    return False
    return True


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
                penalty += np.exp(-beta * area2)
    return float(penalty)


def random_noncollinear_points(n: int, dim: int, seed: int) -> Array2D:
    rng = np.random.default_rng(seed)
    return rng.uniform(-1.0, 1.0, size=(n, dim))


def time_function(fn: Callable[[Array2D, float], bool], points: Array2D, tol: float, reps: int) -> float:
    start = time.perf_counter()
    for _ in range(reps):
        fn(points, tol)
    end = time.perf_counter()
    return (end - start) / reps


def run_benchmark() -> None:
    tol = 1e-8
    reps = 30
    cases = [(20, 2), (40, 2), (60, 2), (20, 3), (40, 3)]

    print("Benchmark: no_three_collinear (average seconds per call)")
    print("n dim   loop_s      vectorized_s  speedup")

    for idx, (n, dim) in enumerate(cases, start=1):
        points = random_noncollinear_points(n=n, dim=dim, seed=1234 + idx)

        loop_t = time_function(no_three_collinear_loop, points, tol, reps)
        vec_t = time_function(no_three_collinear, points, tol, reps)
        speedup = loop_t / vec_t if vec_t > 0 else float("inf")

        print(f"{n:>2}  {dim}   {loop_t:>9.6f}   {vec_t:>11.6f}  {speedup:>6.2f}x")

    print("\nBenchmark: collinearity_penalty (average seconds per call)")
    print("n dim   loop_s      vectorized_s  speedup")

    beta = 12.0
    for idx, (n, dim) in enumerate(cases, start=1):
        points = random_noncollinear_points(n=n, dim=dim, seed=4321 + idx)

        loop_t = time_function(collinearity_penalty_loop, points, beta, reps)
        vec_t = time_function(collinearity_penalty, points, beta, reps)
        speedup = loop_t / vec_t if vec_t > 0 else float("inf")

        print(f"{n:>2}  {dim}   {loop_t:>9.6f}   {vec_t:>11.6f}  {speedup:>6.2f}x")


if __name__ == "__main__":
    run_benchmark()
