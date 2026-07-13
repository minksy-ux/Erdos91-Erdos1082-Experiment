#!/usr/bin/env python3
"""Independent verifier for #91 witness proof objects.

This checker intentionally uses a separate implementation path from
verify_witness_proof_object.py and emits a standalone transcript.
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

from erdos_distance_explorer import shape_similarity_distance


@dataclass
class IndependentCheck:
    name: str
    passed: bool
    details: str


def _pairwise_sq(points: np.ndarray) -> np.ndarray:
    vals: List[float] = []
    n = len(points)
    for i in range(n - 1):
        for j in range(i + 1, n):
            d = points[i] - points[j]
            vals.append(float(d @ d))
    return np.array(vals, dtype=float)


def _normalized_distance_fingerprint(points: np.ndarray, tol: float) -> Tuple[float, ...]:
    sq = _pairwise_sq(points)
    if sq.size == 0:
        return tuple()
    base = float(np.min(sq[sq > 0])) if np.any(sq > 0) else 1.0
    ratio = sq / base
    rounded = np.round(ratio / tol) * tol
    return tuple(float(x) for x in np.sort(rounded))


def _normalized_radial_fingerprint(points: np.ndarray, tol: float) -> Tuple[float, ...]:
    centered = points - points.mean(axis=0)
    r = np.linalg.norm(centered, axis=1)
    if r.size == 0:
        return tuple()
    scale = float(np.max(r)) if np.max(r) > 0 else 1.0
    normalized = r / scale
    rounded = np.round(normalized / tol) * tol
    return tuple(float(x) for x in np.sort(rounded))


def _triangle_area_fingerprint(points: np.ndarray, tol: float) -> Tuple[float, ...]:
    vals: List[float] = []
    n = len(points)
    for i in range(n - 2):
        p0 = points[i]
        for j in range(i + 1, n - 1):
            v1 = points[j] - p0
            for k in range(j + 1, n):
                v2 = points[k] - p0
                area2 = abs(float(v1[0] * v2[1] - v1[1] * v2[0]))
                if area2 > tol:
                    vals.append(area2 * area2)
    if not vals:
        return tuple()
    arr = np.array(vals, dtype=float)
    base = float(np.min(arr)) if np.min(arr) > 0 else 1.0
    normalized = arr / base
    rounded = np.round(normalized / tol) * tol
    return tuple(float(x) for x in np.sort(rounded))


def _load_points(payload: Dict[str, Any], key: str) -> np.ndarray:
    return np.array(payload["witness"][key]["canonical_normalized_points"], dtype=float)


def verify_payload(payload: Dict[str, Any], tol: float) -> Tuple[bool, List[IndependentCheck], bool]:
    if not payload.get("witness_found", False):
        return True, [], False

    points_a = _load_points(payload, "candidate_a")
    points_b = _load_points(payload, "candidate_b")

    exact_a = int(payload["witness"]["candidate_a"]["exact_distinct_sq"])
    exact_b = int(payload["witness"]["candidate_b"]["exact_distinct_sq"])
    shape_tol = float(payload.get("shape_tol", 0.0))
    shape_distance = float(payload["witness"]["shape_distance"])

    dist_fp_a = _normalized_distance_fingerprint(points_a, tol)
    dist_fp_b = _normalized_distance_fingerprint(points_b, tol)

    radial_fp_a = _normalized_radial_fingerprint(points_a, tol)
    radial_fp_b = _normalized_radial_fingerprint(points_b, tol)

    area_fp_a = _triangle_area_fingerprint(points_a, tol)
    area_fp_b = _triangle_area_fingerprint(points_b, tol)

    procrustes = shape_similarity_distance(points_a, points_b)

    checks = [
        IndependentCheck(
            "equal_exact_objective",
            exact_a == exact_b,
            f"exact_a={exact_a}, exact_b={exact_b}",
        ),
        IndependentCheck(
            "shape_distance_separated",
            shape_distance > shape_tol,
            f"shape_distance={shape_distance:.6f}, tol={shape_tol:.6f}",
        ),
        IndependentCheck(
            "independent_procrustes_separated",
            procrustes > shape_tol,
            f"procrustes={procrustes:.6f}, tol={shape_tol:.6f}",
        ),
        IndependentCheck(
            "distance_fingerprint_mismatch",
            dist_fp_a != dist_fp_b,
            f"len_a={len(dist_fp_a)}, len_b={len(dist_fp_b)}",
        ),
        IndependentCheck(
            "radial_fingerprint_mismatch",
            radial_fp_a != radial_fp_b,
            f"len_a={len(radial_fp_a)}, len_b={len(radial_fp_b)}",
        ),
        IndependentCheck(
            "area_fingerprint_mismatch",
            area_fp_a != area_fp_b,
            f"len_a={len(area_fp_a)}, len_b={len(area_fp_b)}",
        ),
    ]

    # Decision requires exact equality and at least one independent separating fingerprint.
    separating = any(
        c.passed
        for c in checks
        if c.name in {"distance_fingerprint_mismatch", "radial_fingerprint_mismatch", "area_fingerprint_mismatch"}
    )
    decision = checks[0].passed and separating
    checks.append(
        IndependentCheck(
            "independent_decision",
            decision,
            "decision = equal_exact_objective AND any(independent fingerprint mismatch)",
        )
    )

    required_checks = {"equal_exact_objective", "independent_decision"}
    required_ok = all(c.passed for c in checks if c.name in required_checks)
    return required_ok, checks, True


def _expand_inputs(inputs: List[str]) -> List[Path]:
    out: List[Path] = []
    for item in inputs:
        p = Path(item)
        if p.is_dir():
            out.extend(sorted(p.glob("*.json")))
        elif p.is_file():
            out.append(p)
    return out


def _render_markdown(results: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    lines.append("# Independent Witness Verifier Transcript (#91)")
    lines.append("")
    lines.append("| File | Applicable | Pass | Checks Passed |")
    lines.append("|---|:---:|:---:|---:|")
    for row in results:
        lines.append(
            f"| {row['file']} | {row['applicable']} | {row['pass']} | {row['checks_passed']}/{row['checks_total']} |"
        )
    lines.append("")
    for row in results:
        lines.append(f"## {row['file']}")
        lines.append("")
        if not row["applicable"]:
            lines.append("- status: SKIP (no witness_found claim)")
            lines.append("")
            continue
        for c in row["checks"]:
            status = "PASS" if c["passed"] else "FAIL"
            lines.append(f"- [{status}] {c['name']}: {c['details']}")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Independent verifier for #91 witness proof objects")
    parser.add_argument("--inputs", nargs="+", required=True, help="JSON files or directories")
    parser.add_argument("--tol", type=float, default=1e-10, help="rounding tolerance for independent fingerprints")
    parser.add_argument("--out-md", type=str, default="results/independent_verifier_transcript_91.md")
    parser.add_argument("--out-json", type=str, default="results/independent_verifier_transcript_91.json")
    parser.add_argument("--strict", action="store_true", help="exit non-zero if any applicable file fails")
    args = parser.parse_args()

    if args.tol <= 0:
        parser.error("--tol must be > 0")

    paths = _expand_inputs(args.inputs)
    if not paths:
        print("No JSON inputs found; skipping independent verification.")
        return

    rows: List[Dict[str, Any]] = []
    failures = 0
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            rows.append(
                {
                    "file": str(path),
                    "applicable": False,
                    "pass": True,
                    "checks_total": 0,
                    "checks_passed": 0,
                    "checks": [],
                }
            )
            continue

        ok, checks, applicable = verify_payload(payload, tol=args.tol)
        if applicable and not ok:
            failures += 1

        rows.append(
            {
                "file": str(path),
                "applicable": applicable,
                "pass": ok,
                "checks_total": len(checks),
                "checks_passed": sum(1 for c in checks if c.passed),
                "checks": [
                    {"name": c.name, "passed": c.passed, "details": c.details}
                    for c in checks
                ],
            }
        )

    markdown = _render_markdown(rows)

    out_md = Path(args.out_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown, encoding="utf-8")

    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps({"results": rows}, indent=2) + "\n", encoding="utf-8")

    print(markdown)
    print(f"Saved independent verifier transcript to {out_md}")
    print(f"Saved independent verifier JSON to {out_json}")

    if args.strict and failures > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
