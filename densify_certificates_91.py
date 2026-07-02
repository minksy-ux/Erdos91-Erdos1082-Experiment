#!/usr/bin/env python3
"""Orchestrate densification of finite Erdős #91 certificates.

This script runs structured searches for a list of n values, reuses the
certified archive when requested, and refreshes the ladder / pattern artifacts
after the search batch completes.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class RunRecord:
    n: int
    command: List[str]
    returncode: int
    started_at: str
    finished_at: str


@dataclass
class WitnessRecord:
    n: int
    command: List[str]
    returncode: int
    json_path: str
    witness_found: bool
    started_at: str
    finished_at: str


def _parse_n_values(text: str) -> List[int]:
    values: List[int] = []
    for item in text.split(","):
        stripped = item.strip()
        if stripped:
            values.append(int(stripped))
    return values


def _run_command(command: List[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    src_path = str(cwd / "src")
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{src_path}:{existing_pythonpath}" if existing_pythonpath else src_path
    return subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True)


def _command_for_run_experiments(args: argparse.Namespace, n: int) -> List[str]:
    command = [
        sys.executable,
        "run_experiments.py",
        "--n",
        str(n),
        "--trials",
        str(args.trials),
        "--steps",
        str(args.steps),
        "--seed",
        str(args.seed),
        "--opt-method",
        args.opt_method,
        "--distance-tol",
        str(args.distance_tol),
        "--db-path",
        args.db_path,
        "--certify-top",
        str(args.certify_top),
        "--cert-dps",
        str(args.cert_dps),
        "--mode",
        args.mode,
        "--benchmark-runs",
        str(args.benchmark_runs),
        "--family-tol",
        str(args.family_tol),
        "--family-top",
        str(args.family_top),
        "--archive-path",
        args.archive_path,
        "--archive-size",
        str(args.archive_size),
        "--archive-elite-count",
        str(args.archive_elite_count),
    ]
    if args.replay_archive:
        command.append("--replay-archive")
    if args.archive_only:
        command.append("--archive-only")
    if args.exact_ranking_all:
        command.append("--exact-ranking-all")
    if args.mode == "ray":
        command.extend(["--ray-cpus", str(args.ray_cpus)])
    return command


def _promoted_witness_artifacts_from_manifest(root: Path) -> List[str]:
    manifest_path = root / "proof_ladder_manifest.json"
    if not manifest_path.exists():
        return []

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    promoted: List[str] = []
    for rung in payload.get("certified_rungs", []):
        if int(rung.get("level", -1)) != 1:
            continue
        for artifact in rung.get("artifacts", []):
            if not isinstance(artifact, str):
                continue
            if artifact.startswith("results/erdos91_witness_") and artifact.endswith(".json"):
                promoted.append(artifact)
    return sorted(set(promoted))


def _extract_witness_paths_from_script(script_path: Path) -> List[str]:
    source = script_path.read_text(encoding="utf-8")
    basenames = set(re.findall(r"erdos91_witness_[a-zA-Z0-9_]+\.json", source))
    return sorted(f"results/{name}" for name in basenames)


def _validate_promoted_witness_inputs(root: Path) -> None:
    promoted = _promoted_witness_artifacts_from_manifest(root)
    if not promoted:
        return

    script_names = [
        "pattern_ledger_91.py",
        "bridge_lemma_91.py",
        "conjecture_generator_91.py",
    ]

    missing_by_script: Dict[str, List[str]] = {}
    promoted_set = set(promoted)
    for script_name in script_names:
        declared = set(_extract_witness_paths_from_script(root / script_name))
        missing = sorted(promoted_set - declared)
        if missing:
            missing_by_script[script_name] = missing

    if not missing_by_script:
        return

    details = []
    for script_name, missing in missing_by_script.items():
        details.append(f"{script_name} missing promoted witnesses: {', '.join(missing)}")
    joined = "; ".join(details)
    raise RuntimeError(
        "Promoted rung-1 witness artifacts must be present in every rung generator input list before regeneration. "
        + joined
    )


def _command_for_witness_certificate(args: argparse.Namespace, n: int) -> List[str]:
    return [
        sys.executable,
        "generate_91_witness_certificate.py",
        "--db-path",
        args.db_path,
        "--n",
        str(n),
        "--shape-tol",
        str(args.witness_shape_tol),
        "--invariant-tol",
        str(args.witness_invariant_tol),
        "--out",
        f"results/erdos91_witness_n{n}.md",
        "--json-out",
        f"results/erdos91_witness_n{n}.json",
    ]


def _read_witness_found(root: Path, json_rel_path: str) -> bool:
    payload_path = root / json_rel_path
    if not payload_path.exists():
        return False
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    return bool(payload.get("witness_found", False))


def _promote_witnesses_in_manifest(root: Path, promoted_json_paths: List[str]) -> bool:
    if not promoted_json_paths:
        return False

    manifest_path = root / "proof_ladder_manifest.json"
    if not manifest_path.exists():
        return False

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rung1 = None
    for rung in manifest.get("certified_rungs", []):
        if int(rung.get("level", -1)) == 1:
            rung1 = rung
            break
    if rung1 is None:
        return False

    changed = False
    n_values = set(int(n) for n in rung1.get("n_values", []))
    artifacts = set(str(path) for path in rung1.get("artifacts", []))

    for rel_path in promoted_json_paths:
        artifacts.add(rel_path)
        stem = Path(rel_path).stem
        marker = "erdos91_witness_n"
        if marker not in stem:
            continue
        n_text = stem.split(marker, 1)[1]
        if n_text.isdigit():
            n_values.add(int(n_text))

    normalized_n_values = sorted(n_values)
    normalized_artifacts = sorted(artifacts)
    if normalized_n_values != rung1.get("n_values", []) or normalized_artifacts != rung1.get("artifacts", []):
        rung1["n_values"] = normalized_n_values
        rung1["artifacts"] = normalized_artifacts
        changed = True

    if changed:
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return changed


def _refresh_artifacts(root: Path, regenerate_patterns: bool) -> None:
    env = os.environ.copy()
    src_path = str(root / "src")
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{src_path}:{existing_pythonpath}" if existing_pythonpath else src_path
    subprocess.run(
        [sys.executable, "build_ladder_status.py", "--manifest", "proof_ladder_manifest.json", "--out", "ladder_status.md"],
        cwd=root,
        env=env,
        text=True,
        check=True,
    )
    if regenerate_patterns:
        _validate_promoted_witness_inputs(root)
        subprocess.run(
            [sys.executable, "pattern_ledger_91.py", "--root", ".", "--out", "results/pattern_ledger_91.md", "--json-out", "results/pattern_ledger_91.json"],
            cwd=root,
            env=env,
            text=True,
            check=True,
        )
        subprocess.run(
            [sys.executable, "bridge_lemma_91.py", "--root", ".", "--out", "results/bridge_lemma_91.md", "--json-out", "results/bridge_lemma_91.json"],
            cwd=root,
            env=env,
            text=True,
            check=True,
        )
        subprocess.run(
            [sys.executable, "asymptotic_signal_91.py", "--root", ".", "--out", "results/asymptotic_signal_91.md", "--json-out", "results/asymptotic_signal_91.json"],
            cwd=root,
            env=env,
            text=True,
            check=True,
        )
        subprocess.run(
            [sys.executable, "conjecture_generator_91.py", "--root", ".", "--out", "results/conjecture_ladder_91.md", "--json-out", "results/conjecture_ladder_91.json"],
            cwd=root,
            env=env,
            text=True,
            check=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Densify finite Erdős #91 certificates")
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument("--n-values", default="14,16,18,20,22,24,26,28,30,32", help="comma-separated n values to search")
    parser.add_argument("--trials", type=int, default=80, help="number of random starts per n")
    parser.add_argument("--steps", type=int, default=300, help="optimization steps per trial")
    parser.add_argument("--seed", type=int, default=42, help="global random seed")
    parser.add_argument("--opt-method", choices=["anneal", "hillclimb", "direct"], default="anneal", help="optimizer to use")
    parser.add_argument("--distance-tol", type=float, default=1e-6, help="distance tolerance")
    parser.add_argument("--db-path", default="results/erdos_experiments.db", help="SQLite database output path")
    parser.add_argument("--certify-top", type=int, default=10, help="number of top candidates to certify exactly")
    parser.add_argument("--cert-dps", type=int, default=100, help="decimal precision for exact checks")
    parser.add_argument("--mode", choices=["serial", "ray"], default="serial", help="execution mode")
    parser.add_argument("--ray-cpus", type=int, default=0, help="CPU count for Ray init (0=auto)")
    parser.add_argument("--benchmark-runs", type=int, default=1, help="repeat count for each n value")
    parser.add_argument("--family-tol", type=float, default=0.02, help="shape-distance tolerance for family counting")
    parser.add_argument("--family-top", type=int, default=12, help="max certified minimizers used for #91 family evidence")
    parser.add_argument("--archive-path", default="results/best_exact_archive.json", help="JSON archive of certified best candidates")
    parser.add_argument("--archive-size", type=int, default=50, help="maximum number of certified archive entries to retain")
    parser.add_argument("--archive-elite-count", type=int, default=8, help="number of top certified archive candidates used as replay seeds")
    parser.add_argument("--replay-archive", action="store_true", help="seed searches from the certified archive")
    parser.add_argument("--archive-only", action="store_true", help="use only archived certified survivors as starting points")
    parser.add_argument("--exact-ranking-all", action="store_true", help="certify all trials and rank by exact certified distance count")
    parser.add_argument("--skip-witness-generation", action="store_true", help="skip witness certificate generation and auto-promotion")
    parser.add_argument("--skip-pattern-ledger", action="store_true", help="skip regenerating the pattern ledger and conjecture report")
    parser.add_argument("--witness-shape-tol", type=float, default=0.01, help="shape tolerance for witness certificate generation")
    parser.add_argument("--witness-invariant-tol", type=float, default=1e-10, help="invariant tolerance for witness certificate generation")
    parser.add_argument("--dry-run", action="store_true", help="print the commands without executing them")
    args = parser.parse_args()

    n_values = _parse_n_values(args.n_values)
    if not n_values:
        parser.error("--n-values must contain at least one value")
    if args.trials < 1:
        parser.error("--trials must be >= 1")
    if args.steps < 1:
        parser.error("--steps must be >= 1")
    if args.certify_top < 1:
        parser.error("--certify-top must be >= 1")
    if args.family_top < 2:
        parser.error("--family-top must be >= 2")
    if args.archive_size < 1:
        parser.error("--archive-size must be >= 1")
    if args.archive_elite_count < 1:
        parser.error("--archive-elite-count must be >= 1")
    if args.archive_only and not args.replay_archive:
        parser.error("--archive-only requires --replay-archive")
    if args.witness_shape_tol <= 0:
        parser.error("--witness-shape-tol must be > 0")
    if args.witness_invariant_tol <= 0:
        parser.error("--witness-invariant-tol must be > 0")

    root = Path(args.root)
    run_records: List[RunRecord] = []
    witness_records: List[WitnessRecord] = []
    started_batch = datetime.now(timezone.utc).isoformat()

    for n in n_values:
        command = _command_for_run_experiments(args, n)
        if args.dry_run:
            print(" ".join(command))
            run_records.append(
                RunRecord(
                    n=n,
                    command=command,
                    returncode=0,
                    started_at=started_batch,
                    finished_at=started_batch,
                )
            )
            continue

        started_at = datetime.now(timezone.utc).isoformat()
        completed = _run_command(command, cwd=root)
        finished_at = datetime.now(timezone.utc).isoformat()
        print(completed.stdout)
        if completed.stderr:
            print(completed.stderr, file=sys.stderr)
        if completed.returncode != 0:
            raise SystemExit(completed.returncode)
        run_records.append(
            RunRecord(
                n=n,
                command=command,
                returncode=completed.returncode,
                started_at=started_at,
                finished_at=finished_at,
            )
        )

    if not args.dry_run:
        promoted_witnesses: List[str] = []
        if not args.skip_witness_generation:
            for n in n_values:
                witness_command = _command_for_witness_certificate(args, n)
                started_at = datetime.now(timezone.utc).isoformat()
                completed = _run_command(witness_command, cwd=root)
                finished_at = datetime.now(timezone.utc).isoformat()
                if completed.stdout:
                    print(completed.stdout)
                if completed.stderr:
                    print(completed.stderr, file=sys.stderr)

                json_rel_path = f"results/erdos91_witness_n{n}.json"
                witness_found = completed.returncode == 0 and _read_witness_found(root, json_rel_path)
                if witness_found:
                    promoted_witnesses.append(json_rel_path)

                witness_records.append(
                    WitnessRecord(
                        n=n,
                        command=witness_command,
                        returncode=completed.returncode,
                        json_path=json_rel_path,
                        witness_found=witness_found,
                        started_at=started_at,
                        finished_at=finished_at,
                    )
                )

            _promote_witnesses_in_manifest(root, promoted_witnesses)

        _refresh_artifacts(root=root, regenerate_patterns=not args.skip_pattern_ledger)

        summary_path = root / "results" / "densify_certificates_91.json"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_payload: Dict[str, Any] = {
            "started_at": started_batch,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "n_values": n_values,
            "runs": [asdict(record) for record in run_records],
            "search": {
                "trials": args.trials,
                "steps": args.steps,
                "seed": args.seed,
                "opt_method": args.opt_method,
                "distance_tol": args.distance_tol,
                "db_path": args.db_path,
                "certify_top": args.certify_top,
                "cert_dps": args.cert_dps,
                "mode": args.mode,
                "benchmark_runs": args.benchmark_runs,
                "family_tol": args.family_tol,
                "family_top": args.family_top,
                "archive_path": args.archive_path,
                "archive_size": args.archive_size,
                "archive_elite_count": args.archive_elite_count,
                "replay_archive": args.replay_archive,
                "archive_only": args.archive_only,
                "exact_ranking_all": args.exact_ranking_all,
                "skip_witness_generation": args.skip_witness_generation,
                "witness_shape_tol": args.witness_shape_tol,
                "witness_invariant_tol": args.witness_invariant_tol,
            },
            "witness_generation": [asdict(record) for record in witness_records],
            "promoted_witness_artifacts": promoted_witnesses,
            "artifacts_refreshed": [
                "ladder_status.md",
                "results/pattern_ledger_91.md",
                "results/pattern_ledger_91.json",
                "results/bridge_lemma_91.md",
                "results/bridge_lemma_91.json",
                "results/asymptotic_signal_91.md",
                "results/asymptotic_signal_91.json",
                "results/conjecture_ladder_91.md",
                "results/conjecture_ladder_91.json",
            ],
        }
        summary_path.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
        print(json.dumps(summary_payload, indent=2))
        print(f"Saved densify summary to {summary_path}")


if __name__ == "__main__":
    main()