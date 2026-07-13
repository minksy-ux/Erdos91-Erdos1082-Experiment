#!/usr/bin/env python3
"""Generate a human-readable proof ladder status page from the manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _artifact_line(path_str: str, expected: str | None) -> str:
    path = Path(path_str)
    actual = _sha256(path)
    if expected is None and actual is None:
        return f"- {path_str}: missing"
    if actual is None:
        return f"- {path_str}: missing (expected {expected})"
    if expected is None:
        return f"- {path_str}: {actual}"
    if actual == expected:
        return f"- {path_str}: {actual}"
    return f"- {path_str}: {actual} (manifest expected {expected})"


def _window_key(payload: Dict[str, Any]) -> Tuple[int, int, int] | None:
    window = payload.get("window_composition", {})
    if not isinstance(window, dict):
        return None
    try:
        ws = int(window.get("window_start"))
        wm = int(window.get("window_mid"))
        we = int(window.get("window_end"))
    except (TypeError, ValueError):
        return None
    return (ws, wm, we)


def _collect_bridge_window_rows(results_dir: Path) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[int, int, int], Dict[str, str | None]] = {}
    pattern = re.compile(r"bridge_transfer_proof_91_window_\d+_\d+(?:_exception[0-9_]+)?\.json$")

    for path in sorted(results_dir.glob("bridge_transfer_proof_91_window_*.json")):
        if not pattern.search(path.name):
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue

        key = _window_key(payload)
        if key is None:
            continue

        conclusion = payload.get("conclusion", {})
        if not isinstance(conclusion, dict):
            continue
        status = str(conclusion.get("transfer_lemma_status", "-"))
        bucket = grouped.setdefault(key, {"strict": None, "exception": None})
        if "_exception" in path.stem:
            bucket["exception"] = status
        else:
            bucket["strict"] = status

    rows: List[Dict[str, Any]] = []
    for (ws, wm, we), values in sorted(grouped.items()):
        strict_status = values.get("strict") or "missing"
        exception_status = values.get("exception") or "missing"
        delta = "same" if strict_status == exception_status else "changed"
        rows.append(
            {
                "window": f"{ws}->{wm}->{we}",
                "strict": strict_status,
                "exception": exception_status,
                "delta": delta,
            }
        )
    return rows


def build_status(manifest: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Live Ladder Status")
    lines.append("")
    lines.append(f"- version: {manifest.get('version')}")
    lines.append(f"- next target: {manifest.get('next_target')}")
    lines.append("")
    lines.append("## Rungs")
    lines.append("")
    lines.append("| Level | Name | Status | n values | Strength |")
    lines.append("|---:|---|---|---|---|")
    for rung in manifest.get("certified_rungs", []):
        n_values = ", ".join(str(v) for v in rung.get("n_values", [])) or "-"
        lines.append(
            f"| {rung.get('level')} | {rung.get('name')} | {rung.get('status')} | {n_values} | {rung.get('strength')} |"
        )
    lines.append("")
    lines.append("## Gaps")
    lines.append("")
    for gap in manifest.get("gaps", []):
        lines.append(f"- {gap}")
    lines.append("")
    lines.append("## Fingerprints")
    lines.append("")
    fingerprints = manifest.get("fingerprints", {})
    for path_str in sorted(fingerprints):
        lines.append(_artifact_line(path_str, fingerprints.get(path_str)))
    lines.append("")

    lines.append("## Bridge Window Matrix")
    lines.append("")
    rows = _collect_bridge_window_rows(Path("results"))
    if not rows:
        lines.append("- no bridge transfer window artifacts found")
        lines.append("")
        return "\n".join(lines)

    lines.append("| Window | Strict status | Exception-aware status | Delta |")
    lines.append("|---|---|---|---|")
    for row in rows:
        lines.append(f"| {row['window']} | {row['strict']} | {row['exception']} | {row['delta']} |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a proof ladder status page")
    parser.add_argument("--manifest", default="proof_ladder_manifest.json", help="manifest path")
    parser.add_argument("--out", default="ladder_status.md", help="output markdown path")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    status = build_status(manifest)

    out_path = Path(args.out)
    out_path.write_text(status + "\n", encoding="utf-8")
    print(status)
    print(f"Saved ladder status to {out_path}")


if __name__ == "__main__":
    main()