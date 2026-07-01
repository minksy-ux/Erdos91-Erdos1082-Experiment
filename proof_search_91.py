#!/usr/bin/env python3
"""Proof-search driver for Erdős #91.

This script does not prove #91. It automates the strongest currently available
computational test: search for exact minimizers and check whether the minimizer
set splits into multiple similarity classes.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from collections import Counter
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, List, Optional

from erdos_distance_explorer import count_distinct_distances, shape_similarity_distance
from scipy.spatial import ConvexHull, QhullError
from run_experiments import archive_pool_limit, execute_batch, family_count, load_best_archive
from utils.database import ExperimentDB
from verification.exact_verifier import ExactVerifier


@dataclass
class ProofSearchRun:
    n: int
    run_tag: str
    best_exact_sq: Optional[int]
    best_candidate_count: int
    num_families: int
    num_signature_families: int
    witness_found: bool
    exact_valid_candidates: int
    hull_vertices: int
    interior_points: int
    hull_distinct: Optional[int]
    profile_signature: str
    signatures: List[str]


@dataclass
class ProofSearchSummary:
    n: int
    benchmark_runs: int
    mean_best_exact_sq: Optional[float]
    std_best_exact_sq: Optional[float]
    min_best_exact_sq: Optional[int]
    max_best_exact_sq: Optional[int]
    witness_runs: int
    total_runs: int
    runs: List[ProofSearchRun]


def parse_n_values(text: str) -> List[int]:
    values = []
    for item in text.split(","):
        stripped = item.strip()
        if stripped:
            values.append(int(stripped))
    return values


def distance_multiplicity_profile(points) -> List[int]:
    if len(points) < 2:
        return []
    deltas = []
    for i in range(len(points) - 1):
        for j in range(i + 1, len(points)):
            delta = points[i] - points[j]
            deltas.append(round(float((delta @ delta) ** 0.5), 6))
    histogram = Counter(deltas)
    return sorted(histogram.values(), reverse=True)


def profile_signature(points) -> str:
    profile = distance_multiplicity_profile(points)
    if not profile:
        return "empty"
    preview = ",".join(str(value) for value in profile[:12])
    return f"len={len(profile)}:{preview}"


def hull_interior_stats(points) -> tuple[int, int, Optional[int]]:
    if len(points) < 3:
        hull_vertices = len(points)
        return hull_vertices, 0, None
    try:
        hull = ConvexHull(points)
    except QhullError:
        return len(points), 0, None
    hull_vertices = len(set(int(v) for v in hull.vertices))
    interior_points = len(points) - hull_vertices
    hull_distinct = None
    if hull_vertices >= 2:
        hull_points = points[sorted(set(int(v) for v in hull.vertices))]
        hull_distinct = int(count_distinct_distances(hull_points))
    return hull_vertices, interior_points, hull_distinct


def run_proof_search_for_n(
    *,
    n: int,
    args: argparse.Namespace,
    db: ExperimentDB,
    verifier: ExactVerifier,
    ray_module: Any = None,
    run_tag_prefix: str,
) -> ProofSearchSummary:
    best_exact_values: List[int] = []
    runs: List[ProofSearchRun] = []
    archive_points = []

    if args.replay_archive:
        archive_points = load_best_archive(args.archive_path, n, limit=archive_pool_limit(args))

    for run_idx in range(args.benchmark_runs):
        run_tag = f"{run_tag_prefix}_n{n}_r{run_idx}"
        results, best_exact = execute_batch(
            n=n,
            run_tag=run_tag,
            args=args,
            db=db,
            verifier=verifier,
            seed_offset=(n * 10_000 + run_idx * 1_000_000),
            ray_module=ray_module,
            archive_points=archive_points,
            archive_path=args.archive_path,
            archive_size=args.archive_size,
            archive_only=args.archive_only,
        )

        if best_exact is not None:
            best_exact_values.append(best_exact)

        valid_results = [result for result in results if result.exact_valid and result.exact_distinct_sq is not None]
        if valid_results:
            best_exact_sq = min(result.exact_distinct_sq for result in valid_results if result.exact_distinct_sq is not None)
            minimizers = [result for result in valid_results if result.exact_distinct_sq == best_exact_sq]
            families, signature_families, _, signatures = family_count(minimizers, tol=args.family_tol)
            hull_vertices, interior_points, hull_distinct = hull_interior_stats(minimizers[0].points)
            profile_sig = profile_signature(minimizers[0].points)
            witness_found = families >= args.min_families
            runs.append(
                ProofSearchRun(
                    n=n,
                    run_tag=run_tag,
                    best_exact_sq=int(best_exact_sq),
                    best_candidate_count=len(minimizers),
                    num_families=families,
                    num_signature_families=signature_families,
                    witness_found=witness_found,
                    exact_valid_candidates=len(valid_results),
                    hull_vertices=hull_vertices,
                    interior_points=interior_points,
                    hull_distinct=hull_distinct,
                    profile_signature=profile_sig,
                    signatures=signatures,
                )
            )
        else:
            runs.append(
                ProofSearchRun(
                    n=n,
                    run_tag=run_tag,
                    best_exact_sq=None,
                    best_candidate_count=0,
                    num_families=0,
                    num_signature_families=0,
                    witness_found=False,
                    exact_valid_candidates=0,
                    hull_vertices=0,
                    interior_points=0,
                    hull_distinct=None,
                    profile_signature="empty",
                    signatures=[],
                )
            )

    mean_best_exact_sq = mean(best_exact_values) if best_exact_values else None
    std_best_exact_sq = pstdev(best_exact_values) if len(best_exact_values) > 1 else 0.0 if best_exact_values else None
    min_best_exact_sq = min(best_exact_values) if best_exact_values else None
    max_best_exact_sq = max(best_exact_values) if best_exact_values else None
    witness_runs = sum(1 for item in runs if item.witness_found)

    return ProofSearchSummary(
        n=n,
        benchmark_runs=args.benchmark_runs,
        mean_best_exact_sq=mean_best_exact_sq,
        std_best_exact_sq=std_best_exact_sq,
        min_best_exact_sq=min_best_exact_sq,
        max_best_exact_sq=max_best_exact_sq,
        witness_runs=witness_runs,
        total_runs=len(runs),
        runs=runs,
    )


def print_summary(summary: ProofSearchSummary) -> None:
    print(f"\n#91 proof-search summary for n={summary.n}")
    if summary.mean_best_exact_sq is not None:
        print(
            f"  mean_best_exact_sq={summary.mean_best_exact_sq:.3f} std={summary.std_best_exact_sq:.3f} "
            f"min={summary.min_best_exact_sq} max={summary.max_best_exact_sq}"
        )
    else:
        print("  no exact-certified candidates were found")
    print(f"  witness_runs={summary.witness_runs}/{summary.total_runs}")
    for item in summary.runs:
        if item.best_exact_sq is None:
            print(f"  {item.run_tag}: no certified minimizer candidates")
            continue
        print(
            f"  {item.run_tag}: best_exact_sq={item.best_exact_sq} "
            f"minimizers={item.best_candidate_count} families={item.num_families} "
            f"signature_families={item.num_signature_families} witness={item.witness_found} "
            f"hull_vertices={item.hull_vertices} interior_points={item.interior_points} "
            f"hull_distinct={item.hull_distinct} profile={item.profile_signature}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Proof-search driver for Erdős #91")
    parser.add_argument("--n-list", type=str, default="8,10,12,14,16,18,20", help="comma-separated n values to test")
    parser.add_argument("--trials", type=int, default=24, help="number of search trials per run")
    parser.add_argument("--steps", type=int, default=220, help="optimization steps per trial")
    parser.add_argument("--seed", type=int, default=42, help="global random seed")
    parser.add_argument("--opt-method", type=str, default="anneal", choices=["anneal", "hillclimb", "direct"], help="optimization method")
    parser.add_argument("--distance-tol", type=float, default=1e-6, help="distance tolerance")
    parser.add_argument("--cert-dps", type=int, default=100, help="decimal precision for exact checks")
    parser.add_argument("--benchmark-runs", type=int, default=2, help="repeat count for each n value")
    parser.add_argument("--family-tol", type=float, default=0.02, help="shape-distance tolerance for family counting")
    parser.add_argument("--family-top", type=int, default=12, help="max certified minimizers used for family counting")
    parser.add_argument("--min-families", type=int, default=2, help="minimum number of families to count as a witness")
    parser.add_argument("--certify-top", type=int, default=4, help="number of top candidates to certify exactly")
    parser.add_argument("--db-path", type=str, default="results/proof_search_91.db", help="SQLite database output path")
    parser.add_argument("--archive-path", type=str, default="results/best_exact_archive.json", help="JSON archive of certified best candidates")
    parser.add_argument("--archive-size", type=int, default=50, help="maximum number of certified archive entries to retain")
    parser.add_argument("--archive-elite-count", type=int, default=8, help="number of top archive candidates used as replay seeds")
    parser.add_argument("--replay-archive", action="store_true", help="seed future runs from certified archive survivors")
    parser.add_argument("--archive-only", action="store_true", help="use only archived certified survivors as starting points")
    parser.add_argument("--exact-ranking-all", action="store_true", help="certify all trials and rank by exact certified distance count")
    parser.add_argument("--mode", type=str, default="serial", choices=["serial", "ray"], help="execution mode")
    parser.add_argument("--ray-cpus", type=int, default=0, help="CPU count for Ray init (0=auto)")
    parser.add_argument("--report-json", type=str, default="", help="optional path to save a JSON report")
    args = parser.parse_args()

    if args.trials < 1:
        parser.error("--trials must be >= 1")
    if args.steps < 1:
        parser.error("--steps must be >= 1")
    if args.benchmark_runs < 1:
        parser.error("--benchmark-runs must be >= 1")
    if args.family_tol <= 0:
        parser.error("--family-tol must be > 0")
    if args.min_families < 2:
        parser.error("--min-families must be >= 2")
    if args.certify_top < 0:
        parser.error("--certify-top must be >= 0")
    if args.archive_size < 1:
        parser.error("--archive-size must be >= 1")
    if args.archive_elite_count < 1:
        parser.error("--archive-elite-count must be >= 1")
    if args.archive_only and not args.replay_archive:
        parser.error("--archive-only requires --replay-archive")
    args.exact_ranking_all = True
    if args.certify_top == 0:
        parser.error("--certify-top requires a positive value when exact ranking is enabled")

    n_values = parse_n_values(args.n_list)
    if not n_values:
        parser.error("No n values provided")

    run_tag_prefix = datetime.now().strftime("%Y%m%d_%H%M%S")
    db = ExperimentDB(args.db_path)
    verifier = ExactVerifier(dps=args.cert_dps)
    ray_module = None

    if args.mode == "ray":
        try:
            import ray as ray_import
        except ImportError as exc:
            raise RuntimeError("Ray mode requested but ray is not installed. Install with: pip install -e .[parallel]") from exc
        ray_import.init(num_cpus=(args.ray_cpus or None), ignore_reinit_error=True)
        ray_module = ray_import

    all_summaries: List[ProofSearchSummary] = []
    try:
        for n in n_values:
            summary = run_proof_search_for_n(
                n=n,
                args=args,
                db=db,
                verifier=verifier,
                ray_module=ray_module,
                run_tag_prefix=run_tag_prefix,
            )
            all_summaries.append(summary)
            print_summary(summary)
    finally:
        if ray_module is not None:
            ray_module.shutdown()

    if args.report_json:
        report = [asdict(item) for item in all_summaries]
        Path(args.report_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report_json).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nSaved proof-search report to {args.report_json}")


if __name__ == "__main__":
    main()
