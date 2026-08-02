#!/usr/bin/env python3
"""Build the release provenance manifest after a passing disclosure scan."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    root = args.root.resolve()
    output = args.output.resolve()
    scan_path = root / "scan-report.json"
    if not scan_path.exists():
        raise SystemExit("scan-report.json is missing")
    scan = json.loads(scan_path.read_text(encoding="utf-8"))
    if scan.get("status") != "passed" or scan.get("findings"):
        raise SystemExit("refusing to build manifest from a failed scan")

    files = [
        path
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and path.resolve() != output
        and "tmp/" not in path.relative_to(root).as_posix()
    ]
    payload = {
        "schema_version": 1,
        "kind": "paper-release-provenance-manifest",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "hash_algorithm": "sha256",
        "root": ".",
        "unlisted_files_allowed": False,
        "excluded_from_manifest": ["provenance-manifest.json", "tmp/**"],
        "release_scope": (
            "Paper sources, selected audit records, generated tables, analysis "
            "code, and figures. Complete run directories and raw traces are "
            "reserved for a separate archival deposit with DOI pending."
        ),
        "redactions": [
            {
                "files": [
                    "data/generated/posthoc-metrics.json",
                    "data/taxonomy/coder-agreement.json",
                ],
                "rule": (
                    "Replace absolute local user-home study and label paths "
                    "with <RELEASE_ROOT> or release-relative paths."
                ),
                "substantive_values_changed": False,
            }
        ],
        "secret_pii_scan": {
            "path": "scan-report.json",
            "status": scan["status"],
            "findings": len(scan["findings"]),
            "text_files_scanned": scan["text_files_scanned"],
        },
        "archive": {
            "host": "Zenodo planned; GitHub release fallback",
            "doi": "pending",
            "note": "Do not replace with a DOI until the external deposit exists.",
        },
        "files": [
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in files
        ],
    }
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {output} with {len(files)} files")


if __name__ == "__main__":
    main()

