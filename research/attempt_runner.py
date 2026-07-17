#!/usr/bin/env python3
"""Run one comparable architecture attempt, sealed grade, and bundle audit."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from ouroboros import load_env_file, provider_for
from research.adapters.common import HybridPacksAdapter, MinimalV2Adapter, StateAdapter, WorkspaceV12Adapter
from research.audit import seal_attempt_bundle
from research.broker import (
    ActiveGraphHostInference,
    AuthorityBroker,
    BrokerBudget,
    BrokerConfig,
    BudgetExhausted,
    InferenceProvider,
)
from research.contracts import AttemptRecord, ResourceUsage
from research.curriculum import validate_manifest
from research.grading import GraderSpec, SealedGrader
from research.harbor_jobs import authorize_scored_execution
from research.sandbox import SandboxLimits


class TaskSpec(BaseModel):
    suite_id: str
    task_id: str
    study_id: str = "common_outcome"
    prompt: str = Field(min_length=1)
    image: str
    network: bool = False
    command_environment: dict[str, str] = Field(default_factory=dict)
    sandbox_limits: dict[str, float | int] = Field(default_factory=dict)


ADAPTERS: dict[str, type[StateAdapter]] = {
    "workspace_v1_2": WorkspaceV12Adapter,
    "minimal_v2": MinimalV2Adapter,
    "hybrid_packs": HybridPacksAdapter,
}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _source_hashes(root: Path, approach_id: str) -> dict[str, str]:
    catalog = _load_json(root / "research/approaches.json")
    for approach in catalog["approaches"]:
        if approach["id"] == approach_id:
            return {row["path"]: row["sha256"] for row in approach["sources"]}
    raise ValueError(f"unknown approach: {approach_id}")


def _make_container_writable(root: Path) -> None:
    """Let the fixed unprivileged container UID modify only its disposable copy."""

    root.chmod(root.stat().st_mode | 0o777)
    for path in root.rglob("*"):
        mode = path.stat().st_mode
        path.chmod(mode | (0o777 if path.is_dir() else 0o222))


def run_attempt(
    *,
    repository: Path,
    approach_id: str,
    arm: str,
    task_spec: TaskSpec,
    task_workspace: Path,
    grader_spec: GraderSpec,
    grader_workspace: Path,
    run_dir: Path,
    retained_state: Path | None,
    sham_context: Path | None,
    provider_name: str,
    model: str,
    seed: int,
    replication: int,
    budget: BrokerBudget,
    inference_provider: InferenceProvider | None = None,
    command_sandbox: Any | None = None,
    grader_sandbox: Any | None = None,
) -> dict[str, Any]:
    if run_dir.exists():
        raise FileExistsError(f"run directory already exists: {run_dir}")
    source_workspace = task_workspace.resolve(strict=True)
    if not source_workspace.is_dir() or source_workspace.is_symlink():
        raise ValueError("task workspace must be a regular directory")
    for path in source_workspace.rglob("*"):
        relative = path.relative_to(source_workspace)
        if path.is_symlink():
            raise ValueError("agent workspace contains a symlink")
        if any(part in {".grader", "hidden", "private"} for part in relative.parts):
            raise ValueError("agent workspace contains a grader/private-named path")
    for path in grader_workspace.resolve(strict=True).rglob("*"):
        if path.is_symlink():
            raise ValueError("grader workspace contains a symlink")
    adapter_type = ADAPTERS[approach_id]
    curriculum_manifest = None
    if arm in {"evolved", "native_evolved", "cold_ablation"}:
        if retained_state is None:
            raise ValueError(f"{arm} requires evolved state")
        curriculum_manifest = validate_manifest(retained_state, approach_id=approach_id)
    run_dir.mkdir(parents=True)
    workspace = run_dir / "workspace"
    shutil.copytree(source_workspace, workspace, symlinks=False)
    _make_container_writable(workspace)
    adapter = adapter_type(model=model, retained_state=retained_state, sham_context=sham_context)
    prepared = adapter.prepare(task=task_spec.model_dump(), arm=arm, seed=seed)
    provider = inference_provider or ActiveGraphHostInference(provider_for(provider_name))
    limits = SandboxLimits(
        wall_seconds=float(task_spec.sandbox_limits.get("wall_seconds", min(600, budget.max_wall_seconds))),
        memory_mb=int(task_spec.sandbox_limits.get("memory_mb", 4096)),
        cpus=float(task_spec.sandbox_limits.get("cpus", 4)),
        pids=int(task_spec.sandbox_limits.get("pids", 512)),
        tmpfs_mb=int(task_spec.sandbox_limits.get("tmpfs_mb", 512)),
        output_bytes=int(task_spec.sandbox_limits.get("output_bytes", 2_000_000)),
    )
    broker = AuthorityBroker(
        BrokerConfig(
            workspace=workspace,
            trace_path=run_dir / "trace.jsonl",
            image=task_spec.image,
            budget=budget,
            sandbox_limits=limits,
            network=task_spec.network,
            command_environment=task_spec.command_environment,
        ),
        provider=provider,
        sandbox=command_sandbox,
    )
    run_id = run_dir.name
    started = datetime.now(UTC).isoformat()
    status = "failed"
    outcome: dict[str, Any]
    try:
        result = adapter.run(prepared, broker)
        outcome = result.model_dump(mode="json")
        status = "completed" if result.status == "completed" else "failed"
    except BudgetExhausted as exc:
        outcome = {"status": "budget_exhausted", "error": str(exc)}
        status = "budget_exhausted"
    except Exception as exc:
        outcome = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}
        status = "failed"
    finished = datetime.now(UTC).isoformat()
    (run_dir / "outcome.json").write_text(json.dumps(outcome, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    attempt = AttemptRecord(
        run_id=run_id,
        approach_id=approach_id,
        study_id=task_spec.study_id,
        suite_id=task_spec.suite_id,
        task_id=task_spec.task_id,
        arm=arm,  # type: ignore[arg-type]
        replication=replication,
        seed=seed,
        model=model,
        task_image_digest=task_spec.image,
        approach_source_hashes=_source_hashes(repository, approach_id),
        started_at=started,
        finished_at=finished,
        status=status,  # type: ignore[arg-type]
        usage=ResourceUsage.model_validate(broker.usage.model_dump()),
        trace_path="trace.jsonl",
        submission_path="workspace",
        metadata={
            "adapter": adapter.descriptor.model_dump(mode="json"),
            "retained_state_hash": prepared.retained_state_hash,
            "retained_state_present": prepared.retained_state_present,
            "retained_state_exposed": prepared.retained_state_exposed,
            "exposed_context_sha256": prepared.exposed_context_sha256,
            "exposed_context_bytes": prepared.exposed_context_bytes,
            "curriculum_manifest": (
                curriculum_manifest.model_dump(mode="json") if curriculum_manifest is not None else None
            ),
        },
    )
    (run_dir / "attempt.json").write_text(attempt.model_dump_json(indent=2) + "\n", encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix=".ouroboros-sealed-grader-", dir=run_dir.parent) as temporary:
        sealed = Path(temporary) / "grader"
        shutil.copytree(grader_workspace.resolve(strict=True), sealed, symlinks=False)
        score = SealedGrader(grader_spec, sandbox=grader_sandbox).grade(
            run_id=run_id,
            grader_workspace=sealed,
            submission=workspace,
            output_dir=run_dir / "grader",
        )
    audit = seal_attempt_bundle(run_dir)
    return {
        "run_id": run_id,
        "attempt_status": attempt.status,
        "primary_score": score.primary_score,
        "passed": score.passed,
        "grader_error": score.grader_error,
        "usage": attempt.usage.model_dump(mode="json"),
        "audit_seal_sha256": audit["seal_sha256"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approach", choices=sorted(ADAPTERS), required=True)
    parser.add_argument(
        "--arm",
        choices=["cold", "evolved", "cold_ablation", "sham_improvement_control", "native_evolved"],
        required=True,
    )
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--grader-spec", type=Path, required=True)
    parser.add_argument("--grader-workspace", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--retained-state", type=Path)
    parser.add_argument("--sham-context", type=Path)
    parser.add_argument("--provider", choices=["openai", "anthropic"], default="openai")
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--replication", type=int, default=1)
    parser.add_argument("--max-cost-usd", type=float, default=50)
    parser.add_argument("--max-wall-seconds", type=float, default=14_400)
    parser.add_argument("--max-model-calls", type=int, default=120)
    parser.add_argument("--max-output-tokens", type=int, default=400_000)
    parser.add_argument("--max-tool-calls", type=int, default=1_000)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    task_spec = TaskSpec.model_validate(_load_json(args.task))
    authorize_scored_execution(args.root.resolve(), suite_id=task_spec.suite_id)
    load_env_file(args.root / ".env")
    required = "OPENAI_API_KEY" if args.provider == "openai" else "ANTHROPIC_API_KEY"
    import os

    if not os.environ.get(required):
        parser.error(f"{required} is not set; a repository .env is supported")
    result = run_attempt(
        repository=args.root.resolve(),
        approach_id=args.approach,
        arm=args.arm,
        task_spec=task_spec,
        task_workspace=args.workspace,
        grader_spec=GraderSpec.model_validate(_load_json(args.grader_spec)),
        grader_workspace=args.grader_workspace,
        run_dir=args.run_dir,
        retained_state=args.retained_state,
        sham_context=args.sham_context,
        provider_name=args.provider,
        model=args.model,
        seed=args.seed,
        replication=args.replication,
        budget=BrokerBudget(
            max_cost_usd=args.max_cost_usd,
            max_wall_seconds=args.max_wall_seconds,
            max_model_calls=args.max_model_calls,
            max_output_tokens=args.max_output_tokens,
            max_tool_calls=args.max_tool_calls,
        ),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["attempt_status"] == "completed" and not result.get("grader_error") else 1


if __name__ == "__main__":
    raise SystemExit(main())
