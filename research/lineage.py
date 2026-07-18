#!/usr/bin/env python3
"""Build architecture-native retained state from leakage-safe development evidence.

The external benchmark agent and grader finish before this module runs.  The
reflection model receives only the public instruction, the agent's own output,
and a coarse score receipt.  Exact grader tests, logs, expected values, and
oracle material never enter the lineage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterator, Literal

from activegraph import Graph, Runtime, llm_behavior
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ouroboros import Config, OfflineProvider, Ouroboros
from research.curriculum import (
    EXPECTED_MUTATION_UNITS,
    EvolutionManifest,
    build_manifest,
    export_minimal_state,
    validate_manifest,
    write_manifest,
)
from research.hybrid_author import (
    BehaviorCase,
    ResearchBudget,
    ResearchTask,
    author_evaluate_and_record,
    load_env_file,
    provider_for,
    utc_now,
    write_json,
)

SHA256 = re.compile(r"^[0-9a-f]{64}$")
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
APPROACHES = ("workspace_v1_2", "minimal_v2", "hybrid_packs")
MAX_ARTIFACT_EXCERPT = 64_000
CONTEXT_INTERFACE = {
    "schema_version": 1,
    "request_event": "hybrid.task.requested",
    "result_event": "hybrid.task.completed",
    "operation": "development_guidance",
    "query_field": "query",
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


class PublicScoreReceipt(BaseModel):
    """Only the scalar feedback surface allowed to cross the grader boundary."""

    model_config = ConfigDict(extra="forbid")

    grader_id: str = Field(min_length=1, max_length=160)
    grader_revision: str = Field(min_length=1, max_length=160)
    primary_score: float
    passed: bool | None = None
    receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class DevelopmentEvidence(BaseModel):
    """A bounded, explicit allowlist of experience visible to a lineage author."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    suite_id: str = Field(min_length=1, max_length=160)
    task_id: str = Field(min_length=1, max_length=200)
    parent_run_id: str = Field(min_length=1, max_length=128)
    approach_id: Literal["workspace_v1_2", "minimal_v2", "hybrid_packs"]
    arm: Literal["cold", "evolved", "cold_ablation", "sham_improvement_control", "native_evolved"]
    public_instruction: str = Field(min_length=1, max_length=100_000)
    agent_status: Literal["completed", "blocked", "failed", "timed_out", "budget_exhausted"]
    agent_summary: str = Field(default="", max_length=20_000)
    agent_evidence: list[str] = Field(default_factory=list, max_length=64)
    owned_artifact_excerpt: str = Field(default="", max_length=MAX_ARTIFACT_EXCERPT)
    owned_artifact_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    owned_artifact_bytes: int = Field(default=0, ge=0, le=20 * 1024 * 1024)
    score: PublicScoreReceipt
    source_hashes: dict[str, str] = Field(min_length=1, max_length=32)
    hidden_evaluator_content_exposed: bool = False
    created_at: str

    @field_validator("parent_run_id")
    @classmethod
    def valid_parent_run_id(cls, value: str) -> str:
        if not SAFE_ID.fullmatch(value):
            raise ValueError("parent run id must be filesystem- and receipt-safe")
        return value

    @field_validator("agent_evidence")
    @classmethod
    def bounded_agent_evidence(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values if value.strip()]
        if any(len(value) > 4_000 for value in cleaned):
            raise ValueError("agent evidence rows must be at most 4,000 characters")
        return cleaned

    @field_validator("source_hashes")
    @classmethod
    def valid_source_hashes(cls, values: dict[str, str]) -> dict[str, str]:
        denied_fragments = ("hidden", "private", "manager", "oracle", "secret", "expected", "grader_log")
        for name, digest in values.items():
            normalized = name.lower()
            if any(fragment in normalized for fragment in denied_fragments) or not re.fullmatch(
                r"[a-z][a-z0-9_]{1,63}", name
            ):
                raise ValueError(f"source hash name is not allowed: {name!r}")
            if not SHA256.fullmatch(digest):
                raise ValueError(f"source hash is invalid: {name!r}")
        return values

    @model_validator(mode="after")
    def enforce_boundary(self) -> "DevelopmentEvidence":
        if self.hidden_evaluator_content_exposed:
            raise ValueError("hidden evaluator content may not enter development evidence")
        if bool(self.owned_artifact_sha256) != bool(self.owned_artifact_bytes):
            raise ValueError("owned artifact digest and byte count must be present together")
        if self.owned_artifact_bytes and not self.owned_artifact_excerpt:
            raise ValueError("owned artifact requires a bounded excerpt")
        return self

    def digest(self) -> str:
        return sha256_json(self.model_dump(mode="json"))


