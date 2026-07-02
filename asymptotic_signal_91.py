#!/usr/bin/env python3
"""Generate a rung-5 asymptotic signal report for Erdős #91.

This report estimates which high-level asymptotic ingredients are already
supported by the finite certificates, the bridge candidate, and the observed
consensus plateau.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


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


def _format_list(values: Iterable[str]) -> str:
    items = sorted(set(value for value in values if value))
    return ", ".join(items) if items else "-"


def _best_exact_gap(exclusion: Dict[str, Any]) -> int | None:
    gap = exclusion.get("exact_gap_to_next_best")
    return int(gap) if gap is not None else None


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


def build_report(root: Path) -> Tuple[str, Dict[str, Any]]:
    pattern = _load_json(root / "results" / "pattern_ledger_91.json") or {}
    bridge = _load_json(root / "results" / "bridge_lemma_91.json") or {}
    exclusion = _load_json(root / "results" / "erdos91_exclusion_n32_v1.json") or {}
    consensus = _consensus_records(root)

    witness_rows = pattern.get("witness_rows", []) if isinstance(pattern, dict) else []
    observations = pattern.get("observations", {}) if isinstance(pattern, dict) else {}
    candidate_bridge = bridge.get("candidate_bridge", {}) if isinstance(bridge, dict) else {}

    common_families = observations.get("common_seed_families", []) if isinstance(observations, dict) else []
    seed_union = observations.get("seed_family_union", "-") if isinstance(observations, dict) else "-"
    consensus_best_values = observations.get("consensus_best_exact_values", []) if isinstance(observations, dict) else []
    consensus_signature_counts = observations.get("consensus_signature_family_counts", []) if isinstance(observations, dict) else []

    n_support = sorted({int(row.get("n", -1)) for row in witness_rows if isinstance(row, dict) and row.get("n") is not None})
    witness_strength = max((int(row.get("passed", 0)) for row in witness_rows if isinstance(row, dict)), default=0)
    witness_total = max((int(row.get("total", 0)) for row in witness_rows if isinstance(row, dict)), default=0)
    common_family_count = len(common_families)
    consensus_best = sorted({int(record.get("aggregate_best_exact_sq", 0)) for record in consensus if record.get("aggregate_best_exact_sq") is not None})
    consensus_witness_runs = sum(int(record.get("witness_runs", 0)) for record in consensus)
    consensus_total_runs = sum(int(record.get("total_runs", 0)) for record in consensus)
    gap = _best_exact_gap(exclusion)
    excluded = exclusion.get("excluded_certified_count")
    exclusion_ratio = None
    if excluded is not None:
        certified = exclusion.get("certified_rows_in_scope")
        if certified:
            exclusion_ratio = float(excluded) / float(certified)

    plateau_strength = len(set(consensus_best))
    signal_score = (
        0.35 * (1.0 if common_family_count > 0 else 0.0)
        + 0.25 * (1.0 if plateau_strength == 1 else 0.0)
        + 0.20 * (1.0 if gap is not None and gap > 0 else 0.0)
        + 0.20 * (min(1.0, witness_strength / max(1, witness_total)) if witness_total else 0.0)
    )

    lines: List[str] = []
    lines.append("# Rung 5 Asymptotic Signal for Erdős #91")
    lines.append("")
    lines.append("This report summarizes the asymptotic ingredients that are already visible")
    lines.append("in the finite evidence base.")
    lines.append("")
    lines.append("## Evidence Snapshot")
    lines.append("")
    lines.append(f"- witness n support: {n_support}")
    lines.append(f"- common seed families: {_format_list(common_families)}")
    lines.append(f"- seed-family union: {seed_union}")
    lines.append(f"- consensus best exact values at n=32: {consensus_best}")
    lines.append(f"- consensus signature-family counts at n=32: {consensus_signature_counts}")
    lines.append(f"- consensus witness runs: {consensus_witness_runs}/{consensus_total_runs}")
    lines.append(f"- exclusion gap to next best: {gap}")
    lines.append(f"- excluded certified rows in scope: {excluded}")
    lines.append(f"- exclusion ratio over certified rows: {exclusion_ratio if exclusion_ratio is not None else '-'}")
    lines.append(f"- bridge target: {candidate_bridge.get('next_target', 50)}")
    lines.append("")
    lines.append("## Asymptotic Signal Components")
    lines.append("")
    lines.append("| Component | Value | Interpretation |")
    lines.append("|---|---:|---|")
    lines.append(f"| Common-family persistence | {common_family_count} | shared finite core that should survive a continuation lemma |")
    lines.append(f"| Plateau rigidity | {1 if plateau_strength == 1 else 0} | n=32 consensus best exact is flat across the optimizers |")
    lines.append(f"| Exclusion positivity | {1 if gap is not None and gap > 0 else 0} | certified rows above the best value are genuinely prunable |")
    lines.append(f"| Witness strength | {witness_strength}/{witness_total} | strongest finite non-similarity proof object |")
    lines.append(f"| Signal score | {signal_score:.2f} | coarse readiness score for the asymptotic program |")
    lines.append("")
    lines.append("## Candidate Asymptotic Strategy")
    lines.append("")
    lines.append("1. Use the common family symmetry_120 as the finite core around which the")
    lines.append("   nearby witness bundles organize.")
    lines.append("2. Use the n=22/26 witness cluster together with the n=32 plateau at best")
    lines.append("   exact = 484 as fixed anchors for a local continuation lemma.")
    lines.append("3. Use the positive exclusion gap to justify that the bridge must rule out")
    lines.append("   exterior cells, not just the observed witness families.")
    lines.append("4. Use the rung-4 bridge report to state a concrete continuation problem")
    lines.append("   over the next n window.")
    lines.append("")
    lines.append("## What Still Blocks a Full Proof")
    lines.append("")
    lines.append("- no uniform density lower bound yet")
    lines.append("- no cell-level branch-and-bound completeness argument yet")
    lines.append("- no asymptotic classification of all minimizers yet")
    lines.append("- no formal bridge from the observed plateau to all n >= N yet")
    lines.append("")
    lines.append("## Next Asymptotic Target")
    lines.append("")
    lines.append("- n=50 inductive window")
    lines.append("")

    payload: Dict[str, Any] = {
        "signal_score": signal_score,
        "evidence": {
            "witness_n_support": n_support,
            "common_seed_families": common_families,
            "seed_family_union": seed_union,
            "consensus_best_exact_values": consensus_best_values,
            "consensus_signature_family_counts": consensus_signature_counts,
            "exclusion_gap_to_next_best": gap,
            "excluded_certified_count": excluded,
            "exclusion_ratio": exclusion_ratio,
            "bridge_target": candidate_bridge.get("next_target", 50),
        },
        "strategy": {
            "core_family": candidate_bridge.get("core_family", "symmetry_120"),
            "secondary_family": candidate_bridge.get("secondary_family", "concentric_shells"),
            "anchor_n": candidate_bridge.get("anchor_n", [14, 22, 26, 32]),
            "target_n": candidate_bridge.get("next_target", 50),
        },
        "open_gaps": [
            "uniform density lower bound",
            "cell-level completeness",
            "asymptotic minimizer classification",
            "formal bridge to all n >= N",
        ],
    }
    return "\n".join(lines), payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a rung-5 asymptotic signal report for Erdős #91")
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument("--out", default="results/asymptotic_signal_91.md", help="markdown output path")
    parser.add_argument("--json-out", default="results/asymptotic_signal_91.json", help="json output path")
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
    print(f"Saved asymptotic signal report to {out_path}")
    print(f"Saved asymptotic signal report JSON to {json_path}")


if __name__ == "__main__":
    main()