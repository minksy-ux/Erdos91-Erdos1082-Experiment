#!/usr/bin/env python3
"""Generate a rung-4 bridge-lemma candidate report for Erdős #91.

This report is not a proof. It summarizes the recurring finite structure that
would need to be preserved by an inductive bridge between the observed finite
certificates and the next larger n window.
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


def _candidate_paths(root: Path) -> List[Path]:
    return sorted((root / "results").glob("erdos91_witness_n*.json"))


def _best_payloads_by_n(paths: List[Path]) -> List[Tuple[Path, Dict[str, Any]]]:
    best: Dict[int, Tuple[Tuple[int, int, int, int], Path, Dict[str, Any]]] = {}
    for path in paths:
        payload = _load_json(path)
        if not isinstance(payload, dict) or not payload.get("witness_found"):
            continue

        raw_n = payload.get("n")
        try:
            n = int(raw_n)
        except Exception:
            continue

        proof = payload.get("non_similarity_proof_object", {})
        checks = proof.get("checks", [])
        passed = sum(1 for check in checks if check.get("passed")) if isinstance(checks, list) else 0
        total = len(checks) if isinstance(checks, list) else 0
        decision = 1 if bool(proof.get("decision", False)) else 0
        canonical_name = 1 if path.name == f"erdos91_witness_n{n}.json" else 0
        score = (decision, passed, total, canonical_name)

        existing = best.get(n)
        if existing is None or score > existing[0]:
            best[n] = (score, path, payload)

    return [(best[n][1], best[n][2]) for n in sorted(best)]


def _family_set(payload: Dict[str, Any]) -> List[str]:
    witness = payload.get("witness", {})
    families = {
        witness.get("candidate_a", {}).get("seed_family"),
        witness.get("candidate_b", {}).get("seed_family"),
    }
    return sorted(family for family in families if family)


def _separating_checks(payload: Dict[str, Any]) -> List[str]:
    proof = payload.get("non_similarity_proof_object", {})
    separating = proof.get("separating_checks", [])
    if separating:
        return [str(name) for name in separating]
    return [
        str(check.get("name", ""))
        for check in proof.get("checks", [])
        if check.get("passed")
    ]


def _consensus_records(root: Path) -> List[Dict[str, Any]]:
    paths = [
        root / "results" / "proof_search_91_consensus_n32_anneal_small.json",
        root / "results" / "proof_search_91_consensus_n32_hillclimb_small.json",
        root / "results" / "proof_search_91_consensus_n32_direct_small.json",
    ]
    records: List[Dict[str, Any]] = []
    for path in paths:
        payload = _load_json_list(path)
        if payload:
            records.append(payload[0])
    return records


def _format_list(values: Iterable[str]) -> str:
    items = sorted(set(value for value in values if value))
    return ", ".join(items) if items else "-"


def build_report(root: Path) -> Tuple[str, Dict[str, Any]]:
    witness_paths = _candidate_paths(root)
    witness_payloads = _best_payloads_by_n(witness_paths)

    exclusion = _load_json(root / "results" / "erdos91_exclusion_n32_v1.json") or {}
    consensus = _consensus_records(root)

    lines: List[str] = []
    lines.append("# Rung 4 Bridge Report for Erdős #91")
    lines.append("")
    lines.append("This report identifies the finite evidence that must be preserved by a")
    lines.append("bridge lemma between the current witness certificates and the next n range.")
    lines.append("")
    lines.append("## Evidence Table")
    lines.append("")
    lines.append("| n | Source | Best exact | Passed checks | Seed families | Separating checks |")
    lines.append("|---:|---|---:|---:|---|---|")

    witness_rows: List[Dict[str, Any]] = []
    for path, payload in sorted(witness_payloads, key=lambda item: (int(item[1].get("n", -1)), item[0].name)):
        families = _format_list(_family_set(payload))
        separating = ", ".join(_separating_checks(payload)) or "-"
        best_exact = payload.get("best_exact_distinct_sq", "-")
        proof = payload.get("non_similarity_proof_object", {})
        passed = sum(1 for check in proof.get("checks", []) if check.get("passed"))
        total = len(proof.get("checks", []))
        n = int(payload.get("n", -1))
        witness_rows.append(
            {
                "n": n,
                "source": path.name,
                "best_exact": best_exact,
                "passed": passed,
                "total": total,
                "families": families,
                "separating": separating,
            }
        )
        lines.append(f"| {n} | {path.name} | {best_exact} | {passed}/{total} | {families} | {separating} |")

    lines.append("")
    lines.append("## Bridge Preconditions")
    lines.append("")
    n_values = sorted({row["n"] for row in witness_rows})
    families_union = _format_list(family for _, payload in witness_payloads for family in _family_set(payload))
    common_families = set(_family_set(witness_payloads[0][1])) if witness_payloads else set()
    for _, payload in witness_payloads[1:]:
        common_families &= set(_family_set(payload))

    if n_values:
        lines.append(f"- Witness support spans n values: {n_values}.")
    lines.append(f"- Union of observed seed families: {families_union}.")
    lines.append(f"- Common seed families across all witness bundles: {', '.join(sorted(common_families)) if common_families else '-'}.")
    lines.append(f"- n=32 consensus best exact values: {sorted({record.get('aggregate_best_exact_sq') for record in consensus if record.get('aggregate_best_exact_sq') is not None})}.")
    lines.append(f"- n=32 consensus witness runs: {sum(int(record.get('witness_runs', 0)) for record in consensus)}/{sum(int(record.get('total_runs', 0)) for record in consensus)}.")
    lines.append(f"- n=32 exclusion gap to next best: {exclusion.get('exact_gap_to_next_best', '-')}")
    lines.append(f"- n=32 excluded certified count: {exclusion.get('excluded_certified_count', '-')}")
    lines.append("")
    lines.append("## Candidate Bridge Lemma")
    lines.append("")
    lines.append("If the witness family symmetry_120 remains stable under the current local")
    lines.append("perturbation pattern, and if the n=22 and n=32 anchors continue to sit on")
    lines.append("the same finite core as n=14/26, then a branch-continuation lemma should")
    lines.append("be able to extend the finite non-similarity families across the next window.")
    lines.append("")
    lines.append("## What Still Needs Proof")
    lines.append("")
    lines.append("1. A stability statement showing the observed witness families persist under")
    lines.append("   small perturbations without changing the exact objective value.")
    lines.append("2. A continuation lemma from the current n anchors to a larger contiguous")
    lines.append("   range, not just isolated points.")
    lines.append("3. A pruning argument that makes the exclusion gap uniform enough to support")
    lines.append("   the bridge across the next window.")
    lines.append("")
    lines.append("## Next Bridge Target")
    lines.append("")
    lines.append("- n=50 inductive window")
    lines.append("")

    payload: Dict[str, Any] = {
        "witness_rows": witness_rows,
        "observations": {
            "n_values": n_values,
            "seed_family_union": families_union,
            "common_seed_families": sorted(common_families),
            "consensus_best_exact_values": sorted({record.get('aggregate_best_exact_sq') for record in consensus if record.get('aggregate_best_exact_sq') is not None}),
            "consensus_witness_runs": sum(int(record.get('witness_runs', 0)) for record in consensus),
            "consensus_total_runs": sum(int(record.get('total_runs', 0)) for record in consensus),
            "exclusion_gap_to_next_best": exclusion.get("exact_gap_to_next_best"),
            "excluded_certified_count": exclusion.get("excluded_certified_count"),
        },
        "candidate_bridge": {
            "core_family": "symmetry_120",
            "secondary_family": "concentric_shells",
            "anchor_n": [14, 22, 26, 32],
            "next_target": 50,
            "required_properties": [
                "stability under perturbation",
                "preservation of objective plateau",
                "uniform exclusion gap near the anchor window",
            ],
        },
    }
    return "\n".join(lines), payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a rung-4 bridge report for Erdős #91")
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument("--out", default="results/bridge_lemma_91.md", help="markdown output path")
    parser.add_argument("--json-out", default="results/bridge_lemma_91.json", help="json output path")
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
    print(f"Saved bridge report to {out_path}")
    print(f"Saved bridge report JSON to {json_path}")


if __name__ == "__main__":
    main()