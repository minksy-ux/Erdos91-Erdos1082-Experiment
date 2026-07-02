#!/usr/bin/env python3
"""Generate a human-readable proof ladder status page from the manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List


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