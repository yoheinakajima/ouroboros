#!/usr/bin/env python3
"""Run exact selected SWE/Terminal jobs through the pinned Harbor adapter."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from research.freeze import inspect_selections, verify_lock

SUITES = {
    "swe": ("ouro_swe_50", "research/selections/swe_verified.json", "benchmark/.cache/swe_harbor"),
    "terminal": (
        "ouro_terminal_12",
        "research/selections/terminal_bench_2.json",
        "benchmark/.cache/terminal2",
    ),
}


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _ids(rows: list[Any]) -> list[str]:
    return [str(row["id"] if isinstance(row, dict) else row) for row in rows]


def authorize_scored_execution(repository: Path, *, suite_id: str) -> None:
    design = _read(repository / "research/hard_benchmark.json")
    approaches = _read(repository / "research/approaches.json")
    suites = {str(row["id"]): row for row in design.get("suites", [])}
    if design.get("execution_enabled") is not True:
        raise PermissionError("scored execution is locked")
    if suite_id not in suites or suites[suite_id].get("selection_status") != "frozen":
        raise PermissionError(f"suite is not frozen for scored execution: {suite_id}")
    if approaches.get("freeze_status") != "frozen":
        raise PermissionError("approach definitions are not frozen")
    selections = inspect_selections(repository, profile="local_no_account")
    if not selections["frozen"]:
        raise PermissionError("local selection manifests are not all frozen")
    if not verify_lock(repository).get("valid"):
        raise PermissionError("protocol freeze lock is invalid")


def build_command(
    *,
    repository: Path,
    harbor_binary: Path,
    suite: str,
    split: str,
    job_name: str,
    jobs_dir: Path,
    concurrency: int,
    oracle: bool,
    approach_id: str | None = None,
    arm: str | None = None,
    model: str = "gpt-5.6-sol",
    provider: str = "openai",
    seed: int = 0,
    retained_state: Path | None = None,
    sham_context: Path | None = None,
    task_ids: list[str] | None = None,
) -> list[str]:
    if suite not in SUITES:
        raise ValueError(f"unknown Harbor suite: {suite}")
    if split not in {"development", "evaluation", "all"}:
        raise ValueError(f"unknown split: {split}")
    if concurrency < 1:
        raise ValueError("concurrency must be positive")
    suite_id, manifest_relative, task_root_relative = SUITES[suite]
    manifest = _read(repository / manifest_relative)
    allowed = _ids(manifest["development"] + manifest["evaluation"])
    selected = allowed if split == "all" else _ids(manifest[split])
    if task_ids:
        if not set(task_ids) <= set(selected):
            raise ValueError("requested task is not in the selected split")
        selected = [item for item in selected if item in set(task_ids)]
    if not selected:
        raise ValueError("job selection is empty")
    task_root = (repository / task_root_relative).resolve(strict=True)
    missing = [item for item in selected if not (task_root / item).is_dir()]
    if missing:
        raise FileNotFoundError(f"materialized Harbor tasks missing: {missing}")
    if suite == "swe":
        from research.swe_harbor import verify_materialized

        materialized = verify_materialized(repository=repository, output=task_root, task_ids=selected)
        if not materialized["passed"]:
            raise PermissionError(f"materialized SWE task hardening failed: {materialized['issues']}")

    command = [
        str(harbor_binary),
        "run",
        "-p",
        str(task_root),
        "-n",
        str(concurrency),
        "--job-name",
        job_name,
        "--jobs-dir",
        str(jobs_dir),
        "--yes",
        "--quiet",
    ]
    for task_id in selected:
        command.extend(["--include-task-name", task_id])
    if oracle:
        command.extend(["--agent", "oracle"])
        return command

    if approach_id is None or arm is None:
        raise ValueError("scored Harbor jobs require approach_id and arm")
    authorize_scored_execution(repository, suite_id=suite_id)
    command.extend(
        [
            "--agent",
            "research.harbor_agent:OuroborosHarborAgent",
            "--model",
            model,
            "--agent-kwarg",
            f"approach_id={approach_id}",
            "--agent-kwarg",
            f"arm={arm}",
            "--agent-kwarg",
            f"repository={repository}",
            "--agent-kwarg",
            f"provider_name={provider}",
            "--agent-kwarg",
            f"seed={seed}",
        ]
    )
    if retained_state is not None:
        command.extend(["--agent-kwarg", f"retained_state={retained_state.resolve(strict=True)}"])
    if sham_context is not None:
        command.extend(["--agent-kwarg", f"sham_context={sham_context.resolve(strict=True)}"])
    return command


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=sorted(SUITES), required=True)
    parser.add_argument("--split", choices=["development", "evaluation", "all"], default="evaluation")
    parser.add_argument("--task", action="append")
    parser.add_argument("--oracle", action="store_true")
    parser.add_argument("--approach", choices=["workspace_v1_2", "minimal_v2", "hybrid_packs"])
    parser.add_argument(
        "--arm",
        choices=["cold", "evolved", "cold_ablation", "sham_improvement_control", "native_evolved"],
    )
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--provider", choices=["openai", "anthropic"], default="openai")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--retained-state", type=Path)
    parser.add_argument("--sham-context", type=Path)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--job-name", required=True)
    parser.add_argument("--jobs-dir", type=Path)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    repository = args.root.resolve()
    harbor_binary = Path(sys.executable).with_name("harbor")
    if not harbor_binary.is_file():
        parser.error("run with the isolated Harbor Python environment")
    jobs_dir = args.jobs_dir or repository / (
        "benchmark/.cache/calibration/harbor" if args.oracle else "artifacts/hard-benchmark"
    )
    command = build_command(
        repository=repository,
        harbor_binary=harbor_binary,
        suite=args.suite,
        split=args.split,
        job_name=args.job_name,
        jobs_dir=jobs_dir.resolve(),
        concurrency=args.concurrency,
        oracle=args.oracle,
        approach_id=args.approach,
        arm=args.arm,
        model=args.model,
        provider=args.provider,
        seed=args.seed,
        retained_state=args.retained_state,
        sham_context=args.sham_context,
        task_ids=args.task,
    )
    preview = {"command": command, "model_calls_allowed": not args.oracle, "execute": args.execute}
    print(json.dumps(preview, indent=2, sort_keys=True))
    if not args.execute:
        return 0
    environment = os.environ.copy()
    harbor_source = repository / "benchmark/.cache/harbor/src"
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(repository), str(harbor_source), *([existing] if existing else [])]
    )
    environment["HARBOR_TELEMETRY"] = "0"
    completed = subprocess.run(command, cwd=repository, env=environment, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
