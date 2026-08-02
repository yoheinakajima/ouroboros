#!/usr/bin/env python3
"""Build an architecture-masked packet for the frozen mutation taxonomy.

This script does not label items. It extracts the 84 reflection/update
proposals, removes direct architecture/task/outcome metadata, assigns opaque
identifiers, shuffles order, and writes a separate metadata key for joining
after labels are frozen.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
from pathlib import Path
from typing import Any


APPROACHES = ("workspace_v1_2", "minimal_v2", "hybrid_packs")
SHUFFLE_SEED = 20260723
SCORE_PATTERNS = (
    re.compile(r"\b\d+(?:\.\d+)?\s*/\s*\d+(?:\.\d+)?\b"),
    re.compile(r"\bscore\s*(?:was|of|=|:)?\s*-?\d+(?:\.\d+)?%?\b", re.IGNORECASE),
    re.compile(r"\bpassed\s*=\s*(?:true|false)\b", re.IGNORECASE),
)
OUTCOME_PATTERNS = (
    re.compile(
        r"\b(?:the\s+)?official (?:evaluator|evaluation|grader)"
        r"\s+(?:accepted|passed|failed|returned a failing score|rejected)[^.]*",
        re.IGNORECASE,
    ),
    re.compile(r"\bthe supplied attempt (?:passed|failed)[^.]*", re.IGNORECASE),
)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def opaque_id(approach: str, sequence: int) -> str:
    digest = hashlib.sha256(f"{SHUFFLE_SEED}|{approach}|{sequence}".encode("utf-8")).hexdigest()
    return f"mutation-{digest[:12]}"


def redact_text(
    value: str,
    *,
    approach: str,
    suite: str,
    task: str,
) -> tuple[str, int]:
    redactions = 0
    output = value
    literal_targets = {
        approach,
        suite,
        task,
        task.replace("__", "/"),
        "workspace_v1_2",
        "minimal_v2",
        "hybrid_packs",
    }
    if "__" in task:
        repository, issue = task.split("__", 1)
        literal_targets.add(f"{repository}__{issue}")
    for target in sorted(literal_targets, key=len, reverse=True):
        if not target:
            continue
        matches = len(re.findall(re.escape(target), output, flags=re.IGNORECASE))
        if matches:
            output = re.sub(re.escape(target), "[identifier redacted]", output, flags=re.IGNORECASE)
            redactions += matches
    for pattern in SCORE_PATTERNS:
        output, count = pattern.subn("[numeric outcome redacted]", output)
        redactions += count
    for pattern in OUTCOME_PATTERNS:
        output, count = pattern.subn("[external outcome redacted]", output)
        redactions += count
    return output, redactions


def masked_lesson(
    lesson: dict[str, Any],
    *,
    approach: str,
    suite: str,
    task: str,
) -> tuple[dict[str, Any], int]:
    output: dict[str, Any] = {}
    redactions = 0
    for field in ("title", "scope", "steps", "pitfalls", "validation"):
        raw = lesson.get(field, [] if field != "title" and field != "scope" else "")
        if isinstance(raw, list):
            values = []
            for item in raw:
                masked, count = redact_text(
                    str(item), approach=approach, suite=suite, task=task
                )
                values.append(masked)
                redactions += count
            output[field] = values
        else:
            masked, count = redact_text(
                str(raw), approach=approach, suite=suite, task=task
            )
            output[field] = masked
            redactions += count
    return output, redactions


def generation_metadata(generation_dir: Path, approach: str) -> dict[str, Any]:
    evidence = read_json(generation_dir / "evidence.public.json")
    task = str(evidence.get("task_id") or generation_dir.name.split("-", 2)[-1])
    suite = str(evidence.get("suite_id") or "")
    sequence_match = re.match(r"generation-(\d+)-", generation_dir.name)
    if sequence_match is None:
        raise ValueError(f"cannot parse generation: {generation_dir}")
    sequence = int(sequence_match.group(1))
    score_receipt = evidence.get("score") or {}
    score = score_receipt.get("primary_score")
    passed = score_receipt.get("passed")
    return {
        "approach_id": approach,
        "sequence": sequence,
        "suite_id": suite,
        "task_id": task,
        "score": score,
        "maximum_score": 50.0 if suite == "ouro_activegraph_50" else 1.0,
        "score_passed": passed,
    }


def architecture_acceptance(generation_dir: Path, approach: str, passed: bool | None) -> bool | None:
    if approach == "minimal_v2":
        return passed
    if approach == "hybrid_packs":
        result_path = generation_dir / "native-hybrid" / "result.json"
        if result_path.is_file():
            return bool(read_json(result_path).get("accepted"))
        return None
    state = Path(read_json(generation_dir / "complete.json")["state"])
    record = state / "lineage" / "records" / (
        f"{int(generation_dir.name.split('-')[1]):03d}-"
        f"{generation_dir.name.split('-', 2)[-1]}.json"
    )
    if not record.is_file():
        return None
    architecture = read_json(record).get("architecture_result") or {}
    return int(architecture.get("accepted_generations", 0)) > 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "taxonomy",
    )
    args = parser.parse_args()
    run_root = args.run_root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    packet: list[dict[str, Any]] = []
    key: list[dict[str, Any]] = []
    for approach in APPROACHES:
        approach_root = run_root / "development" / "replication-01" / approach
        generation_dirs = [
            path
            for path in sorted(approach_root.glob("generation-*"))
            if (path / "complete.json").is_file()
            and (path / "evidence.public.json").is_file()
            and (path / "reflection" / "lesson.json").is_file()
        ]
        for generation_dir in generation_dirs:
            metadata = generation_metadata(generation_dir, approach)
            lesson_path = generation_dir / "reflection" / "lesson.json"
            lesson = read_json(lesson_path)
            masked, redactions = masked_lesson(
                lesson,
                approach=approach,
                suite=metadata["suite_id"],
                task=metadata["task_id"],
            )
            item_id = opaque_id(approach, metadata["sequence"])
            serialized = json.dumps(masked, sort_keys=True, ensure_ascii=False)
            packet.append(
                {
                    "masked_id": item_id,
                    "excerpt": masked,
                    "redaction_count": redactions,
                    "truncated": False,
                    "excerpt_sha256": hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
                }
            )
            accepted = architecture_acceptance(
                generation_dir, approach, metadata["score_passed"]
            )
            key.append(
                {
                    "masked_id": item_id,
                    **metadata,
                    "mutation_accepted": accepted,
                    "generation_dir": str(generation_dir),
                    "lesson_sha256": hashlib.sha256(lesson_path.read_bytes()).hexdigest(),
                }
            )

    generator = random.Random(SHUFFLE_SEED)
    generator.shuffle(packet)
    if len(packet) != 84 or len({row["masked_id"] for row in packet}) != 84:
        raise ValueError(f"expected 84 unique items, got {len(packet)}")

    packet_path = output_dir / "masked-packet.jsonl"
    packet_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in packet),
        encoding="utf-8",
    )
    write_csv(output_dir / "metadata-key.csv", sorted(key, key=lambda row: row["masked_id"]))

    label_fields = [
        "masked_id",
        "primary_update_target",
        "secondary_update_target",
        "representational_form",
        "transfer_scope",
        "abstraction_level",
        "evidence_grounding",
        "failure_specificity",
        "validation_strategy",
        "consolidation_operation",
        "executable_status",
        "anticipated_activation",
        "counterfactual_actionability",
        "novelty_relative_to_prior_state",
        "confidence",
        "rationale",
    ]
    write_csv(
        output_dir / "labels-blank.csv",
        [{field: row["masked_id"] if field == "masked_id" else "" for field in label_fields} for row in packet],
    )

    manifest = {
        "status": "architecture-masked taxonomy packet; labels not yet assigned",
        "codebook": "../MUTATION_TAXONOMY_CODEBOOK.md",
        "items": len(packet),
        "shuffle_seed": SHUFFLE_SEED,
        "packet_sha256": hashlib.sha256(packet_path.read_bytes()).hexdigest(),
        "total_redactions": sum(row["redaction_count"] for row in packet),
        "truncated_items": sum(row["truncated"] for row in packet),
        "note": (
            "The metadata key must not be supplied to the primary coder. "
            "The excerpts are architecture-masked, not guaranteed architecture-anonymous."
        ),
    }
    (output_dir / "packet-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
