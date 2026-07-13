#!/usr/bin/env python3
"""Build a fixed-n exclusion report for Erd\u0151s #91.

This is a bounded, auditable computational exclusion artifact.
It summarizes the exact certified minimizer class in the database,
the next-best exact gap, and the excluded certified candidates in scope.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from erdos_distance_explorer import shape_similarity_distance, signature_from_points


@dataclass
class ExclusionRow:
    id: int
    n: int
    run_tag: str
    trial_id: int
    seed_family: str
    exact_distinct_sq: int
    exact_min_distinct_from_point: int
    exact_max_distinct_from_point: int
    exact_is_valid: bool
    energy: float
    points: np.ndarray


def _load_rows(db_path: str, n: int, run_tag: Optional[str]) -> List[ExclusionRow]:
    query = (
        "SELECT id, n, run_tag, trial_id, seed_family, exact_distinct_sq, "
        "exact_min_distinct_from_point, exact_max_distinct_from_point, exact_is_valid, energy, points_json "
        "FROM experiments WHERE n = ?"
    )
    params: List[Any] = [n]
    if run_tag:
        query += " AND run_tag = ?"
        params.append(run_tag)
    query += " ORDER BY exact_distinct_sq ASC, exact_min_distinct_from_point DESC, energy ASC"

    rows: List[ExclusionRow] = []
    with sqlite3.connect(db_path) as conn:
        for raw in conn.execute(query, params).fetchall():
            rows.append(
                ExclusionRow(
                    id=int(raw[0]),
                    n=int(raw[1]),
                    run_tag=str(raw[2]),
                    trial_id=int(raw[3]),
                    seed_family=str(raw[4]),
                    exact_distinct_sq=int(raw[5]),
                    exact_min_distinct_from_point=int(raw[6]),
                    exact_max_distinct_from_point=int(raw[7]),
                    exact_is_valid=bool(raw[8]),
                    energy=float(raw[9]),
                    points=np.array(json.loads(raw[10]), dtype=float),
                )
            )
    return rows


def _distance_profile(points: np.ndarray, tol: float = 1e-6) -> List[int]:
    counts: Dict[float, int] = {}
    for i in range(len(points) - 1):
        for j in range(i + 1, len(points)):
            d = float(np.linalg.norm(points[i] - points[j]))
            key = round(d / tol) * tol
            counts[key] = counts.get(key, 0) + 1
    return sorted(counts.values(), reverse=True)


def _profile_preview(profile: List[int], take: int = 16) -> str:
    if not profile:
        return "empty"
    return ",".join(str(v) for v in profile[:take])


def _pick_witness_pair(rows: List[ExclusionRow], shape_tol: float) -> Optional[Tuple[ExclusionRow, ExclusionRow, float]]:
    if len(rows) < 2:
        return None
    best: Optional[Tuple[ExclusionRow, ExclusionRow, float]] = None
    for i in range(len(rows) - 1):
        for j in range(i + 1, len(rows)):
            d = shape_similarity_distance(rows[i].points, rows[j].points)
            if d <= shape_tol:
                continue
            if best is None or d > best[2]:
                best = (rows[i], rows[j], float(d))
    return best


def _build_report(
    *,
    db_path: str,
    n: int,
    run_tag: Optional[str],
    shape_tol: float,
    invariant_tol: float,
) -> Tuple[List[str], Dict[str, Any]]:
    rows = _load_rows(db_path, n, run_tag)
    if not rows:
        raise RuntimeError(f"No certified valid rows found for n={n} and selected filters")

    exact_valid_rows = [row for row in rows if row.exact_is_valid and row.exact_distinct_sq is not None]
    best_exact = min(row.exact_distinct_sq for row in exact_valid_rows)
    minimizers = [row for row in exact_valid_rows if row.exact_distinct_sq == best_exact]
    exact_gap_rows = [row for row in exact_valid_rows if row.exact_distinct_sq > best_exact]
    next_best_exact = min((row.exact_distinct_sq for row in exact_gap_rows), default=None)
    exact_gap = None if next_best_exact is None else next_best_exact - best_exact
    witness = _pick_witness_pair(minimizers, shape_tol=shape_tol)

    uncertified_rows = [row for row in rows if not row.exact_is_valid or row.exact_distinct_sq is None]

    lines: List[str] = []
    lines.append(f"# Erd\u0151s #91 Fixed-n Exclusion Report (n={n})")
    lines.append("")
    lines.append("This report is a bounded exclusion artifact over the certified database rows in scope.")
    lines.append("")
    lines.append("## Setup")
    lines.append(f"- Database: {db_path}")
    lines.append(f"- n: {n}")
    lines.append(f"- run_tag filter: {run_tag if run_tag else 'all'}")
    lines.append(f"- rows in scope: {len(rows)}")
    lines.append(f"- shape tolerance: {shape_tol}")
    lines.append(f"- invariant tolerance: {invariant_tol}")
    lines.append("")
    lines.append("## Exact Objective Summary")
    lines.append(f"- best exact distinct squared-distance count: {best_exact}")
    lines.append(f"- certified minimizers in scope: {len(minimizers)}")
    lines.append(f"- exact-valid rows with larger exact objective: {len(exact_gap_rows)}")
    lines.append(f"- uncertified / invalid rows in scope: {len(uncertified_rows)}")
    lines.append(f"- next-best exact distinct squared-distance count: {next_best_exact if next_best_exact is not None else '-'}")
    lines.append(f"- exact objective gap to next-best: {exact_gap if exact_gap is not None else '-'}")
    lines.append("")

    if witness is not None:
        a, b, d = witness
        sig_a = signature_from_points(a.points, tol=1e-6)
        sig_b = signature_from_points(b.points, tol=1e-6)
        prof_a = _distance_profile(a.points)
        prof_b = _distance_profile(b.points)

        lines.append("## Witness Pair")
        lines.append("Found a non-similar pair among the certified minimizers in scope.")
        lines.append(f"- Candidate A: id={a.id}, run_tag={a.run_tag}, trial={a.trial_id}, seed_family={a.seed_family}")
        lines.append(f"- Candidate B: id={b.id}, run_tag={b.run_tag}, trial={b.trial_id}, seed_family={b.seed_family}")
        lines.append(f"- Exact objective equality: {a.exact_distinct_sq} = {b.exact_distinct_sq}")
        lines.append(f"- Shape distance: {d:.6f} (> tol={shape_tol})")
        lines.append(f"- Signature equality: {sig_a == sig_b}")
        lines.append(f"- Multiplicity-profile equality: {prof_a == prof_b}")
        lines.append(f"- A profile preview: {_profile_preview(prof_a)}")
        lines.append(f"- B profile preview: {_profile_preview(prof_b)}")
        lines.append("")
    else:
        lines.append("## Witness Pair")
        lines.append("No non-similar pair was found among the minimizers in scope.")
        lines.append("")

    lines.append("## Excluded Certified Candidates")
    lines.append("Rows below are exact-valid candidates in scope with objective strictly above the best exact value.")
    lines.append("| Rank | id | run_tag | trial | seed_family | exact_sq | gap | min_pt | max_pt |")
    lines.append("|---:|---:|---|---:|---|---:|---:|---:|---:|")
    for rank, row in enumerate(exact_gap_rows[:20], start=1):
        gap = row.exact_distinct_sq - best_exact
        lines.append(
            f"| {rank} | {row.id} | {row.run_tag} | {row.trial_id} | {row.seed_family} | {row.exact_distinct_sq} | {gap} | {row.exact_min_distinct_from_point} | {row.exact_max_distinct_from_point} |"
        )
    if len(exact_gap_rows) > 20:
        lines.append(f"\n- truncated: {len(exact_gap_rows) - 20} additional excluded rows not shown")

    lines.append("")
    lines.append("## Uncertified Rows")
    lines.append("Rows below were explored but not certified exact-valid, so they cannot be used as final objective exclusions.")
    lines.append("| Rank | id | run_tag | trial | seed_family | exact_sq | min_pt | max_pt |")
    lines.append("|---:|---:|---|---:|---|---:|---:|---:|")
    for rank, row in enumerate(uncertified_rows[:20], start=1):
        exact_sq = row.exact_distinct_sq if row.exact_distinct_sq is not None else -1
        lines.append(
            f"| {rank} | {row.id} | {row.run_tag} | {row.trial_id} | {row.seed_family} | {exact_sq} | {row.exact_min_distinct_from_point} | {row.exact_max_distinct_from_point} |"
        )
    if len(uncertified_rows) > 20:
        lines.append(f"\n- truncated: {len(uncertified_rows) - 20} additional uncertified rows not shown")

    lines.append("")
    lines.append("## Exclusion Statement")
    lines.append(
        "Within the certified rows in scope, every excluded candidate has exact objective strictly larger than the best exact value."
    )
    lines.append(
        "This is a bounded exclusion log, not a global completeness proof over configuration space."
    )

    payload: Dict[str, Any] = {
        "n": n,
        "db_path": db_path,
        "run_tag": run_tag,
        "shape_tol": shape_tol,
        "invariant_tol": invariant_tol,
        "certified_rows_in_scope": len(rows),
        "best_exact_distinct_sq": best_exact,
        "certified_minimizer_count": len(minimizers),
        "excluded_certified_count": len(exact_gap_rows),
        "next_best_exact_distinct_sq": next_best_exact,
        "exact_gap_to_next_best": exact_gap,
        "witness_found": witness is not None,
        "witness": None,
        "excluded_rows": [
            {
                "id": row.id,
                "run_tag": row.run_tag,
                "trial_id": row.trial_id,
                "seed_family": row.seed_family,
                "exact_distinct_sq": row.exact_distinct_sq,
                "exact_min_distinct_from_point": row.exact_min_distinct_from_point,
                "exact_max_distinct_from_point": row.exact_max_distinct_from_point,
                "energy": row.energy,
            }
            for row in exact_gap_rows
        ],
        "summary": {
            "bounded_exclusion": True,
            "scope": "all database rows at fixed n",
            "global_completeness": False,
        },
        "uncertified_rows": [
            {
                "id": row.id,
                "run_tag": row.run_tag,
                "trial_id": row.trial_id,
                "seed_family": row.seed_family,
                "exact_distinct_sq": row.exact_distinct_sq,
                "exact_min_distinct_from_point": row.exact_min_distinct_from_point,
                "exact_max_distinct_from_point": row.exact_max_distinct_from_point,
                "energy": row.energy,
            }
            for row in uncertified_rows
        ],
    }

    if witness is not None:
        a, b, d = witness
        payload["witness"] = {
            "candidate_a": {
                "id": a.id,
                "run_tag": a.run_tag,
                "trial_id": a.trial_id,
                "seed_family": a.seed_family,
                "exact_distinct_sq": a.exact_distinct_sq,
            },
            "candidate_b": {
                "id": b.id,
                "run_tag": b.run_tag,
                "trial_id": b.trial_id,
                "seed_family": b.seed_family,
                "exact_distinct_sq": b.exact_distinct_sq,
            },
            "shape_distance": d,
        }

    return lines, payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a fixed-n exclusion report for Erd\u0151s #91")
    parser.add_argument("--db-path", type=str, default="results/proof_search_91.db", help="path to SQLite database")
    parser.add_argument("--n", type=int, required=True, help="n value to analyze")
    parser.add_argument("--run-tag", type=str, default="", help="optional run_tag filter")
    parser.add_argument("--shape-tol", type=float, default=0.01, help="shape similarity tolerance")
    parser.add_argument("--invariant-tol", type=float, default=1e-10, help="tolerance for invariant rounding")
    parser.add_argument("--out", type=str, default="results/erdos91_exclusion_n{n}.md", help="markdown output path")
    parser.add_argument("--json-out", type=str, default="results/erdos91_exclusion_n{n}.json", help="json output path")
    args = parser.parse_args()

    if args.n < 3:
        parser.error("--n must be >= 3")
    if args.shape_tol <= 0:
        parser.error("--shape-tol must be > 0")
    if args.invariant_tol <= 0:
        parser.error("--invariant-tol must be > 0")

    run_tag = args.run_tag.strip() or None
    lines, payload = _build_report(
        db_path=args.db_path,
        n=args.n,
        run_tag=run_tag,
        shape_tol=args.shape_tol,
        invariant_tol=args.invariant_tol,
    )

    out_path = Path(args.out.format(n=args.n) if "{n}" in args.out else args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    json_path = Path(args.json_out.format(n=args.n) if "{n}" in args.json_out else args.json_out)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("\n".join(lines))
    print(f"Saved exclusion report to {out_path}")
    print(f"Saved exclusion payload to {json_path}")


if __name__ == "__main__":
    main()