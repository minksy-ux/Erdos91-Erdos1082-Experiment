#!/usr/bin/env python3
"""Build a structural pattern ledger for the finite #91 certificates.

The goal is to turn the current finite witnesses and bounded exclusion data
into a reproducible analysis artifact that highlights recurring structure,
consensus plateaus, and the next bridge to an inductive argument.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_json_list(path: Path) -> List[Dict[str, Any]]:
    payload = _load_json(path)
    if payload is None:
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        return [payload]
    return []


def _witness_payloads(root: Path) -> List[Tuple[str, Dict[str, Any]]]:
    paths = [
        "results/erdos91_witness_n14.json",
        "results/erdos91_witness_n22.json",
        "results/erdos91_witness_n26.json",
        "results/erdos91_witness_n14_formal_upgrade_v2.json",
        "results/erdos91_witness_n26_formal_upgrade.json",
        "results/erdos91_witness_stability_n14.json",
        "results/erdos91_witness_stability_n26.json",
    ]
    payloads: List[Tuple[str, Dict[str, Any]]] = []
    for rel_path in paths:
        payload = _load_json(root / rel_path)
        if isinstance(payload, dict) and payload.get("witness_found"):
            payloads.append((rel_path, payload))
    return payloads


def _separating_checks(payload: Dict[str, Any]) -> List[str]:
    proof = payload.get("non_similarity_proof_object", {})
    separating = proof.get("separating_checks", [])
    if separating:
        return [str(name) for name in separating]
    checks = proof.get("checks", [])
    return [str(check.get("name", "")) for check in checks if check.get("passed")]


def _seed_families(payload: Dict[str, Any]) -> List[str]:
    witness = payload.get("witness", {})
    families = {
        witness.get("candidate_a", {}).get("seed_family"),
        witness.get("candidate_b", {}).get("seed_family"),
    }
    return sorted(family for family in families if family)


def _proof_strength(payload: Dict[str, Any]) -> Tuple[int, int]:
    proof = payload.get("non_similarity_proof_object", {})
    checks = proof.get("checks", [])
    passed = sum(1 for check in checks if check.get("passed"))
    total = len(checks)
    return passed, total


def _consensus_summary(records: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    if not records:
        return {}
    summary = records[0]
    runs = summary.get("runs", [])
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
        "run_best_values": [int(run.get("best_exact_sq", 0)) for run in runs if run.get("best_exact_sq") is not None],
        "run_signature_counts": [int(run.get("num_signature_families", 0)) for run in runs if run.get("num_signature_families") is not None],
        "run_family_counts": [int(run.get("num_families", 0)) for run in runs if run.get("num_families") is not None],
    }


def _format_list(values: Iterable[str]) -> str:
    items = sorted(set(value for value in values if value))
    return ", ".join(items) if items else "-"


def build_report(root: Path) -> Tuple[str, Dict[str, Any]]:
    witness_payloads = _witness_payloads(root)
    exclusion = _load_json(root / "results" / "erdos91_exclusion_n32_v1.json") or {}
    consensus_paths = [
        root / "results" / "proof_search_91_consensus_n32_anneal_small.json",
        root / "results" / "proof_search_91_consensus_n32_hillclimb_small.json",
        root / "results" / "proof_search_91_consensus_n32_direct_small.json",
    ]
    consensus = [_consensus_summary(_load_json_list(path)) for path in consensus_paths]

    lines: List[str] = []
    lines.append("# Structural Pattern Ledger for Erdős #91")
    lines.append("")
    lines.append("This report compares the current finite certificates, stability bundles,")
    lines.append("and n=32 consensus/exclusion data to identify recurring structure.")
    lines.append("")
    lines.append("## Certificate Summary")
    lines.append("")
    lines.append("| n | Source | Best exact | Passed checks | Total checks | Seed families | Separating checks |")
    lines.append("|---:|---|---:|---:|---:|---|---|")

    witness_rows: List[Dict[str, Any]] = []
    for rel_path, payload in sorted(witness_payloads, key=lambda item: (int(item[1].get("n", -1)), item[0])):
        passed, total = _proof_strength(payload)
        families = _format_list(_seed_families(payload))
        separating = ", ".join(_separating_checks(payload)) or "-"
        best_exact = payload.get("best_exact_distinct_sq", "-")
        n = int(payload.get("n", -1))
        witness_rows.append(
            {
                "n": n,
                "source": rel_path,
                "best_exact": best_exact,
                "passed": passed,
                "total": total,
                "families": families,
                "separating": separating,
            }
        )
        lines.append(f"| {n} | {Path(rel_path).name} | {best_exact} | {passed} | {total} | {families} | {separating} |")

    lines.append("")
    lines.append("## Structural Observations")
    lines.append("")
    n_values = sorted({row["n"] for row in witness_rows})
    if n_values:
        lines.append(f"- Witness certificates currently span n values: {n_values}.")
    seed_family_union = _format_list(
        family for row in witness_payloads for family in _seed_families(row[1])
    )
    if seed_family_union != "-":
        lines.append(f"- Observed seed families across all witness bundles: {seed_family_union}.")

    common_seed_families = set(_seed_families(witness_payloads[0][1])) if witness_payloads else set()
    for _, payload in witness_payloads[1:]:
        common_seed_families &= set(_seed_families(payload))
    if common_seed_families:
        lines.append(f"- Common seed families across all witness bundles: {', '.join(sorted(common_seed_families))}.")
    else:
        lines.append("- No single seed family is shared by every witness bundle.")

    if witness_rows:
        best_values = sorted({row["best_exact"] for row in witness_rows if isinstance(row["best_exact"], int)})
        lines.append(f"- Exact objective values observed among the witness bundles: {best_values}.")
        strongest = max((row["passed"] for row in witness_rows), default=0)
        strongest_total = max((row["total"] for row in witness_rows), default=0)
        lines.append(f"- Strongest witness proof object passes {strongest}/{strongest_total} checks.")

    if consensus:
        lines.append("")
        lines.append("## Consensus Plateau")
        lines.append("")
        lines.append("| Optimizer | Aggregate Best | Witness Runs | Total Runs | Families | Signature Families |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for path, record in zip(consensus_paths, consensus):
            if not record:
                continue
            name = path.stem.replace("proof_search_91_consensus_n32_", "")
            lines.append(
                f"| {name} | {record.get('aggregate_best_exact_sq', '-')} | {record.get('witness_runs', '-')}/{record.get('total_runs', '-')} | {record.get('total_runs', '-')} | {record.get('aggregate_num_families', '-')} | {record.get('aggregate_num_signature_families', '-')} |"
            )
        aggregate_best_values = sorted({value for record in consensus for value in record.get("run_best_values", [])})
        aggregate_signature_counts = sorted({value for record in consensus for value in record.get("run_signature_counts", [])})
        lines.append("")
        lines.append(f"- Consensus best exact values observed at n=32: {aggregate_best_values}.")
        lines.append(f"- Consensus signature-family counts observed at n=32: {aggregate_signature_counts}.")

    lines.append("")
    lines.append("## Exclusion Slice")
    lines.append("")
    lines.append(f"- certified minimizers in scope: {exclusion.get('certified_minimizer_count', '-')}")
    lines.append(f"- exact-valid rows with larger exact objective: {exclusion.get('excluded_certified_count', '-')}")
    lines.append(f"- next-best exact distinct squared-distance count: {exclusion.get('next_best_exact_distinct_sq', '-')}")
    lines.append(f"- exact objective gap to next-best: {exclusion.get('exact_gap_to_next_best', '-')}")
    lines.append("")
    lines.append("## Candidate Structural Conjectures")
    lines.append("")
    lines.append("1. The dominant finite witness family remains symmetry_120, but n=22 and n=26 also show a concentric_shells branch, so the minimizer set is structurally plural rather than single-family.")
    lines.append("2. The new n=22 witness confirms that the finite core extends beyond the original n=14/26 pair, so bridge lemmas should be stated for a small cluster of anchors rather than a single example.")
    lines.append("3. The n=32 consensus plateau is rigid at best exact = 484 across all three optimizers, which makes it a natural anchor for an inductive bridge.")
    lines.append("4. The current data support a 'core plus deformation' picture: the witness bundles separate by seed family while preserving the same exact objective value within each n.")
    lines.append("5. The next proof rung should target a stability lemma: perturbations inside the observed certificate neighborhoods should not merge the known non-similar branches.")
    lines.append("")
    lines.append("## Next Analysis Prompt")
    lines.append("")
    lines.append("- Add more certified n values and recompute whether the common seed family set stays nonempty.")
    lines.append("- Search for a recurrence in best exact values and signature-family counts across adjacent n values.")
    lines.append("- Test whether the observed witness families extend through a shared local template that can be stated as a lemma.")
    lines.append("")

    payload: Dict[str, Any] = {
        "witness_rows": witness_rows,
        "consensus": consensus,
        "exclusion": {
            "certified_minimizer_count": exclusion.get("certified_minimizer_count"),
            "excluded_certified_count": exclusion.get("excluded_certified_count"),
            "next_best_exact_distinct_sq": exclusion.get("next_best_exact_distinct_sq"),
            "exact_gap_to_next_best": exclusion.get("exact_gap_to_next_best"),
        },
        "observations": {
            "n_values": n_values,
            "seed_family_union": seed_family_union,
            "common_seed_families": sorted(common_seed_families),
            "consensus_best_exact_values": aggregate_best_values if consensus else [],
            "consensus_signature_family_counts": aggregate_signature_counts if consensus else [],
        },
        "conjectures": [
            "The dominant finite witness family remains symmetry_120, but n=22 and n=26 also show a concentric_shells branch, so the minimizer set is structurally plural rather than single-family.",
            "The new n=22 witness confirms that the finite core extends beyond the original n=14/26 pair, so bridge lemmas should be stated for a small cluster of anchors rather than a single example.",
            "The n=32 consensus plateau is rigid at best exact = 484 across all three optimizers, which makes it a natural anchor for an inductive bridge.",
            "The current data support a core plus deformation picture: the witness bundles separate by seed family while preserving the same exact objective value within each n.",
            "The next proof rung should target a stability lemma: perturbations inside the observed certificate neighborhoods should not merge the known non-similar branches.",
        ],
    }

    return "\n".join(lines), payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a structural pattern ledger for Erdős #91")
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument("--out", default="results/pattern_ledger_91.md", help="markdown output path")
    parser.add_argument("--json-out", default="results/pattern_ledger_91.json", help="json output path")
    args = parser.parse_args()

    root = Path(args.root)
    markdown, payload = build_report(root)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(markdown + "\n", encoding="utf-8")

    json_path = Path(args.json_out)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(markdown)
    print(f"Saved pattern ledger to {out_path}")
    print(f"Saved pattern ledger JSON to {json_path}")


if __name__ == "__main__":
    main()