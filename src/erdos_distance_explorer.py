#!/usr/bin/env python3
"""Prototype explorer for Erdős #91 / #1082 distance heuristics."""

from __future__ import annotations

import argparse
import json
import math
import os
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np
from scipy.spatial.distance import pdist

Array2D = np.ndarray


@dataclass
class Candidate:
    points: Array2D
    distinct_distances: int
    max_distinct_from_point: int
    no_three_collinear: bool
    energy: float


def regular_polygon(n: int, radius: float = 1.0, dim: int = 2) -> Array2D:
    if dim != 2:
        raise ValueError("regular_polygon supports only dim=2")
    theta = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    return np.stack([radius * np.cos(theta), radius * np.sin(theta)], axis=1)


def fibonacci_sphere(n: int, radius: float = 1.0, seed: Optional[int] = None) -> Array2D:
    if n <= 0:
        raise ValueError("fibonacci_sphere requires n >= 1")
    if n == 1:
        return np.array([[0.0, radius, 0.0]], dtype=float)
    rng = np.random.default_rng(seed)
    points = np.zeros((n, 3), dtype=float)
    phi = np.pi * (3.0 - np.sqrt(5.0))
    for i in range(n):
        y = 1.0 - (2.0 * i) / float(n - 1)
        r = math.sqrt(max(0.0, 1.0 - y * y))
        theta = phi * i
        x = math.cos(theta) * r
        z = math.sin(theta) * r
        points[i] = np.array([x, y, z]) * radius
    jitter = 0.01 * rng.standard_normal(points.shape)
    return points + jitter


def perturbed_regular_polygon(n: int, radius: float = 1.0, scale: float = 0.08, seed: Optional[int] = None) -> Array2D:
    rng = np.random.default_rng(seed)
    points = regular_polygon(n, radius=radius)
    return points + scale * rng.standard_normal(points.shape)


def random_uniform_points(n: int, radius: float = 1.0, dim: int = 2, seed: Optional[int] = None) -> Array2D:
    rng = np.random.default_rng(seed)
    return radius * (2.0 * rng.random((n, dim)) - 1.0)


def lattice_patch(n: int, spacing: float = 0.4, perturb: float = 0.02, dim: int = 2, seed: Optional[int] = None) -> Array2D:
    rng = np.random.default_rng(seed)
    m = int(math.ceil(n ** (1.0 / dim)))
    grid = []
    if dim == 2:
        for i in range(m):
            for j in range(m):
                if len(grid) >= n:
                    break
                grid.append((i - (m - 1) / 2, j - (m - 1) / 2))
            if len(grid) >= n:
                break
    elif dim == 3:
        for i in range(m):
            for j in range(m):
                for k in range(m):
                    if len(grid) >= n:
                        break
                    grid.append((i - (m - 1) / 2, j - (m - 1) / 2, k - (m - 1) / 2))
                if len(grid) >= n:
                    break
            if len(grid) >= n:
                break
    else:
        raise ValueError("lattice_patch supports only dim=2 or dim=3")
    points = np.array(grid, dtype=float)[:n] * spacing
    points += perturb * rng.standard_normal(points.shape)
    return points


def count_distinct_distances(points: Array2D, tol: float = 1e-6) -> int:
    dists = pdist(points)
    if dists.size == 0:
        return 0
    values = np.round(dists / tol) * tol
    return int(np.unique(values).size)


def max_distinct_from_point(points: Array2D, tol: float = 1e-6) -> int:
    n = len(points)
    if n <= 1:
        return 0
    values = []
    for i in range(n):
        dists = np.linalg.norm(points[np.arange(n) != i] - points[i], axis=1)
        values.append(int(np.unique(np.round(dists / tol) * tol).size))
    return max(values)