class DevelopmentLesson(BaseModel):
    """The common reflection output, later encoded in each native mutation unit."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3, max_length=160)
    scope: str = Field(min_length=10, max_length=1_200)
    trigger_terms: list[str] = Field(min_length=1, max_length=24)
    steps: list[str] = Field(min_length=1, max_length=16)
    pitfalls: list[str] = Field(default_factory=list, max_length=12)
    validation: list[str] = Field(default_factory=list, max_length=12)
    confidence: Literal["low", "medium", "high"]

    @field_validator("trigger_terms", "steps", "pitfalls", "validation")
    @classmethod
    def clean_rows(cls, values: list[str]) -> list[str]:
        cleaned = list(dict.fromkeys(value.strip() for value in values if value.strip()))
        if any(len(value) > 800 for value in cleaned):
            raise ValueError("lesson rows must be at most 800 characters")
        return cleaned


class ReflectionBudget(BaseModel):
    model: str = "gpt-5.6-sol"
    max_cost_usd: float = Field(default=5.0, gt=0)
    max_output_tokens: int = Field(default=8_000, ge=512, le=40_000)
    timeout_seconds: float = Field(default=600.0, gt=0, le=1_800)


def _event_usage(events: list[Any]) -> dict[str, Any]:
    responses = [event for event in events if event.type == "llm.responded"]
    cost = Decimal("0")
    for event in responses:
        try:
            cost += Decimal(str(event.payload.get("cost_usd", "0") or "0"))
        except Exception:
            pass
    return {
        "model_calls": sum(event.type == "llm.requested" for event in events),
        "input_tokens": sum(int(event.payload.get("input_tokens", 0) or 0) for event in responses),
        "output_tokens": sum(int(event.payload.get("output_tokens", 0) or 0) for event in responses),
        "cost_usd": str(cost),
    }


def reflection_prompt(evidence: DevelopmentEvidence) -> str:
    payload = evidence.model_dump(mode="json")
    return f"""You are the reflection stage of a governed recursive-improvement experiment.

Distill one reusable lesson from the development evidence below. Prefer general methods that can transfer to a
different repository or task. Separate what was actually evidenced from speculation. A passing score can support a
procedure; a failing score should become a warning or changed strategy, never a claim that the attempted method works.

AUTHORITY AND LEAKAGE BOUNDARY
- You receive only the public instruction, the agent's own summary/evidence/artifact, and one scalar grader receipt.
- Do not invent hidden tests, expected outputs, grader details, or oracle knowledge.
- Do not preserve task-specific answer code when a more general diagnostic or validation method is available.
- Trigger terms should be short retrieval terms likely to occur in future task prompts.
- Steps must be executable guidance, not a narrative transcript.

