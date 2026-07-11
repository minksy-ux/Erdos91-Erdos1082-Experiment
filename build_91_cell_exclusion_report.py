#!/usr/bin/env python3
"""Build a coarse cell-level exclusion artifact for Erd1s #91 at fixed n.

This is a bounded computational artifact: cells are formed in a normalized
coordinate chart and excluded when all certified rows in that cell have exact
objective strictly above the global certified minimum.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

from erdos_distance_explorer import sort_points_canonical


@dataclass
class Row:
    id: int
    run_tag: str
    trial_id: int
    seed_family: str
    exact_sq: int
    exact_valid: bool
    points: np.ndarray


def _load_rows(db_path: str, n: int) -> List[Row]:
    query = (
        "SELECT id, run_tag, trial_id, seed_family, exact_distinct_sq, exact_is_valid, points_json "
        "FROM experiments WHERE n = ? AND exact_distinct_sq IS NOT NULL"
    )
    rows: List[Row] = []
    with sqlite3.connect(db_path) as conn:
        for raw in conn.execute(query, (n,)).fetchall():
            rows.append(
                Row(
                    id=int(raw[0]),
                    run_tag=str(raw[1]),
                    trial_id=int(raw[2]),
                    seed_family=str(raw[3]),
                    exact_sq=int(raw[4]),
                    exact_valid=bool(raw[5]),
                    points=np.array(json.loads(raw[6]), dtype=float),
                )
            )
    return rows


def _normalize(points: np.ndarray) -> np.ndarray:
    pts = sort_points_canonical(points)
    centered = pts - pts.mean(axis=0)
    norm = np.linalg.norm(centered)
    if norm <= 1e-12:
        return centered
    return centered / norm


def _cell_key(points: np.ndarray, prefix_points: int, bin_size: float) -> str:
    normed = _normalize(points)
    m = min(prefix_points, len(normed))
    vec = normed[:m].reshape(-1)
    bins = np.round(vec / bin_size).astype(int)
    return "|".join(str(int(x)) for x in bins.tolist())


def _build_payload(rows: List[Row], n: int, bin_size: float, prefix_points: int) -> Dict[str, Any]:
    certified = [r for r in rows if r.exact_valid]
    if not certified:
        raise RuntimeError("No exact-valid rows found for selected n")

    best_exact = min(r.exact_sq for r in certified)
    cells: Dict[str, List[Row]] = defaultdict(list)
    for row in certified:
        cells[_cell_key(row.points, prefix_points=prefix_points, bin_size=bin_size)].append(row)

    cell_rows: List[Dict[str, Any]] = []
    excluded = 0
    for key, members in cells.items():
        min_exact = min(r.exact_sq for r in members)
        status = "candidate_minimizer_cell" if min_exact == best_exact else "excluded_cell"
        if status == "excluded_cell":
            excluded += 1
        rep = min(members, key=lambda r: (r.exact_sq, r.id))
        cell_rows.append(
            {
                "cell_key": key,
                "rows": len(members),
                "min_exact_sq": min_exact,
                "status": status,
                "representative": {
                    "id": rep.id,
                    "run_tag": rep.run_tag,
                    "trial_id": rep.trial_id,
                    "seed_family": rep.seed_family,
                    "exact_sq": rep.exact_sq,
                },
            }
        )

    cell_rows.sort(key=lambda c: (c["min_exact_sq"], -c["rows"]))

    return {
        "n": n,
        "bin_size": bin_size,
        "prefix_points": prefix_points,
        "certified_rows": len(certified),
        "best_exact_sq": best_exact,
        "cells_total": len(cell_rows),
        "cells_excluded": excluded,
        "cells_candidate_minimizer": len(cell_rows) - excluded,
        "cells": cell_rows,
        "summary": {
            "artifact_type": "coarse_cell_exclusion",
            "bounded": True,
            "global_completeness": False,
        },
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append(f"# #91 Cell-Level Exclusion Report (n={payload['n']})")
    lines.append("")
    lines.append("This is a bounded coarse-cell exclusion artifact in a normalized chart.")
    lines.append("")
    lines.append("## Setup")
    lines.append(f"- n: {payload['n']}")
    lines.append(f"- bin_size: {payload['bin_size']}")
    lines.append(f"- prefix_points: {payload['prefix_points']}")
    lines.append(f"- certified_rows: {payload['certified_rows']}")
    lines.append(f"- best_exact_sq: {payload['best_exact_sq']}")
    lines.append("")
    lines.append("## Cell Summary")
    lines.append(f"- total cells: {payload['cells_total']}")
    lines.append(f"- excluded cells (min_exact > best): {payload['cells_excluded']}")
    lines.append(f"- candidate minimizer cells: {payload['cells_candidate_minimizer']}")
    lines.append("")
    lines.append("| Rank | Cell status | min_exact_sq | rows | representative id | seed_family |")
    lines.append("|---:|---|---:|---:|---:|---|")
    for idx, cell in enumerate(payload["cells"][:40], start=1):
        rep = cell["representative"]
        lines.append(
            f"| {idx} | {cell['status']} | {cell['min_exact_sq']} | {cell['rows']} | {rep['id']} | {rep['seed_family']} |"
        )
    if len(payload["cells"]) > 40:
        lines.append("")
        lines.append(f"- truncated: {len(payload['cells']) - 40} additional cells not shown")
    lines.append("")
    lines.append("## Exclusion Statement")
    lines.append("Cells marked excluded_cell have certified lower objective bound above the global best within this chart discretization.")
    lines.append("This is not a global completeness proof.")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build coarse cell-level exclusion artifact for #91")
    parser.add_argument("--db-path", type=str, default="results/erdos_experiments.db")
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument("--bin-size", type=float, default=0.06)
    parser.add_argument("--prefix-points", type=int, default=6)
    parser.add_argument("--out", type=str, default="results/erdos91_cell_exclusion_n{n}.md")
    parser.add_argument("--json-out", type=str, default="results/erdos91_cell_exclusion_n{n}.json")
    args = parser.parse_args()

    if args.n < 3:
        parser.error("--n must be >= 3")
    if args.bin_size <= 0:
        parser.error("--bin-size must be > 0")
    if args.prefix_points < 2:
        parser.error("--prefix-points must be >= 2")

    rows = _load_rows(args.db_path, args.n)
    payload = _build_payload(rows, n=args.n, bin_size=args.bin_size, prefix_points=args.prefix_points)
    markdown = _to_markdown(payload)

    out_md = Path(args.out.format(n=args.n) if "{n}" in args.out else args.out)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown, encoding="utf-8")

    out_json = Path(args.json_out.format(n=args.n) if "{n}" in args.json_out else args.json_out)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(markdown)
    print(f"Saved cell exclusion report to {out_md}")
    print(f"Saved cell exclusion JSON to {out_json}")


if __name__ == "__main__":
    main()