def no_three_collinear(points: Array2D, tol: float = 1e-8) -> bool:
    n, dim = points.shape
    if n < 3:
        return True
    if dim not in (2, 3):
        raise ValueError("no_three_collinear supports only dim=2 or dim=3")

    for i in range(n - 2):
        vectors = points[i + 1 :] - points[i]
        m = vectors.shape[0]
        if m < 2:
            continue

        tri = np.triu_indices(m, k=1)
        if dim == 2:
            cross = vectors[:, None, 0] * vectors[None, :, 1] - vectors[:, None, 1] * vectors[None, :, 0]
            if np.any(np.abs(cross[tri]) <= tol):
                return False
        else:
            cross = np.cross(vectors[:, None, :], vectors[None, :, :], axis=-1)
            norms = np.linalg.norm(cross, axis=-1)
            if np.any(norms[tri] <= tol):
                return False
    return True


def triangle_area_measure(v1: Array2D, v2: Array2D, dim: int) -> float:
    if dim == 2:
        return float(abs(v1[0] * v2[1] - v1[1] * v2[0]))
    if dim == 3:
        return float(np.linalg.norm(np.cross(v1, v2)))
    raise ValueError("Only dim=2 or dim=3 are supported")


def distance_repetition_energy(points: Array2D, num_bins: int = 30) -> float:
    dists = pdist(points)
    if dists.size == 0:
        return 0.0
    hist, _ = np.histogram(dists, bins=num_bins, density=False)
    if hist.sum() == 0:
        return 0.0
    hist = hist.astype(float) / hist.sum()
    return float(np.sum(hist**2))


def soft_cluster_energy(points: Array2D, bandwidth: float = 0.02) -> float:
    """Kernel-based distance repetition measure.

    Uses a Gaussian kernel to estimate how much distance pairs overlap.
    Returns a value in (0, 1] that is HIGH when pairwise distances cluster
    together (few distinct distances) and LOW when they are well spread out.
    This provides a smoother gradient signal than the histogram-based measure.
    """
    dists = pdist(points)
    if len(dists) < 2:
        return 0.0
    diff = dists[:, None] - dists[None, :]
    K = np.exp(-0.5 * (diff / bandwidth) ** 2)
    n = len(dists)
    # Mean off-diagonal kernel value (exclude trivial self-comparisons)
    total = (K.sum() - n) / max(1, n * (n - 1))
    return float(total)


def collinearity_penalty(points: Array2D, beta: float = 12.0) -> float:
    n, dim = points.shape
    if n < 3:
        return 0.0
    if dim not in (2, 3):
        raise ValueError("collinearity_penalty supports only dim=2 or dim=3")

    penalty = 0.0
    for i in range(n - 2):
        vectors = points[i + 1 :] - points[i]
        m = vectors.shape[0]
        if m < 2:
            continue

        tri = np.triu_indices(m, k=1)
        if dim == 2:
            cross = vectors[:, None, 0] * vectors[None, :, 1] - vectors[:, None, 1] * vectors[None, :, 0]
            area2_vals = np.abs(cross[tri])
        else:
            cross = np.cross(vectors[:, None, :], vectors[None, :, :], axis=-1)
            area2_vals = np.linalg.norm(cross, axis=-1)[tri]
        penalty += float(np.exp(-beta * area2_vals).sum())
    return penalty


def energy_function(
    points: Array2D,
    lambda_repeat: float = 4.0,
    lambda_col: float = 20.0,
    lambda_disp: float = 0.01,
    lambda_soft: float = 2.0,
    num_bins: int = 30,
) -> float:
    rep = distance_repetition_energy(points, num_bins=num_bins)
    soft = soft_cluster_energy(points)
    col = collinearity_penalty(points)
    dists = pdist(points)
    disp = float(np.sum(dists)) if dists.size else 0.0
    # Both terms are low when distances repeat a lot (few distinct distances).
    repeat_loss = 1.0 / (rep + 1e-9)
    soft_loss = 1.0 / (soft + 1e-9)
    return lambda_repeat * repeat_loss + lambda_soft * soft_loss + lambda_col * col + lambda_disp * disp


