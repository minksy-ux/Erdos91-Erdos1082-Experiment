#!/usr/bin/env python3
"""Build and verify a machine-readable bridge-step hypothesis for Erdos #91.

This script evaluates candidate finite transitions n -> n' against a concrete
hypothesis H(n) used by rung-4 bridge work.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple


REQUIRED_SEPARATING_CHECKS = [
    "distance_signature_mismatch",
    "normalized_sq_spectrum_mismatch",
    "normalized_area2_spectrum_mismatch",
    "normalized_gram_eigen_spectrum_mismatch",
]


@dataclass
class TransitionResult:
    source_n: int
    target_n: int
    source_path: str | None
    target_path: str | None
    status: str
    blockers: List[str]
    source_witness: bool
    target_witness: bool
    source_best_exact: int | None
    target_best_exact: int | None
    source_common_families: List[str]
    target_common_families: List[str]
    source_required_checks_present: bool
    target_required_checks_present: bool
    source_decision: bool
    target_decision: bool


def _load_json(path: Path) -> Dict[str, Any] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return payload
    return None


def _candidate_witness_paths(root: Path, n: int) -> List[Path]:
    pattern = f"erdos91_witness_n{n}*.json"
    candidates = sorted((root / "results").glob(pattern))
    exact_default = root / "results" / f"erdos91_witness_n{n}.json"
    if exact_default.exists() and exact_default not in candidates:
        candidates.insert(0, exact_default)
    return candidates


def _payload_quality(payload: Dict[str, Any]) -> Tuple[int, int, int]:
    witness_found = 1 if payload.get("witness_found", False) else 0
    decision = 1 if payload.get("non_similarity_proof_object", {}).get("decision", False) else 0
    separating = _separating_check_set(payload)
    required_count = sum(1 for name in REQUIRED_SEPARATING_CHECKS if name in separating)
    return (witness_found, decision, required_count)


def _select_best_payload(root: Path, n: int) -> Tuple[Path | None, Dict[str, Any] | None]:
    candidates = _candidate_witness_paths(root, n)
    best_path: Path | None = None
    best_payload: Dict[str, Any] | None = None
    best_score = (-1, -1, -1)

    for path in candidates:
        payload = _load_json(path)
        if payload is None:
            continue
        score = _payload_quality(payload)
        if score > best_score:
            best_score = score
            best_path = path
            best_payload = payload

    return best_path, best_payload


def _family_set(payload: Dict[str, Any]) -> List[str]:
    witness = payload.get("witness", {})
    families = {
        witness.get("candidate_a", {}).get("seed_family"),
        witness.get("candidate_b", {}).get("seed_family"),
    }
    return sorted(str(item) for item in families if item)


def _separating_check_set(payload: Dict[str, Any]) -> set[str]:
    proof = payload.get("non_similarity_proof_object", {})
    checks = proof.get("separating_checks", [])
    if isinstance(checks, list):
        return {str(name) for name in checks}
    return set()


def _parse_transitions(raw: str) -> List[Tuple[int, int]]:
    pairs: List[Tuple[int, int]] = []
    for item in raw.split(","):
        token = item.strip()
        if not token:
            continue
        if ":" not in token:
            raise ValueError(f"invalid transition token '{token}', expected a:b")
        left, right = token.split(":", 1)
        pairs.append((int(left.strip()), int(right.strip())))
    return pairs


def _evaluate_transition(root: Path, source_n: int, target_n: int, required_core_family: str | None) -> TransitionResult:
    source_path, source_payload = _select_best_payload(root, source_n)
    target_path, target_payload = _select_best_payload(root, target_n)

    blockers: List[str] = []

    if source_payload is None:
        blockers.append(f"missing source witness file for n={source_n}")
    if target_payload is None:
        blockers.append(f"missing target witness file for n={target_n}")

    if source_payload is None or target_payload is None:
        return TransitionResult(
            source_n=source_n,
            target_n=target_n,
            source_path=str(source_path) if source_path else None,
            target_path=str(target_path) if target_path else None,
            status="blocked",
            blockers=blockers,
            source_witness=False,
            target_witness=False,
            source_best_exact=None,
            target_best_exact=None,
            source_common_families=[],
            target_common_families=[],
            source_required_checks_present=False,
            target_required_checks_present=False,
            source_decision=False,
            target_decision=False,
        )

    source_witness = bool(source_payload.get("witness_found", False))
    target_witness = bool(target_payload.get("witness_found", False))

    if not source_witness:
        blockers.append(f"source n={source_n} has witness_found=false")
    if not target_witness:
        blockers.append(f"target n={target_n} has witness_found=false")

    source_decision = bool(source_payload.get("non_similarity_proof_object", {}).get("decision", False))
    target_decision = bool(target_payload.get("non_similarity_proof_object", {}).get("decision", False))
    if source_witness and not source_decision:
        blockers.append(f"source n={source_n} decision=false")
    if target_witness and not target_decision:
        blockers.append(f"target n={target_n} decision=false")

    source_families = _family_set(source_payload)
    target_families = _family_set(target_payload)
    if required_core_family:
        if source_witness and required_core_family not in source_families:
            blockers.append(f"source n={source_n} does not contain {required_core_family}")
        if target_witness and required_core_family not in target_families:
            blockers.append(f"target n={target_n} does not contain {required_core_family}")

    source_checks = _separating_check_set(source_payload)
    target_checks = _separating_check_set(target_payload)
    source_checks_ok = set(REQUIRED_SEPARATING_CHECKS).issubset(source_checks)
    target_checks_ok = set(REQUIRED_SEPARATING_CHECKS).issubset(target_checks)

    if source_witness and not source_checks_ok:
        missing = sorted(set(REQUIRED_SEPARATING_CHECKS) - source_checks)
        blockers.append(f"source n={source_n} missing separating checks: {', '.join(missing)}")
    if target_witness and not target_checks_ok:
        missing = sorted(set(REQUIRED_SEPARATING_CHECKS) - target_checks)
        blockers.append(f"target n={target_n} missing separating checks: {', '.join(missing)}")

    status = "certified" if not blockers else "blocked"

    return TransitionResult(
        source_n=source_n,
        target_n=target_n,
        source_path=str(source_path) if source_path else None,
        target_path=str(target_path) if target_path else None,
        status=status,
        blockers=blockers,
        source_witness=source_witness,
        target_witness=target_witness,
        source_best_exact=source_payload.get("best_exact_distinct_sq"),
        target_best_exact=target_payload.get("best_exact_distinct_sq"),
        source_common_families=source_families,
        target_common_families=target_families,
        source_required_checks_present=source_checks_ok,
        target_required_checks_present=target_checks_ok,
        source_decision=source_decision,
        target_decision=target_decision,
    )


def _choose_pilot(transitions: Sequence[TransitionResult]) -> TransitionResult | None:
    certified = [item for item in transitions if item.status == "certified"]
    if not certified:
        return None

    preferred_step2 = [item for item in certified if (item.target_n - item.source_n) == 2]
    if preferred_step2:
        return sorted(preferred_step2, key=lambda item: (item.source_n, item.target_n))[0]
    return sorted(certified, key=lambda item: (item.target_n - item.source_n, item.source_n, item.target_n))[0]


def _build_hypothesis_payload(
    transitions: Sequence[TransitionResult],
    pilot: TransitionResult | None,
    hypothesis_id: str,
    required_core_family: str | None,
) -> Dict[str, Any]:
    return {
        "hypothesis_id": hypothesis_id,
        "statement": "If H(n) holds and bridge prerequisites are certified, then H(n') holds for the tested finite transition n->n'.",
        "H_n_definition": {
            "witness_found": True,
            "non_similarity_decision": True,
            "required_separating_checks": REQUIRED_SEPARATING_CHECKS,
            "required_core_family": required_core_family,
        },
        "tested_transitions": [asdict(item) for item in transitions],
        "pilot_transition": asdict(pilot) if pilot is not None else None,
        "pilot_status": "certified" if pilot is not None else "blocked",
        "notes": [
            "A certified pilot transition is a finite bridge witness, not yet a universal n->n+2 theorem.",
            "Blocked transitions identify concrete data gaps for the next densification target.",
        ],
    }


def _build_markdown_report(transitions: Sequence[TransitionResult], pilot: TransitionResult | None) -> str:
    lines: List[str] = []
    lines.append("# Bridge Step Verification #91")
    lines.append("")
    lines.append("## Transition Checks")
    lines.append("")
    lines.append("| Transition | Status | Source witness | Target witness | Source checks ok | Target checks ok |")
    lines.append("|---|---|:---:|:---:|:---:|:---:|")
    for item in transitions:
        lines.append(
            f"| {item.source_n}->{item.target_n} | {item.status} | {item.source_witness} | {item.target_witness} | {item.source_required_checks_present} | {item.target_required_checks_present} |"
        )
    lines.append("")

    for item in transitions:
        if item.blockers:
            lines.append(f"- blockers for {item.source_n}->{item.target_n}: {'; '.join(item.blockers)}")

    lines.append("")
    lines.append("## Pilot Result")
    lines.append("")
    if pilot is None:
        lines.append("- No certified transition available yet.")
    else:
        lines.append(f"- Certified pilot transition: {pilot.source_n}->{pilot.target_n}")
        lines.append("- This is the current machine-checkable finite bridge witness.")
        if (pilot.target_n - pilot.source_n) != 2:
            lines.append("- Note: this pilot is a longer-step surrogate; n->n+2 remains open for this window.")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify finite bridge-step hypotheses for Erdos #91")
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument(
        "--transitions",
        default="22:24,24:26,22:26",
        help="comma-separated transitions formatted as source:target",
    )
    parser.add_argument("--hypothesis-id", default="H91-bridge-step-v1", help="identifier for this bridge hypothesis run")
    parser.add_argument(
        "--required-core-family",
        default="any",
        help="required seed family for both endpoints; default 'any' disables family gating",
    )
    parser.add_argument("--out-json", default="results/bridge_step_hypothesis_91.json", help="output JSON hypothesis path")
    parser.add_argument("--out-md", default="results/bridge_step_verification_91.md", help="output markdown report path")
    parser.add_argument("--strict", action="store_true", help="exit non-zero unless at least one certified transition exists")
    args = parser.parse_args()

    root = Path(args.root)
    required_core_family = args.required_core_family.strip()
    if required_core_family.lower() in {"", "any", "none"}:
        required_core_family = None

    transitions = [
        _evaluate_transition(root, source, target, required_core_family)
        for source, target in _parse_transitions(args.transitions)
    ]
    pilot = _choose_pilot(transitions)

    hypothesis = _build_hypothesis_payload(
        transitions=transitions,
        pilot=pilot,
        hypothesis_id=args.hypothesis_id,
        required_core_family=required_core_family,
    )
    report = _build_markdown_report(transitions, pilot)

    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(hypothesis, indent=2) + "\n", encoding="utf-8")

    out_md = Path(args.out_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(report + "\n", encoding="utf-8")

    print(report)
    print(f"Saved bridge hypothesis JSON to {out_json}")
    print(f"Saved bridge verification report to {out_md}")

    if args.strict and pilot is None:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
