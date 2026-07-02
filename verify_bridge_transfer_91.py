#!/usr/bin/env python3
"""Build a machine-readable bridge transfer proof object for Erdos #91."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def _load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return payload


def _find_transition(step_payload: Dict[str, Any], source_n: int, target_n: int) -> Dict[str, Any] | None:
    for item in step_payload.get("tested_transitions", []):
        if not isinstance(item, dict):
            continue
        if int(item.get("source_n", -1)) == source_n and int(item.get("target_n", -1)) == target_n:
            return item
    return None


def _build_window_composition(
    step_payload: Dict[str, Any],
    asymptotic_payload: Dict[str, Any],
    window_start: int,
    window_mid: int,
    window_end: int,
) -> Dict[str, Any]:
    certified_edges: List[Dict[str, Any]] = []
    blocked_edges: List[Dict[str, Any]] = []

    edge_a = _find_transition(step_payload, window_start, window_mid)
    edge_b = _find_transition(step_payload, window_start, window_start + 2)
    edge_c = _find_transition(step_payload, window_start + 2, window_mid)

    for edge in [edge_a, edge_b, edge_c]:
        if edge is None:
            continue
        if edge.get("status") == "certified":
            certified_edges.append(edge)
        else:
            blocked_edges.append(edge)

    evidence = asymptotic_payload.get("evidence", {}) if isinstance(asymptotic_payload, dict) else {}
    exclusion_gap = evidence.get("exclusion_gap_to_next_best")
    consensus_values = evidence.get("consensus_best_exact_values", [])
    anchor_support = {
        "bounded_exclusion_gap_positive": exclusion_gap is not None and float(exclusion_gap) > 0,
        "consensus_plateau_fixed": isinstance(consensus_values, list) and len(consensus_values) == 1,
    }

    if certified_edges and anchor_support["bounded_exclusion_gap_positive"] and anchor_support["consensus_plateau_fixed"]:
        status = "surrogate-certified"
    else:
        status = "blocked"

    return {
        "window_start": window_start,
        "window_mid": window_mid,
        "window_end": window_end,
        "status": status,
        "certified_edges": certified_edges,
        "blocked_edges": blocked_edges,
        "anchor_support": anchor_support,
    }


def _build_proof_object(
    schema_id: str,
    step_payload: Dict[str, Any],
    asymptotic_payload: Dict[str, Any],
    window_start: int,
    window_mid: int,
    window_end: int,
    generated_from: List[str],
) -> Dict[str, Any]:
    window = _build_window_composition(step_payload, asymptotic_payload, window_start, window_mid, window_end)

    verified_transitions = [
        item
        for item in step_payload.get("tested_transitions", [])
        if isinstance(item, dict)
    ]

    n_plus_2_ok = any(
        item.get("status") == "certified" and (int(item.get("target_n", -1)) - int(item.get("source_n", -1)) == 2)
        for item in verified_transitions
    )
    surrogate_ok = any(
        item.get("status") == "certified" and (int(item.get("target_n", -1)) - int(item.get("source_n", -1)) > 2)
        for item in verified_transitions
    )

    transfer_status = "surrogate-certified" if surrogate_ok else "blocked"
    if n_plus_2_ok:
        transfer_status = "n+2-certified"

    blocked_vertices = sorted(
        {
            int(edge.get("source_n", -1))
            for edge in window.get("blocked_edges", [])
            if isinstance(edge, dict)
        }
        |
        {
            int(edge.get("target_n", -1))
            for edge in window.get("blocked_edges", [])
            if isinstance(edge, dict)
        }
    )
    blocked_vertices = [n for n in blocked_vertices if n >= 0]
    if blocked_vertices:
        next_unlock = (
            "certify witness transitions covering blocked window vertices: "
            + ", ".join(str(n) for n in blocked_vertices)
        )
    else:
        next_unlock = "extend certified edges to the next window"
    if n_plus_2_ok:
        next_unlock = "extend n+2 certification to the next window"

    return {
        "schema_id": schema_id,
        "proof_object_id": "bridge-transfer-proof-91-v1",
        "hypothesis_source": step_payload.get("hypothesis_id", "H91-bridge-step-v1"),
        "required_hypotheses": {
            "H_witness": step_payload.get("H_n_definition", {}),
            "H_anchor": {
                "bounded_exclusion_gap_positive": window.get("anchor_support", {}).get("bounded_exclusion_gap_positive", False),
                "consensus_plateau_fixed": window.get("anchor_support", {}).get("consensus_plateau_fixed", False),
            },
        },
        "verified_transitions": verified_transitions,
        "window_composition": window,
        "conclusion": {
            "transfer_lemma_status": transfer_status,
            "n_plus_2_status": "certified" if n_plus_2_ok else "blocked",
            "surrogate_step_status": "certified" if surrogate_ok else "blocked",
            "next_required_unlock": next_unlock,
        },
        "generated_from": generated_from,
    }


def _build_markdown_report(payload: Dict[str, Any]) -> str:
    window = payload.get("window_composition", {})
    conclusion = payload.get("conclusion", {})

    lines: List[str] = []
    lines.append("# Bridge Window Composition #91")
    lines.append("")
    lines.append("## Transfer Status")
    lines.append("")
    lines.append(f"- transfer_lemma_status: {conclusion.get('transfer_lemma_status', '-')}")
    lines.append(f"- n_plus_2_status: {conclusion.get('n_plus_2_status', '-')}")
    lines.append(f"- surrogate_step_status: {conclusion.get('surrogate_step_status', '-')}")
    lines.append(f"- next_required_unlock: {conclusion.get('next_required_unlock', '-')}")
    lines.append("")

    lines.append("## Window")
    lines.append("")
    lines.append(
        f"- window: [{window.get('window_start', '-')}, {window.get('window_end', '-')}] via mid {window.get('window_mid', '-')}"
    )
    lines.append(f"- window_status: {window.get('status', '-')}")
    lines.append("")

    lines.append("## Certified Edges")
    lines.append("")
    certified = window.get("certified_edges", [])
    if not certified:
        lines.append("- none")
    else:
        for edge in certified:
            lines.append(f"- {edge.get('source_n')}->{edge.get('target_n')} ({edge.get('status')})")
    lines.append("")

    lines.append("## Blocked Edges")
    lines.append("")
    blocked = window.get("blocked_edges", [])
    if not blocked:
        lines.append("- none")
    else:
        for edge in blocked:
            blockers = edge.get("blockers", [])
            reason = "; ".join(str(item) for item in blockers) if blockers else "unspecified"
            lines.append(f"- {edge.get('source_n')}->{edge.get('target_n')}: {reason}")
    lines.append("")

    lines.append("## Anchor Support")
    lines.append("")
    anchor = window.get("anchor_support", {})
    lines.append(f"- bounded_exclusion_gap_positive: {anchor.get('bounded_exclusion_gap_positive', False)}")
    lines.append(f"- consensus_plateau_fixed: {anchor.get('consensus_plateau_fixed', False)}")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compose bridge transfer proof object for Erdos #91")
    parser.add_argument("--schema", default="bridge_transfer_schema_91.json", help="schema JSON path")
    parser.add_argument("--step-hypothesis", default="results/bridge_step_hypothesis_91.json", help="bridge-step hypothesis JSON")
    parser.add_argument("--asymptotic", default="results/asymptotic_signal_91.json", help="asymptotic signal JSON")
    parser.add_argument("--window", default="22:26:32", help="window triple start:mid:end")
    parser.add_argument("--out-json", default="results/bridge_transfer_proof_91.json", help="output transfer proof JSON")
    parser.add_argument("--out-md", default="results/bridge_window_composition_91.md", help="output markdown report")
    args = parser.parse_args()

    try:
        ws, wm, we = [int(part.strip()) for part in args.window.split(":")]
    except Exception as exc:
        raise SystemExit(f"invalid --window value '{args.window}', expected start:mid:end") from exc

    schema_path = Path(args.schema)
    step_path = Path(args.step_hypothesis)
    asymptotic_path = Path(args.asymptotic)

    schema = _load_json(schema_path)
    step_payload = _load_json(step_path)
    asymptotic_payload = _load_json(asymptotic_path)

    proof_payload = _build_proof_object(
        schema_id=str(schema.get("schema_id", "bridge-transfer-proof-91-v1")),
        step_payload=step_payload,
        asymptotic_payload=asymptotic_payload,
        window_start=ws,
        window_mid=wm,
        window_end=we,
        generated_from=[str(step_path), str(asymptotic_path), str(schema_path)],
    )

    markdown = _build_markdown_report(proof_payload)

    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(proof_payload, indent=2) + "\n", encoding="utf-8")

    out_md = Path(args.out_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown + "\n", encoding="utf-8")

    print(markdown)
    print(f"Saved bridge transfer proof JSON to {out_json}")
    print(f"Saved bridge window report to {out_md}")


if __name__ == "__main__":
    main()
