#!/usr/bin/env python3
"""Validate score-blind selections and hash-seal the benchmark protocol."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

SHA256 = re.compile(r"^[0-9a-f]{64}$")
DIGEST_IMAGE = re.compile(r"^[^\s@]+@sha256:[0-9a-f]{64}$")
LOCK_PATH = Path("research/freeze.lock.json")
LOCK_INPUTS = (
    "LICENSE",
    "README.md",
    "pyproject.toml",
    "evidence/activegraph_50_calibration.json",
    "evidence/swe_verified_calibration.json",
    "evidence/terminal_bench_2_calibration.json",
    "evidence/swe_harbor_materialization.json",
    "docs/BENCHMARK_AUDIT.md",
    "docs/LOCAL_TEST_PLAN.md",
    "docs/RESEARCH_DESIGN.md",
    "docs/SANDBOX_DECISION.md",
    "research/PROTOCOL.md",
    "research/local_study.json",
    "research/approaches.json",
    "research/hard_benchmark.json",
    "research/broker_protocol.json",
    "research/agent.py",
    "research/attempt_runner.py",
    "research/audit.py",
    "research/broker.py",
    "research/contracts.py",
    "research/environment.lock.json",
    "research/freeze.py",
    "research/grading.py",
    "research/harbor_agent.py",
    "research/harbor_jobs.py",
    "research/hybrid_author.py",
    "research/lineage.py",
    "research/readiness.py",
    "research/sandbox.py",
    "research/smoke.py",
    "research/swe_harbor.py",
    "research/swe_official.py",
    "research/benchmark_runner.py",
    "research/bootstrap_benchmarks.py",
    "research/activegraph_benchmark.py",
    "research/activegraph_task_runtime.py",
    "research/comparison.py",
    "research/calibration.py",
    "research/curriculum.py",
    "research/adapters/base.py",
    "research/adapters/common.py",
    "experiments/hybrid_ouroboros.py",
    "ouroboros.py",
    "recovered/v1.2/ouroboros.py",
    "benchmarks/activegraph_50/Dockerfile",
    "benchmarks/activegraph_50/ACTIVEGRAPH_API.md",
)


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ids(rows: list[Any]) -> list[str]:
    return [str(row["id"] if isinstance(row, dict) else row) for row in rows]


def inspect_selections(root: str | Path, *, profile: str | None = None) -> dict[str, Any]:
    repository = Path(root).resolve()
    benchmark = _read(repository / "research/hard_benchmark.json")
    issues: list[dict[str, str]] = []
    checked: list[str] = []
    statuses: dict[str, str] = {}
    selected_ids: set[str] | None = None
    if profile:
        profiles = {row["id"]: row for row in benchmark.get("execution_profiles", [])}
        if profile not in profiles:
            return {
                "schema_version": 1,
                "valid": False,
                "calibration_ready": False,
                "frozen": False,
                "checked_manifests": [],
                "statuses": {},
                "issues": [{"code": "unknown_execution_profile", "suite_id": profile}],
            }
        selected_ids = set(profiles[profile]["suites"])
    for suite in benchmark.get("suites", []):
        suite_id = str(suite["id"])
        if selected_ids is not None and suite_id not in selected_ids:
            continue
        relative = suite.get("selection_manifest")
        if not relative:
            issues.append({"code": "selection_manifest_missing", "suite_id": suite_id})
            continue
        path = (repository / str(relative)).resolve()
        if repository not in path.parents or not path.is_file():
            issues.append({"code": "selection_manifest_unreadable", "suite_id": suite_id})
            continue
        try:
            manifest = _read(path)
        except (OSError, json.JSONDecodeError) as exc:
            issues.append({"code": "selection_manifest_invalid", "suite_id": suite_id, "detail": str(exc)})
            continue
        checked.append(path.relative_to(repository).as_posix())
        status = str(manifest.get("status", ""))
        statuses[suite_id] = status
        if manifest.get("suite_id") != suite_id:
            issues.append({"code": "selection_suite_mismatch", "suite_id": suite_id})
        if manifest.get("source_revision") != suite.get("upstream_revision"):
            issues.append({"code": "selection_revision_mismatch", "suite_id": suite_id})
        development = _ids(manifest.get("development", []))
        evaluation = _ids(manifest.get("evaluation", []))
        if len(development) != suite.get("development_instances"):
            issues.append({"code": "development_count_mismatch", "suite_id": suite_id})
        if len(evaluation) != suite.get("evaluation_instances"):
            issues.append({"code": "evaluation_count_mismatch", "suite_id": suite_id})
        if len(set(development)) != len(development) or len(set(evaluation)) != len(evaluation):
            issues.append({"code": "duplicate_selection_id", "suite_id": suite_id})
        if set(development) & set(evaluation):
            issues.append({"code": "selection_split_overlap", "suite_id": suite_id})
        if not manifest.get("selection_rule", {}).get("score_blind"):
            issues.append({"code": "selection_not_score_blind", "suite_id": suite_id})
        if status == "frozen":
            evidence_relative = str(manifest.get("calibration_evidence", ""))
            evidence_path = (repository / evidence_relative).resolve()
            if not evidence_relative or repository not in evidence_path.parents or not evidence_path.is_file():
                issues.append({"code": "calibration_evidence_missing", "suite_id": suite_id})
            else:
                try:
                    evidence = _read(evidence_path)
                except (OSError, json.JSONDecodeError) as exc:
                    issues.append(
                        {"code": "calibration_evidence_invalid", "suite_id": suite_id, "detail": str(exc)}
                    )
                else:
                    if (
                        evidence.get("suite_id") != suite_id
                        or evidence.get("passed") is not True
                        or evidence.get("model_calls") != 0
                    ):
                        issues.append({"code": "calibration_evidence_failed", "suite_id": suite_id})
        for row in development + evaluation:
            if not row.strip():
                issues.append({"code": "empty_selection_id", "suite_id": suite_id})
        for key, value in _walk(manifest):
            if key.endswith("sha256") and (not isinstance(value, str) or not SHA256.fullmatch(value)):
                issues.append({"code": "invalid_sha256", "suite_id": suite_id, "detail": key})
            if key == "image" and (not isinstance(value, str) or not DIGEST_IMAGE.fullmatch(value)):
                issues.append({"code": "unpinned_image", "suite_id": suite_id, "detail": str(value)})
    calibration_ready = not issues and all(
        status.startswith("calibration_locked") or status == "frozen" for status in statuses.values()
    )
    frozen = calibration_ready and bool(statuses) and all(status == "frozen" for status in statuses.values())
    return {
        "schema_version": 1,
        "valid": not issues,
        "calibration_ready": calibration_ready,
        "frozen": frozen,
        "checked_manifests": sorted(checked),
        "statuses": statuses,
        "issues": issues,
        "profile": profile or "all",
    }


def _walk(value: Any, prefix: str = "") -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            name = f"{prefix}.{key}" if prefix else str(key)
            rows.append((str(key), item))
            rows.extend(_walk(item, name))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            rows.extend(_walk(item, f"{prefix}[{index}]"))
    return rows


def build_lock(root: str | Path) -> dict[str, Any]:
    repository = Path(root).resolve()
    selections = sorted((repository / "research/selections").glob("*.json"))
    inputs = [repository / relative for relative in LOCK_INPUTS] + selections
    missing = [str(path.relative_to(repository)) for path in inputs if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"freeze inputs missing: {missing}")
    files = {path.relative_to(repository).as_posix(): _sha256(path) for path in inputs}
    canonical = json.dumps(files, sort_keys=True, separators=(",", ":"))
    return {
        "schema_version": 1,
        "protocol_version": _read(repository / "research/hard_benchmark.json")["protocol_version"],
        "files": files,
        "root_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
    }


def verify_lock(root: str | Path) -> dict[str, Any]:
    repository = Path(root).resolve()
    path = repository / LOCK_PATH
    if not path.is_file():
        return {"valid": False, "error": "freeze lock missing"}
    recorded = _read(path)
    actual = build_lock(repository)
    return {
        "valid": recorded == actual,
        "recorded_root_sha256": recorded.get("root_sha256"),
        "actual_root_sha256": actual["root_sha256"],
    }


def write_lock(root: str | Path) -> dict[str, Any]:
    repository = Path(root).resolve()
    payload = build_lock(repository)
    target = repository / LOCK_PATH
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(target)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--profile")
    parser.add_argument("--write-lock", action="store_true")
    args = parser.parse_args(argv)
    selections = inspect_selections(args.root, profile=args.profile)
    if args.write_lock:
        if not selections["calibration_ready"]:
            raise SystemExit("refusing to lock invalid or incomplete selections")
        lock = write_lock(args.root)
    else:
        lock = verify_lock(args.root)
    report = {"selections": selections, "lock": lock}
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if selections["calibration_ready"] and lock.get("valid", args.write_lock) else 1


if __name__ == "__main__":
    raise SystemExit(main())
