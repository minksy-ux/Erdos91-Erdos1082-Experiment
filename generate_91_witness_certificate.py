#!/usr/bin/env python3
"""Generate a #91 witness certificate from experiment DB rows.

The certificate is computational evidence, not a formal proof.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from erdos_distance_explorer import shape_similarity_distance, signature_from_points, sort_points_canonical


@dataclass
class CandidateRow:
    id: int
    n: int
    run_tag: str
    trial_id: int
    seed_family: str
    exact_distinct_sq: int
    exact_min_distinct_from_point: int
    exact_max_distinct_from_point: int
    exact_is_valid: bool
    points: np.ndarray


def _load_candidates(db_path: str, n: int, run_tag: Optional[str]) -> List[CandidateRow]:
    query = (
        "SELECT id, n, run_tag, trial_id, seed_family, exact_distinct_sq, "
        "exact_min_distinct_from_point, exact_max_distinct_from_point, exact_is_valid, points_json "
        "FROM experiments WHERE n = ? AND exact_distinct_sq IS NOT NULL AND exact_is_valid = 1"
    )
    params: List[Any] = [n]
    if run_tag:
        query += " AND run_tag = ?"
        params.append(run_tag)
    query += " ORDER BY exact_distinct_sq ASC, exact_min_distinct_from_point DESC, energy ASC"

    rows: List[CandidateRow] = []
    with sqlite3.connect(db_path) as conn:
        for raw in conn.execute(query, params).fetchall():
            points = np.array(json.loads(raw[9]), dtype=float)
            rows.append(
                CandidateRow(
                    id=int(raw[0]),
                    n=int(raw[1]),
                    run_tag=str(raw[2]),
                    trial_id=int(raw[3]),
                    seed_family=str(raw[4]),
                    exact_distinct_sq=int(raw[5]),
                    exact_min_distinct_from_point=int(raw[6]),
                    exact_max_distinct_from_point=int(raw[7]),
                    exact_is_valid=bool(raw[8]),
                    points=points,
                )
            )
    return rows


def _distance_multiplicity_profile(points: np.ndarray, tol: float = 1e-6) -> List[int]:
    counts: Dict[float, int] = {}
    for i in range(len(points) - 1):
        for j in range(i + 1, len(points)):
            d = float(np.linalg.norm(points[i] - points[j]))
            key = round(d / tol) * tol
            counts[key] = counts.get(key, 0) + 1
    return sorted(counts.values(), reverse=True)


def _profile_preview(profile: List[int], take: int = 16) -> str:
    if not profile:
        return "empty"
    return ",".join(str(v) for v in profile[:take])


def _pick_non_similar_pair(cands: List[CandidateRow], tol: float) -> Optional[Tuple[CandidateRow, CandidateRow, float]]:
    if len(cands) < 2:
        return None
    best: Optional[Tuple[CandidateRow, CandidateRow, float]] = None
    for i in range(len(cands) - 1):
        for j in range(i + 1, len(cands)):
            d = shape_similarity_distance(cands[i].points, cands[j].points)
            if d <= tol:
                continue
            if best is None or d > best[2]:
                best = (cands[i], cands[j], float(d))
    return best


def _normalize_points(points: np.ndarray) -> np.ndarray:
    centered = points - points.mean(axis=0)
    norm = np.linalg.norm(centered)
    if norm <= 1e-12:
        return centered
    return centered / norm


def _canonical_normalized_points(points: np.ndarray) -> np.ndarray:
    return _normalize_points(sort_points_canonical(points))


def _format_points(points: np.ndarray, decimals: int = 8) -> List[str]:
    lines: List[str] = []
    for idx, p in enumerate(points):
        x = f"{p[0]:.{decimals}f}"
        y = f"{p[1]:.{decimals}f}"
        lines.append(f"{idx:02d}: ({x}, {y})")
    return lines


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
    """Similarity-invariant spectrum of squared doubled-triangle areas.

    For each triple (i, j, k), use area2 = |(p_j - p_i) x (p_k - p_i)|.
    Under similarity transforms, area2 scales by s^2, so area2^2 scales by s^4.
    Normalizing by the minimum positive value makes the multiset scale-invariant.
    """
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
    """Similarity-invariant centered Gram eigenvalue ratios.

    Let X be centered coordinates (rows are points), G = X X^T.
    Non-zero eigenvalues of G are invariant under orthogonal transforms and scale by s^2.
    Dividing by the largest positive eigenvalue removes scale.
    """
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
    """Build an interval-style mismatch certificate for rounded invariant spectra.

    Each rounded value has effective uncertainty up to tol/2 from quantization.
    For aligned mismatching entries, a conservative lower bound is
    max(0, |a_i - b_i| - tol).
    Positive lower bound certifies true mismatch under this uncertainty model.
    """
    if len(a) != len(b):
        return {
            "length_a": len(a),
            "length_b": len(b),
            "mismatch_detected": True,
            "certified_mismatch": True,
            "certified_lower_bound": None,
            "reason": "length_mismatch",
            "comparison_tol": tol,
        }

    diffs = [abs(float(x) - float(y)) for x, y in zip(a, b)]
    mismatch_diffs = [d for d in diffs if d > 0.0]
    if not mismatch_diffs:
        return {
            "length_a": len(a),
            "length_b": len(b),
            "mismatch_detected": False,
            "certified_mismatch": False,
            "certified_lower_bound": 0.0,
            "reason": "no_mismatch",
            "comparison_tol": tol,
        }

    min_diff = min(mismatch_diffs)
    lower_bound = max(0.0, min_diff - tol)
    return {
        "length_a": len(a),
        "length_b": len(b),
        "mismatch_detected": True,
        "certified_mismatch": lower_bound > 0.0,
        "certified_lower_bound": lower_bound,
        "min_observed_mismatch": min_diff,
        "reason": "value_mismatch",
        "comparison_tol": tol,
    }


def _build_non_similarity_proof_object(
    *,
    a: CandidateRow,
    b: CandidateRow,
    shape_distance: float,
    shape_tol: float,
    invariant_tol: float,
) -> Dict[str, Any]:
    sig_a = signature_from_points(a.points, tol=1e-6)
    sig_b = signature_from_points(b.points, tol=1e-6)
    spectrum_a = _normalized_sq_spectrum(a.points, tol=invariant_tol)
    spectrum_b = _normalized_sq_spectrum(b.points, tol=invariant_tol)
    area_spectrum_a = _normalized_area2_spectrum(a.points, tol=invariant_tol)
    area_spectrum_b = _normalized_area2_spectrum(b.points, tol=invariant_tol)
    gram_spectrum_a = _normalized_gram_eigen_spectrum(a.points, tol=invariant_tol)
    gram_spectrum_b = _normalized_gram_eigen_spectrum(b.points, tol=invariant_tol)
    spectrum_cert = _build_mismatch_certificate(spectrum_a, spectrum_b, invariant_tol)
    area_spectrum_cert = _build_mismatch_certificate(area_spectrum_a, area_spectrum_b, invariant_tol)
    gram_spectrum_cert = _build_mismatch_certificate(gram_spectrum_a, gram_spectrum_b, invariant_tol)

    checks: List[Dict[str, Any]] = [
        {
            "name": "equal_exact_objective",
            "passed": a.exact_distinct_sq == b.exact_distinct_sq,
            "details": f"A={a.exact_distinct_sq}, B={b.exact_distinct_sq}",
        },
        {
            "name": "shape_distance_separated",
            "passed": shape_distance > shape_tol,
            "details": f"shape_distance={shape_distance:.6f}, tolerance={shape_tol}",
        },
        {
            "name": "distance_signature_mismatch",
            "passed": sig_a != sig_b,
            "details": f"signature_equal={sig_a == sig_b}",
        },
        {
            "name": "normalized_sq_spectrum_mismatch",
            "passed": spectrum_a != spectrum_b,
            "details": f"spectrum_equal={spectrum_a == spectrum_b}, invariant_tol={invariant_tol}",
        },
        {
            "name": "normalized_area2_spectrum_mismatch",
            "passed": area_spectrum_a != area_spectrum_b,
            "details": f"area_spectrum_equal={area_spectrum_a == area_spectrum_b}, invariant_tol={invariant_tol}",
        },
        {
            "name": "normalized_gram_eigen_spectrum_mismatch",
            "passed": gram_spectrum_a != gram_spectrum_b,
            "details": f"gram_spectrum_equal={gram_spectrum_a == gram_spectrum_b}, invariant_tol={invariant_tol}",
        },
        {
            "name": "normalized_sq_spectrum_certified_mismatch",
            "passed": bool(spectrum_cert["certified_mismatch"]),
            "details": f"lower_bound={spectrum_cert.get('certified_lower_bound')}, invariant_tol={invariant_tol}",
        },
        {
            "name": "normalized_area2_spectrum_certified_mismatch",
            "passed": bool(area_spectrum_cert["certified_mismatch"]),
            "details": f"lower_bound={area_spectrum_cert.get('certified_lower_bound')}, invariant_tol={invariant_tol}",
        },
        {
            "name": "normalized_gram_eigen_spectrum_certified_mismatch",
            "passed": bool(gram_spectrum_cert["certified_mismatch"]),
            "details": f"lower_bound={gram_spectrum_cert.get('certified_lower_bound')}, invariant_tol={invariant_tol}",
        },
    ]

    passed_names = [check["name"] for check in checks if check["passed"]]
    separating = [
        name
        for name in passed_names
        if name
        in {
            "distance_signature_mismatch",
            "normalized_sq_spectrum_mismatch",
            "normalized_area2_spectrum_mismatch",
            "normalized_gram_eigen_spectrum_mismatch",
        }
    ]

    verification_log = [
        "Input rows loaded from exact-valid experiment records.",
        "Witness pair selected among exact-objective minimizers.",
        f"Shape-separation check used threshold {shape_tol}.",
        f"Similarity-invariant normalized squared-spectrum compared at tol {invariant_tol}.",
    ]

    return {
        "status": "evidence-grade",
        "claim": "Candidate A and Candidate B are non-similar minimizers.",
        "decision": len(separating) > 0 and (a.exact_distinct_sq == b.exact_distinct_sq),
        "separating_checks": separating,
        "checks": checks,
        "verification_log": verification_log,
        "invariant_snapshots": {
            "normalized_sq_spectrum": {
                "a": list(spectrum_a),
                "b": list(spectrum_b),
                "mismatch_certificate": spectrum_cert,
            },
            "normalized_area2_spectrum": {
                "a": list(area_spectrum_a),
                "b": list(area_spectrum_b),
                "mismatch_certificate": area_spectrum_cert,
            },
            "normalized_gram_eigen_spectrum": {
                "a": list(gram_spectrum_a),
                "b": list(gram_spectrum_b),
                "mismatch_certificate": gram_spectrum_cert,
            },
        },
        "disclaimer": "This object is numerical evidence with explicit checks; it is not a universal formal proof.",
    }


def _parse_n_values(text: str) -> List[int]:
    values: List[int] = []
    for token in text.split(","):
        stripped = token.strip()
        if stripped:
            values.append(int(stripped))
    return values


def _resolve_output_path(raw: str, n: int, default_pattern: str) -> str:
    text = raw.strip()
    if not text:
        return default_pattern.format(n=n)
    if "{n}" in text:
        return text.format(n=n)
    return text


def _build_certificate(
    *,
    db_path: str,
    n: int,
    run_tag: Optional[str],
    shape_tol: float,
    coord_decimals: int,
    invariant_tol: float,
) -> Tuple[List[str], Dict[str, Any]]:
    rows = _load_candidates(db_path, n, run_tag)
    if not rows:
        raise RuntimeError(f"No certified valid candidates found for n={n} and selected filters")

    best_exact = min(r.exact_distinct_sq for r in rows)
    minimizers = [r for r in rows if r.exact_distinct_sq == best_exact]
    pair = _pick_non_similar_pair(minimizers, tol=shape_tol)

    lines: List[str] = []
    lines.append(f"# Erd\u0151s #91 Witness Certificate (n={n})")
    lines.append("")
    lines.append("This is computational evidence, not a formal proof.")
    lines.append("")
    lines.append("## Setup")
    lines.append(f"- Database: {db_path}")
    lines.append(f"- n: {n}")
    lines.append(f"- run_tag filter: {run_tag if run_tag else 'all'}")
    lines.append(f"- best exact distinct squared-distance count: {best_exact}")
    lines.append(f"- certified minimizer count in scope: {len(minimizers)}")
    lines.append(f"- shape tolerance: {shape_tol}")
    lines.append("")

    if pair is None:
        lines.append("## Result")
        lines.append("No non-similar pair was found under the selected shape tolerance.")
        payload: Dict[str, Any] = {
            "n": n,
            "db_path": db_path,
            "run_tag": run_tag,
            "shape_tol": shape_tol,
            "best_exact_distinct_sq": best_exact,
            "certified_minimizer_count": len(minimizers),
            "witness_found": False,
            "non_similarity_proof_object": {
                "status": "not-applicable",
                "claim": "No witness pair found.",
                "decision": False,
                "checks": [],
                "verification_log": ["No non-similar pair available under configured tolerance."],
            },
        }
    else:
        a, b, d = pair
        sig_a = signature_from_points(a.points, tol=1e-6)
        sig_b = signature_from_points(b.points, tol=1e-6)
        prof_a = _distance_multiplicity_profile(a.points)
        prof_b = _distance_multiplicity_profile(b.points)
        points_a = _canonical_normalized_points(a.points)
        points_b = _canonical_normalized_points(b.points)

        lines.append("## Result")
        lines.append("Found a non-similar certified minimizer pair with equal exact objective.")
        lines.append("")
        lines.append("## Witness Pair")
        lines.append(f"- Candidate A: id={a.id}, run_tag={a.run_tag}, trial={a.trial_id}, seed_family={a.seed_family}")
        lines.append(f"- Candidate B: id={b.id}, run_tag={b.run_tag}, trial={b.trial_id}, seed_family={b.seed_family}")
        lines.append(f"- Exact objective equality: {a.exact_distinct_sq} = {b.exact_distinct_sq}")
        lines.append(
            f"- Per-point exact ranges: A[min,max]=[{a.exact_min_distinct_from_point},{a.exact_max_distinct_from_point}], "
            f"B[min,max]=[{b.exact_min_distinct_from_point},{b.exact_max_distinct_from_point}]"
        )
        lines.append(f"- Shape distance: {d:.6f} (> tol={shape_tol})")
        lines.append(f"- Signature equality: {sig_a == sig_b}")
        lines.append(f"- Multiplicity-profile equality: {prof_a == prof_b}")
        lines.append(f"- A profile preview: {_profile_preview(prof_a)}")
        lines.append(f"- B profile preview: {_profile_preview(prof_b)}")
        lines.append("")
        lines.append("## Canonical Normalized Coordinates")
        lines.append("Coordinates are centered, scaled to unit Frobenius norm, and angle-sorted.")
        lines.append("")
        lines.append("### Candidate A")
        lines.extend([f"- {row}" for row in _format_points(points_a, decimals=coord_decimals)])
        lines.append("")
        lines.append("### Candidate B")
        lines.extend([f"- {row}" for row in _format_points(points_b, decimals=coord_decimals)])

        proof_object = _build_non_similarity_proof_object(
            a=a,
            b=b,
            shape_distance=d,
            shape_tol=shape_tol,
            invariant_tol=invariant_tol,
        )
        lines.append("")
        lines.append("## Non-Similarity Proof Object")
        lines.append("Evidence-grade check bundle for this witness pair.")
        lines.append(f"- Decision: {proof_object['decision']}")
        lines.append(f"- Separating checks: {', '.join(proof_object['separating_checks']) if proof_object['separating_checks'] else 'none'}")
        lines.append(f"- Status: {proof_object['status']}")
        lines.append(f"- Disclaimer: {proof_object['disclaimer']}")

        payload = {
            "n": n,
            "db_path": db_path,
            "run_tag": run_tag,
            "shape_tol": shape_tol,
            "best_exact_distinct_sq": best_exact,
            "certified_minimizer_count": len(minimizers),
            "witness_found": True,
            "non_similarity_proof_object": proof_object,
            "witness": {
                "shape_distance": d,
                "signature_equal": sig_a == sig_b,
                "multiplicity_profile_equal": prof_a == prof_b,
                "candidate_a": {
                    "id": a.id,
                    "run_tag": a.run_tag,
                    "trial_id": a.trial_id,
                    "seed_family": a.seed_family,
                    "exact_distinct_sq": a.exact_distinct_sq,
                    "exact_min_distinct_from_point": a.exact_min_distinct_from_point,
                    "exact_max_distinct_from_point": a.exact_max_distinct_from_point,
                    "canonical_normalized_points": points_a.tolist(),
                },
                "candidate_b": {
                    "id": b.id,
                    "run_tag": b.run_tag,
                    "trial_id": b.trial_id,
                    "seed_family": b.seed_family,
                    "exact_distinct_sq": b.exact_distinct_sq,
                    "exact_min_distinct_from_point": b.exact_min_distinct_from_point,
                    "exact_max_distinct_from_point": b.exact_max_distinct_from_point,
                    "canonical_normalized_points": points_b.tolist(),
                },
            },
        }

    return lines, payload


def _write_one_certificate(
    *,
    db_path: str,
    n: int,
    run_tag: Optional[str],
    shape_tol: float,
    coord_decimals: int,
    invariant_tol: float,
    out_path: str,
    json_out_path: str,
) -> Dict[str, Any]:
    lines, payload = _build_certificate(
        db_path=db_path,
        n=n,
        run_tag=run_tag,
        shape_tol=shape_tol,
        coord_decimals=coord_decimals,
        invariant_tol=invariant_tol,
    )

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    json_out = Path(json_out_path)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("\n".join(lines))
    print(f"Saved witness certificate to {out}")
    print(f"Saved witness payload to {json_out}")

    return {
        "n": n,
        "certificate_path": str(out),
        "json_path": str(json_out),
        "witness_found": bool(payload.get("witness_found", False)),
        "best_exact_distinct_sq": payload.get("best_exact_distinct_sq"),
        "certified_minimizer_count": payload.get("certified_minimizer_count"),
        "shape_distance": payload.get("witness", {}).get("shape_distance") if payload.get("witness") else None,
    }


def _write_appendix(path: str, db_path: str, run_tag: Optional[str], shape_tol: float, rows: List[Dict[str, Any]]) -> None:
    lines: List[str] = []
    lines.append("# Erd\u0151s #91 Witness Appendix")
    lines.append("")
    lines.append("This appendix aggregates per-n witness certificates generated by the computational pipeline.")
    lines.append("")
    lines.append("## Setup")
    lines.append(f"- Database: {db_path}")
    lines.append(f"- run_tag filter: {run_tag if run_tag else 'all'}")
    lines.append(f"- shape tolerance: {shape_tol}")
    lines.append(f"- n values: {','.join(str(item['n']) for item in rows)}")
    lines.append("")
    lines.append("## Summary")
    lines.append("| n | Witness Found | Best Exact Distinct Sq | Certified Minimizers | Shape Distance | Certificate | JSON |")
    lines.append("|---:|:---:|---:|---:|---:|---|---|")
    for row in rows:
        shape_distance = "-"
        if row["shape_distance"] is not None:
            shape_distance = f"{float(row['shape_distance']):.6f}"
        lines.append(
            f"| {row['n']} | {row['witness_found']} | {row['best_exact_distinct_sq']} | "
            f"{row['certified_minimizer_count']} | {shape_distance} | {row['certificate_path']} | {row['json_path']} |"
        )

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved witness appendix to {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate #91 witness certificate from experiment DB")
    parser.add_argument("--db-path", type=str, default="results/proof_search_91.db", help="path to SQLite database")
    selector_group = parser.add_mutually_exclusive_group(required=True)
    selector_group.add_argument("--n", type=int, help="single n value to extract witness from")
    selector_group.add_argument("--n-list", type=str, help="comma-separated n values for batch certificate generation")
    parser.add_argument("--run-tag", type=str, default="", help="optional run_tag filter")
    parser.add_argument("--shape-tol", type=float, default=0.01, help="shape similarity tolerance")
    parser.add_argument("--invariant-tol", type=float, default=1e-10, help="tolerance for normalized spectrum invariant comparisons")
    parser.add_argument("--out", type=str, default="", help="output markdown path")
    parser.add_argument("--json-out", type=str, default="", help="optional output JSON path")
    parser.add_argument("--appendix-out", type=str, default="", help="optional markdown appendix path for batch mode")
    parser.add_argument("--coord-decimals", type=int, default=8, help="decimal places for printed coordinates")
    args = parser.parse_args()

    if args.shape_tol <= 0:
        parser.error("--shape-tol must be > 0")
    if args.invariant_tol <= 0:
        parser.error("--invariant-tol must be > 0")
    if args.coord_decimals < 1:
        parser.error("--coord-decimals must be >= 1")

    if args.n is not None:
        n_values = [args.n]
    else:
        n_values = _parse_n_values(args.n_list or "")
        if not n_values:
            parser.error("--n-list must contain at least one integer")

    if any(n < 3 for n in n_values):
        parser.error("all n values must be >= 3")

    if len(n_values) > 1 and args.out.strip() and "{n}" not in args.out:
        parser.error("--out must include '{n}' placeholder when using --n-list")
    if len(n_values) > 1 and args.json_out.strip() and "{n}" not in args.json_out:
        parser.error("--json-out must include '{n}' placeholder when using --n-list")
    if args.appendix_out.strip() and len(n_values) == 1:
        parser.error("--appendix-out is only used with --n-list")

    run_tag = args.run_tag.strip() or None
    batch_rows: List[Dict[str, Any]] = []
    for n in n_values:
        output_path = _resolve_output_path(args.out, n, "results/erdos91_witness_n{n}.md")
        json_output_path = _resolve_output_path(args.json_out, n, "results/erdos91_witness_n{n}.json")
        batch_rows.append(
            _write_one_certificate(
                db_path=args.db_path,
                n=n,
                run_tag=run_tag,
                shape_tol=args.shape_tol,
                coord_decimals=args.coord_decimals,
                invariant_tol=args.invariant_tol,
                out_path=output_path,
                json_out_path=json_output_path,
            )
        )

    if len(n_values) > 1:
        appendix_path = args.appendix_out.strip() or "results/erdos91_witness_appendix.md"
        _write_appendix(appendix_path, args.db_path, run_tag, args.shape_tol, batch_rows)


if __name__ == "__main__":
    main()
