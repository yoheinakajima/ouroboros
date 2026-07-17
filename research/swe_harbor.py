#!/usr/bin/env python3
"""Materialize pinned SWE-bench Verified rows as official Harbor tasks."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

HARBOR_REVISION = "19f72aa8b45c710744d231edbb57a903b4216553"
SWEBENCH_REVISION = "f7bbbb2ccdf479001d6467c9e34af59e44a840f9"
IMAGE_MANIFEST = "research/selections/swe_verified_images.json"
OFFICIAL_IMAGE = re.compile(r"^swebench/[A-Za-z0-9][A-Za-z0-9._/-]*@sha256:[0-9a-f]{64}$")


PATCH_EXPORT_VERIFIER = """#!/bin/bash
set -euo pipefail

cd /testbed
mkdir -p /logs/verifier

# Capture new files as well as tracked edits. The official pinned SWE-bench
# evaluator consumes this patch after Harbor has destroyed the agent task
# environment; no evaluator tests or expected outputs are mounted here.
git add -A
git diff --cached --binary --full-index > /logs/verifier/model.patch
sha256sum /logs/verifier/model.patch > /logs/verifier/model.patch.sha256

# Harbor requires a syntactically valid reward, but this is explicitly not the
# SWE score. The host-side official evaluator replaces this placeholder.
echo 0 > /logs/verifier/reward.txt
"""


def _task_dockerfile(image: str) -> str:
    return (
        f"FROM {image}\n\n"
        'ENV PATH="/opt/miniconda3/envs/testbed/bin:${PATH}" \\\n'
        "    CONDA_DEFAULT_ENV=testbed\n\n"
        "WORKDIR /testbed\n"
        "RUN mkdir -p /logs\n"
    )


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


def _harden_task(task_root: Path, *, instance_id: str, image: str) -> None:
    """Make Harbor an immutable patch-producing shell for official SWE eval."""

    if not OFFICIAL_IMAGE.fullmatch(image):
        raise ValueError(f"SWE image is not digest pinned: {instance_id}")
    dockerfile = task_root / "environment/Dockerfile"
    if not dockerfile.is_file():
        raise FileNotFoundError(f"generated SWE Dockerfile missing: {instance_id}")
    dockerfile.write_text(_task_dockerfile(image), encoding="utf-8")

    verifier = task_root / "tests/test.sh"
    if not verifier.is_file():
        raise FileNotFoundError(f"generated SWE verifier missing: {instance_id}")
    verifier.write_text(PATCH_EXPORT_VERIFIER, encoding="utf-8")

    task_toml = task_root / "task.toml"
    task_text = task_toml.read_text(encoding="utf-8")
    verifier_header = "[verifier]\nnetwork_mode = \"public\""
    if task_text.count(verifier_header) != 1:
        raise ValueError(f"unexpected SWE verifier network contract: {instance_id}")
    task_toml.write_text(
        task_text.replace(verifier_header, "[verifier]\nnetwork_mode = \"no-network\""),
        encoding="utf-8",
    )


def verify_materialized(
    *, repository: Path, output: Path, task_ids: list[str] | None = None
) -> dict[str, Any]:
    """Reject mutable or evaluator-bearing Harbor SWE task environments."""

    manifest = json.loads((repository / "research/selections/swe_verified.json").read_text(encoding="utf-8"))
    selected = [str(item) for item in manifest["development"] + manifest["evaluation"]]
    requested = task_ids or selected
    if not requested or not set(requested) <= set(selected):
        raise ValueError("verification is limited to the committed SWE selection")
    image_manifest = json.loads((repository / IMAGE_MANIFEST).read_text(encoding="utf-8"))
    images = {str(key): str(value) for key, value in image_manifest.get("images", {}).items()}
    issues: list[dict[str, str]] = []
    task_hashes: dict[str, str] = {}
    for instance_id in requested:
        task_root = output / instance_id
        expected_image = images.get(instance_id, "")
        expected_dockerfile = _task_dockerfile(expected_image)
        paths = {
            "dockerfile": task_root / "environment/Dockerfile",
            "verifier": task_root / "tests/test.sh",
            "task": task_root / "task.toml",
        }
        if any(not path.is_file() for path in paths.values()):
            issues.append({"instance_id": instance_id, "code": "materialized_task_incomplete"})
            continue
        if not OFFICIAL_IMAGE.fullmatch(expected_image):
            issues.append({"instance_id": instance_id, "code": "official_image_not_digest_pinned"})
        if paths["dockerfile"].read_text(encoding="utf-8") != expected_dockerfile:
            issues.append({"instance_id": instance_id, "code": "environment_not_digest_pinned"})
        if paths["verifier"].read_text(encoding="utf-8") != PATCH_EXPORT_VERIFIER:
            issues.append({"instance_id": instance_id, "code": "harbor_verifier_not_patch_only"})
        task_text = paths["task"].read_text(encoding="utf-8")
        if '[verifier]\nnetwork_mode = "no-network"' not in task_text:
            issues.append({"instance_id": instance_id, "code": "harbor_verifier_network_enabled"})
        task_hashes[instance_id] = _hash_tree(task_root)
    return {
        "schema_version": 1,
        "passed": not issues and len(task_hashes) == len(requested),
        "task_count": len(requested),
        "task_hashes": task_hashes,
        "issues": issues,
    }


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
    image_manifest_path = repository / IMAGE_MANIFEST
    image_manifest = json.loads(image_manifest_path.read_text(encoding="utf-8"))
    if image_manifest.get("suite_id") != manifest.get("suite_id"):
        raise ValueError("SWE image manifest suite mismatch")
    pinned_images = {str(key): str(value) for key, value in image_manifest.get("images", {}).items()}
    selected = manifest["development"] + manifest["evaluation"]
    invalid_images = any(not OFFICIAL_IMAGE.fullmatch(item) for item in pinned_images.values())
    if set(pinned_images) != set(selected) or invalid_images:
        raise ValueError("SWE image manifest must exactly pin every selected official image")
    requested = task_ids or selected
    if not requested or len(set(requested)) != len(requested):
        raise ValueError("task IDs must be nonempty and unique")
    if not set(requested) <= set(selected):
        raise ValueError("materialization is limited to the committed selection")
    missing_images = set(requested) - pinned_images.keys()
    if missing_images:
        raise ValueError(f"selected SWE images are not pinned: {sorted(missing_images)}")

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
    for path in generated:
        _harden_task(path, instance_id=path.name, image=pinned_images[path.name])
    task_hashes = {path.name: _hash_tree(path) for path in generated}
    canonical_hashes = json.dumps(task_hashes, sort_keys=True, separators=(",", ":"))
    return {
        "schema_version": 1,
        "passed": len(generated) == len(requested),
        "model_calls": 0,
        "task_count": len(generated),
        "task_ids": requested,
        "task_hashes": task_hashes,
        "aggregate_task_hash_sha256": hashlib.sha256(canonical_hashes.encode()).hexdigest(),
        "harbor_revision": HARBOR_REVISION,
        "swebench_revision": SWEBENCH_REVISION,
        "dataset_revision": manifest["dataset"]["revision"],
        "dataset_sha256": manifest["dataset"]["parquet_sha256"],
        "image_manifest": IMAGE_MANIFEST,
        "image_manifest_sha256": hashlib.sha256(image_manifest_path.read_bytes()).hexdigest(),
        "official_grader": "host-side pinned SWE-bench evaluator after Harbor patch export",
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
