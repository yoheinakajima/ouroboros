#!/usr/bin/env python3
"""Hash and validate the provenance of architecture-specific evolved state."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

MANIFEST_NAME = "evolution_manifest.json"
DENIED_PARTS = {".env", "grader", "manager", "private", "secret", "secrets"}
EXPECTED_MUTATION_UNITS = {
    "workspace_v1_2": "arbitrary workspace tree",
    "minimal_v2": "evaluated procedure or pure deterministic capability",
    "hybrid_packs": "atomic set of complete hash-pinned ActiveGraph Packs",
}


class EvolutionManifest(BaseModel):
    schema_version: int = 1
    approach_id: Literal["workspace_v1_2", "minimal_v2", "hybrid_packs"]
    mutation_unit: str = Field(min_length=1)
    development_suites: list[str] = Field(min_length=1)
    development_task_ids: list[str] = Field(min_length=1)
    parent_run_ids: list[str] = Field(min_length=1)
    feedback_policy: Literal["public_only", "public_plus_score_receipt"]
    hidden_evaluator_content_exposed: bool = False
    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    artifact_bytes: int = Field(ge=1)
    created_at: str

    @model_validator(mode="after")
    def no_hidden_evaluator_content(self) -> "EvolutionManifest":
        if self.hidden_evaluator_content_exposed:
            raise ValueError("evolved state may not be built from hidden evaluator content")
        if len(set(self.development_task_ids)) != len(self.development_task_ids):
            raise ValueError("development task ids must be unique")
        if len(set(self.parent_run_ids)) != len(self.parent_run_ids):
            raise ValueError("parent run ids must be unique")
        if len(self.parent_run_ids) != len(self.development_task_ids):
            raise ValueError("every development task requires one retained parent run id")
        if self.mutation_unit != EXPECTED_MUTATION_UNITS[self.approach_id]:
            raise ValueError("mutation unit does not match the frozen approach contract")
        return self


def hash_artifact(root: str | Path) -> tuple[str, int]:
    state = Path(root).resolve(strict=True)
    if not state.is_dir() or state.is_symlink():
        raise ValueError("evolved state must be a real directory")
    digest = hashlib.sha256()
    total = 0
    files = 0
    for path in sorted(state.rglob("*")):
        relative = path.relative_to(state)
        if path.is_symlink():
            raise ValueError(f"evolved state contains a symlink: {relative}")
        if not path.is_file() or relative.as_posix() == MANIFEST_NAME:
            continue
        if any(part.lower() in DENIED_PARTS for part in relative.parts):
            raise ValueError(f"evolved state contains a private/evaluator path: {relative}")
        raw = path.read_bytes()
        files += 1
        total += len(raw)
        digest.update(relative.as_posix().encode())
        digest.update(b"\0")
        digest.update(raw)
        digest.update(b"\0")
    if not files or total == 0:
        raise ValueError("evolved state artifact is empty")
    return digest.hexdigest(), total


def export_minimal_state(root: str | Path) -> Path:
    """Create the bounded adapter export from a native Minimal v2 state.

    The export contains learned procedures, promoted-capability descriptors,
    and evaluation receipt hashes. Generated capability source and author-held
    cases stay in the hash-pinned native state but are not exposed as model
    context by the common adapter.
    """

    from activegraph import Runtime

    state = Path(root).resolve(strict=True)
    metadata_path = state / "organism.json"
    trace_path = state / "trace.sqlite"
    for path in (metadata_path, trace_path):
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"minimal native state requires regular {path.name}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    run_id = str(metadata.get("run_id", "")).strip()
    if not run_id:
        raise ValueError("minimal organism metadata is missing run_id")
    runtime = Runtime.load(str(trace_path), run_id=run_id, behaviors=[])

    procedures: list[dict[str, object]] = []
    capabilities: list[dict[str, object]] = []
    evidence_receipts: list[str] = []
    for item in runtime.graph.all_objects():
        data = dict(item.data)
        if item.type == "procedure":
            procedures.append(
                {
                    "name": str(data.get("name", "")),
                    "trigger_terms": [str(value) for value in data.get("trigger_terms", [])],
                    "steps": [str(value) for value in data.get("steps", [])],
                    "evidence": str(data.get("evidence", data.get("evidence_receipt", ""))),
                }
            )
        elif item.type == "promotion" and data.get("status") == "active":
            capabilities.append(
                {
                    "name": str(data.get("capability_name", "")),
                    "description": str(data.get("description", "")),
                    "pack_name": str(data.get("pack_name", "")),
                    "bundle_hash": str(data.get("bundle_hash", "")),
                }
            )
        elif item.type in {"mutation_trial", "external_evaluation"}:
            receipt = str(data.get("evaluation_receipt", ""))
            if receipt:
                evidence_receipts.append(receipt)
    payload = {
        "schema_version": 1,
        "engine_version": str(metadata.get("engine_version", "")),
        "run_id": run_id,
        "procedures": sorted(procedures, key=lambda row: (str(row["name"]), json.dumps(row, sort_keys=True))),
        "capabilities": sorted(capabilities, key=lambda row: (str(row["name"]), str(row["bundle_hash"]))),
        "evidence_receipts": sorted(set(evidence_receipts)),
    }
    target = state / "state_export.json"
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(target)
    return target


def build_manifest(
    root: str | Path,
    *,
    approach_id: Literal["workspace_v1_2", "minimal_v2", "hybrid_packs"],
    mutation_unit: str,
    development_suites: list[str],
    development_task_ids: list[str],
    parent_run_ids: list[str],
    feedback_policy: Literal["public_only", "public_plus_score_receipt"],
) -> EvolutionManifest:
    digest, total = hash_artifact(root)
    return EvolutionManifest(
        approach_id=approach_id,
        mutation_unit=mutation_unit,
        development_suites=development_suites,
        development_task_ids=development_task_ids,
        parent_run_ids=parent_run_ids,
        feedback_policy=feedback_policy,
        artifact_sha256=digest,
        artifact_bytes=total,
        created_at=datetime.now(UTC).isoformat(),
    )


def write_manifest(root: str | Path, manifest: EvolutionManifest) -> Path:
    state = Path(root).resolve(strict=True)
    target = state / MANIFEST_NAME
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)
    return target


def validate_manifest(root: str | Path, *, approach_id: str) -> EvolutionManifest:
    state = Path(root).resolve(strict=True)
    path = state / MANIFEST_NAME
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"evolved state requires {MANIFEST_NAME}")
    manifest = EvolutionManifest.model_validate_json(path.read_text(encoding="utf-8"))
    if manifest.approach_id != approach_id:
        raise ValueError("evolved-state approach id mismatch")
    digest, total = hash_artifact(state)
    if digest != manifest.artifact_sha256 or total != manifest.artifact_bytes:
        raise ValueError("evolved-state artifact hash/size drift")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state", type=Path)
    parser.add_argument("--approach", choices=["workspace_v1_2", "minimal_v2", "hybrid_packs"], required=True)
    parser.add_argument("--mutation-unit", required=True)
    parser.add_argument("--suite", action="append", required=True)
    parser.add_argument("--task", action="append", required=True)
    parser.add_argument("--parent-run", action="append", required=True)
    parser.add_argument("--feedback-policy", choices=["public_only", "public_plus_score_receipt"], required=True)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args(argv)
    if args.verify:
        manifest = validate_manifest(args.state, approach_id=args.approach)
    else:
        manifest = build_manifest(
            args.state,
            approach_id=args.approach,
            mutation_unit=args.mutation_unit,
            development_suites=args.suite,
            development_task_ids=args.task,
            parent_run_ids=args.parent_run,
            feedback_policy=args.feedback_policy,
        )
        write_manifest(args.state, manifest)
    print(json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
