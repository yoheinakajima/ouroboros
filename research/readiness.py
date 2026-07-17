#!/usr/bin/env python3
"""No-spend preflight for reproducible benchmark and open-source readiness."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from research.freeze import inspect_selections, verify_lock
from research.sandbox import docker_status


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _issue(code: str, message: str, *, scope: str = "benchmark", severity: str = "blocker") -> dict[str, str]:
    return {"code": code, "message": message, "scope": scope, "severity": severity}


def inspect_readiness(root: str | Path) -> dict[str, Any]:
    repository = Path(root).resolve()
    issues: list[dict[str, str]] = []
    required = [
        "README.md",
        "pyproject.toml",
        "research/hard_benchmark.json",
        "research/approaches.json",
        "research/broker_protocol.json",
        "research/environment.lock.json",
        "research/PROTOCOL.md",
    ]
    for relative in required:
        if not (repository / relative).is_file():
            issues.append(_issue("required_file_missing", relative, scope="structure", severity="error"))

    benchmark_path = repository / "research" / "hard_benchmark.json"
    approaches_path = repository / "research" / "approaches.json"
    broker_path = repository / "research" / "broker_protocol.json"
    environment_path = repository / "research" / "environment.lock.json"
    benchmark = _read_json(benchmark_path) if benchmark_path.is_file() else {}
    approaches = _read_json(approaches_path) if approaches_path.is_file() else {}
    broker = _read_json(broker_path) if broker_path.is_file() else {}
    environment = _read_json(environment_path) if environment_path.is_file() else {}

    if broker and broker.get("implementation_status") != "ready":
        issues.append(_issue("broker_not_ready", str(broker.get("implementation_status"))))

    if benchmark and benchmark.get("execution_enabled") is not True:
        issues.append(_issue("execution_disabled", str(benchmark.get("execution_lock_reason", "locked"))))
    suite_ids: set[str] = set()
    for suite in benchmark.get("suites", []):
        suite_id = str(suite.get("id", ""))
        if not suite_id or suite_id in suite_ids:
            issues.append(_issue("suite_id_invalid", suite_id or "<empty>", scope="structure", severity="error"))
        suite_ids.add(suite_id)
        revision = str(suite.get("upstream_revision", ""))
        if not revision or revision.startswith("UN"):
            issues.append(_issue("suite_revision_unpinned", f"{suite_id}: {revision or '<missing>'}"))
        if suite.get("selection_status") != "frozen":
            issues.append(_issue("suite_selection_unfrozen", f"{suite_id}: {suite.get('selection_status')}"))

    if approaches.get("freeze_status") != "frozen":
        issues.append(_issue("approaches_unfrozen", str(approaches.get("freeze_status"))))
    approach_ids: set[str] = set()
    for approach in approaches.get("approaches", []):
        approach_id = str(approach.get("id", ""))
        if not approach_id or approach_id in approach_ids:
            issues.append(_issue("approach_id_invalid", approach_id or "<empty>", scope="structure", severity="error"))
        approach_ids.add(approach_id)
        if approach.get("adapter_status") != "ready":
            issues.append(_issue("adapter_not_ready", f"{approach_id}: {approach.get('adapter_status')}"))
        for capability, ready in approach.get("hardening", {}).items():
            if ready is not True:
                issues.append(_issue("hardening_incomplete", f"{approach_id}: {capability}"))
        for source in approach.get("sources", []):
            relative = str(source.get("path", ""))
            path = (repository / relative).resolve()
            if repository not in path.parents or not path.is_file():
                issues.append(
                    _issue(
                        "approach_source_missing",
                        f"{approach_id}: {relative}",
                        scope="structure",
                        severity="error",
                    )
                )
                continue
            expected = str(source.get("sha256", ""))
            actual = _sha256(path)
            if expected != actual:
                issues.append(
                    _issue(
                        "approach_hash_drift",
                        f"{approach_id}: {relative} expected {expected}, got {actual}",
                    )
                )

    if not (repository / "LICENSE").is_file():
        issues.append(
            _issue(
                "license_missing",
                "Choose and add the repository license before publication.",
                scope="open_source",
            )
        )
    if shutil.which("docker") is None:
        issues.append(_issue("docker_missing", "Docker is required by the external evaluators.", scope="environment"))
    else:
        status = docker_status()
        if not status.get("ready"):
            issues.append(
                _issue(
                    "docker_daemon_unavailable",
                    str(status.get("error", "Docker daemon is not ready")),
                    scope="environment",
                )
            )
    if sys.version_info < (3, 11):
        issues.append(
            _issue(
                "python_too_old",
                f"Python {sys.version.split()[0]}; >=3.11 required",
                scope="environment",
            )
        )
    for package, expected in environment.get("packages", {}).items():
        try:
            actual = version(package)
        except PackageNotFoundError:
            issues.append(_issue("package_missing", package, scope="environment"))
            continue
        if actual != expected:
            issues.append(
                _issue(
                    "package_version_drift",
                    f"{package}: expected {expected}, got {actual}",
                    scope="environment",
                )
            )

    selection_report = inspect_selections(repository, profile="local_no_account")
    if not selection_report["calibration_ready"]:
        issues.append(
            _issue(
                "selection_calibration_not_ready",
                json.dumps(selection_report["issues"], sort_keys=True),
            )
        )
    lock_report = verify_lock(repository)
    if not lock_report.get("valid"):
        issues.append(_issue("freeze_lock_invalid", str(lock_report)))
    smoke_path = repository / "evidence" / "calibration_smoke.json"
    if not smoke_path.is_file():
        issues.append(_issue("calibration_smoke_missing", str(smoke_path.relative_to(repository))))
    else:
        try:
            smoke = _read_json(smoke_path)
            if (
                smoke.get("passed") is not True
                or smoke.get("model_calls") != 0
                or smoke.get("upstream_tasks_executed") is not False
            ):
                issues.append(_issue("calibration_smoke_failed", "six-family no-model smoke did not pass"))
        except (OSError, json.JSONDecodeError) as exc:
            issues.append(_issue("calibration_smoke_invalid", str(exc), severity="error"))
    bootstrap_path = repository / "evidence" / "benchmark_bootstrap.json"
    if not bootstrap_path.is_file():
        issues.append(_issue("benchmark_bootstrap_missing", str(bootstrap_path.relative_to(repository))))
    else:
        try:
            bootstrap = _read_json(bootstrap_path)
            if (
                bootstrap.get("ready") is not True
                or bootstrap.get("model_calls") != 0
                or bootstrap.get("terminal_tasks_checked") != 18
                or bootstrap.get("terminal_images_checked") != 18
            ):
                issues.append(_issue("benchmark_bootstrap_failed", "local source/image verification incomplete"))
        except (OSError, json.JSONDecodeError) as exc:
            issues.append(_issue("benchmark_bootstrap_invalid", str(exc), severity="error"))

    try:
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=repository, text=True, capture_output=True, timeout=10, check=False
        )
        if status.returncode != 0:
            issues.append(_issue("git_status_failed", status.stderr.strip(), scope="open_source", severity="error"))
        elif status.stdout.strip():
            issues.append(
                _issue(
                    "worktree_dirty",
                    "Commit or intentionally exclude all release inputs.",
                    scope="open_source",
                )
            )
    except (OSError, subprocess.TimeoutExpired) as exc:
        issues.append(_issue("git_status_failed", str(exc), scope="open_source", severity="error"))

    errors = [item for item in issues if item["severity"] == "error"]
    blockers = [item for item in issues if item["severity"] == "blocker"]
    scored_only_codes = {"execution_disabled", "suite_selection_unfrozen", "approaches_unfrozen"}
    calibration_blockers = [item for item in blockers if item["code"] not in scored_only_codes]
    return {
        "schema_version": 1,
        "ready": not errors and not blockers,
        "ready_for_oracle_calibration": not errors and not calibration_blockers,
        "structurally_valid": not errors,
        "execution_enabled": benchmark.get("execution_enabled") is True,
        "approaches": sorted(approach_ids),
        "suites": sorted(suite_ids),
        "issue_count": len(issues),
        "issues": issues,
        "selection_report": selection_report,
        "freeze_lock": lock_report,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--development",
        action="store_true",
        help="succeed when schemas and paths are sound, while still reporting blockers",
    )
    args = parser.parse_args(argv)
    report = inspect_readiness(args.root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if (report["structurally_valid"] if args.development else report["ready"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
