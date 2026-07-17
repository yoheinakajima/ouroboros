"""Common, architecture-neutral records for benchmark attempts and scores."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ResourceUsage(BaseModel):
    model_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: int = 0
    wall_seconds: float = 0.0
    cost_usd: float = 0.0


class AttemptRecord(BaseModel):
    """One immutable attempt; failures and retries are first-class rows."""

    schema_version: int = 1
    run_id: str
    approach_id: str
    study_id: str
    suite_id: str
    task_id: str
    arm: Literal["cold", "evolved", "cold_ablation", "sham_improvement_control", "native_evolved"]
    replication: int = Field(ge=1)
    seed: int
    model: str
    task_image_digest: str
    approach_source_hashes: dict[str, str]
    started_at: str
    finished_at: str
    status: Literal["completed", "failed", "timed_out", "budget_exhausted", "infrastructure_error"]
    usage: ResourceUsage
    trace_path: str
    submission_path: str | None = None
    parent_run_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScoreRecord(BaseModel):
    """A grader-owned result kept separate from the agent's success claim."""

    schema_version: int = 1
    run_id: str
    grader_id: str
    grader_revision: str
    primary_score: float
    passed: bool | None = None
    components: dict[str, float | int | str | bool | None] = Field(default_factory=dict)
    regressions: list[str] = Field(default_factory=list)
    evidence_paths: list[str] = Field(default_factory=list)
    grader_error: str | None = None