DEVELOPMENT EVIDENCE
{json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)}
"""


def reflect_evidence(
    evidence: DevelopmentEvidence,
    *,
    run_dir: str | Path,
    provider: Any,
    budget: ReflectionBudget,
) -> tuple[DevelopmentLesson, dict[str, Any]]:
    """Run one recorded ActiveGraph LLM behavior over sanitized evidence."""

    root = Path(run_dir).resolve()
    if root.exists() and any(root.iterdir()):
        raise FileExistsError(f"reflection run directory is not empty: {root}")
    root.mkdir(parents=True, exist_ok=True)
    write_json(root / "evidence.public.json", evidence.model_dump(mode="json"))
    prompt = reflection_prompt(evidence)

    @llm_behavior(
        name="research.development_reflector",
        on=["goal.created"],
        description=prompt,
        output_schema=DevelopmentLesson,
        model=budget.model,
        temperature=0.1,
        max_tokens=budget.max_output_tokens,
        timeout_seconds=budget.timeout_seconds,
        creates=["development_lesson"],
    )
    def reflector(event: Any, graph: Any, ctx: Any, llm_output: DevelopmentLesson) -> None:
        graph.add_object("development_lesson", llm_output.model_dump(mode="json"))

    run_id = "lineage_reflection_" + uuid.uuid4().hex
    runtime = Runtime(
        Graph(run_id=run_id),
        behaviors=[reflector],
        persist_to=str(root / "trace.sqlite"),
        llm_provider=provider,
        budget={
            "max_cost_usd": budget.max_cost_usd,
            # ActiveGraph reserves one call beyond the behavior response while
            # finalizing a structured turn; successful reflection still makes
            # exactly one provider request, which the receipt verifies.
            "max_llm_calls": 2,
            "max_events": 100,
            "max_behavior_calls": 20,
            "max_seconds": budget.timeout_seconds + 30,
        },
        native_structured_output=True,
    )
    started = time.monotonic()
    runtime.run_goal("Distill the supplied development attempt into one reusable lesson.", actor="research_manager")
    elapsed = time.monotonic() - started
    lessons = runtime.graph.objects(type="development_lesson")
    failures = [
        {"behavior": item.behavior, "reason": item.reason, "message": item.message}
        for item in runtime.errors
    ]
    if len(lessons) != 1 or failures:
        raise RuntimeError(f"development reflection failed: lessons={len(lessons)} failures={failures}")
    lesson = DevelopmentLesson.model_validate(lessons[0].data)
    write_json(root / "lesson.json", lesson.model_dump(mode="json"))
    summary = {
        "schema_version": 1,
        "run_id": run_id,
        "model": budget.model,
        "evidence_sha256": evidence.digest(),
        "lesson_sha256": sha256_json(lesson.model_dump(mode="json")),
        "usage": _event_usage(list(runtime.graph.events)),
        "elapsed_seconds": round(elapsed, 6),
        "failures": failures,
    }
    write_json(root / "summary.json", summary)
    return lesson, summary


def _one_trial_dir(job_dir: Path, task_id: str) -> Path:
    matches = sorted(path for path in job_dir.glob(f"{task_id}__*") if path.is_dir())
    if len(matches) != 1:
        raise ValueError(f"expected one Harbor trial for {task_id}, found {len(matches)}")
    return matches[0]


def extract_swe_evidence(
    repository: str | Path,
    *,
    job_dir: str | Path,
    task_id: str,
) -> DevelopmentEvidence:
    """Create a strict public-only record from one completed SWE development job."""

    root = Path(repository).resolve(strict=True)
    job = Path(job_dir).resolve(strict=True)
    selection = json.loads((root / "research/selections/swe_verified.json").read_text(encoding="utf-8"))
    if task_id not in selection["development"]:
        raise ValueError("SWE lineage evidence must come from the frozen development split")
    trial = _one_trial_dir(job, task_id)
    instruction_path = root / "benchmark/.cache/swe_harbor" / task_id / "instruction.md"
    summary_path = trial / "agent/ouroboros-summary.json"
    patch_path = trial / "verifier/model.patch"
    receipt_path = job / "official-evaluation/receipt.json"
    trace_path = trial / "agent/trace.jsonl"
    for path in (instruction_path, summary_path, patch_path, receipt_path, trace_path):
        if not path.is_file() or path.is_symlink():
            raise FileNotFoundError(path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("suite_id") != "ouro_swe_50" or receipt.get("instance_id") != task_id:
        raise ValueError("official receipt does not match the requested SWE task")
    if receipt.get("run_id") != job.name or receipt.get("completed") is not True or receipt.get("error") is not False:
        raise ValueError("official SWE receipt is incomplete or belongs to another run")
    approach_id = str(summary.get("approach_id", ""))
    if approach_id not in APPROACHES:
        raise ValueError("agent summary has an unknown approach")
    patch = patch_path.read_bytes()
    truncation_note = "\n[artifact excerpt truncated; full bytes are hash-pinned]\n"
    excerpt_limit = MAX_ARTIFACT_EXCERPT - len(truncation_note)
    excerpt = patch[:excerpt_limit].decode("utf-8", errors="replace")
    if len(patch) > MAX_ARTIFACT_EXCERPT:
        excerpt += truncation_note
    source_hashes = {
        "agent_summary": sha256_bytes(summary_path.read_bytes()),
        "agent_trace": sha256_bytes(trace_path.read_bytes()),
        "grader_receipt": sha256_bytes(receipt_path.read_bytes()),
        "public_instruction": sha256_bytes(instruction_path.read_bytes()),
        "submission_patch": sha256_bytes(patch),
    }
    status = str(summary.get("status", "failed"))
    if status not in {"completed", "blocked", "failed", "timed_out", "budget_exhausted"}:
        status = "failed"
    return DevelopmentEvidence(
        suite_id="ouro_swe_50",
        task_id=task_id,
        parent_run_id=job.name,
        approach_id=approach_id,  # type: ignore[arg-type]
        arm=str(summary.get("arm", "cold")),  # type: ignore[arg-type]
        public_instruction=instruction_path.read_text(encoding="utf-8"),
        agent_status=status,  # type: ignore[arg-type]
        agent_summary=str(summary.get("summary", "")),
        agent_evidence=[str(value) for value in summary.get("evidence", [])],
        owned_artifact_excerpt=excerpt,
        owned_artifact_sha256=sha256_bytes(patch),
        owned_artifact_bytes=len(patch),
        score=PublicScoreReceipt(
            grader_id="official_swe_bench",
            grader_revision=str(receipt["official_evaluator_revision"]),
            primary_score=1.0 if receipt.get("resolved") is True else 0.0,
            passed=bool(receipt.get("resolved")),
            receipt_sha256=sha256_bytes(receipt_path.read_bytes()),
        ),
        source_hashes=source_hashes,
        hidden_evaluator_content_exposed=False,
        created_at=utc_now(),
    )


@contextmanager
def _new_output(path: str | Path) -> Iterator[Path]:
    target = Path(path).resolve()
    if target.exists():
        raise FileExistsError(f"output state already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{target.name}-", dir=target.parent))
    try:
        yield temporary
        temporary.replace(target)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def _copy_parent(parent_state: str | Path | None, destination: Path, *, approach_id: str) -> EvolutionManifest | None:
    if parent_state is None:
        return None
    parent = Path(parent_state).resolve(strict=True)
    manifest = validate_manifest(parent, approach_id=approach_id)
    for path in parent.iterdir():
        if path.name == "evolution_manifest.json":
            continue
        target = destination / path.name
        if path.is_symlink():
            raise ValueError(f"parent retained state contains a symlink: {path.name}")
        if path.is_dir():
            shutil.copytree(path, target)
        elif path.is_file():
            shutil.copy2(path, target)
    return manifest


def _copy_prior_lineage(parent: Path | None, destination: Path) -> None:
    """Preserve earlier detailed records when an architecture exports a new state."""

    if parent is None:
        return
    source = parent / "lineage"
    if not source.exists():
        return
    if not source.is_dir() or source.is_symlink():
        raise ValueError("parent lineage must be a real directory")
    shutil.copytree(source, destination / "lineage")


def _lineage_lists(
    previous: EvolutionManifest | None,
    evidence: DevelopmentEvidence,
) -> tuple[list[str], list[str], list[str]]:
    suites = list(previous.development_suites) if previous else []
    tasks = list(previous.development_task_ids) if previous else []
    parents = list(previous.parent_run_ids) if previous else []
    if evidence.task_id in tasks or evidence.parent_run_id in parents:
        raise ValueError("development task and parent run ids may enter a lineage only once")
    if evidence.suite_id not in suites:
        suites.append(evidence.suite_id)
    tasks.append(evidence.task_id)
    parents.append(evidence.parent_run_id)
    return suites, tasks, parents


def _record_lineage(
    root: Path,
    *,
    retained_approach_id: Literal["workspace_v1_2", "minimal_v2", "hybrid_packs"],
    cross_approach_calibration: bool,
    evidence: DevelopmentEvidence,
    lesson: DevelopmentLesson,
    architecture_result: dict[str, Any],
    index: int,
) -> None:
    record = {
        "schema_version": 1,
        "sequence": index,
        "suite_id": evidence.suite_id,
        "task_id": evidence.task_id,
        "parent_run_id": evidence.parent_run_id,
        "source_approach_id": evidence.approach_id,
        "retained_approach_id": retained_approach_id,
        "cross_approach_calibration": cross_approach_calibration,
        "evidence_sha256": evidence.digest(),
        "score_receipt_sha256": evidence.score.receipt_sha256,
        "score_passed": evidence.score.passed,
        "lesson": lesson.model_dump(mode="json"),
        "lesson_sha256": sha256_json(lesson.model_dump(mode="json")),
        "architecture_result": architecture_result,
        "hidden_evaluator_content_exposed": False,
        "created_at": utc_now(),
    }
    write_json(root / "lineage" / "records" / f"{index:03d}-{evidence.task_id}.json", record)


def _check_evidence_origin(
    evidence: DevelopmentEvidence,
    *,
    retained_approach_id: Literal["workspace_v1_2", "minimal_v2", "hybrid_packs"],
    allow_cross_approach_calibration: bool,
) -> bool:
    """Reject cross-approach inheritance unless a builder calibration says so explicitly."""

    cross_approach = evidence.approach_id != retained_approach_id
    if cross_approach and not allow_cross_approach_calibration:
        raise ValueError(
            f"{retained_approach_id} may not inherit development evidence from {evidence.approach_id}; "
            "use independently generated evidence for scored lineages"
        )
    return cross_approach


def _seal_state(
    root: Path,
    *,
    approach_id: Literal["workspace_v1_2", "minimal_v2", "hybrid_packs"],
    previous: EvolutionManifest | None,
    evidence: DevelopmentEvidence,
) -> EvolutionManifest:
    suites, tasks, parents = _lineage_lists(previous, evidence)
    manifest = build_manifest(
        root,
        approach_id=approach_id,
        mutation_unit=EXPECTED_MUTATION_UNITS[approach_id],
        development_suites=suites,
        development_task_ids=tasks,
        parent_run_ids=parents,
        feedback_policy="public_plus_score_receipt",
    )
    write_manifest(root, manifest)
    validate_manifest(root, approach_id=approach_id)
    return manifest


def apply_minimal_lesson(
    *,
    evidence: DevelopmentEvidence,
    lesson: DevelopmentLesson,
    output_state: str | Path,
    parent_state: str | Path | None = None,
    allow_cross_approach_calibration: bool = False,
) -> dict[str, Any]:
    """Encode a passing external experience as a native Minimal-v2 procedure."""

    cross_approach = _check_evidence_origin(
        evidence,
        retained_approach_id="minimal_v2",
        allow_cross_approach_calibration=allow_cross_approach_calibration,
    )
    with _new_output(output_state) as state:
        previous = _copy_parent(parent_state, state, approach_id="minimal_v2")
        workspace = state.parent / f".{state.name}-workspace"
        workspace.mkdir(parents=True, exist_ok=False)
        try:
            organism = Ouroboros(
                Config(workspace=workspace, state_dir=state, model="offline-lineage-import"),
                llm_provider=OfflineProvider(),
                load_promotions=False,
            )
            adoption = organism.adopt_evaluated_procedure(
                name=lesson.title,
                trigger_terms=lesson.trigger_terms,
                steps=lesson.steps + lesson.validation,
                evidence_receipt="sha256:" + evidence.score.receipt_sha256,
                parent_run_id=evidence.parent_run_id,
                passed=evidence.score.passed is True,
            )
            organism.runtime.save_state()
        finally:
            shutil.rmtree(workspace, ignore_errors=True)
        index = len(previous.development_task_ids) + 1 if previous else 1
        _record_lineage(
            state,
            retained_approach_id="minimal_v2",
            cross_approach_calibration=cross_approach,
            evidence=evidence,
            lesson=lesson,
            architecture_result={"native_import": adoption, "model_calls": 0},
            index=index,
        )
        export_minimal_state(state)
        manifest = _seal_state(
            state,
            approach_id="minimal_v2",
            previous=previous,
            evidence=evidence,
        )
    return {"approach_id": "minimal_v2", "state": str(Path(output_state).resolve()), **manifest.model_dump()}


def apply_workspace_lesson(
    *,
    repository: str | Path,
    evidence: DevelopmentEvidence,
    lesson: DevelopmentLesson,
    output_state: str | Path,
    native_run_root: str | Path,
    parent_state: str | Path | None = None,
    model: str = "gpt-5.6-sol",
    max_cost_usd: float = 10.0,
    generations: int = 1,
    allow_cross_approach_calibration: bool = False,
) -> dict[str, Any]:
    """Let the recovered v1.2 kernel rewrite a retained workspace around the lesson."""

    cross_approach = _check_evidence_origin(
        evidence,
        retained_approach_id="workspace_v1_2",
        allow_cross_approach_calibration=allow_cross_approach_calibration,
    )
    repository_path = Path(repository).resolve(strict=True)
    run_root = Path(native_run_root).resolve()
    run_root.mkdir(parents=True, exist_ok=True)
    load_env_file(repository_path / ".env")
    with tempfile.TemporaryDirectory(prefix="ouro-workspace-lineage-") as temporary:
        seed = Path(temporary) / "seed"
        seed.mkdir()
        previous: EvolutionManifest | None = None
        if parent_state is not None:
            parent = Path(parent_state).resolve(strict=True)
            previous = validate_manifest(parent, approach_id="workspace_v1_2")
            prior_workspace = parent / "final_workspace" if (parent / "final_workspace").is_dir() else parent
            shutil.copytree(prior_workspace, seed, dirs_exist_ok=True)
        development = seed / "_development"
        development.mkdir(parents=True, exist_ok=True)
        write_json(development / "current_evidence.json", evidence.model_dump(mode="json"))
        write_json(development / "current_lesson.json", lesson.model_dump(mode="json"))
        run_id = f"lineage-workspace-{len(previous.development_task_ids) + 1 if previous else 1}-{uuid.uuid4().hex[:8]}"
        objective = (
            "Evolve this retained software-engineering workspace using _development/current_evidence.json and "
            "_development/current_lesson.json. Preserve useful prior capabilities, turn the evidenced lesson into "
            "concise reusable behavior or tools for future unfamiliar repository and terminal tasks, and add "
            "executable public checks for anything you claim. Do not invent or reconstruct hidden grader content."
        )
        command = [
            sys.executable,
            str(repository_path / "recovered/v1.2/ouroboros.py"),
            objective,
            "--generations",
            str(generations),
            "--seed-dir",
            str(seed),
            "--provider",
            "openai",
            "--model",
            model,
            "--run-root",
            str(run_root),
            "--run-id",
            run_id,
            "--max-tool-turns",
            "32",
            "--max-tool-calls-per-turn",
            "4",
            "--max-llm-calls",
            "48",
            "--llm-timeout",
            "600",
            "--max-cost-usd",
            str(max_cost_usd),
            "--quiet",
        ]
        started = time.monotonic()
        completed = subprocess.run(
            command,
            cwd=repository_path,
            env=os.environ.copy(),
            text=True,
            capture_output=True,
            timeout=7_200,
            check=False,
        )
        native_run = run_root / run_id
        (native_run / "lineage-process.stdout.txt").write_text(completed.stdout[-200_000:], encoding="utf-8")
        (native_run / "lineage-process.stderr.txt").write_text(completed.stderr[-200_000:], encoding="utf-8")
        result_path = native_run / "result.json"
        if completed.returncode != 0 or not result_path.is_file():
            raise RuntimeError(f"workspace lineage evolution failed with exit code {completed.returncode}: {run_id}")
        native_result = json.loads(result_path.read_text(encoding="utf-8"))
        final_workspace = native_run / "final_workspace"
        if native_result.get("status") not in {"completed", "baseline_only"} or not final_workspace.is_dir():
            raise RuntimeError(f"workspace lineage did not produce a valid final workspace: {native_result}")
        with _new_output(output_state) as state:
            shutil.copytree(final_workspace, state / "final_workspace")
            _copy_prior_lineage(Path(parent_state).resolve(strict=True) if parent_state is not None else None, state)
            index = len(previous.development_task_ids) + 1 if previous else 1
            _record_lineage(
                state,
                retained_approach_id="workspace_v1_2",
                cross_approach_calibration=cross_approach,
                evidence=evidence,
                lesson=lesson,
                architecture_result={
                    "native_run_id": run_id,
                    "native_status": native_result["status"],
                    "accepted_generations": native_result.get("accepted_generations", 0),
                    "usage": native_result.get("usage", {}),
                    "elapsed_seconds": round(time.monotonic() - started, 6),
                },
                index=index,
            )
            manifest = _seal_state(
                state,
                approach_id="workspace_v1_2",
                previous=previous,
                evidence=evidence,
            )
    return {
        "approach_id": "workspace_v1_2",
        "state": str(Path(output_state).resolve()),
        "native_run": str(native_run),
        **manifest.model_dump(),
    }


def _lesson_output(evidence_row: dict[str, Any], lesson: DevelopmentLesson) -> dict[str, Any]:
    return {
        "suite_id": evidence_row["suite_id"],
        "task_id": evidence_row["task_id"],
        "title": lesson.title,
        "scope": lesson.scope,
        "trigger_terms": lesson.trigger_terms,
        "steps": lesson.steps,
        "pitfalls": lesson.pitfalls,
        "validation": lesson.validation,
        "confidence": lesson.confidence,
        "score_passed": evidence_row["score_passed"],
    }


def _hybrid_task(records: list[dict[str, Any]]) -> ResearchTask:
    public: list[BehaviorCase] = []
    private: list[BehaviorCase] = []
    transfer: list[BehaviorCase] = []
    for index, record in enumerate(records, 1):
        lesson = DevelopmentLesson.model_validate(record["lesson"])
        expected = {"lessons": [_lesson_output(record, lesson)]}
        public.append(
            BehaviorCase(
                id=f"public-{index:03d}",
                payload={
                    "operation": "development_guidance",
                    "query": f"{record['suite_id']} {record['task_id']} {lesson.scope}",
                    "limit": 1,
                },
                expected=expected,
                expected_graph={"object_type_counts": {"guidance_query": index}},
            )
        )
        private.append(
            BehaviorCase(
                id=f"private-{index:03d}",
                payload={
                    "operation": "development_guidance",
                    "query": " ".join(lesson.trigger_terms),
                    "limit": 1,
                },
                expected=expected,
                expected_graph={"object_type_counts": {"guidance_query": index}},
            )
        )
        transfer.append(
            BehaviorCase(
                id=f"transfer-{index:03d}",
                payload={
                    "operation": "development_guidance",
                    "query": f"future task involving {' '.join(lesson.trigger_terms[:6])}",
                    "limit": 1,
                },
                expected=expected,
                expected_graph={"object_type_counts": {"guidance_query": index}},
            )
        )
    version = f"1.{len(records) - 1}.0"
    return ResearchTask(
        id=f"development_playbook_{len(records):03d}",
        title="Grow a transferable development-guidance Pack",
        category="recursive-improvement",
        objective=(
            "Author exactly one complete ActiveGraph Pack named development_playbook at version "
            f"{version}. It must retrieve the best retained development lesson for a new query and record each "
            "query as a typed guidance_query object. This proposal replaces the prior version atomically."
        ),
        behavior_contract=(
            "On hybrid.task.requested with operation=development_guidance, rank the embedded lessons by deterministic "
            "case-insensitive lexical relevance to payload.query, honor limit, add one durable guidance_query object, "
            "and emit exactly one hybrid.task.completed event preserving request_id with output "
            "{'lessons': [best lesson objects]}. Return an empty lessons list only when no lesson has positive overlap."
        ),
        constraints=[
            "Return exactly one Pack named development_playbook.",
            f"Use version {version}.",
            "Declare the guidance_query object type and one behavior; request no tools or external capabilities.",
            "Embed only the supplied public lesson records and use deterministic ActiveGraph graph state.",
            "Preserve every earlier public behavior while adding the newest lesson.",
        ],
        public_cases=public,
        private_cases=private,
        transfer_cases=transfer,
    )


def _hybrid_records(parent: Path | None) -> list[dict[str, Any]]:
    if parent is None:
        return []
    records_root = parent / "lineage/records"
    rows = []
    for path in sorted(records_root.glob("*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        rows.append(
            {
                "suite_id": value["suite_id"],
                "task_id": value["task_id"],
                "score_passed": value["score_passed"],
                "lesson": value["lesson"],
            }
        )
    return rows


def _sanitize_hybrid_organism(source: Path, destination: Path) -> None:
    registry_path = source / "registry.json"
    identity_path = source / "identity.db"
    for path in (registry_path, identity_path):
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"hybrid organism is missing regular {path.name}")
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["research_context_interface"] = CONTEXT_INTERFACE
    write_json(destination / "registry.json", registry)
    shutil.copy2(identity_path, destination / "identity.db")
    for entry in registry.get("adopted", []):
        relative = Path(str(entry["path"]))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("hybrid registry path escapes retained state")
        pack_source = source / relative
        pack_target = destination / relative
        if not pack_source.is_dir() or pack_source.is_symlink():
            raise ValueError(f"hybrid adopted Pack is missing: {relative}")
        shutil.copytree(pack_source, pack_target)


def apply_hybrid_lesson(
    *,
    repository: str | Path,
    docs_root: str | Path,
    evidence: DevelopmentEvidence,
    lesson: DevelopmentLesson,
    output_state: str | Path,
    native_run_dir: str | Path,
    parent_state: str | Path | None = None,
    model: str = "gpt-5.6-sol",
    max_cost_usd: float = 30.0,
    max_llm_calls: int = 12,
    allow_cross_approach_calibration: bool = False,
) -> dict[str, Any]:
    """Author, privately trial, adopt, restart, and export a guidance Pack."""

    cross_approach = _check_evidence_origin(
        evidence,
        retained_approach_id="hybrid_packs",
        allow_cross_approach_calibration=allow_cross_approach_calibration,
    )
    repository_path = Path(repository).resolve(strict=True)
    run_dir = Path(native_run_dir).resolve()
    if run_dir.exists() and any(run_dir.iterdir()):
        raise FileExistsError(f"Hybrid native run directory is not empty: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)
    parent: Path | None = None
    previous: EvolutionManifest | None = None
    if parent_state is not None:
        parent = Path(parent_state).resolve(strict=True)
        previous = validate_manifest(parent, approach_id="hybrid_packs")
        _sanitize_hybrid_organism(parent, run_dir / "organism")
    records = _hybrid_records(parent)
    records.append(
        {
            "suite_id": evidence.suite_id,
            "task_id": evidence.task_id,
            "score_passed": evidence.score.passed,
            "lesson": lesson.model_dump(mode="json"),
        }
    )
    task = _hybrid_task(records)
    write_json(run_dir / "lineage_task.public.json", task.author_view())
    load_env_file(repository_path / ".env")
    result = author_evaluate_and_record(
        task,
        docs_root=docs_root,
        run_dir=run_dir,
        provider=provider_for("openai"),
        budget=ResearchBudget(
            model=model,
            max_cost_usd=max_cost_usd,
            max_llm_calls=max_llm_calls,
            max_output_tokens=40_000,
            author_timeout_seconds=900,
            trial_timeout_seconds=120,
            max_events=10_000,
            max_behavior_calls=2_000,
            max_author_attempts=4,
        ),
    )
    if not result.get("research_success"):
        raise RuntimeError("Hybrid development Pack was not adopted and transfer-verified")
    with _new_output(output_state) as state:
        _sanitize_hybrid_organism(run_dir / "organism", state)
        _copy_prior_lineage(parent, state)
        index = len(previous.development_task_ids) + 1 if previous else 1
        _record_lineage(
            state,
            retained_approach_id="hybrid_packs",
            cross_approach_calibration=cross_approach,
            evidence=evidence,
            lesson=lesson,
            architecture_result={
                "native_run": str(run_dir),
                "accepted": result.get("accepted"),
                "evolution": result.get("evolution"),
                "transfer": {
                    "passed": result.get("transfer", {}).get("passed"),
                    "total": result.get("transfer", {}).get("total"),
                },
                "author_usage": result.get("author", {}).get("usage", {}),
            },
            index=index,
        )
        manifest = _seal_state(
            state,
            approach_id="hybrid_packs",
            previous=previous,
            evidence=evidence,
        )
    return {
        "approach_id": "hybrid_packs",
        "state": str(Path(output_state).resolve()),
        "native_run": str(run_dir),
        **manifest.model_dump(),
    }


def load_evidence(path: str | Path) -> DevelopmentEvidence:
    return DevelopmentEvidence.model_validate_json(Path(path).read_text(encoding="utf-8"))


def load_lesson(path: str | Path) -> DevelopmentLesson:
    return DevelopmentLesson.model_validate_json(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract = subparsers.add_parser("extract-swe", help="sanitize one completed SWE development job")
    extract.add_argument("--job-dir", type=Path, required=True)
    extract.add_argument("--task-id", required=True)
    extract.add_argument("--output", type=Path, required=True)

    reflect = subparsers.add_parser("reflect", help="distill public evidence with one recorded LLM call")
    reflect.add_argument("--evidence", type=Path, required=True)
    reflect.add_argument("--run-dir", type=Path, required=True)
    reflect.add_argument("--model", default="gpt-5.6-sol")
    reflect.add_argument("--max-cost-usd", type=float, default=5.0)

    apply = subparsers.add_parser("apply", help="encode one lesson in an architecture-native retained state")
    apply.add_argument("--approach", choices=APPROACHES, required=True)
    apply.add_argument("--evidence", type=Path, required=True)
    apply.add_argument("--lesson", type=Path, required=True)
    apply.add_argument("--output-state", type=Path, required=True)
    apply.add_argument("--parent-state", type=Path)
    apply.add_argument("--native-run", type=Path)
    apply.add_argument("--docs-root", type=Path, default=Path(__file__).resolve().parents[2] / "activegraph/docs")
    apply.add_argument("--model", default="gpt-5.6-sol")
    apply.add_argument("--max-cost-usd", type=float, default=30.0)
    apply.add_argument(
        "--allow-cross-approach-calibration",
        action="store_true",
        help="allow shared evidence only for a labeled unscored builder calibration",
    )

    args = parser.parse_args(argv)
    repository = Path(__file__).resolve().parents[1]
    if args.command == "extract-swe":
        evidence = extract_swe_evidence(repository, job_dir=args.job_dir, task_id=args.task_id)
        write_json(args.output, evidence.model_dump(mode="json"))
        print(evidence.model_dump_json(indent=2))
        return 0
    if args.command == "reflect":
        load_env_file(repository / ".env")
        lesson, summary = reflect_evidence(
            load_evidence(args.evidence),
            run_dir=args.run_dir,
            provider=provider_for("openai"),
            budget=ReflectionBudget(model=args.model, max_cost_usd=args.max_cost_usd),
        )
        print(json.dumps({"lesson": lesson.model_dump(), "summary": summary}, indent=2, sort_keys=True))
        return 0

    evidence = load_evidence(args.evidence)
    lesson = load_lesson(args.lesson)
    if args.approach == "minimal_v2":
        result = apply_minimal_lesson(
            evidence=evidence,
            lesson=lesson,
            output_state=args.output_state,
            parent_state=args.parent_state,
            allow_cross_approach_calibration=args.allow_cross_approach_calibration,
        )
    elif args.approach == "workspace_v1_2":
        if args.native_run is None:
            parser.error("workspace_v1_2 apply requires --native-run as a run-root directory")
        result = apply_workspace_lesson(
            repository=repository,
            evidence=evidence,
            lesson=lesson,
            output_state=args.output_state,
            native_run_root=args.native_run,
            parent_state=args.parent_state,
            model=args.model,
            max_cost_usd=args.max_cost_usd,
            allow_cross_approach_calibration=args.allow_cross_approach_calibration,
        )
    else:
        if args.native_run is None:
            parser.error("hybrid_packs apply requires --native-run as a new run directory")
        result = apply_hybrid_lesson(
            repository=repository,
            docs_root=args.docs_root,
            evidence=evidence,
            lesson=lesson,
            output_state=args.output_state,
            native_run_dir=args.native_run,
            parent_state=args.parent_state,
            model=args.model,
            max_cost_usd=args.max_cost_usd,
            allow_cross_approach_calibration=args.allow_cross_approach_calibration,
        )
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
