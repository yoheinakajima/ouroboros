#!/usr/bin/env python3
"""Scan the release package for secrets, PII, and local environment paths."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


TEXT_SUFFIXES = {
    ".bib",
    ".cff",
    ".csv",
    ".json",
    ".jsonl",
    ".md",
    ".py",
    ".tex",
    ".txt",
    ".yaml",
    ".yml",
}

PATTERNS = {
    "openai_key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "github_token": re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "private_key": re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    ),
    "email_address": re.compile(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE
    ),
    "ipv4_address": re.compile(
        r"(?<![\d.])(?:25[0-5]|2[0-4]\d|1?\d?\d)"
        r"(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}(?![\d.])"
    ),
    "macos_user_path": re.compile("/" + "Users" + r"/[^/\s\"']+"),
    "linux_home_path": re.compile("/" + "home" + r"/[^/\s\"']+"),
    "windows_user_path": re.compile(
        r"\b[A-Za-z]:\\(?:Users|Documents and Settings)\\[^\\\s\"']+",
        re.IGNORECASE,
    ),
    "environment_secret_assignment": re.compile(
        r"(?im)^\s*(?:OPENAI_API_KEY|ANTHROPIC_API_KEY|AWS_SECRET_ACCESS_KEY|"
        r"GITHUB_TOKEN|PASSWORD)\s*=\s*\S+"
    ),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_text_files(root: Path) -> list[Path]:
    excluded_names = {"provenance-manifest.json", "scan-report.json"}
    return [
        path
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and path.name not in excluded_names
        and path.suffix.lower() in TEXT_SUFFIXES
        and "output/pdf" not in path.as_posix()
    ]


def scan(root: Path) -> tuple[list[dict[str, object]], int]:
    findings: list[dict[str, object]] = []
    files = iter_text_files(root)
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        for kind, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                line_number = text.count("\n", 0, match.start()) + 1
                line = lines[line_number - 1] if lines else ""
                preview = line.strip()
                if len(preview) > 160:
                    preview = preview[:157] + "..."
                findings.append(
                    {
                        "kind": kind,
                        "path": path.relative_to(root).as_posix(),
                        "line": line_number,
                        "line_sha256": hashlib.sha256(
                            line.encode("utf-8")
                        ).hexdigest(),
                        "preview_redacted": pattern.sub("<REDACTED>", preview),
                    }
                )
    return findings, len(files)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write-report", type=Path)
    args = parser.parse_args()

    root = args.root.resolve()
    findings, file_count = scan(root)
    report = {
        "schema_version": 1,
        "kind": "release-secret-pii-scan",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "root": ".",
        "text_files_scanned": file_count,
        "patterns": sorted(PATTERNS),
        "findings": findings,
        "status": "passed" if not findings else "failed",
        "scanner_sha256": sha256(Path(__file__).resolve()),
    }
    if args.write_report:
        args.write_report.resolve().write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report, indent=2, sort_keys=True))
    if findings:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

