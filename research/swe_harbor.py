#!/usr/bin/env python3
"""Materialize pinned SWE-bench Verified rows as official Harbor tasks."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

HARBOR_REVISION = "19f72aa8b45c710744d231edbb57a903b4216553"
SWEBENCH_REVISION = "f7bbbb2ccdf479001d6467c9e34af59e44a840f9"


def _revision(path: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=path,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"cannot inspect revision: {path}")
    return result.stdout.strip()


def _hash_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"generated Harbor task contains a symlink: {path}")
        if not path.is_file():
            continue
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def materialize(
    *,
    repository: Path,
    cache: Path,
    output: Path,
    task_ids: list[str] | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    harbor = (cache / "harbor").resolve(strict=True)
    swebench = (cache / "swe").resolve(strict=True)
    if _revision(harbor) != HARBOR_REVISION:
        raise ValueError("Harbor source revision drift")
    if _revision(swebench) != SWEBENCH_REVISION:
        raise ValueError("SWE-bench source revision drift")

    parquet_path = (cache / "swe_verified/data/test-00000-of-00001.parquet").resolve(strict=True)
    manifest = json.loads((repository / "research/selections/swe_verified.json").read_text(encoding="utf-8"))
    selected = manifest["development"] + manifest["evaluation"]
    requested = task_ids or selected
    if not requested or len(set(requested)) != len(requested):
        raise ValueError("task IDs must be nonempty and unique")
    if not set(requested) <= set(selected):
        raise ValueError("materialization is limited to the committed selection")

    try:
        import pyarrow.parquet as parquet
    except ImportError as exc:
        raise RuntimeError("pyarrow is required in the isolated SWE-bench environment") from exc
    rows = parquet.read_table(parquet_path).to_pylist()
    by_id = {str(row["instance_id"]): dict(row) for row in rows}
    missing = set(requested) - by_id.keys()
    if missing:
        raise ValueError(f"selected IDs missing from pinned parquet: {sorted(missing)}")

    adapter_source = harbor / "adapters/swebench/src"
    sys.path.insert(0, str(adapter_source))
    try:
        import swebench_adapter.adapter as adapter_module
    finally:
        sys.path.pop(0)

    class PinnedLoader:
        def __init__(self) -> None:
            self._by_id = by_id

        def all_ids(self) -> list[str]:
            return list(self._by_id)

        def load(self, instance_id: str) -> Any:
            return adapter_module.SWEBenchRecord.from_dict(self._by_id[instance_id])

        def get_raw(self, instance_id: str) -> dict[str, Any]:
            return self._by_id[instance_id]

        def all_records(self) -> list[dict[str, Any]]:
            return list(self._by_id.values())

    adapter_module.SWEBenchLoader = PinnedLoader
    converter = adapter_module.SWEBenchAdapter(
        output_dir=output,
        task_ids=requested,
        all_tasks=False,
        overwrite=overwrite,
        max_timeout_sec=14_400,
        template_dir=harbor / "adapters/swebench/src/swebench_adapter/task-template",
    )
    generated, failures = converter.generate_many(requested, overwrite=overwrite)
    if failures:
        raise RuntimeError(f"SWE Harbor materialization failures: {failures}")
    task_hashes = {path.name: _hash_tree(path) for path in generated}
    return {
        "schema_version": 1,
        "passed": len(generated) == len(requested),
        "model_calls": 0,
        "task_count": len(generated),
        "task_ids": requested,
        "task_hashes": task_hashes,
        "harbor_revision": HARBOR_REVISION,
        "swebench_revision": SWEBENCH_REVISION,
        "dataset_revision": manifest["dataset"]["revision"],
        "dataset_sha256": manifest["dataset"]["parquet_sha256"],
        "output": str(output.resolve()),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--task", action="append")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    cache = (args.cache or args.root / "benchmark/.cache").resolve()
    output = (args.output or cache / "swe_harbor").resolve()
    receipt = materialize(
        repository=args.root.resolve(),
        cache=cache,
        output=output,
        task_ids=args.task,
        overwrite=args.overwrite,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
