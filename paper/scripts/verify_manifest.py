#!/usr/bin/env python3
"""Verify every provenance hash and the completeness of the release manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_path(root: Path, relative: str) -> Path:
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        raise ValueError(f"unsafe manifest path: {relative!r}")
    resolved = (root / Path(*pure.parts)).resolve()
    if root not in resolved.parents:
        raise ValueError(f"path escapes release root: {relative!r}")
    return resolved


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    root = manifest_path.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    listed: set[str] = set()

    for record in manifest.get("files", []):
        relative = str(record["path"])
        try:
            path = safe_path(root, relative)
        except ValueError as exc:
            failures.append(str(exc))
            continue
        if relative in listed:
            failures.append(f"duplicate manifest entry: {relative}")
            continue
        listed.add(relative)
        if not path.is_file():
            failures.append(f"missing file: {relative}")
            continue
        actual_bytes = path.stat().st_size
        actual_hash = sha256(path)
        if actual_bytes != int(record["bytes"]):
            failures.append(
                f"byte mismatch: {relative}: {actual_bytes} != {record['bytes']}"
            )
        if actual_hash != str(record["sha256"]):
            failures.append(
                f"hash mismatch: {relative}: {actual_hash} != {record['sha256']}"
            )

    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
        and path.resolve() != manifest_path
        and "tmp/" not in path.relative_to(root).as_posix()
    }
    unlisted = sorted(actual - listed)
    stale = sorted(listed - actual)
    failures.extend(f"unlisted release file: {path}" for path in unlisted)
    failures.extend(f"stale manifest entry: {path}" for path in stale)

    if failures:
        print("\n".join(f"FAIL: {failure}" for failure in failures))
        raise SystemExit(1)
    print(
        f"VERIFIED {len(listed)} files: hashes, byte counts, paths, and "
        "manifest completeness all pass"
    )


if __name__ == "__main__":
    main()

