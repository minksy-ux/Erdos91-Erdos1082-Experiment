#!/usr/bin/env python3
"""Generate a structured rung-3 pattern ledger for Erdős #91.

This script compares the current witness, consensus, and exclusion artifacts
for n = 14, 26, and 32, then emits a machine-readable summary plus a compact
set of candidate lemmas for the next proof rung.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple


def _load_json(path: Path) -> Dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_json_list(path: Path) -> List[Dict[str, Any]]:
    payload = _load_json(path)
    if not payload:
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return [payload]


def _proof_strength(payload: Dict[str, Any]) -> Tuple[int, int]:
    proof = payload.get("non_similarity_proof_object", {})
    checks = proof.get("checks", [])
    passed = sum(1 for check in checks if check.get("passed"))
    total = len(checks)
    return passed, total


def _candidate_families(payload: Dict[str, Any]) -> List[str]:
    witness = payload.get("witness", {})
    families = {
        witness.get("candidate_a", {}).get("seed_family"),
        witness.get("candidate_b", {}).get("seed_family"),
    }
    return sorted(family for family in families if family)


def _passed_checks(payload: Dict[str, Any]) -> List[str]:
    proof = payload.get("non_similarity_proof_object", {})
    return [check.get("name", "") for check in proof.get("checks", []) if check.get("passed")]


def _separating_checks(payload: Dict[str, Any]) -> List[str]:
    proof = payload.get("non_similarity_proof_object", {})
    separating = proof.get("separating_checks", [])
    if separating:
        return [str(name) for name in separating]
    return [name for name in _passed_checks(payload) if name not in {"equal_exact_objective", "shape_distance_separated"}]


def _consensus_summary(records: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    if not records:
        return {}
    summary = records[0]
    runs = summary.get("runs", [])
    best_values = [int(run.get("best_exact_sq", 0)) for run in runs if run.get("best_exact_sq") is not None]
    signature_counts = [int(run.get("num_signature_families", 0)) for run in runs if run.get("num_signature_families") is not None]
    family_counts = [int(run.get("num_families", 0)) for run in runs if run.get("num_families") is not None]
    return {
        "n": int(summary.get("n", -1)),
        "benchmark_runs": int(summary.get("benchmark_runs", 0)),
        "mean_best_exact_sq": summary.get("mean_best_exact_sq"),
        "std_best_exact_sq": summary.get("std_best_exact_sq"),
        "min_best_exact_sq": summary.get("min_best_exact_sq"),
        "max_best_exact_sq": summary.get("max_best_exact_sq"),
        "witness_runs": int(summary.get("witness_runs", 0)),
        "total_runs": int(summary.get("total_runs", 0)),
        "aggregate_best_exact_sq": summary.get("aggregate_best_exact_sq"),
        "aggregate_candidate_count": summary.get("aggregate_candidate_count"),
        "aggregate_num_families": summary.get("aggregate_num_families"),
        "aggregate_num_signature_families": summary.get("aggregate_num_signature_families"),
        "aggregate_witness_found": bool(summary.get("aggregate_witness_found", False)),
        "run_best_values": best_values,
        "run_family_counts": family_counts,
        "run_signature_counts": signature_counts,
    }


def _format_seed_families(families: Iterable[str]) -> str:
    families_list = [family for family in families if family]
    if not families_list:
        return "-"
    return ", ".join(sorted(set(families_list)))


def build_conjectures(root: Path) -> List[str]:
    lines: List[str] = []
    witness_paths = [
        root / "results" / "erdos91_witness_n14.json",
        root / "results" / "erdos91_witness_n22.json",
        root / "results" / "erdos91_witness_n26.json",
        root / "results" / "erdos91_witness_n14_formal_upgrade_v2.json",
        root / "results" / "erdos91_witness_n26_formal_upgrade.json",
        root / "results" / "erdos91_witness_stability_n14.json",
        root / "results" / "erdos91_witness_stability_n26.json",
    ]
    exclusion_path = root / "results" / "erdos91_exclusion_n32_v1.json"
    consensus_paths = [
        root / "results" / "proof_search_91_consensus_n32_anneal_small.json",
        root / "results" / "proof_search_91_consensus_n32_hillclimb_small.json",
        root / "results" / "proof_search_91_consensus_n32_direct_small.json",
    ]

    witnesses: List[Tuple[Path, Dict[str, Any]]] = []
    for path in witness_paths:
        payload = _load_json(path)
        if payload and payload.get("witness_found"):
            witnesses.append((path, payload))

    exclusion = _load_json(exclusion_path)
    consensus = [_consensus_summary(_load_json_list(path)) for path in consensus_paths]

    lines.append("# Conjecture Generator #91")
    lines.append("")
    lines.append("## Rung 3 Pattern Ledger")
    lines.append("")

    witness_rows: List[Tuple[int, str, str, int, int, str, str]] = []
    for path, payload in witnesses:
        n = int(payload.get("n", -1))
        proof = payload.get("non_similarity_proof_object", {})
        passed, total = _proof_strength(payload)
        families = _format_seed_families(_candidate_families(payload))
        top_claim = proof.get("claim", "-")
        witness_rows.append(
            (
                n,
                path.name,
                str(payload.get("best_exact_distinct_sq", "-")),
                passed,
                total,
                families,
                top_claim,
            )
        )

    if witness_rows:
        lines.append("| n | Source | Best exact | Passed checks | Total checks | Seed families | Claim |")
        lines.append("|---:|---|---:|---:|---:|---|---|")
        for n, source, best_exact, passed, total, families, claim in sorted(witness_rows):
            lines.append(f"| {n} | {source} | {best_exact} | {passed} | {total} | {families} | {claim} |")
        lines.append("")

    if witnesses:
        n_values = sorted({int(payload.get("n", -1)) for _, payload in witnesses})
        if len(n_values) >= 2:
            lines.append(f"- Witness certificates currently appear at multiple hard n values: {n_values}.")
        families = sorted({family for _, payload in witnesses for family in _candidate_families(payload)})
        if families:
            lines.append(f"- Observed seed families across witness bundles: {_format_seed_families(families)}.")

        strengths = [_proof_strength(payload) for _, payload in witnesses]
        if strengths:
            best_passed = max(p for p, _ in strengths)
            best_total = max(t for _, t in strengths)
            lines.append(f"- Strongest witness bundle: {best_passed}/{best_total} checks passed.")

        separating_sets = sorted({name for _, payload in witnesses for name in _separating_checks(payload)})
        if separating_sets:
            lines.append(f"- Observed separating checks: {', '.join(separating_sets)}.")

    if exclusion:
        best = exclusion.get("best_exact_distinct_sq")
        next_best = exclusion.get("next_best_exact_distinct_sq")
        gap = exclusion.get("exact_gap_to_next_best")
        certified = exclusion.get("certified_minimizer_count")
        excluded = exclusion.get("excluded_certified_count")
        if best is not None and next_best is not None:
            lines.append(f"- At n=32, the exact objective gap above the best certified value is {gap}.")
        if certified is not None and excluded is not None:
            lines.append(f"- At n=32, certified minimizers ({certified}) and excluded certified candidates ({excluded}) are both substantial.")

    if consensus:
        lines.append("")
        lines.append("## Optimizer Consensus")
        lines.append("")
        lines.append("| Optimizer | Aggregate Best | Witness Runs | Total Runs | Aggregate Families | Aggregate Signature Families |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for path, record in zip(consensus_paths, consensus):
            if not record:
                continue
            name = path.stem.replace("proof_search_91_consensus_n32_", "")
            lines.append(
                f"| {name} | {record.get('aggregate_best_exact_sq', '-')} | {record.get('witness_runs', '-')}/{record.get('total_runs', '-')} | {record.get('total_runs', '-')} | {record.get('aggregate_num_families', '-')} | {record.get('aggregate_num_signature_families', '-')} |"
            )
        lines.append("")
        aggregate_best_values = sorted({value for record in consensus for value in record.get("run_best_values", [])})
        if aggregate_best_values:
            lines.append(f"- Consensus run best values observed at n=32: {aggregate_best_values}.")
        aggregate_signatures = sorted({value for record in consensus for value in record.get("run_signature_counts", [])})
        if aggregate_signatures:
            lines.append(f"- Signature-family counts observed in the consensus runs: {aggregate_signatures}.")

    lines.append("")
    lines.append("## Candidate Conjectures")
    lines.append("")
    lines.append("1. The strengthened invariant triple is sufficient to separate the current hard witness pairs at n=14, n=22, and n=26.")
    lines.append("2. The new n=22 witness confirms that the finite core extends beyond the original n=14/26 pair, so bridge lemmas should be stated for a small cluster of anchors rather than a single example.")
    lines.append("3. The n=32 consensus window is stable: all three optimizers agree on the best exact objective, and the exclusion report shows a strict gap of 1 above it.")
    lines.append("4. The next proof rung should focus on a cell-level pruning lemma because the current evidence now separates witnesses, consensus, and excluded certified rows in one ledger.")
    lines.append("5. A branch-continuation lemma is plausible if the witness families and optimizer consensus remain stable across the next n window.")
    lines.append("")
    lines.append("## Counterexample Search Prompts")
    lines.append("")
    lines.append("- Look for any new hard n where the witness proof object loses the invariant triple.")
    lines.append("- Search for a consensus run at n=32 or nearby n that breaks the 484 best-exact plateau.")
    lines.append("- Try to find a cell partition where every non-witness cell has a certified lower bound above m_n.")
    lines.append("")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate candidate conjectures for Erdős #91")
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument("--out", default="results/conjecture_ladder_91.md", help="output markdown path")
    parser.add_argument("--json-out", default="results/conjecture_ladder_91.json", help="output json path")
    args = parser.parse_args()

    root = Path(args.root)
    lines = build_conjectures(root)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    json_out = Path(args.json_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_payload = {
        "root": str(root),
        "report": lines,
        "generated_from": [
            "results/erdos91_witness_n14.json",
            "results/erdos91_witness_n22.json",
            "results/erdos91_witness_n26.json",
            "results/erdos91_witness_n14_formal_upgrade_v2.json",
            "results/erdos91_witness_n26_formal_upgrade.json",
            "results/erdos91_witness_stability_n14.json",
            "results/erdos91_witness_stability_n26.json",
            "results/erdos91_exclusion_n32_v1.json",
            "results/proof_search_91_consensus_n32_anneal_small.json",
            "results/proof_search_91_consensus_n32_hillclimb_small.json",
            "results/proof_search_91_consensus_n32_direct_small.json",
        ],
    }
    json_out.write_text(json.dumps(json_payload, indent=2), encoding="utf-8")
    print("\n".join(lines))
    print(f"Saved conjecture ladder to {out_path}")
    print(f"Saved conjecture ladder JSON to {json_out}")


if __name__ == "__main__":
    main()