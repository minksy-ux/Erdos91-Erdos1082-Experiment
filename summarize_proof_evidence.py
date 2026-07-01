#!/usr/bin/env python3
"""Aggregate #91 proof-search JSON reports into a ranked evidence scoreboard."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class EvidenceRow:
    n: int
    witness_runs: int
    total_runs: int
    witness_ratio: float
    max_families: int
    max_signature_families: int
    min_best_exact_sq: int | None
    max_best_exact_sq: int | None


def load_reports(paths: List[str]) -> Dict[int, List[Dict[str, Any]]]:
    merged: Dict[int, List[Dict[str, Any]]] = {}
    for path in paths:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        for summary in payload:
            n = int(summary["n"])
            merged.setdefault(n, []).append(summary)
    return merged


def aggregate_for_n(summaries: List[Dict[str, Any]]) -> EvidenceRow:
    n = int(summaries[0]["n"])
    witness_runs = sum(int(s["witness_runs"]) for s in summaries)
    total_runs = sum(int(s["total_runs"]) for s in summaries)
    max_families = 0
    max_sig_families = 0
    min_exact: int | None = None
    max_exact: int | None = None

    for s in summaries:
        for run in s.get("runs", []):
            max_families = max(max_families, int(run.get("num_families", 0)))
            max_sig_families = max(max_sig_families, int(run.get("num_signature_families", 0)))
        mn = s.get("min_best_exact_sq")
        mx = s.get("max_best_exact_sq")
        if mn is not None:
            mn = int(mn)
            min_exact = mn if min_exact is None else min(min_exact, mn)
        if mx is not None:
            mx = int(mx)
            max_exact = mx if max_exact is None else max(max_exact, mx)

    witness_ratio = (witness_runs / total_runs) if total_runs else 0.0
    return EvidenceRow(
        n=n,
        witness_runs=witness_runs,
        total_runs=total_runs,
        witness_ratio=witness_ratio,
        max_families=max_families,
        max_signature_families=max_sig_families,
        min_best_exact_sq=min_exact,
        max_best_exact_sq=max_exact,
    )


def to_markdown(rows: List[EvidenceRow], top_k: int) -> str:
    lines = []
    lines.append("# Erdős #91 Proof-Evidence Scoreboard")
    lines.append("")
    lines.append("Rows ranked by witness ratio, then max family split.")
    lines.append("")
    lines.append("| Rank | n | Witness Runs | Ratio | Max Families | Max Signature Families | Best Exact Range |")
    lines.append("|---:|---:|---:|---:|---:|---:|---:|")
    for idx, row in enumerate(rows[:top_k], start=1):
        exact_range = "-"
        if row.min_best_exact_sq is not None and row.max_best_exact_sq is not None:
            exact_range = f"{row.min_best_exact_sq}..{row.max_best_exact_sq}"
        lines.append(
            f"| {idx} | {row.n} | {row.witness_runs}/{row.total_runs} | {row.witness_ratio:.2f} | "
            f"{row.max_families} | {row.max_signature_families} | {exact_range} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize #91 proof-search evidence reports")
    parser.add_argument("--reports", nargs="+", required=True, help="paths to proof_search_91 JSON reports")
    parser.add_argument("--top-k", type=int, default=10, help="number of rows to keep in the markdown scoreboard")
    parser.add_argument("--out", type=str, default="results/proof_evidence_scoreboard.md", help="output markdown path")
    args = parser.parse_args()

    if args.top_k < 1:
        parser.error("--top-k must be >= 1")

    merged = load_reports(args.reports)
    rows = [aggregate_for_n(summaries) for _, summaries in merged.items()]
    rows.sort(key=lambda r: (r.witness_ratio, r.max_families, r.max_signature_families, -r.n), reverse=True)

    markdown = to_markdown(rows, top_k=args.top_k)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(markdown, encoding="utf-8")

    print(markdown)
    print(f"Saved scoreboard to {out_path}")


if __name__ == "__main__":
    main()
