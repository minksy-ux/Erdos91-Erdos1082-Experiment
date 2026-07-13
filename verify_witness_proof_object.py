#!/usr/bin/env python3
"""Verify non-similarity proof objects embedded in witness JSON artifacts.

This script re-checks evidence-grade claims from certificate JSON files
without re-running the search pipeline.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from erdos_distance_explorer import shape_similarity_distance, signature_from_points


@dataclass
class CheckResult:
    name: str
    expected: bool
    actual: bool
    details: str


def _normalized_sq_spectrum(points: np.ndarray, tol: float = 1e-10) -> Tuple[float, ...]:
    sq_vals: List[float] = []
    for i in range(len(points) - 1):
        for j in range(i + 1, len(points)):
            delta = points[i] - points[j]
            sq_vals.append(float(delta @ delta))
    if not sq_vals:
        return tuple()
    base = min(v for v in sq_vals if v > 0.0)
    normalized = [round((v / base) / tol) * tol for v in sq_vals]
    return tuple(sorted(normalized))


def _normalized_area2_spectrum(points: np.ndarray, tol: float = 1e-10) -> Tuple[float, ...]:
    vals: List[float] = []
    n = len(points)
    for i in range(n - 2):
        pi = points[i]
        for j in range(i + 1, n - 1):
            v1 = points[j] - pi
            for k in range(j + 1, n):
                v2 = points[k] - pi
                area2 = abs(float(v1[0] * v2[1] - v1[1] * v2[0]))
                if area2 > tol:
                    vals.append(area2 * area2)
    if not vals:
        return tuple()
    base = min(vals)
    normalized = [round((v / base) / tol) * tol for v in vals]
    return tuple(sorted(normalized))


def _normalized_gram_eigen_spectrum(points: np.ndarray, tol: float = 1e-10) -> Tuple[float, ...]:
    centered = points - points.mean(axis=0)
    gram = centered @ centered.T
    eigvals = np.linalg.eigvalsh(gram)
    positive = [float(v) for v in eigvals if v > tol]
    if not positive:
        return tuple()
    top = max(positive)
    normalized = [round((v / top) / tol) * tol for v in sorted(positive, reverse=True)]
    return tuple(normalized)


def _build_mismatch_certificate(a: Tuple[float, ...], b: Tuple[float, ...], tol: float) -> Dict[str, Any]:
    if len(a) != len(b):
        return {
            "mismatch_detected": True,
            "certified_mismatch": True,
            "certified_lower_bound": None,
            "reason": "length_mismatch",
        }

    diffs = [abs(float(x) - float(y)) for x, y in zip(a, b)]
    mismatch_diffs = [d for d in diffs if d > 0.0]
    if not mismatch_diffs:
        return {
            "mismatch_detected": False,
            "certified_mismatch": False,
            "certified_lower_bound": 0.0,
            "reason": "no_mismatch",
        }

    min_diff = min(mismatch_diffs)
    lower_bound = max(0.0, min_diff - tol)
    return {
        "mismatch_detected": True,
        "certified_mismatch": lower_bound > 0.0,
        "certified_lower_bound": lower_bound,
        "reason": "value_mismatch",
    }


def _load_points(payload: Dict[str, Any], key: str) -> np.ndarray:
    raw = payload["witness"][key]["canonical_normalized_points"]
    return np.array(raw, dtype=float)


def verify_payload(payload: Dict[str, Any], invariant_tol: float) -> Tuple[bool, List[CheckResult], bool]:
    if "witness_found" not in payload or "non_similarity_proof_object" not in payload:
        # Not a witness certificate JSON payload.
        return True, [], False

    if not payload.get("witness_found", False):
        # No witness pair exists, so no positive non-similarity claim to verify.
        return True, [], False

    proof = payload.get("non_similarity_proof_object", {})
    checks_declared = {
        str(item.get("name")): bool(item.get("passed"))
        for item in proof.get("checks", [])
        if "name" in item
    }

    points_a = _load_points(payload, "candidate_a")
    points_b = _load_points(payload, "candidate_b")

    exact_a = int(payload["witness"]["candidate_a"]["exact_distinct_sq"])
    exact_b = int(payload["witness"]["candidate_b"]["exact_distinct_sq"])
    shape_distance = float(payload["witness"]["shape_distance"])
    shape_tol = float(payload.get("shape_tol", 0.0))

    actual_equal_exact = exact_a == exact_b
    actual_shape_sep = shape_distance > shape_tol
    sig_equal = signature_from_points(points_a, tol=1e-6) == signature_from_points(points_b, tol=1e-6)
    actual_sig_mismatch = not sig_equal
    spectrum_equal = _normalized_sq_spectrum(points_a, tol=invariant_tol) == _normalized_sq_spectrum(points_b, tol=invariant_tol)
    actual_spectrum_mismatch = not spectrum_equal
    area_spectrum_equal = _normalized_area2_spectrum(points_a, tol=invariant_tol) == _normalized_area2_spectrum(points_b, tol=invariant_tol)
    actual_area_spectrum_mismatch = not area_spectrum_equal
    gram_spectrum_equal = _normalized_gram_eigen_spectrum(points_a, tol=invariant_tol) == _normalized_gram_eigen_spectrum(points_b, tol=invariant_tol)
    actual_gram_spectrum_mismatch = not gram_spectrum_equal
    sq_cert = _build_mismatch_certificate(
        _normalized_sq_spectrum(points_a, tol=invariant_tol),
        _normalized_sq_spectrum(points_b, tol=invariant_tol),
        invariant_tol,
    )
    area_cert = _build_mismatch_certificate(
        _normalized_area2_spectrum(points_a, tol=invariant_tol),
        _normalized_area2_spectrum(points_b, tol=invariant_tol),
        invariant_tol,
    )
    gram_cert = _build_mismatch_certificate(
        _normalized_gram_eigen_spectrum(points_a, tol=invariant_tol),
        _normalized_gram_eigen_spectrum(points_b, tol=invariant_tol),
        invariant_tol,
    )

    measured: List[CheckResult] = [
        CheckResult(
            name="equal_exact_objective",
            expected=checks_declared.get("equal_exact_objective", actual_equal_exact),
            actual=actual_equal_exact,
            details=f"exact_a={exact_a}, exact_b={exact_b}",
        ),
        CheckResult(
            name="shape_distance_separated",
            expected=checks_declared.get("shape_distance_separated", actual_shape_sep),
            actual=actual_shape_sep,
            details=f"shape_distance={shape_distance:.6f}, shape_tol={shape_tol}",
        ),
        CheckResult(
            name="distance_signature_mismatch",
            expected=checks_declared.get("distance_signature_mismatch", actual_sig_mismatch),
            actual=actual_sig_mismatch,
            details=f"signature_equal={sig_equal}",
        ),
        CheckResult(
            name="normalized_sq_spectrum_mismatch",
            expected=checks_declared.get("normalized_sq_spectrum_mismatch", actual_spectrum_mismatch),
            actual=actual_spectrum_mismatch,
            details=f"spectrum_equal={spectrum_equal}, invariant_tol={invariant_tol}",
        ),
        CheckResult(
            name="normalized_area2_spectrum_mismatch",
            expected=checks_declared.get("normalized_area2_spectrum_mismatch", actual_area_spectrum_mismatch),
            actual=actual_area_spectrum_mismatch,
            details=f"area_spectrum_equal={area_spectrum_equal}, invariant_tol={invariant_tol}",
        ),
        CheckResult(
            name="normalized_gram_eigen_spectrum_mismatch",
            expected=checks_declared.get("normalized_gram_eigen_spectrum_mismatch", actual_gram_spectrum_mismatch),
            actual=actual_gram_spectrum_mismatch,
            details=f"gram_spectrum_equal={gram_spectrum_equal}, invariant_tol={invariant_tol}",
        ),
        CheckResult(
            name="normalized_sq_spectrum_certified_mismatch",
            expected=checks_declared.get("normalized_sq_spectrum_certified_mismatch", bool(sq_cert["certified_mismatch"])),
            actual=bool(sq_cert["certified_mismatch"]),
            details=f"lower_bound={sq_cert.get('certified_lower_bound')}, invariant_tol={invariant_tol}",
        ),
        CheckResult(
            name="normalized_area2_spectrum_certified_mismatch",
            expected=checks_declared.get("normalized_area2_spectrum_certified_mismatch", bool(area_cert["certified_mismatch"])),
            actual=bool(area_cert["certified_mismatch"]),
            details=f"lower_bound={area_cert.get('certified_lower_bound')}, invariant_tol={invariant_tol}",
        ),
        CheckResult(
            name="normalized_gram_eigen_spectrum_certified_mismatch",
            expected=checks_declared.get("normalized_gram_eigen_spectrum_certified_mismatch", bool(gram_cert["certified_mismatch"])),
            actual=bool(gram_cert["certified_mismatch"]),
            details=f"lower_bound={gram_cert.get('certified_lower_bound')}, invariant_tol={invariant_tol}",
        ),
    ]

    checks_ok = all(item.expected == item.actual for item in measured)

    separating = [
        item.name
        for item in measured
        if item.actual
        and item.name
        in {
            "distance_signature_mismatch",
            "normalized_sq_spectrum_mismatch",
            "normalized_area2_spectrum_mismatch",
            "normalized_gram_eigen_spectrum_mismatch",
            "normalized_sq_spectrum_certified_mismatch",
            "normalized_area2_spectrum_certified_mismatch",
            "normalized_gram_eigen_spectrum_certified_mismatch",
        }
    ]
    decision_expected = bool(proof.get("decision", False))
    decision_actual = actual_equal_exact and len(separating) > 0
    decision_ok = decision_expected == decision_actual

    return checks_ok and decision_ok, measured, True


def _expand_inputs(inputs: List[str]) -> List[Path]:
    expanded: List[Path] = []
    for item in inputs:
        p = Path(item)
        if p.is_dir():
            expanded.extend(sorted(p.glob("*.json")))
        else:
            expanded.append(p)
    return expanded


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify witness non-similarity proof objects from JSON artifacts")
    parser.add_argument("--inputs", nargs="+", required=True, help="JSON files or directories containing witness JSON files")
    parser.add_argument("--invariant-tol", type=float, default=1e-10, help="tolerance for normalized spectrum checks")
    parser.add_argument("--strict", action="store_true", help="exit non-zero if any file fails verification")
    args = parser.parse_args()

    if args.invariant_tol <= 0:
        parser.error("--invariant-tol must be > 0")

    paths = _expand_inputs(args.inputs)
    if not paths:
        raise SystemExit("No JSON inputs found")

    failed = 0
    verified = 0

    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        ok, checks, applicable = verify_payload(payload, invariant_tol=args.invariant_tol)

        print(f"\nVerifying: {path}")
        if not applicable:
            print("  status: SKIP (no witness_found claim)")
            continue

        for item in checks:
            status = "PASS" if item.expected == item.actual else "FAIL"
            print(
                f"  [{status}] {item.name}: expected={item.expected} actual={item.actual} | {item.details}"
            )

        if ok:
            print("  overall: PASS")
            verified += 1
        else:
            print("  overall: FAIL")
            failed += 1

    print(f"\nSummary: verified={verified}, failed={failed}, total_inputs={len(paths)}")

    if args.strict and failed > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
