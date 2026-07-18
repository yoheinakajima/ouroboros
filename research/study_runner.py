#!/usr/bin/env python3
"""Resumable execution of the frozen local Ouroboros comparison.

The runner preserves the preregistered task order and builds independent,
sequential retained-state lineages.  Every paid task is its own restart point:
Harbor/local attempt, official grading, sanitized evidence, reflection, native
adoption, and held-out result rows are recorded separately.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Literal

from research.activegraph_benchmark import materialize as materialize_activegraph
from research.adapters.common import HybridPacksAdapter, MinimalV2Adapter, WorkspaceV12Adapter
from research.comparison import ResultRow, compare
from research.curriculum import validate_manifest
from research.freeze import verify_lock
from research.grading import GraderSpec, SealedGrader
from research.harbor_jobs import build_command
from research.hybrid_author import load_env_file, provider_for, write_json
from research.lineage import (
    ReflectionBudget,
    apply_hybrid_lesson,
    apply_minimal_lesson,
    apply_workspace_lesson,
    extract_attempt_evidence,
    extract_swe_evidence,
    extract_terminal_evidence,
    load_evidence,
    load_lesson,
    reflect_evidence,
)
from research.readiness import inspect_readiness
from research.swe_official import grade_patch, locate_harbor_patch

APPROACHES = ("workspace_v1_2", "minimal_v2", "hybrid_packs")
APPROACH_SLUGS = {"workspace_v1_2": "workspace", "minimal_v2": "minimal", "hybrid_packs": "hybrid"}
SUITES = ("ouro_swe_50", "ouro_terminal_12", "ouro_activegraph_50")
HARBOR_SUITE = {"ouro_swe_50": "swe", "ouro_terminal_12": "terminal"}
SELECTIONS = {
    "ouro_swe_50": "research/selections/swe_verified.json",
    "ouro_terminal_12": "research/selections/terminal_bench_2.json",
    "ouro_activegraph_50": "research/selections/activegraph_50.json",
}
ADAPTERS = {
    "workspace_v1_2": WorkspaceV12Adapter,
    "minimal_v2": MinimalV2Adapter,
    "hybrid_packs": HybridPacksAdapter,
}
MODEL = "gpt-5.6-sol"
SAFE = re.compile(r"[^A-Za-z0-9_.-]+")


@dataclass(frozen=True)
class TaskRef:
    suite_id: str
    task_id: str


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _component(value: str, *, limit: int = 72) -> str:
    cleaned = SAFE.sub("-", value).strip("-._") or "task"
    if len(cleaned) <= limit:
        return cleaned
    suffix = hashlib.sha256(value.encode()).hexdigest()[:10]
    return cleaned[: limit - len(suffix) - 1] + "-" + suffix


def _seed(replication: int, task: TaskRef) -> int:
    label = f"ouroboros_local_comparison_v1/{replication}/{task.suite_id}/{task.task_id}"
    return int(hashlib.sha256(label.encode()).hexdigest()[:8], 16)


def _ids(rows: Iterable[Any]) -> list[str]:
    return [str(row["id"] if isinstance(row, dict) else row) for row in rows]


def development_tasks(repository: Path) -> list[TaskRef]:
    rows: list[TaskRef] = []
    for suite_id in SUITES:
        selection = _read(repository / SELECTIONS[suite_id])
        rows.extend(TaskRef(suite_id, task_id) for task_id in _ids(selection["development"]))
    return rows


def evaluation_tasks(repository: Path, *, probe: bool) -> list[TaskRef]:
    study = _read(repository / "research/local_study.json")
    probe_ids = study["recursive_probe"]
    rows: list[TaskRef] = []
    for suite_id in SUITES:
        selection = _read(repository / SELECTIONS[suite_id])
        if probe:
            key = {
                "ouro_swe_50": "swe_verified",
                "ouro_terminal_12": "terminal_bench_2",
                "ouro_activegraph_50": "activegraph_50",
            }[suite_id]
            selected = [str(value) for value in probe_ids[key]]
            allowed = set(_ids(selection["evaluation"]))
            if not set(selected) <= allowed:
                raise ValueError(f"recursive probe is not a held-out subset for {suite_id}")
        else:
            selected = _ids(selection["evaluation"])
        rows.extend(TaskRef(suite_id, task_id) for task_id in selected)
    return rows


def plan(repository: Path, *, replications: int) -> dict[str, Any]:
    development = development_tasks(repository)
    probe = evaluation_tasks(repository, probe=True)
    full = evaluation_tasks(repository, probe=False)
    return {
        "schema_version": 1,
        "model": MODEL,
        "replications": replications,
        "development_tasks_per_lineage": len(development),
        "development_attempts": len(development) * len(APPROACHES) * replications,
        "probe_tasks": len(probe),
        "one_replication_probe_attempts": len(probe) * len(APPROACHES) * 4,
        "full_evaluation_tasks": len(full),
        "preliminary_full_attempts": len(full) * len(APPROACHES) * 2 * replications,
        "suites": {
            suite_id: {
                "development": sum(row.suite_id == suite_id for row in development),
                "probe": sum(row.suite_id == suite_id for row in probe),
                "evaluation": sum(row.suite_id == suite_id for row in full),
            }
            for suite_id in SUITES
        },
    }


def _docker_image(repository: Path) -> dict[str, Any]:
    selection = _read(repository / SELECTIONS["ouro_activegraph_50"])
    tag = str(selection["container"]["local_tag"])
    completed = subprocess.run(
        ["docker", "image", "inspect", tag],
        cwd=repository,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"ActiveGraph image is missing: {tag}: {completed.stderr.strip()}")
    image = json.loads(completed.stdout)[0]
    image_id = str(image["Id"])
    return {
        "reference": image_id,
        "local_tag": tag,
        "image_id": image_id,
        "architecture": str(image["Architecture"]),
        "os": str(image["Os"]),
        "dockerfile_sha256": _sha256(repository / selection["container"]["dockerfile"]),
        "recorded_arm64_image_id": selection["container"].get("observed_local_arm64_image_id"),
        "portability_note": (
            "The run resolves the frozen local tag to an exact image id and rechecks it before every local attempt; "
            "the manifest's observed arm64 id is not portable to the x86_64 reference runtime."
        ),
    }


def _calibrate_activegraph_container(activegraph_root: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for task_root in sorted(path for path in activegraph_root.iterdir() if (path / "task.json").is_file()):
        grader = GraderSpec.model_validate(_read(task_root / "grader.json"))
        for candidate, expected in (("workspace", 20.0), ("oracle", 50.0)):
            score = SealedGrader(grader).grade(
                run_id=f"calibration-{task_root.name}-{candidate}",
                grader_workspace=task_root / "grader",
                submission=task_root / candidate,
                output_dir=activegraph_root / "_container_calibration" / task_root.name / candidate,
            )
            rows.append(
                {
                    "task_id": task_root.name,
                    "candidate": candidate,
                    "expected_score": expected,
                    "observed_score": score.primary_score,
                    "grader_error": score.grader_error,
                }
            )
    passed = len(rows) == 10 and all(
        row["observed_score"] == row["expected_score"] and not row["grader_error"] for row in rows
    )
    report = {"schema_version": 1, "model_calls": 0, "passed": passed, "checks": rows}
    _atomic_json(activegraph_root / "_container_calibration/receipt.json", report)
    if not passed:
        raise RuntimeError(f"run-specific ActiveGraph container calibration failed: {rows}")
    return report


def initialize(repository: Path, run_root: Path, *, replications: int, concurrency: int) -> dict[str, Any]:
    manifest_path = run_root / "study.json"
    if manifest_path.is_file():
        manifest = _read(manifest_path)
        if manifest.get("model") != MODEL or manifest.get("replications") != replications:
            raise ValueError("existing study model/replication contract differs from the requested run")
        return manifest
    if run_root.exists() and any(run_root.iterdir()):
        raise FileExistsError(f"study directory is nonempty but has no study.json: {run_root}")
    readiness = inspect_readiness(repository, profile="local_no_account")
    if not readiness["ready"]:
        raise RuntimeError(f"research readiness failed: {readiness['issues']}")
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=repository, text=True, capture_output=True, check=True
    ).stdout.strip()
    if status:
        raise RuntimeError("scored study initialization requires a clean tracked worktree")
    load_env_file(repository / ".env")
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not configured")
    image = _docker_image(repository)
    run_root.mkdir(parents=True, exist_ok=True)
    activegraph_root = run_root / "infrastructure/activegraph_50"
    materialize_activegraph(activegraph_root, image=image["reference"])
    container_calibration = _calibrate_activegraph_container(activegraph_root)
    lock = verify_lock(repository)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repository, text=True, capture_output=True, check=True
    ).stdout.strip()
    manifest = {
        "schema_version": 1,
        "study_id": "ouroboros_local_comparison_v1",
        "status": "initialized",
        "model": MODEL,
        "provider": "openai",
        "replications": replications,
        "concurrency": concurrency,
        "repository_commit": commit,
        "protocol_root_sha256": lock["recorded_root_sha256"],
        "created_at": _now(),
        "plan": plan(repository, replications=replications),
        "activegraph_container": image,
        "activegraph_container_calibration": container_calibration,
    }
    _atomic_json(manifest_path, manifest)
    return manifest


def _load_study(repository: Path, run_root: Path) -> dict[str, Any]:
    manifest = _read(run_root / "study.json")
    lock = verify_lock(repository)
    if not lock["valid"] or lock["recorded_root_sha256"] != manifest["protocol_root_sha256"]:
        raise RuntimeError("protocol freeze drifted after study initialization")
    current_image = _docker_image(repository)
    if current_image["image_id"] != manifest["activegraph_container"]["image_id"]:
        raise RuntimeError("ActiveGraph local image tag drifted after study initialization")
    return manifest


def _process(
    command: list[str],
    *,
    repository: Path,
    log_dir: Path,
    environment: dict[str, str] | None = None,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    log_dir.mkdir(parents=True, exist_ok=True)
    _atomic_json(log_dir / "command.json", {"command": command, "started_at": _now()})
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=repository,
        env=environment,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    (log_dir / "stdout.txt").write_text(completed.stdout[-1_000_000:], encoding="utf-8")
    (log_dir / "stderr.txt").write_text(completed.stderr[-1_000_000:], encoding="utf-8")
    _atomic_json(
        log_dir / "process.json",
        {"returncode": completed.returncode, "elapsed_seconds": time.monotonic() - started, "finished_at": _now()},
    )
    return completed


def _trial(job_dir: Path, task_id: str) -> Path:
    matches = sorted(path for path in job_dir.glob(f"{task_id}__*") if path.is_dir())
    if len(matches) != 1:
        raise ValueError(f"expected one Harbor trial for {task_id}, found {len(matches)} in {job_dir}")
    return matches[0]


def _harbor_environment(repository: Path) -> dict[str, str]:
    environment = os.environ.copy()
    paths = [str(repository), str(repository / "benchmark/.cache/harbor/src")]
    if environment.get("PYTHONPATH"):
        paths.append(environment["PYTHONPATH"])
    environment["PYTHONPATH"] = os.pathsep.join(paths)
    environment["HARBOR_TELEMETRY"] = "0"
    return environment


def _run_harbor(
    repository: Path,
    *,
    output_root: Path,
    task: TaskRef,
    approach_id: str,
    arm: str,
    seed: int,
    retained_state: Path | None,
    sham_context: Path | None,
) -> Path:
    job_name = _component(f"{output_root.parent.name}-{APPROACH_SLUGS[approach_id]}-{arm}-{task.task_id}", limit=118)
    jobs_dir = output_root / "jobs"
    job_dir = jobs_dir / job_name
    if (job_dir / "result.json").is_file():
        return job_dir
    harbor = repository / "benchmark/.cache/venvs/harbor/bin/harbor"
    if not harbor.is_file():
        raise FileNotFoundError("isolated Harbor executable is missing")
    command = build_command(
        repository=repository,
        harbor_binary=harbor,
        suite=HARBOR_SUITE[task.suite_id],
        split="development" if "development" in output_root.parts else "evaluation",
        job_name=job_name,
        jobs_dir=jobs_dir,
        concurrency=1,
        oracle=False,
        approach_id=approach_id,
        arm=arm,
        model=MODEL,
        provider="openai",
        seed=seed,
        retained_state=retained_state,
        sham_context=sham_context,
        task_ids=[task.task_id],
    )
    completed = _process(
        command,
        repository=repository,
        log_dir=output_root / "harbor-process",
        environment=_harbor_environment(repository),
        timeout=18_000,
    )
    if not (job_dir / "result.json").is_file():
        raise RuntimeError(f"Harbor produced no job result (exit {completed.returncode}): {job_name}")
    return job_dir


def _grade_swe(repository: Path, *, job_dir: Path, task_id: str) -> dict[str, Any]:
    output = job_dir / "official-evaluation"
    receipt = output / "receipt.json"
    if receipt.is_file():
        return _read(receipt)
    if output.exists() and any(output.iterdir()):
        raise RuntimeError(f"partial official SWE evaluation requires inspection: {output}")
    patch = locate_harbor_patch(job_dir, task_id)
    return grade_patch(
        repository=repository,
        instance_id=task_id,
        patch_path=patch,
        run_dir=output,
        run_id=job_dir.name,
        model_name=MODEL,
        timeout_seconds=3_600,
    )


def _activegraph_paths(run_root: Path, task_id: str) -> tuple[Path, Path, Path, Path]:
    task_root = run_root / "infrastructure/activegraph_50" / task_id
    return task_root / "task.json", task_root / "workspace", task_root / "grader.json", task_root / "grader"


def _run_activegraph(
    repository: Path,
    run_root: Path,
    *,
    output_root: Path,
    task: TaskRef,
    approach_id: str,
    arm: str,
    seed: int,
    replication: int,
    retained_state: Path | None,
    sham_context: Path | None,
) -> Path:
    attempt = output_root / "attempt"
    if (attempt / "audit.json").is_file() and (attempt / "grader/score.json").is_file():
        return attempt
    if attempt.exists():
        raise RuntimeError(f"partial ActiveGraph attempt requires inspection: {attempt}")
    task_json, workspace, grader_json, grader = _activegraph_paths(run_root, task.task_id)
    command = [
        str(repository / ".venv/bin/python"),
        "-m",
        "research.attempt_runner",
        "--approach",
        approach_id,
        "--arm",
        arm,
        "--task",
        str(task_json),
        "--workspace",
        str(workspace),
        "--grader-spec",
        str(grader_json),
        "--grader-workspace",
        str(grader),
        "--run-dir",
        str(attempt),
        "--model",
        MODEL,
        "--seed",
        str(seed),
        "--replication",
        str(replication),
        "--max-cost-usd",
        "50",
        "--max-model-calls",
        "120",
        "--max-output-tokens",
        "400000",
    ]
    if retained_state is not None:
        command.extend(["--retained-state", str(retained_state)])
    if sham_context is not None:
        command.extend(["--sham-context", str(sham_context)])
    completed = _process(command, repository=repository, log_dir=output_root / "attempt-process", timeout=18_000)
    if not (attempt / "grader/score.json").is_file():
        raise RuntimeError(f"ActiveGraph attempt produced no score (exit {completed.returncode})")
    return attempt


def _development_attempt(
    repository: Path,
    run_root: Path,
    *,
    generation: Path,
    task: TaskRef,
    approach_id: str,
    replication: int,
    parent_state: Path | None,
) -> Path:
    evidence_path = generation / "evidence.public.json"
    if evidence_path.is_file():
        return evidence_path
    arm = "cold" if parent_state is None else "native_evolved"
    seed = _seed(replication, task)
    if task.suite_id in HARBOR_SUITE:
        job_dir = _run_harbor(
            repository,
            output_root=generation / "development/harbor",
            task=task,
            approach_id=approach_id,
            arm=arm,
            seed=seed,
            retained_state=parent_state,
            sham_context=None,
        )
        if task.suite_id == "ouro_swe_50":
            _grade_swe(repository, job_dir=job_dir, task_id=task.task_id)
            evidence = extract_swe_evidence(repository, job_dir=job_dir, task_id=task.task_id)
        else:
            evidence = extract_terminal_evidence(repository, job_dir=job_dir, task_id=task.task_id)
    else:
        attempt = _run_activegraph(
            repository,
            run_root,
            output_root=generation / "development/local",
            task=task,
            approach_id=approach_id,
            arm=arm,
            seed=seed,
            replication=replication,
            retained_state=parent_state,
            sham_context=None,
        )
        task_json, _, _, _ = _activegraph_paths(run_root, task.task_id)
        evidence = extract_attempt_evidence(repository, run_dir=attempt, task_json=task_json)
    write_json(evidence_path, evidence.model_dump(mode="json"))
    return evidence_path


def _reflect_and_apply(
    repository: Path,
    *,
    generation: Path,
    approach_id: str,
    parent_state: Path | None,
) -> Path:
    state = generation / "state"
    if (state / "evolution_manifest.json").is_file():
        validate_manifest(state, approach_id=approach_id)
        return state
    evidence = load_evidence(generation / "evidence.public.json")
    reflection = generation / "reflection"
    lesson_path = reflection / "lesson.json"
    if lesson_path.is_file():
        lesson = load_lesson(lesson_path)
    else:
        load_env_file(repository / ".env")
        lesson, _ = reflect_evidence(
            evidence,
            run_dir=reflection,
            provider=provider_for("openai"),
            budget=ReflectionBudget(model=MODEL, max_cost_usd=10.0, max_output_tokens=8_000),
        )
    if approach_id == "minimal_v2":
        apply_minimal_lesson(evidence=evidence, lesson=lesson, output_state=state, parent_state=parent_state)
    elif approach_id == "workspace_v1_2":
        apply_workspace_lesson(
            repository=repository,
            evidence=evidence,
            lesson=lesson,
            output_state=state,
            native_run_root=generation / "native-workspace",
            parent_state=parent_state,
            model=MODEL,
            max_cost_usd=50.0,
            generations=1,
        )
    else:
        apply_hybrid_lesson(
            repository=repository,
            docs_root=repository.parent / "activegraph/docs",
            evidence=evidence,
            lesson=lesson,
            output_state=state,
            native_run_dir=generation / "native-hybrid",
            parent_state=parent_state,
            model=MODEL,
            max_cost_usd=50.0,
            max_llm_calls=20,
        )
    validate_manifest(state, approach_id=approach_id)
    _atomic_json(generation / "complete.json", {"completed_at": _now(), "state": str(state)})
    return state


def run_development(
    repository: Path,
    run_root: Path,
    *,
    replication: int,
    approach_id: str,
    through_generation: int | None = None,
) -> Path:
    _load_study(repository, run_root)
    parent: Path | None = None
    tasks = development_tasks(repository)
    if through_generation is not None:
        if not 1 <= through_generation <= len(tasks):
            raise ValueError(f"through_generation must be within [1, {len(tasks)}]")
        selected_tasks = tasks[:through_generation]
    else:
        selected_tasks = tasks
    lineage = run_root / "development" / f"replication-{replication:02d}" / approach_id
    for index, task in enumerate(selected_tasks, 1):
        generation = lineage / f"generation-{index:03d}-{_component(task.task_id)}"
        print(
            f"[development r{replication} {approach_id}] {index}/{len(tasks)} {task.suite_id}/{task.task_id}",
            flush=True,
        )
        _development_attempt(
            repository,
            run_root,
            generation=generation,
            task=task,
            approach_id=approach_id,
            replication=replication,
            parent_state=parent,
        )
        parent = _reflect_and_apply(
            repository, generation=generation, approach_id=approach_id, parent_state=parent
        )
    assert parent is not None
    validate_manifest(parent, approach_id=approach_id)
    if len(selected_tasks) == len(tasks):
        _atomic_json(lineage / "lineage-complete.json", {"completed_at": _now(), "final_state": str(parent)})
    return parent


def final_state(run_root: Path, *, replication: int, approach_id: str) -> Path:
    lineage = run_root / "development" / f"replication-{replication:02d}" / approach_id
    receipt = _read(lineage / "lineage-complete.json")
    state = Path(receipt["final_state"]).resolve(strict=True)
    validate_manifest(state, approach_id=approach_id)
    return state


def _opaque_sham(length: int, *, label: str) -> str:
    rows: list[str] = []
    index = 0
    while sum(len(row) for row in rows) < length:
        digest = hashlib.sha256(f"{label}/{index}".encode()).hexdigest()
        rows.append(f"opaque_record_{index:06d}={digest}\n")
        index += 1
    return "".join(rows)[:length]


def sham_context(run_root: Path, *, replication: int, approach_id: str, state: Path) -> Path:
    root = run_root / "controls/sham" / f"replication-{replication:02d}" / approach_id
    target = root / "context.txt"
    if target.is_file():
        return target
    adapter = ADAPTERS[approach_id](model=MODEL, retained_state=state)
    prepared = adapter.prepare(task={"prompt": "opaque context-size calibration query"}, arm="evolved", seed=0)
    length = max(1, min(64_000, prepared.exposed_context_bytes))
    value = _opaque_sham(length, label=f"{replication}/{approach_id}")
    root.mkdir(parents=True, exist_ok=True)
    target.write_text(value, encoding="utf-8")
    _atomic_json(
        root / "receipt.json",
        {
            "schema_version": 1,
            "purpose": "unrelated opaque artifact matched to retained context size",
            "source_state": str(state),
            "source_state_hash": prepared.retained_state_hash,
            "target_bytes": prepared.exposed_context_bytes,
            "actual_bytes": len(value.encode()),
            "sha256": _sha256(target),
        },
    )
    return target


def _iso_elapsed(result: dict[str, Any]) -> float:
    try:
        started = datetime.fromisoformat(str(result["started_at"]).replace("Z", "+00:00"))
        finished = datetime.fromisoformat(str(result["finished_at"]).replace("Z", "+00:00"))
        return max(0.0, (finished - started).total_seconds())
    except Exception:
        return 0.0


def _evaluate_one(
    repository: Path,
    run_root: Path,
    *,
    stage: str,
    task: TaskRef,
    approach_id: str,
    arm: str,
    replication: int,
    state: Path,
    sham: Path,
) -> ResultRow:
    output = (
        run_root
        / "evaluation"
        / stage
        / f"replication-{replication:02d}"
        / approach_id
        / arm
        / task.suite_id
        / _component(task.task_id)
    )
    row_path = output / "result-row.json"
    if row_path.is_file():
        return ResultRow.model_validate(_read(row_path))
    retained = state if arm in {"evolved", "cold_ablation"} else None
    sham_path = sham if arm == "sham_improvement_control" else None
    seed = _seed(replication, task)
    if task.suite_id in HARBOR_SUITE:
        job_dir = _run_harbor(
            repository,
            output_root=output / "evaluation/harbor",
            task=task,
            approach_id=approach_id,
            arm=arm,
            seed=seed,
            retained_state=retained,
            sham_context=sham_path,
        )
        trial = _trial(job_dir, task.task_id)
        summary = _read(trial / "agent/ouroboros-summary.json")
        trial_result = _read(trial / "result.json")
        usage = summary.get("usage", {})
        if task.suite_id == "ouro_swe_50":
            receipt = _grade_swe(repository, job_dir=job_dir, task_id=task.task_id)
            score = 1.0 if receipt.get("resolved") is True else 0.0
            valid = receipt.get("passed") is True
            invalid_reason = None if valid else "official SWE evaluator error"
        else:
            reward = trial_result.get("verifier_result", {}).get("rewards", {}).get("reward")
            score = float(reward) if isinstance(reward, (int, float)) else 0.0
            valid = trial_result.get("exception_info") is None and isinstance(reward, (int, float))
            invalid_reason = None if valid else "Harbor task/verifier infrastructure error"
        maximum = 1.0
        wall = _iso_elapsed(trial_result)
        provenance = {"job_dir": str(job_dir), "trial_dir": str(trial)}
    else:
        attempt = _run_activegraph(
            repository,
            run_root,
            output_root=output / "evaluation/local",
            task=task,
            approach_id=approach_id,
            arm=arm,
            seed=seed,
            replication=replication,
            retained_state=retained,
            sham_context=sham_path,
        )
        attempt_row = _read(attempt / "attempt.json")
        score_row = _read(attempt / "grader/score.json")
        usage = attempt_row.get("usage", {})
        score = float(score_row["primary_score"])
        maximum = 50.0
        valid = not bool(score_row.get("grader_error"))
        invalid_reason = None if valid else str(score_row.get("grader_error"))
        started = datetime.fromisoformat(attempt_row["started_at"])
        finished = datetime.fromisoformat(attempt_row["finished_at"])
        wall = max(0.0, (finished - started).total_seconds())
        provenance = {"attempt_dir": str(attempt), "audit_sha256": _sha256(attempt / "audit.json")}
    row = ResultRow(
        approach_id=approach_id,
        suite_id=task.suite_id,
        task_id=task.task_id,
        arm=arm,  # type: ignore[arg-type]
        seed=seed,
        replication=replication,
        score=score,
        maximum_score=maximum,
        cost_usd=float(usage.get("cost_usd", 0) or 0),
        wall_seconds=wall,
        valid=valid,
        invalid_reason=invalid_reason,
    )
    _atomic_json(row_path, row.model_dump(mode="json"))
    _atomic_json(output / "provenance.json", provenance)
    return row


def run_evaluation(
    repository: Path,
    run_root: Path,
    *,
    stage: Literal["probe", "preliminary"],
    replication: int,
    approach_id: str,
    concurrency: int,
) -> list[ResultRow]:
    _load_study(repository, run_root)
    state = final_state(run_root, replication=replication, approach_id=approach_id)
    sham = sham_context(run_root, replication=replication, approach_id=approach_id, state=state)
    tasks = evaluation_tasks(repository, probe=stage == "probe")
    arms = (
        ("cold", "evolved", "cold_ablation", "sham_improvement_control")
        if stage == "probe"
        else ("cold", "evolved")
    )
    rows: list[ResultRow] = []
    for arm in arms:
        for suite_id in SUITES:
            selected = [task for task in tasks if task.suite_id == suite_id]
            print(
                f"[evaluation {stage} r{replication} {approach_id} {arm}] {suite_id}: {len(selected)} tasks",
                flush=True,
            )
            errors: list[str] = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = {
                    executor.submit(
                        _evaluate_one,
                        repository,
                        run_root,
                        stage=stage,
                        task=task,
                        approach_id=approach_id,
                        arm=arm,
                        replication=replication,
                        state=state,
                        sham=sham,
                    ): task
                    for task in selected
                }
                for future in concurrent.futures.as_completed(futures):
                    task = futures[future]
                    try:
                        row = future.result()
                    except Exception as exc:
                        errors.append(f"{task.suite_id}/{task.task_id}: {type(exc).__name__}: {exc}")
                    else:
                        rows.append(row)
                        print(f"  {task.task_id}: {row.score:g}/{row.maximum_score:g}", flush=True)
            if errors:
                raise RuntimeError("evaluation group had failures:\n" + "\n".join(errors))
    aggregate(run_root, stage=stage)
    return rows


def _result_paths(run_root: Path, stage: str) -> list[Path]:
    return sorted((run_root / "evaluation" / stage).glob("**/result-row.json"))


def aggregate(run_root: Path, *, stage: str) -> dict[str, Any]:
    rows = [ResultRow.model_validate(_read(path)) for path in _result_paths(run_root, stage)]
    results_path = run_root / f"results-{stage}.jsonl"
    results_path.write_text(
        "".join(row.model_dump_json() + "\n" for row in rows),
        encoding="utf-8",
    )
    comparison = compare(rows) if rows else {"schema_version": 1, "valid_rows": 0}
    summary = {
        "schema_version": 1,
        "stage": stage,
        "attempts": len(rows),
        "valid_attempts": sum(row.valid for row in rows),
        "cost_usd": sum(row.cost_usd for row in rows),
        "recorded_at": _now(),
        "comparison": comparison,
    }
    _atomic_json(run_root / f"report-{stage}.json", summary)
    return summary


def run_study(
    repository: Path,
    run_root: Path,
    *,
    replications: int,
    concurrency: int,
    through: Literal["development", "probe", "preliminary"],
) -> None:
    initialize(repository, run_root, replications=replications, concurrency=concurrency)
    load_env_file(repository / ".env")
    first_replications = [1] if through == "probe" else list(range(1, replications + 1))
    if through == "development":
        first_replications = list(range(1, replications + 1))
    for replication in first_replications:
        for approach_id in APPROACHES:
            run_development(
                repository,
                run_root,
                replication=replication,
                approach_id=approach_id,
            )
        if replication == 1 and through in {"probe", "preliminary"}:
            for approach_id in APPROACHES:
                run_evaluation(
                    repository,
                    run_root,
                    stage="probe",
                    replication=1,
                    approach_id=approach_id,
                    concurrency=concurrency,
                )
            probe_report = aggregate(run_root, stage="probe")
            if probe_report["attempts"] != len(evaluation_tasks(repository, probe=True)) * len(APPROACHES) * 4:
                raise RuntimeError("one-replication probe is incomplete")
            if probe_report["valid_attempts"] != probe_report["attempts"]:
                raise RuntimeError("one-replication probe contains infrastructure-invalid attempts")
    if through != "preliminary":
        return
    for replication in range(1, replications + 1):
        for approach_id in APPROACHES:
            run_evaluation(
                repository,
                run_root,
                stage="preliminary",
                replication=replication,
                approach_id=approach_id,
                concurrency=concurrency,
            )
    aggregate(run_root, stage="preliminary")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    subparsers = parser.add_subparsers(dest="command", required=True)

    show = subparsers.add_parser("plan")
    show.add_argument("--replications", type=int, default=3)

    initialize_parser = subparsers.add_parser("init")
    initialize_parser.add_argument("--run-root", type=Path, required=True)
    initialize_parser.add_argument("--replications", type=int, default=3)
    initialize_parser.add_argument("--concurrency", type=int, default=3)

    development_parser = subparsers.add_parser("development")
    development_parser.add_argument("--run-root", type=Path, required=True)
    development_parser.add_argument("--replication", type=int, required=True)
    development_parser.add_argument("--approach", choices=APPROACHES, required=True)
    development_parser.add_argument("--through-generation", type=int)

    evaluation_parser = subparsers.add_parser("evaluation")
    evaluation_parser.add_argument("--run-root", type=Path, required=True)
    evaluation_parser.add_argument("--stage", choices=["probe", "preliminary"], required=True)
    evaluation_parser.add_argument("--replication", type=int, required=True)
    evaluation_parser.add_argument("--approach", choices=APPROACHES, required=True)
    evaluation_parser.add_argument("--concurrency", type=int, default=3)

    aggregate_parser = subparsers.add_parser("aggregate")
    aggregate_parser.add_argument("--run-root", type=Path, required=True)
    aggregate_parser.add_argument("--stage", choices=["probe", "preliminary"], required=True)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--run-root", type=Path, required=True)
    run_parser.add_argument("--replications", type=int, default=3)
    run_parser.add_argument("--concurrency", type=int, default=3)
    run_parser.add_argument("--through", choices=["development", "probe", "preliminary"], default="preliminary")

    args = parser.parse_args(argv)
    repository = args.root.resolve(strict=True)
    if args.command == "plan":
        print(json.dumps(plan(repository, replications=args.replications), indent=2, sort_keys=True))
        return 0
    if args.command == "init":
        result = initialize(
            repository,
            args.run_root.resolve(),
            replications=args.replications,
            concurrency=args.concurrency,
        )
    elif args.command == "development":
        result = {
            "final_state": str(
                run_development(
                    repository,
                    args.run_root.resolve(strict=True),
                    replication=args.replication,
                    approach_id=args.approach,
                    through_generation=args.through_generation,
                )
            )
        }
    elif args.command == "evaluation":
        result = {
            "attempts": len(
                run_evaluation(
                    repository,
                    args.run_root.resolve(strict=True),
                    stage=args.stage,
                    replication=args.replication,
                    approach_id=args.approach,
                    concurrency=args.concurrency,
                )
            )
        }
    elif args.command == "aggregate":
        result = aggregate(args.run_root.resolve(strict=True), stage=args.stage)
    else:
        run_study(
            repository,
            args.run_root.resolve(),
            replications=args.replications,
            concurrency=args.concurrency,
            through=args.through,
        )
        result = {"status": "completed", "through": args.through}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