def propose_perturbation(points: Array2D, scale: float = 0.03, rng: Optional[np.random.Generator] = None) -> Array2D:
    if rng is None:
        rng = np.random.default_rng()
    perturb = rng.normal(scale=scale, size=points.shape)
    return points + perturb


def hillclimb_optimize(
    init_points: Array2D,
    steps: int = 2000,
    scale: float = 0.04,
    seed: Optional[int] = None,
) -> Tuple[Array2D, float]:
    rng = np.random.default_rng(seed)
    best = init_points.copy()
    best_energy = energy_function(best)
    current = best.copy()
    current_energy = best_energy

    for step in range(steps):
        candidate = propose_perturbation(current, scale=scale, rng=rng)
        candidate_energy = energy_function(candidate)
        if candidate_energy <= current_energy:
            current = candidate
            current_energy = candidate_energy
            if candidate_energy < best_energy:
                best = candidate
                best_energy = candidate_energy
        if step % 200 == 0 and step > 0:
            scale *= 0.98

    return best, best_energy


def simulated_annealing_optimize(
    init_points: Array2D,
    steps: int = 2000,
    scale: float = 0.04,
    temp_start: float = 0.08,
    temp_end: float = 0.001,
    seed: Optional[int] = None,
    restart_every: int = 500,
) -> Tuple[Array2D, float]:
    rng = np.random.default_rng(seed)
    best = init_points.copy()
    best_energy = energy_function(best)
    current = best.copy()
    current_energy = best_energy
    current_scale = scale
    steps_no_improve = 0

    for step in range(steps):
        temperature = temp_start * ((temp_end / temp_start) ** (step / max(1, steps - 1)))
        # Alternate between perturbing all points and a single random point
        # for a mix of global and local moves.
        if rng.random() < 0.3:
            idx = int(rng.integers(len(current)))
            candidate = current.copy()
            candidate[idx] += rng.normal(scale=current_scale, size=current.shape[1])
        else:
            candidate = propose_perturbation(current, scale=current_scale, rng=rng)
        candidate_energy = energy_function(candidate)
        delta = candidate_energy - current_energy
        if delta <= 0.0 or math.exp(-delta / temperature) > rng.random():
            current = candidate
            current_energy = candidate_energy
            if candidate_energy < best_energy:
                best = candidate
                best_energy = candidate_energy
                steps_no_improve = 0
            else:
                steps_no_improve += 1
        else:
            steps_no_improve += 1

        if step % 200 == 0 and step > 0:
            current_scale *= 0.98

        # Restart from best when stuck; use a smaller scale for local refinement
        if steps_no_improve >= restart_every:
            current = best.copy()
            current_energy = best_energy
            current_scale = scale * 0.5
            steps_no_improve = 0

    return best, best_energy


def scipy_local_optimize(
    init_points: Array2D,
    steps: int = 2000,
) -> Tuple[Array2D, float]:
    """Polish a solution with scipy Nelder-Mead to reach a true local minimum.

    Nelder-Mead works without gradient information and is well-suited for the
    non-smooth energy landscape here.  Use this as a final polishing step after
    a stochastic optimizer (SA / hillclimb) to eliminate remaining slack.
    """
    from scipy.optimize import minimize as _scipy_minimize

    n, dim = init_points.shape

    def _objective(flat: np.ndarray) -> float:
        return energy_function(flat.reshape(n, dim))

    result = _scipy_minimize(
        _objective,
        init_points.flatten(),
        method="Nelder-Mead",
        options={
            "maxiter": steps * n,
            "xatol": 1e-8,
            "fatol": 1e-8,
            "adaptive": True,
        },
    )
    best = result.x.reshape(n, dim)
    return best, float(result.fun)


def distinct_distance_objective(points: Array2D, tol: float = 1e-6) -> Tuple[int, float]:
    return count_distinct_distances(points, tol=tol), energy_function(points)


