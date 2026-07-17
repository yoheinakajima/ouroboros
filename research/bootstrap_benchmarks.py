#!/usr/bin/env python3
"""Fetch or verify the anonymous local-core benchmark inputs at exact revisions."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    revision: str
    lfs_include: str | None = None


SOURCES = (
    Source(
        "swe",
        "https://github.com/SWE-bench/SWE-bench.git",
        "f7bbbb2ccdf479001d6467c9e34af59e44a840f9",
    ),
    Source(
        "swe_verified",
        "https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified",
        "c104f840cc67f8b6eec6f759ebc8b2693d585d4a",
        "data/test-00000-of-00001.parquet",
    ),
    Source(
        "terminal2",
        "https://github.com/harbor-framework/terminal-bench-2.git",
        "2fd12b88aafdd04a52c298e3940bcb189f9766d6",
    ),
    Source(
        "harbor",
        "https://github.com/harbor-framework/harbor.git",
        "19f72aa8b45c710744d231edbb57a903b4216553",
    ),
)


def _run(argv: list[str], *, cwd: Path | None = None, timeout: float = 1_800) -> str:
    result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, timeout=timeout, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"command failed ({result.returncode}): {argv!r}\n{result.stderr[-4000:]}")
    return result.stdout.strip()


def fetch_sources(cache: str | Path) -> None:
    root = Path(cache).resolve()
    root.mkdir(parents=True, exist_ok=True)
    if shutil.which("git") is None:
        raise RuntimeError("git is required")
    for source in SOURCES:
        target = root / source.name
        if not target.exists():
            _run(["git", "clone", "--no-checkout", source.url, str(target)])
        if not (target / ".git").is_dir():
            raise RuntimeError(f"refusing to replace non-git cache path: {target}")
        _run(["git", "fetch", "origin", source.revision, "--depth", "1"], cwd=target)
        _run(["git", "checkout", "--detach", source.revision], cwd=target)
        if source.lfs_include:
            if shutil.which("git-lfs") is None and _run(["git", "lfs", "version"], cwd=target) == "":
                raise RuntimeError("git-lfs is required for SWE-bench Verified")
            _run(["git", "lfs", "install", "--local"], cwd=target)
            _run(["git", "lfs", "pull", "--include", source.lfs_include], cwd=target)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest_digest(image: str) -> str:
    raw = _run(["docker", "manifest", "inspect", "--verbose", image], timeout=120)
    descriptor = json.loads(raw)["Descriptor"]["digest"]
    return image.rsplit(":", 1)[0] + "@" + descriptor


def inspect_cache(
    *,
    repository: str | Path,
    cache: str | Path,
    verify_images: bool = False,
) -> dict[str, Any]:
    repo = Path(repository).resolve()
    root = Path(cache).resolve()
    issues: list[dict[str, str]] = []
    revisions: dict[str, str] = {}
    for source in SOURCES:
        target = root / source.name
        if not (target / ".git").is_dir():
            issues.append({"code": "source_missing", "source": source.name})
            continue
        try:
            actual = _run(["git", "rev-parse", "HEAD"], cwd=target, timeout=10)
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
            issues.append({"code": "source_unreadable", "source": source.name, "detail": str(exc)})
            continue
        revisions[source.name] = actual
        if actual != source.revision:
            issues.append({"code": "source_revision_drift", "source": source.name, "detail": actual})
    swe_selection = json.loads((repo / "research/selections/swe_verified.json").read_text(encoding="utf-8"))
    parquet = root / "swe_verified/data/test-00000-of-00001.parquet"
    if not parquet.is_file():
        issues.append({"code": "swe_dataset_missing", "source": "swe_verified"})
    elif _sha256(parquet) != swe_selection["dataset"]["parquet_sha256"]:
        issues.append({"code": "swe_dataset_hash_drift", "source": "swe_verified"})
    terminal = json.loads((repo / "research/selections/terminal_bench_2.json").read_text(encoding="utf-8"))
    image_checks = 0
    for row in terminal["development"] + terminal["evaluation"]:
        task_path = root / "terminal2" / row["id"] / "task.toml"
        if not task_path.is_file():
            issues.append({"code": "terminal_task_missing", "source": row["id"]})
            continue
        if _sha256(task_path) != row["task_toml_sha256"]:
            issues.append({"code": "terminal_task_hash_drift", "source": row["id"]})
        task = tomllib.loads(task_path.read_text(encoding="utf-8"))
        if int(task["environment"]["gpus"]) != 0:
            issues.append({"code": "terminal_gpu_requirement_drift", "source": row["id"]})
        if verify_images:
            expected = row["image"]
            try:
                actual = _manifest_digest(str(task["environment"]["docker_image"]))
                image_checks += 1
                if actual != expected:
                    issues.append(
                        {"code": "terminal_image_digest_drift", "source": row["id"], "detail": actual}
                    )
            except (OSError, RuntimeError, subprocess.TimeoutExpired, KeyError, json.JSONDecodeError) as exc:
                issues.append({"code": "terminal_image_unverifiable", "source": row["id"], "detail": str(exc)})
    return {
        "schema_version": 1,
        "ready": not issues,
        "score_blind": True,
        "model_calls": 0,
        "cache": str(root),
        "revisions": revisions,
        "terminal_tasks_checked": len(terminal["development"]) + len(terminal["evaluation"]),
        "terminal_images_checked": image_checks,
        "issues": issues,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--verify-images", action="store_true")
    args = parser.parse_args(argv)
    cache = args.cache or args.root / "benchmark/.cache"
    if args.fetch:
        fetch_sources(cache)
    report = inspect_cache(repository=args.root, cache=cache, verify_images=args.verify_images)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
