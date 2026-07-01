#!/usr/bin/env python3
"""Structured search runner for Erdos #91/#1082 experiments."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, List, Optional

import numpy as np

from erdos_distance_explorer import (
    count_distinct_distances,
    concentric_shell_seed,
    double_circle_seed,
    max_distinct_from_point,
    no_three_collinear,
    optimize_candidate,
    random_uniform_points,
    paired_polygon_seed,
    regular_polygon,
    shape_similarity_distance,
    signature_from_points,
)
from generation.rigidity_generator import RigidityGenerator
from graph_rigidity import is_generically_rigid, lamans_count, rigid_core
from utils.database import ExperimentDB
from verification.exact_verifier import ExactVerifier


@dataclass
class TrialResult:
    trial_id: int
    db_row_id: int
    points: np.ndarray
    seed_family: str
    distinct: int
    max_distinct: int
    no_three: bool
    energy: float
    exact_distinct_sq: Optional[int] = None
    exact_min_distinct: Optional[int] = None
    exact_max_distinct: Optional[int] = None
    exact_valid: Optional[bool] = None


@dataclass
class ArchiveEntry:
    n: int
    exact_distinct_sq: int
    exact_min_distinct_from_point: int
    exact_max_distinct_from_point: int
    exact_is_valid: bool
    trial_id: int
    seed_family: str
    run_tag: str
    energy: float
    points: np.ndarray


def triangular_lattice_seed(n: int, spacing: float = 0.4) -> np.ndarray:
    points: List[List[float]] = []
    row = 0
    while len(points) < n:
        for k in range(row + 1):
            if len(points) >= n:
                break
            x = spacing * (k - row / 2.0)
            y = spacing * (row * math.sqrt(3.0) / 2.0)
            points.append([x, y])
        row += 1
    return np.array(points, dtype=float)


def symmetry_120_seed(n: int, radius: float = 1.0, rng: Optional[np.random.Generator] = None) -> np.ndarray:
    if rng is None:
        rng = np.random.default_rng()
    points: List[np.ndarray] = []
    layer = 1
    while len(points) < n:
        r = radius * layer
        for k in range(3):
            theta = 2.0 * np.pi * k / 3.0 + np.pi / 6.0
            pt = np.array([r * np.cos(theta), r * np.sin(theta)])
            points.append(pt)
            if len(points) >= n:
                break
        layer += 1
    arr = np.array(points[:n], dtype=float)
    arr += 0.01 * rng.standard_normal(arr.shape)
    arr -= arr.mean(axis=0)
    return arr


def rigidity_seed(n: int, rng: np.random.Generator) -> Optional[np.ndarray]:
    for _ in range(4):
        rg = RigidityGenerator(seed=int(rng.integers(1_000_000)))
        graph = rg.generate_laman_like(n)
        if graph is None:
            continue
        if not is_generically_rigid(graph):
            continue
        if rigid_core(graph).number_of_nodes() != n:
            continue
        if n <= 14 and not lamans_count(graph):
            continue
        return rg.realize(graph, seed=int(rng.integers(1_000_000)))
    return None


def choose_seed(n: int, trial_idx: int, rng: np.random.Generator) -> tuple[np.ndarray, str]:
    mode = trial_idx % 8
    if mode == 0:
        return regular_polygon(n), "regular_polygon"
    if mode == 1:
        return triangular_lattice_seed(n), "triangular_lattice"
    if mode == 2:
        return symmetry_120_seed(n, rng=rng), "symmetry_120"
    if mode == 3:
        rig = rigidity_seed(n, rng)
        if rig is not None:
            return rig, "rigidity_laman"
        # Fall back to concentric shells when rigidity graph generation fails
        return concentric_shell_seed(n, seed=int(rng.integers(1_000_000))), "concentric_shells_fallback"
    if mode == 4:
        return concentric_shell_seed(n, seed=int(rng.integers(1_000_000))), "concentric_shells"
    if mode == 5:
        return double_circle_seed(n, seed=int(rng.integers(1_000_000))), "double_circle"
    if mode == 6:
        return paired_polygon_seed(n, seed=int(rng.integers(1_000_000))), "paired_polygon"
    return random_uniform_points(n, dim=2, seed=int(rng.integers(1_000_000))), "uniform"


def run_single_trial(
    *,
    n: int,
    trial: int,
    trial_seed: int,
    opt_method: str,
    steps: int,
    distance_tol: float,
    init_points: Optional[np.ndarray] = None,
    seed_family: Optional[str] = None,
) -> dict[str, Any]:
    rng = np.random.default_rng(trial_seed)
    if init_points is None:
        init_points, seed_family = choose_seed(n, trial, rng)
    else:
        if seed_family is None:
            seed_family = "archive_replay"
    points, energy = optimize_candidate(
        init_points,
        method=opt_method,
        steps=steps,
        distance_tol=distance_tol,
        seed=int(rng.integers(1_000_000)),
    )
    distinct = count_distinct_distances(points, tol=distance_tol)
    max_distinct = max_distinct_from_point(points, tol=distance_tol)
    no_three = no_three_collinear(points)
    return {
        "trial": trial,
        "seed_family": seed_family,
        "points": points,
        "energy": energy,
        "distinct": distinct,
        "max_distinct": max_distinct,
        "no_three": no_three,
    }


def canonical_signature(points: np.ndarray, tol: float = 1e-5) -> str:
    sig = signature_from_points(points, tol=tol)
    preview = ",".join(f"{x:.6f}" for x in sig[:12])
    return f"len={len(sig)}:{preview}"


def load_best_archive(archive_path: str, n: int, limit: int = 8) -> List[np.ndarray]:
    path = Path(archive_path)
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    entries = [
        item
        for item in payload
        if item.get("n") == n
        and item.get("exact_is_valid")
        and item.get("exact_distinct_sq") is not None
        and item.get("points")
    ]
    entries.sort(
        key=lambda item: (
            item.get("exact_distinct_sq", 10**9),
            -item.get("exact_min_distinct_from_point", 0),
            item.get("energy", 10**9),
        )
    )

    seen: set[str] = set()
    points_out: List[np.ndarray] = []
    for item in entries:
        key = item.get("signature") or json.dumps(item.get("points", []), sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        points_out.append(np.array(item.get("points", []), dtype=float))
        if len(points_out) >= limit:
            break

    return points_out


def save_best_archive(
    archive_path: str,
    entries: List[ArchiveEntry],
    existing_entries: Optional[List[dict[str, Any]]] = None,
    max_entries: int = 50,
) -> None:
    path = Path(archive_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    combined: List[dict[str, Any]] = list(existing_entries or [])
    for entry in entries:
        combined.append(
            {
                "n": entry.n,
                "exact_distinct_sq": entry.exact_distinct_sq,
                "exact_min_distinct_from_point": entry.exact_min_distinct_from_point,
                "exact_max_distinct_from_point": entry.exact_max_distinct_from_point,
                "exact_is_valid": entry.exact_is_valid,
                "trial_id": entry.trial_id,
                "seed_family": entry.seed_family,
                "run_tag": entry.run_tag,
                "energy": entry.energy,
                "points": entry.points.tolist(),
                "signature": canonical_signature(entry.points),
            }
        )

    seen: set[str] = set()
    deduped: List[dict[str, Any]] = []
    for item in sorted(
        combined,
        key=lambda item: (
            item.get("n", 10**9),
            item.get("exact_distinct_sq", 10**9),
            -item.get("exact_min_distinct_from_point", 0),
            item.get("energy", 10**9),
        ),
    ):
        key = item.get("signature") or json.dumps(item.get("points", []), sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= max_entries:
            break

    path.write_text(json.dumps(deduped, indent=2), encoding="utf-8")


def family_count(candidates: List[TrialResult], tol: float) -> tuple[int, int, List[dict[str, Any]], List[str]]:
    reps: List[TrialResult] = []
    pairwise: List[dict[str, Any]] = []
    signatures: List[str] = [canonical_signature(c.points) for c in candidates]

    for i in range(len(candidates)):
        for j in range(i + 1, len(candidates)):
            d = shape_similarity_distance(candidates[i].points, candidates[j].points)
            pairwise.append({"i": i, "j": j, "distance": float(d)})

    for cand in candidates:
        matched = False
        for rep in reps:
            if shape_similarity_distance(cand.points, rep.points) <= tol:
                matched = True
                break
        if not matched:
            reps.append(cand)

    signature_families = len(set(signatures))
    return len(reps), signature_families, pairwise, signatures


def execute_batch(
    *,
    n: int,
    run_tag: str,
    args: argparse.Namespace,
    db: ExperimentDB,
    verifier: ExactVerifier,
    seed_offset: int,
    ray_module: Any = None,
    archive_points: Optional[List[np.ndarray]] = None,
    archive_path: Optional[str] = None,
    archive_size: int = 50,
    archive_only: bool = False,
) -> tuple[List[TrialResult], Optional[int]]:
    rng = np.random.default_rng(args.seed + seed_offset)
    trial_seeds = [int(rng.integers(1_000_000)) for _ in range(args.trials)]
    outputs: List[dict[str, Any]] = []
    archive_points = archive_points or []

    if args.mode == "ray":
        if ray_module is None:
            raise RuntimeError("Internal error: Ray mode selected but ray_module is not initialized")

        @ray_module.remote
        def run_remote(trial: int, trial_seed: int, init_points_payload: Optional[List[List[float]]] = None, seed_family: Optional[str] = None) -> dict[str, Any]:
            init_points = None
            if init_points_payload is not None:
                init_points = np.array(init_points_payload, dtype=float)
            return run_single_trial(
                n=n,
                trial=trial,
                trial_seed=trial_seed,
                opt_method=args.opt_method,
                steps=args.steps,
                distance_tol=args.distance_tol,
                init_points=init_points,
                seed_family=seed_family,
            )

        if archive_only and archive_points:
            replay_pool = archive_points
            futures = [
                run_remote.remote(
                    trial,
                    trial_seeds[trial],
                    replay_pool[trial % len(replay_pool)].tolist(),
                    "archive_only",
                )
                for trial in range(args.trials)
            ]
        else:
            futures = [run_remote.remote(trial, trial_seeds[trial]) for trial in range(args.trials)]
        outputs = ray_module.get(futures)
    else:
        if archive_only and archive_points:
            for trial in range(args.trials):
                replay_init = archive_points[trial % len(archive_points)]
                outputs.append(
                    run_single_trial(
                        n=n,
                        trial=trial,
                        trial_seed=trial_seeds[trial],
                        opt_method=args.opt_method,
                        steps=args.steps,
                        distance_tol=args.distance_tol,
                        init_points=np.array(replay_init, dtype=float),
                        seed_family="archive_only",
                    )
                )
        else:
            for trial in range(args.trials):
                outputs.append(
                    run_single_trial(
                        n=n,
                        trial=trial,
                        trial_seed=trial_seeds[trial],
                        opt_method=args.opt_method,
                        steps=args.steps,
                        distance_tol=args.distance_tol,
                    )
                )

    if archive_points and not archive_only:
        for idx, archived in enumerate(archive_points[: min(4, max(1, args.trials // 10))]):
            outputs.append(
                {
                    "trial": args.trials + idx,
                    "seed_family": "archive_replay",
                    "points": np.array(archived, dtype=float),
                    "energy": 0.0,
                    "distinct": count_distinct_distances(np.asarray(archived), tol=args.distance_tol),
                    "max_distinct": max_distinct_from_point(np.asarray(archived), tol=args.distance_tol),
                    "no_three": no_three_collinear(np.asarray(archived)),
                }
            )

    results: List[TrialResult] = []
    for output in outputs:
        row_id = db.save(
            n=n,
            dim=2,
            trial_id=int(output["trial"]),
            seed=args.seed,
            seed_family=str(output["seed_family"]),
            method=args.opt_method,
            num_distinct=int(output["distinct"]),
            max_distinct_from_point=int(output["max_distinct"]),
            no_three_collinear=bool(output["no_three"]),
            energy=float(output["energy"]),
            points=np.asarray(output["points"]),
            run_tag=run_tag,
        )
        results.append(
            TrialResult(
                trial_id=int(output["trial"]),
                db_row_id=row_id,
                points=np.asarray(output["points"]),
                seed_family=str(output["seed_family"]),
                distinct=int(output["distinct"]),
                max_distinct=int(output["max_distinct"]),
                no_three=bool(output["no_three"]),
                energy=float(output["energy"]),
            )
        )

    results.sort(key=lambda r: (r.distinct, r.energy))

    if args.certify_top > 0:
        certified = list(results) if args.exact_ranking_all else results[: args.certify_top]
        print("\nExact certification:")
        for idx, result in enumerate(certified, start=1):
            cert_name = f"n{n}_trial{result.trial_id}_rank{idx}_{run_tag}"
            cert = verifier.certify(result.points, name=cert_name, save=True)
            result.exact_distinct_sq = int(cert["num_distinct_squared_distances"])
            result.exact_min_distinct = int(cert["min_distinct_from_point"])
            result.exact_max_distinct = int(cert["max_distinct_from_point"])
            result.exact_valid = bool(cert["is_valid"])
            db.update_exact_result(
                row_id=result.db_row_id,
                exact_distinct_sq=result.exact_distinct_sq,
                exact_min_distinct_from_point=result.exact_min_distinct,
                exact_max_distinct_from_point=result.exact_max_distinct,
                exact_is_valid=result.exact_valid,
                cert_name=cert_name,
            )
            print(
                f"  {cert_name}: distinct_sq={result.exact_distinct_sq} "
                f"min_point={result.exact_min_distinct} max_point={result.exact_max_distinct} valid={result.exact_valid}"
            )

    certified_for_rank = [r for r in results if r.exact_distinct_sq is not None]
    if certified_for_rank:
        certified_for_rank.sort(
            key=lambda r: (
                r.exact_distinct_sq if r.exact_distinct_sq is not None else 10**9,
                r.exact_min_distinct if r.exact_min_distinct is not None else 10**9,
                r.energy,
            )
        )

    top = certified_for_rank[:5] if (args.exact_ranking_all and certified_for_rank) else results[:5]
    print(f"\nCompleted {args.trials} trials for n={n} run_tag={run_tag}")
    if args.exact_ranking_all and certified_for_rank:
        print("Top candidates (exact certified ranking):")
    else:
        print("Top candidates (approx ranking):")
    for idx, result in enumerate(top, start=1):
        gap = ""
        if result.exact_distinct_sq is not None:
            gap_val = result.exact_distinct_sq - result.distinct
            gap = f" exact_sq={result.exact_distinct_sq} gap={gap_val} exact_min_point={result.exact_min_distinct}"
        print(
            f"  #{idx} approx={result.distinct} approx_max_point={result.max_distinct} seed={result.seed_family} "
            f"energy={result.energy:.6f} trial={result.trial_id}{gap}"
        )

    floor_half = n // 2
    print("\n#1082 checks:")
    if certified_for_rank:
        best = certified_for_rank[0]
        print(
            f"  exact set bound: {best.exact_distinct_sq} >= {floor_half} "
            f"-> {best.exact_distinct_sq is not None and best.exact_distinct_sq >= floor_half}"
        )
        print(
            f"  exact per-point bound (min point count): {best.exact_min_distinct} >= {floor_half} "
            f"-> {best.exact_min_distinct is not None and best.exact_min_distinct >= floor_half}"
        )
    else:
        best = results[0]
        print(f"  approximate set bound: {best.distinct} >= {floor_half} -> {best.distinct >= floor_half}")
        print(f"  approximate point bound: {best.max_distinct} >= {floor_half} -> {best.max_distinct >= floor_half}")

    valid_certified = [r for r in certified_for_rank if r.exact_valid]
    archive_entries: List[ArchiveEntry] = []
    if valid_certified:
        best_exact = min(r.exact_distinct_sq for r in valid_certified if r.exact_distinct_sq is not None)
        minimizers = [
            r
            for r in valid_certified
            if r.exact_distinct_sq == best_exact
        ]
        minimizers = minimizers[: max(2, args.family_top)]
        families, signature_families, pairwise, signatures = family_count(minimizers, tol=args.family_tol)
        db.save_family_evidence(
            run_tag=run_tag,
            n=n,
            exact_distinct_sq=int(best_exact),
            family_tol=args.family_tol,
            num_candidates=len(minimizers),
            num_families=families,
            num_signature_families=signature_families,
            signatures=signatures,
            pairwise=pairwise,
        )
        print(
            f"\n#91 non-similarity evidence: best exact={best_exact}, "
            f"candidates={len(minimizers)}, shape-families={families}, signature-families={signature_families} "
            f"(tol={args.family_tol})"
        )

        for result in minimizers[:archive_size]:
            if result.exact_distinct_sq is None or result.exact_min_distinct is None or result.exact_max_distinct is None:
                continue
            archive_entries.append(
                ArchiveEntry(
                    n=n,
                    exact_distinct_sq=int(result.exact_distinct_sq),
                    exact_min_distinct_from_point=int(result.exact_min_distinct),
                    exact_max_distinct_from_point=int(result.exact_max_distinct),
                    exact_is_valid=bool(result.exact_valid),
                    trial_id=int(result.trial_id),
                    seed_family=str(result.seed_family),
                    run_tag=run_tag,
                    energy=float(result.energy),
                    points=np.asarray(result.points),
                )
            )

    if archive_path and archive_entries:
        existing: List[dict[str, Any]] = []
        archive_file = Path(archive_path)
        if archive_file.exists():
            try:
                existing = json.loads(archive_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                existing = []
        save_best_archive(archive_path, archive_entries, existing_entries=existing, max_entries=archive_size)

    best_exact_value = None
    if certified_for_rank and certified_for_rank[0].exact_distinct_sq is not None:
        best_exact_value = certified_for_rank[0].exact_distinct_sq
    return results, best_exact_value


def parse_n_values(args: argparse.Namespace) -> List[int]:
    if args.n_list:
        return [int(x.strip()) for x in args.n_list.split(",") if x.strip()]
    return [args.n]


def summarize_benchmark(db: ExperimentDB, run_tag_prefix: str, n: int, trials: int, values: List[int], runs: int) -> None:
    if not values:
        return
    avg = mean(values)
    std = pstdev(values) if len(values) > 1 else 0.0
    err = (1.96 * std / math.sqrt(len(values))) if len(values) > 1 else 0.0
    ci95_low = avg - err
    ci95_high = avg + err
    db.save_benchmark_summary(
        run_tag=run_tag_prefix,
        n=n,
        trials=trials,
        benchmark_runs=runs,
        mean_best_exact=avg,
        std_best_exact=std,
        min_best_exact=float(min(values)),
        max_best_exact=float(max(values)),
        ci95_low=ci95_low,
        ci95_high=ci95_high,
    )
    print(
        f"Benchmark summary n={n}: mean_best_exact={avg:.3f}, std={std:.3f}, "
        f"95% CI=[{ci95_low:.3f}, {ci95_high:.3f}], min={min(values)}, max={max(values)}"
    )


def archive_pool_limit(args: argparse.Namespace) -> int:
    if args.archive_only:
        return max(1, args.archive_elite_count)
    return max(1, min(args.archive_elite_count, args.trials))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run structured Erdos distance experiments")
    parser.add_argument("--n", type=int, default=10, help="number of points")
    parser.add_argument("--n-list", type=str, default="", help="comma-separated n values for benchmark mode")
    parser.add_argument("--trials", type=int, default=100, help="number of random starts")
    parser.add_argument("--steps", type=int, default=2000, help="optimization steps per trial")
    parser.add_argument("--seed", type=int, default=42, help="global random seed")
    parser.add_argument("--opt-method", type=str, default="anneal", choices=["anneal", "hillclimb", "direct"], help="optimization method")
    parser.add_argument("--distance-tol", type=float, default=1e-6, help="distance tolerance")
    parser.add_argument("--db-path", type=str, default="results/erdos_experiments.db", help="SQLite database output path")
    parser.add_argument("--certify-top", type=int, default=3, help="number of top candidates to certify exactly")
    parser.add_argument("--cert-dps", type=int, default=100, help="decimal precision for exact checks")
    parser.add_argument("--mode", type=str, default="serial", choices=["serial", "ray"], help="execution mode")
    parser.add_argument("--ray-cpus", type=int, default=0, help="CPU count for Ray init (0=auto)")
    parser.add_argument("--benchmark-runs", type=int, default=1, help="repeat count for each n value")
    parser.add_argument("--family-tol", type=float, default=0.02, help="shape-distance tolerance for family counting")
    parser.add_argument("--family-top", type=int, default=12, help="max certified minimizers used for #91 family evidence")
    parser.add_argument("--archive-path", type=str, default="results/best_exact_archive.json", help="JSON archive of certified best candidates")
    parser.add_argument("--archive-size", type=int, default=50, help="maximum number of certified archive entries to retain")
    parser.add_argument("--archive-elite-count", type=int, default=8, help="number of top certified archive candidates used as replay seeds")
    parser.add_argument("--replay-archive", action="store_true", help="seed future runs from certified archive survivors")
    parser.add_argument("--archive-only", action="store_true", help="use only archived certified survivors as starting points")
    parser.add_argument(
        "--exact-ranking-all",
        action="store_true",
        help="certify all trials and rank by exact certified distance count",
    )
    args = parser.parse_args()

    if args.n < 1:
        parser.error("--n must be >= 1")
    if args.trials < 1:
        parser.error("--trials must be >= 1")
    if args.steps < 1:
        parser.error("--steps must be >= 1")
    if args.distance_tol <= 0:
        parser.error("--distance-tol must be > 0")
    if args.certify_top < 0:
        parser.error("--certify-top must be >= 0")
    if args.exact_ranking_all and args.certify_top == 0:
        parser.error("--exact-ranking-all requires --certify-top > 0")
    if args.ray_cpus < 0:
        parser.error("--ray-cpus must be >= 0")
    if args.benchmark_runs < 1:
        parser.error("--benchmark-runs must be >= 1")
    if args.family_tol <= 0:
        parser.error("--family-tol must be > 0")
    if args.family_top < 2:
        parser.error("--family-top must be >= 2")
    if args.archive_size < 1:
        parser.error("--archive-size must be >= 1")
    if args.archive_elite_count < 1:
        parser.error("--archive-elite-count must be >= 1")
    if args.archive_only and not args.replay_archive:
        parser.error("--archive-only requires --replay-archive")

    n_values = parse_n_values(args)
    if not n_values:
        parser.error("No n values provided")

    run_tag_prefix = datetime.now().strftime("%Y%m%d_%H%M%S")
    db = ExperimentDB(args.db_path)
    verifier = ExactVerifier(dps=args.cert_dps)
    ray_module = None
    archive_points: List[np.ndarray] = []

    if args.mode == "ray":
        try:
            import ray as ray_import
        except ImportError as exc:
            raise RuntimeError("Ray mode requested but ray is not installed. Install with: pip install -e .[parallel]") from exc
        ray_import.init(num_cpus=(args.ray_cpus or None), ignore_reinit_error=True)
        ray_module = ray_import

    try:
        for n in n_values:
            if args.replay_archive:
                archive_points = load_best_archive(args.archive_path, n, limit=archive_pool_limit(args))
                if args.archive_only and not archive_points:
                    parser.error(f"--archive-only requested but no valid archive candidates found in {args.archive_path} for n={n}")
            best_exact_values: List[int] = []
            for r in range(args.benchmark_runs):
                run_tag = f"{run_tag_prefix}_n{n}_r{r}"
                _, best_exact = execute_batch(
                    n=n,
                    run_tag=run_tag,
                    args=args,
                    db=db,
                    verifier=verifier,
                    seed_offset=(n * 10_000 + r * 1_000_000),
                    ray_module=ray_module,
                    archive_points=(archive_points if args.replay_archive else []),
                    archive_path=args.archive_path,
                    archive_size=args.archive_size,
                    archive_only=args.archive_only,
                )
                if best_exact is not None:
                    best_exact_values.append(best_exact)

                    if args.replay_archive:
                        archive_points = db.get_best_points(n=n, limit=archive_pool_limit(args))

            if args.benchmark_runs > 1 and best_exact_values:
                summarize_benchmark(
                    db=db,
                    run_tag_prefix=run_tag_prefix,
                    n=n,
                    trials=args.trials,
                    values=best_exact_values,
                    runs=args.benchmark_runs,
                )
    finally:
        if ray_module is not None:
            ray_module.shutdown()


if __name__ == "__main__":
    main()