def direct_distinct_optimize(
    init_points: Array2D,
    steps: int = 2000,
    scale: float = 0.04,
    tol: float = 1e-6,
    seed: Optional[int] = None,
) -> Tuple[Array2D, float]:
    rng = np.random.default_rng(seed)
    best = init_points.copy()
    best_obj = distinct_distance_objective(best, tol=tol)
    current = best.copy()
    current_obj = best_obj

    for step in range(steps):
        candidate = propose_perturbation(current, scale=scale, rng=rng)
        candidate_obj = distinct_distance_objective(candidate, tol=tol)
        if candidate_obj < current_obj or (candidate_obj[0] == current_obj[0] and candidate_obj[1] < current_obj[1]):
            current = candidate
            current_obj = candidate_obj
            if candidate_obj < best_obj:
                best = candidate
                best_obj = candidate_obj
        if step % 200 == 0 and step > 0:
            scale *= 0.98

    return best, float(best_obj[1])


def optimize_candidate(
    init_points: Array2D,
    method: str = "anneal",
    steps: int = 2000,
    scale: float = 0.04,
    temp_start: float = 0.08,
    temp_end: float = 0.001,
    distance_tol: float = 1e-6,
    seed: Optional[int] = None,
) -> Tuple[Array2D, float]:
    if method == "hillclimb":
        return hillclimb_optimize(init_points, steps=steps, scale=scale, seed=seed)
    if method == "anneal":
        return simulated_annealing_optimize(
            init_points,
            steps=steps,
            scale=scale,
            temp_start=temp_start,
            temp_end=temp_end,
            seed=seed,
        )
    if method == "anneal_polish":
        # SA followed by a Nelder-Mead local polish to reach a true local min.
        # Splits the step budget: 80% SA, 20% Nelder-Mead.
        sa_steps = max(100, int(steps * 0.8))
        polish_steps = max(50, steps - sa_steps)
        pts, _ = simulated_annealing_optimize(
            init_points,
            steps=sa_steps,
            scale=scale,
            temp_start=temp_start,
            temp_end=temp_end,
            seed=seed,
        )
        return scipy_local_optimize(pts, steps=polish_steps)
    if method == "direct":
        return direct_distinct_optimize(init_points, steps=steps, scale=scale, tol=distance_tol, seed=seed)
    raise ValueError(f"Unknown optimization method: {method}")


def seed_points(n: int, seed_type: str, dim: int, seed: Optional[int] = None) -> Array2D:
    if seed_type == "regular":
        if dim == 2:
            return perturbed_regular_polygon(n, radius=1.0, scale=0.12, seed=seed)
        if dim == 3:
            return fibonacci_sphere(n, radius=1.0, seed=seed)
    if seed_type == "shells" and dim == 2:
        return concentric_shell_seed(n, seed=seed)
    if seed_type == "double_circle" and dim == 2:
        return double_circle_seed(n, seed=seed)
    if seed_type == "paired_polygon" and dim == 2:
        return paired_polygon_seed(n, seed=seed)
    if seed_type == "uniform":
        return random_uniform_points(n, radius=1.0, dim=dim, seed=seed)
    if seed_type == "lattice":
        return lattice_patch(n, spacing=0.35, perturb=0.04, dim=dim, seed=seed)
    raise ValueError(f"Unknown seed type: {seed_type}")


def concentric_shell_seed(n: int, seed: Optional[int] = None) -> Array2D:
    rng = np.random.default_rng(seed)
    points = []
    shells = max(2, int(math.ceil(math.sqrt(n))))
    index = 0
    for shell in range(1, shells + 1):
        per_shell = max(3, int(math.ceil(n / shells)))
        radius = 0.55 * shell
        offset = (shell % 2) * (np.pi / per_shell)
        for k in range(per_shell):
            theta = offset + 2.0 * np.pi * k / per_shell
            points.append([radius * np.cos(theta), radius * np.sin(theta)])
            index += 1
            if index >= n:
                break
        if index >= n:
            break
    arr = np.array(points[:n], dtype=float)
    arr += 0.005 * rng.standard_normal(arr.shape)
    arr -= arr.mean(axis=0)
    return arr


