#!/usr/bin/env python3
"""Rate the architecture-masked mutation packet with an isolated LLM coder.

The process receives only the frozen codebook and masked packet. It never reads
the metadata key. Full prompts, raw responses, model identity, and usage are
recorded for audit. These are pilot model-coded labels, not a substitute for
two independent human coders in a submission.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
from pathlib import Path
from typing import Any

from openai import OpenAI


ENUMS = {
    "primary_update_target": [
        "task_solution",
        "procedure",
        "episodic_memory",
        "deterministic_capability",
        "scaffold_policy",
        "retrieval_memory_policy",
        "validation_asset",
        "configuration",
        "documentation_provenance",
        "none_noop",
        "unclear",
    ],
    "secondary_update_target": [
        "task_solution",
        "procedure",
        "episodic_memory",
        "deterministic_capability",
        "scaffold_policy",
        "retrieval_memory_policy",
        "validation_asset",
        "configuration",
        "documentation_provenance",
        "none",
        "unclear",
    ],
    "representational_form": [
        "natural_language",
        "executable_code",
        "structured_data",
        "test_code",
        "mixed",
        "none",
        "unclear",
    ],
    "transfer_scope": [
        "instance",
        "repository_family",
        "cross_task",
        "self_improvement_process",
        "unclear",
    ],
    "abstraction_level": [
        "observation",
        "prescription",
        "mechanism",
        "policy",
        "unclear",
    ],
    "evidence_grounding": [
        "direct_validated",
        "direct_unvalidated",
        "inferred",
        "unsupported",
        "not_applicable",
        "unclear",
    ],
    "failure_specificity": [
        "none",
        "symptom_only",
        "localized_cause",
        "root_cause_chain",
        "recovery_procedure",
        "preventive_safeguard",
        "unclear",
    ],
    "validation_strategy": [
        "none",
        "static_check",
        "focused_test",
        "integration_test",
        "external_evaluation",
        "multiple_levels",
        "unclear",
    ],
    "consolidation_operation": [
        "append",
        "revise",
        "merge_deduplicate",
        "delete_prune",
        "compress_summarize",
        "none",
        "unclear",
    ],
    "executable_status": [
        "nonexecutable",
        "executable_unvalidated",
        "executable_validated",
        "execution_metadata_only",
        "none",
        "unclear",
    ],
    "anticipated_activation": [
        "always_in_context",
        "conditional_retrieval",
        "automatic_execution",
        "actor_callable",
        "development_only",
        "not_specified",
        "unclear",
    ],
    "counterfactual_actionability": [
        "none",
        "weak",
        "specific",
        "operational",
        "unclear",
    ],
    "novelty_relative_to_prior_state": [
        "duplicate",
        "incremental",
        "new",
        "contradictory",
        "not_coded",
        "unclear",
    ],
    "confidence": ["high", "medium", "low"],
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def response_schema(batch_size: int) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "masked_id": {"type": "string"},
        **{
            field: {"type": "string", "enum": values}
            for field, values in ENUMS.items()
        },
        "rationale": {"type": "string", "minLength": 1, "maxLength": 600},
    }
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "mutation_taxonomy_batch",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "labels": {
                        "type": "array",
                        "minItems": batch_size,
                        "maxItems": batch_size,
                        "items": {
                            "type": "object",
                            "properties": properties,
                            "required": list(properties),
                            "additionalProperties": False,
                        },
                    }
                },
                "required": ["labels"],
                "additionalProperties": False,
            },
        },
    }


def prompt_for(codebook: str, items: list[dict[str, Any]]) -> tuple[str, str]:
    system = (
        "You are an architecture-masked research coder. Apply the frozen codebook "
        "literally. You have no access to architecture, task id, score, acceptance, "
        "sequence, cost, or later outcome metadata. Do not guess hidden facts. "
        "Classify the proposed natural-language update represented by each excerpt, "
        "not an imagined executable implementation. Because no prior-state summary "
        "is supplied, novelty_relative_to_prior_state must be not_coded. "
        "Because activation is not specified by the excerpt, use not_specified "
        "unless the visible proposal explicitly states an activation path. "
        "Return exactly one label object per masked_id."
    )
    user = (
        "FROZEN CODEBOOK\n\n"
        + codebook
        + "\n\nMASKED ITEMS\n\n"
        + json.dumps(items, indent=2, ensure_ascii=False)
    )
    return system, user


def usage_dict(usage: Any) -> dict[str, Any]:
    if usage is None:
        return {}
    if hasattr(usage, "model_dump"):
        return usage.model_dump()
    return {
        key: getattr(usage, key)
        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
        if hasattr(usage, key)
    }


def validate_labels(labels: list[dict[str, Any]], batch: list[dict[str, Any]]) -> None:
    expected_ids = {row["masked_id"] for row in batch}
    actual_ids = {row.get("masked_id") for row in labels}
    if actual_ids != expected_ids or len(labels) != len(batch):
        raise ValueError(f"id mismatch expected={expected_ids} actual={actual_ids}")
    for row in labels:
        for field, allowed in ENUMS.items():
            if row.get(field) not in allowed:
                raise ValueError(f"{row.get('masked_id')} invalid {field}={row.get(field)!r}")
        if row["novelty_relative_to_prior_state"] != "not_coded":
            raise ValueError(f"{row['masked_id']} novelty must be not_coded")
        if not str(row.get("rationale", "")).strip():
            raise ValueError(f"{row['masked_id']} missing rationale")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = ["masked_id", *ENUMS, "rationale", "coder_id", "model"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--packet",
        type=Path,
        default=Path(__file__).resolve().parent / "taxonomy" / "masked-packet.jsonl",
    )
    parser.add_argument(
        "--codebook",
        type=Path,
        default=Path(__file__).resolve().parent / "MUTATION_TAXONOMY_CODEBOOK.md",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "taxonomy" / "coder-sol-a",
    )
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--coder-id", default="masked-sol-a")
    parser.add_argument("--batch-size", type=int, default=7)
    parser.add_argument("--reasoning-effort", default="high")
    parser.add_argument("--max-retries", type=int, default=3)
    args = parser.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not configured")
    packet = read_jsonl(args.packet.resolve())
    codebook = args.codebook.resolve().read_text(encoding="utf-8")
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    client = OpenAI()
    all_labels: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []

    for batch_index, start in enumerate(range(0, len(packet), args.batch_size), start=1):
        batch = packet[start : start + args.batch_size]
        public_items = [
            {
                "masked_id": row["masked_id"],
                "excerpt": row["excerpt"],
                "truncated": row["truncated"],
            }
            for row in batch
        ]
        system, user = prompt_for(codebook, public_items)
        error = ""
        for attempt in range(1, args.max_retries + 1):
            started = time.time()
            try:
                response = client.chat.completions.create(
                    model=args.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    response_format=response_schema(len(batch)),
                    reasoning_effort=args.reasoning_effort,
                )
                raw = response.choices[0].message.content or ""
                parsed = json.loads(raw)
                labels = parsed["labels"]
                validate_labels(labels, batch)
                for row in labels:
                    row["coder_id"] = args.coder_id
                    row["model"] = args.model
                all_labels.extend(labels)
                audit.append(
                    {
                        "batch_index": batch_index,
                        "attempt": attempt,
                        "masked_ids": [row["masked_id"] for row in batch],
                        "model": args.model,
                        "reasoning_effort": args.reasoning_effort,
                        "request": {"system": system, "user": user},
                        "response": raw,
                        "usage": usage_dict(response.usage),
                        "elapsed_seconds": time.time() - started,
                        "status": "completed",
                    }
                )
                print(
                    f"batch {batch_index}: {len(batch)} labels, "
                    f"{time.time() - started:.1f}s",
                    flush=True,
                )
                break
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                audit.append(
                    {
                        "batch_index": batch_index,
                        "attempt": attempt,
                        "masked_ids": [row["masked_id"] for row in batch],
                        "model": args.model,
                        "reasoning_effort": args.reasoning_effort,
                        "request": {"system": system, "user": user},
                        "error": error,
                        "elapsed_seconds": time.time() - started,
                        "status": "failed",
                    }
                )
                print(f"batch {batch_index} attempt {attempt} failed: {error}", flush=True)
                if attempt < args.max_retries:
                    time.sleep(min(2**attempt, 8))
        else:
            raise RuntimeError(f"batch {batch_index} exhausted retries: {error}")

        (output_dir / "audit.jsonl").write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in audit),
            encoding="utf-8",
        )
        write_csv(output_dir / "labels.csv", all_labels)

    if len(all_labels) != len(packet):
        raise ValueError(f"expected {len(packet)} labels, got {len(all_labels)}")
    manifest = {
        "status": "single model-coded architecture-masked pilot",
        "coder_id": args.coder_id,
        "model": args.model,
        "reasoning_effort": args.reasoning_effort,
        "items": len(all_labels),
        "batches": len(audit),
        "packet": str(args.packet.resolve()),
        "codebook": str(args.codebook.resolve()),
        "note": (
            "Not submission-grade inter-rater evidence. The model saw only the "
            "masked packet and frozen codebook; the script never loaded metadata-key.csv."
        ),
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