def double_circle_seed(n: int, seed: Optional[int] = None) -> Array2D:
    rng = np.random.default_rng(seed)
    outer = max(3, n // 2)
    inner = n - outer
    points = []
    for k in range(outer):
        theta = 2.0 * np.pi * k / outer
        points.append([np.cos(theta), np.sin(theta)])
    for k in range(inner):
        theta = 2.0 * np.pi * k / max(1, inner) + (np.pi / max(1, inner))
        points.append([0.55 * np.cos(theta), 0.55 * np.sin(theta)])
    arr = np.array(points[:n], dtype=float)
    arr += 0.004 * rng.standard_normal(arr.shape)
    arr -= arr.mean(axis=0)
    return arr


def paired_polygon_seed(n: int, seed: Optional[int] = None) -> Array2D:
    rng = np.random.default_rng(seed)
    points = []
    m = max(3, n // 2)
    for k in range(m):
        theta = 2.0 * np.pi * k / m
        points.append([np.cos(theta), np.sin(theta)])
        if len(points) < n:
            points.append([0.72 * np.cos(theta + np.pi / m), 0.72 * np.sin(theta + np.pi / m)])
    arr = np.array(points[:n], dtype=float)
    arr += 0.004 * rng.standard_normal(arr.shape)
    arr -= arr.mean(axis=0)
    return arr


def generate_candidates(
    n: int,
    trials: int = 20,
    steps: int = 2000,
    seed: Optional[int] = None,
    seed_type: str = "regular",
    dim: int = 2,
    opt_method: str = "anneal",
    distance_tol: float = 1e-6,
) -> List[Candidate]:
    rng = np.random.default_rng(seed)
    candidates: List[Candidate] = []
    for trial in range(trials):
        points = seed_points(n, seed_type=seed_type, dim=dim, seed=int(rng.integers(1_000_000)))
        points, energy = optimize_candidate(
            points,
            method=opt_method,
            steps=steps,
            scale=0.04,
            temp_start=0.08,
            temp_end=0.001,
            distance_tol=distance_tol,
            seed=int(rng.integers(1_000_000)),
        )
        distinct = count_distinct_distances(points, tol=distance_tol)
        max_dist = max_distinct_from_point(points, tol=distance_tol)
        collinear = no_three_collinear(points)
        candidates.append(Candidate(points, distinct, max_dist, collinear, energy))
    candidates.sort(key=lambda c: (c.distinct_distances, c.energy))
    return candidates


def signature_from_points(points: Array2D, tol: float = 1e-5) -> Tuple[float, ...]:
    dists = pdist(points)
    dists = np.round(dists / tol) * tol
    return tuple(np.sort(dists))


def sort_points_canonical(points: Array2D) -> Array2D:
    center = points.mean(axis=0)
    shifted = points - center
    angles = np.arctan2(shifted[:, 1], shifted[:, 0])
    radii = np.linalg.norm(shifted, axis=1)
    order = np.lexsort((radii, angles))
    return points[order]


def procrustes_distance(a: Array2D, b: Array2D) -> float:
    if a.shape != b.shape:
        raise ValueError("Procrustes distance requires same shape")
    a0 = a - a.mean(axis=0)
    b0 = b - b.mean(axis=0)
    na = np.linalg.norm(a0)
    nb = np.linalg.norm(b0)
    if na < 1e-8 or nb < 1e-8:
        return float("inf")
    a0 /= na
    b0 /= nb
    m = b0.T @ a0
    u, _, vt = np.linalg.svd(m)
    r = u @ vt
    if np.linalg.det(r) < 0:
        u[:, -1] *= -1
        r = u @ vt
    diff = a0 - b0 @ r
    return float(np.linalg.norm(diff))


def shape_similarity_distance(a: Array2D, b: Array2D) -> float:
    if a.shape != b.shape:
        raise ValueError("Shape similarity requires same shape")
    if a.shape[1] == 2:
        return procrustes_distance(sort_points_canonical(a), sort_points_canonical(b))
    return procrustes_distance(a, b)


def save_candidates(candidates: Sequence[Candidate], path: str, top_k: int = 5) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    serialized = []
    for candidate in candidates[:top_k]:
        serialized.append({
            "distinct_distances": candidate.distinct_distances,
            "max_distinct_from_point": candidate.max_distinct_from_point,
            "no_three_collinear": candidate.no_three_collinear,
            "energy": candidate.energy,
            "points": candidate.points.tolist(),
        })
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(serialized, handle, indent=2)


def plot_candidate(candidate: Candidate, title: str, output_path: Optional[str] = None) -> None:
    points = candidate.points
    dim = points.shape[1]
    if dim == 2:
        plt.figure(figsize=(4, 4))
        plt.scatter(points[:, 0], points[:, 1], s=40, c="tab:blue")
        for i, (x, y) in enumerate(points):
            plt.text(x, y, str(i), fontsize=8, ha="center", va="center")
        plt.gca().set_aspect("equal", adjustable="box")
        plt.title(title)
        plt.xticks([])
        plt.yticks([])
    elif dim == 3:
        from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
        fig = plt.figure(figsize=(4, 4))
        ax = fig.add_subplot(111, projection="3d")
        ax.scatter(points[:, 0], points[:, 1], points[:, 2], s=40, c="tab:blue")
        for i, (x, y, z) in enumerate(points):
            ax.text(x, y, z, str(i), fontsize=8)
        ax.set_title(title)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_zticks([])
    else:
        raise ValueError("plot_candidate supports only dim=2 or dim=3")
    plt.tight_layout()
    if output_path is not None:
        directory = os.path.dirname(output_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        plt.savefig(output_path, dpi=200)
        plt.close()
    else:
        plt.show()


def cluster_candidates(
    candidates: Sequence[Candidate],
    method: str = "signature",
    tol: float = 1e-5,
) -> List[List[Candidate]]:
    if method == "signature":
        groups: List[List[Candidate]] = []
        seen: List[Tuple[float, ...]] = []
        for candidate in candidates:
            sig = signature_from_points(candidate.points, tol=tol)
            matched = False
            for idx, existing_sig in enumerate(seen):
                if sig == existing_sig:
                    groups[idx].append(candidate)
                    matched = True
                    break
            if not matched:
                seen.append(sig)
                groups.append([candidate])
        return groups
    if method == "procrustes":
        groups: List[List[Candidate]] = []
        reps: List[Candidate] = []
        for candidate in candidates:
            matched = False
            for idx, rep in enumerate(reps):
                if procrustes_distance(candidate.points, rep.points) <= tol:
                    groups[idx].append(candidate)
                    matched = True
                    break
            if not matched:
                reps.append(candidate)
                groups.append([candidate])
        return groups
    if method == "shape":
        groups: List[List[Candidate]] = []
        reps: List[Candidate] = []
        for candidate in candidates:
            matched = False
            for idx, rep in enumerate(reps):
                if shape_similarity_distance(candidate.points, rep.points) <= tol:
                    groups[idx].append(candidate)
                    matched = True
                    break
            if not matched:
                reps.append(candidate)
                groups.append([candidate])
        return groups
    raise ValueError(f"Unknown cluster method: {method}")


def report_candidate(candidate: Candidate, n: int) -> None:
    print(f"distinct distances = {candidate.distinct_distances}")
    print(f"max distinct from a point = {candidate.max_distinct_from_point}")
    print(f"no three collinear = {candidate.no_three_collinear}")
    print(f"energy = {candidate.energy:.6f}")
    print(f"⌊n/2⌋ threshold = {n // 2}")
    print("verdict:")
    print(f"  #1082 set bound: {candidate.distinct_distances} >= {n // 2} -> {candidate.distinct_distances >= n // 2}")
    print(f"  #1082 point bound: {candidate.max_distinct_from_point} >= {n // 2} -> {candidate.max_distinct_from_point >= n // 2}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Erdős distance experiment explorer")
    parser.add_argument("--n", type=int, default=10, help="number of points")
    parser.add_argument("--trials", type=int, default=16, help="number of search trials")
    parser.add_argument("--steps", type=int, default=2000, help="local search steps per trial")
    parser.add_argument("--seed", type=int, default=42, help="random seed")
    parser.add_argument("--seed-type", type=str, default="regular", choices=["regular", "uniform", "lattice"], help="initial seed family for point sets")
    parser.add_argument("--dim", type=int, default=2, choices=[2, 3], help="dimension of the point set")
    parser.add_argument("--opt-method", type=str, default="anneal", choices=["anneal", "hillclimb", "direct"], help="optimization method for configuration search")
    parser.add_argument("--cluster-by", type=str, default="signature", choices=["signature", "procrustes", "shape"], help="group candidates by exact distance signature, pairwise Procrustes similarity, or shape ordering")
    parser.add_argument("--cluster-tol", type=float, default=1e-3, help="clustering tolerance for signature or shape similarity")
    parser.add_argument("--distance-tol", type=float, default=1e-6, help="distance tolerance for counting distinct distances and direct optimization")
    parser.add_argument("--save-json", type=str, default="", help="optional path to save top candidate coordinates as JSON")
    parser.add_argument("--plot-top", type=int, default=0, help="number of top candidates to plot to PNG files")
    args = parser.parse_args()

    if args.n < 1:
        parser.error("--n must be >= 1")
    if args.trials < 1:
        parser.error("--trials must be >= 1")
    if args.steps < 1:
        parser.error("--steps must be >= 1")
    if args.cluster_tol <= 0.0:
        parser.error("--cluster-tol must be > 0")
    if args.distance_tol <= 0.0:
        parser.error("--distance-tol must be > 0")
    if args.plot_top < 0:
        parser.error("--plot-top must be >= 0")

    print(f"Running {args.trials} candidate trials for n={args.n} dim={args.dim} using seed type '{args.seed_type}' and opt method '{args.opt_method}'...")
    candidates = generate_candidates(
        args.n,
        trials=args.trials,
        steps=args.steps,
        seed=args.seed,
        seed_type=args.seed_type,
        dim=args.dim,
        opt_method=args.opt_method,
        distance_tol=args.distance_tol,
    )
    print("\nTop candidate summary:")
    for i, cand in enumerate(candidates[:3], start=1):
        print(f"\nCandidate #{i}")
        report_candidate(cand, args.n)

    groups = cluster_candidates(candidates, method=args.cluster_by, tol=args.cluster_tol)
    print(f"\nClusters by {args.cluster_by}: {len(groups)} distinct groups among {len(candidates)} candidates")
    for idx, group in enumerate(groups[:5], start=1):
        print(f"  group {idx}: {len(group)} configs, best distinct distances = {group[0].distinct_distances}")

    if args.save_json:
        save_candidates(candidates, args.save_json, top_k=min(5, len(candidates)))
        print(f"Saved top candidates to {args.save_json}")

    if args.plot_top > 0:
        for idx, cand in enumerate(candidates[: args.plot_top], start=1):
            output_path = f"plots/candidate_{idx}.png"
            plot_candidate(cand, title=f"Candidate {idx} (n={args.n})", output_path=output_path)
        print(f"Saved {min(args.plot_top, len(candidates))} candidate plots to plots/")


if __name__ == "__main__":
    main()
