#!/usr/bin/env python3
"""Reproduce quantitative post-hoc analyses for the Ouroboros probe.

This script uses only Python's standard library. It never modifies raw study
artifacts. Generated tables and the JSON summary are written beside the script.

All analyses in this file are exploratory/post-hoc. The preregistered results
remain those in ../REPORT.md and ../report-probe-adjudicated.json.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import random
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


APPROACHES = ("workspace_v1_2", "minimal_v2", "hybrid_packs")
SUITES = ("ouro_swe_50", "ouro_terminal_12", "ouro_activegraph_50")
NO_CONTEXT_ARMS = ("cold", "cold_ablation")
ALL_ARMS = ("cold", "evolved", "cold_ablation", "sham_improvement_control")
CONTEXT_LIMIT = 64_000
CONTEXT_FILE_LIMIT = 16_000
DENIED_CONTEXT_PARTS = {
    ".git",
    ".env",
    "grader",
    "hidden",
    "manager",
    "private",
    "secret",
    "secrets",
    "__pycache__",
}
Z_95 = 1.959963984540054
Z_80_POWER = 0.8416212335729143


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def mean(values: Iterable[float]) -> float:
    rows = list(values)
    return statistics.mean(rows) if rows else 0.0


def median(values: Iterable[float]) -> float:
    rows = list(values)
    return statistics.median(rows) if rows else 0.0


def percentile(values: Iterable[float], probability: float) -> float:
    rows = sorted(values)
    if not rows:
        return 0.0
    position = (len(rows) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return rows[lower]
    weight = position - lower
    return rows[lower] * (1.0 - weight) + rows[upper] * weight


def nearest_rank_percentile(values: Iterable[float], probability: float) -> float:
    """Return the conservative empirical nearest-rank quantile."""
    rows = sorted(values)
    if not rows:
        return 0.0
    rank = max(1, math.ceil(probability * len(rows)))
    return rows[rank - 1]


def average_ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    cursor = 0
    while cursor < len(order):
        end = cursor
        while end + 1 < len(order) and values[order[end + 1]] == values[order[cursor]]:
            end += 1
        average_rank = (cursor + end + 2) / 2.0
        for position in range(cursor, end + 1):
            ranks[order[position]] = average_rank
        cursor = end + 1
    return ranks


def pearson(left: list[float], right: list[float]) -> float:
    if not left or len(left) != len(right):
        return 0.0
    left_mean = mean(left)
    right_mean = mean(right)
    numerator = sum((x - left_mean) * (y - right_mean) for x, y in zip(left, right))
    denominator = math.sqrt(
        sum((x - left_mean) ** 2 for x in left) * sum((y - right_mean) ** 2 for y in right)
    )
    return numerator / denominator if denominator else 0.0


def spearman(left: list[float], right: list[float]) -> float:
    return pearson(average_ranks(left), average_ranks(right))


def solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float]:
    """Solve a small dense linear system with partial-pivot Gauss-Jordan elimination."""
    size = len(vector)
    augmented = [list(matrix[row]) + [vector[row]] for row in range(size)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            raise ValueError("singular matrix")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        scale = augmented[column][column]
        augmented[column] = [value / scale for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [
                value - factor * pivot_value
                for value, pivot_value in zip(augmented[row], augmented[column])
            ]
    return [augmented[row][-1] for row in range(size)]


def ols_retrieval_on_vocabulary_and_failure(
    vocabulary: list[float], failure: list[float], retrievals: list[float]
) -> dict[str, float]:
    """Fit retrieval_count ~ 1 + vocabulary + failure_flag."""
    columns = [[1.0, vocab, flag] for vocab, flag in zip(vocabulary, failure)]
    xtx = [
        [sum(row[left] * row[right] for row in columns) for right in range(3)]
        for left in range(3)
    ]
    xty = [sum(row[column] * outcome for row, outcome in zip(columns, retrievals)) for column in range(3)]
    intercept, vocabulary_coefficient, failure_coefficient = solve_linear_system(xtx, xty)
    fitted = [
        intercept + vocabulary_coefficient * vocab + failure_coefficient * flag
        for vocab, flag in zip(vocabulary, failure)
    ]
    residual_sum_squares = sum((observed - predicted) ** 2 for observed, predicted in zip(retrievals, fitted))
    total_sum_squares = sum((observed - mean(retrievals)) ** 2 for observed in retrievals)
    vocabulary_sd = statistics.stdev(vocabulary)
    failure_sd = statistics.stdev(failure)
    retrieval_sd = statistics.stdev(retrievals)
    return {
        "intercept": intercept,
        "index_vocabulary_coefficient": vocabulary_coefficient,
        "failure_flag_coefficient": failure_coefficient,
        "standardized_index_vocabulary_coefficient": (
            vocabulary_coefficient * vocabulary_sd / retrieval_sd if retrieval_sd else 0.0
        ),
        "standardized_failure_flag_coefficient": (
            failure_coefficient * failure_sd / retrieval_sd if retrieval_sd else 0.0
        ),
        "r_squared": 1.0 - residual_sum_squares / total_sum_squares if total_sum_squares else 0.0,
    }


def conditional_vocabulary_permutation_test(
    vocabulary: list[float],
    failure: list[float],
    retrievals: list[float],
    *,
    permutations: int = 50_000,
    seed: int = 20260723,
) -> dict[str, float | int]:
    """Shuffle vocabulary within pass/fail strata and refit the adjusted OLS model."""
    observed = ols_retrieval_on_vocabulary_and_failure(vocabulary, failure, retrievals)[
        "index_vocabulary_coefficient"
    ]
    groups = {
        flag: [index for index, current in enumerate(failure) if current == flag]
        for flag in sorted(set(failure))
    }
    generator = random.Random(seed)
    exceedances = 0
    for _ in range(permutations):
        permuted = list(vocabulary)
        for indices in groups.values():
            values = [vocabulary[index] for index in indices]
            generator.shuffle(values)
            for index, value in zip(indices, values):
                permuted[index] = value
        coefficient = ols_retrieval_on_vocabulary_and_failure(permuted, failure, retrievals)[
            "index_vocabulary_coefficient"
        ]
        exceedances += int(abs(coefficient) >= abs(observed))
    return {
        "permutations": permutations,
        "seed": seed,
        "two_sided_p_value": (exceedances + 1) / (permutations + 1),
    }


def sha256_json(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def pack_words(value: str) -> set[str]:
    """Match the final Hybrid Pack's casefold/alphanumeric tokenizer."""
    output: set[str] = set()
    token: list[str] = []
    for character in value.casefold():
        if character.isalnum():
            token.append(character)
        elif token:
            output.add("".join(token))
            token = []
    if token:
        output.add("".join(token))
    return output


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def final_state(run_root: Path, approach: str) -> Path:
    complete = run_root / "development" / "replication-01" / approach / "lineage-complete.json"
    return Path(read_json(complete)["final_state"])


def safe_workspace_rows(workspace: Path) -> list[tuple[str, str, int]]:
    rows: list[tuple[str, str, int]] = []
    for path in sorted(workspace.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(workspace)
        if any(part.lower() in DENIED_CONTEXT_PARTS for part in relative.parts):
            continue
        raw = path.read_bytes()[: CONTEXT_FILE_LIMIT + 1]
        if b"\0" in raw:
            continue
        try:
            value = raw[:CONTEXT_FILE_LIMIT].decode("utf-8")
        except UnicodeDecodeError:
            continue
        if len(raw) > CONTEXT_FILE_LIMIT:
            value += "\n[truncated]"
        rows.append((relative.as_posix(), value, path.stat().st_size))
    priority = {"SELF.md": 0, "MEMORY.md": 1}
    rows.sort(key=lambda row: (priority.get(row[0], 2), row[0]))
    return rows


def workspace_expression(run_root: Path) -> dict[str, Any]:
    state = final_state(run_root, "workspace_v1_2")
    workspace = state / "final_workspace" if (state / "final_workspace").is_dir() else state
    manifest = read_json(state / "evolution_manifest.json")
    rows = safe_workspace_rows(workspace)
    sections = [(name, f"## Retained workspace file: {name}\n{text}", raw_bytes) for name, text, raw_bytes in rows]
    serialized = "\n\n".join(section for _, section, _ in sections)
    output = ""
    visible: list[dict[str, Any]] = []
    for name, section, raw_bytes in sections:
        remaining = CONTEXT_LIMIT - len(output)
        if remaining <= 0:
            break
        addition = ("\n\n" if output else "") + section
        delivered = addition[:remaining]
        output += delivered
        visible.append(
            {
                "file": name,
                "fully_visible": len(delivered) == len(addition),
                "delivered_characters": len(delivered),
                "serialized_characters": len(addition),
                "raw_file_bytes": raw_bytes,
            }
        )
    return {
        "approach_id": "workspace_v1_2",
        "artifact_bytes": manifest["artifact_bytes"],
        "eligible_payload_bytes": len(serialized.encode("utf-8")),
        "delivered_context_bytes": len(output.encode("utf-8")),
        "storage_reach": len(output.encode("utf-8")) / manifest["artifact_bytes"],
        "eligible_payload_reach": len(output.encode("utf-8")) / len(serialized.encode("utf-8")),
        "semantic_units_total": len(rows),
        "semantic_units_exposed_per_task": len(visible),
        "semantic_unit_reach_per_task": len(visible) / len(rows),
        "fully_visible_units": sum(row["fully_visible"] for row in visible),
        "corpus_units_exposed_across_probe": len(visible),
        "corpus_unit_reach_across_probe": len(visible) / len(rows),
        "adaptivity_gap": 0.0,
        "expression_mode": "static: same retained files are serialized for every task",
        "runtime_activation": "none",
        "actor_invocable_retained_capabilities": 0,
        "notes": "File is the semantic unit. One of the 18 exposed files is partial.",
        "visible_files": visible,
    }


def minimal_expression(run_root: Path) -> dict[str, Any]:
    state = final_state(run_root, "minimal_v2")
    manifest = read_json(state / "evolution_manifest.json")
    export_path = state / "state_export.json"
    value = read_json(export_path)
    allowed = {
        "procedures": value.get("procedures", []),
        "capabilities": value.get("capabilities", []),
        "evidence_receipts": value.get("evidence_receipts", []),
    }
    context = json.dumps(allowed, indent=2, sort_keys=True, ensure_ascii=False)[:CONTEXT_LIMIT]
    total_units = sum(len(rows) for rows in allowed.values())
    return {
        "approach_id": "minimal_v2",
        "artifact_bytes": manifest["artifact_bytes"],
        "eligible_payload_bytes": export_path.stat().st_size,
        "delivered_context_bytes": len(context.encode("utf-8")),
        "storage_reach": len(context.encode("utf-8")) / manifest["artifact_bytes"],
        "eligible_payload_reach": len(context.encode("utf-8")) / export_path.stat().st_size,
        "semantic_units_total": total_units,
        "semantic_units_exposed_per_task": total_units,
        "semantic_unit_reach_per_task": 1.0 if total_units else 0.0,
        "fully_visible_units": total_units,
        "corpus_units_exposed_across_probe": total_units,
        "corpus_unit_reach_across_probe": 1.0 if total_units else 0.0,
        "adaptivity_gap": 0.0,
        "expression_mode": "static: full semantic export is serialized for every task",
        "procedures": len(allowed["procedures"]),
        "capabilities": len(allowed["capabilities"]),
        "evidence_receipts": len(allowed["evidence_receipts"]),
        "runtime_activation": "none",
        "actor_invocable_retained_capabilities": 0,
        "notes": "Procedure, capability, or receipt is the semantic unit. Database bytes mostly encode provenance.",
    }


def task_directory(run_root: Path, approach: str, arm: str, suite: str, task: str) -> Path:
    return run_root / "evaluation" / "probe" / "replication-01" / approach / arm / suite / task


def trace_path(task_dir: Path) -> Path | None:
    provenance = task_dir / "provenance.json"
    if provenance.is_file():
        trial_dir = Path(read_json(provenance).get("trial_dir", ""))
        harbor_trace = trial_dir / "agent" / "trace.jsonl"
        if harbor_trace.is_file():
            return harbor_trace
    local = task_dir / "evaluation" / "local" / "attempt" / "trace.jsonl"
    if local.is_file():
        return local
    candidates = list(task_dir.glob("**/trace.jsonl"))
    return candidates[0] if candidates else None


def actual_model_request(trace_row: dict[str, Any]) -> dict[str, Any]:
    request = trace_row["request"]
    nested = request.get("request")
    return nested if isinstance(nested, dict) else request


def trace_summary(task_dir: Path) -> dict[str, Any]:
    path = trace_path(task_dir)
    if path is None:
        return {
            "trace_present": False,
            "first_request_sha256": None,
            "first_input_tokens": None,
            "context_bytes": 0,
            "model_calls": 0,
            "tool_calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0.0,
            "operations": {},
            "retained_context": "",
            "task_prompt": "",
        }
    first_request: dict[str, Any] | None = None
    first_input_tokens: int | None = None
    last_usage: dict[str, Any] = {}
    operations: Counter[str] = Counter()
    model_calls = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        operation = str(row.get("operation", "unknown"))
        operations[operation] += 1
        usage = row.get("usage_after")
        if isinstance(usage, dict):
            last_usage = usage
        if operation == "model_complete":
            model_calls += 1
            if first_request is None:
                first_request = actual_model_request(row)
                response = row.get("response", {})
                first_input_tokens = response.get("input_tokens")
    retained_context = ""
    task_prompt = ""
    if first_request:
        for message in first_request.get("messages", []):
            if message.get("role") != "user":
                continue
            try:
                payload = json.loads(message.get("content", ""))
            except (TypeError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict) and "retained_capability_context" in payload:
                retained_context = str(payload["retained_capability_context"])
            if isinstance(payload, dict):
                task_prompt = str(payload.get("task", ""))
            break
    return {
        "trace_present": True,
        "trace_path": str(path),
        "first_request_sha256": sha256_json(first_request) if first_request else None,
        "first_input_tokens": first_input_tokens,
        "context_bytes": len(retained_context.encode("utf-8")),
        "model_calls": int(last_usage.get("model_calls", model_calls)),
        "tool_calls": int(last_usage.get("tool_calls", sum(v for k, v in operations.items() if k != "model_complete"))),
        "input_tokens": int(last_usage.get("input_tokens", 0)),
        "output_tokens": int(last_usage.get("output_tokens", 0)),
        "cost_usd": float(last_usage.get("cost_usd", 0.0)),
        "operations": dict(operations),
        "retained_context": retained_context,
        "task_prompt": task_prompt,
    }


def result_index(run_root: Path) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    rows = load_jsonl(run_root / "results-probe-adjudicated.jsonl")
    return {(row["approach_id"], row["arm"], row["suite_id"], row["task_id"]): row for row in rows}


def build_trace_index(
    run_root: Path, results: dict[tuple[str, str, str, str], dict[str, Any]]
) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    output: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for key in sorted(results):
        approach, arm, suite, task = key
        output[key] = trace_summary(task_directory(run_root, approach, arm, suite, task))
    return output


def hybrid_corpus(run_root: Path) -> list[dict[str, Any]]:
    state = final_state(run_root, "hybrid_packs")
    rows: list[dict[str, Any]] = []
    for path in sorted((state / "lineage" / "records").glob("*.json")):
        record = read_json(path)
        architecture = record.get("architecture_result", {})
        if not architecture.get("accepted"):
            continue
        lesson = record["lesson"]
        serialized = json.dumps(lesson, sort_keys=True, ensure_ascii=False)
        index_text = " ".join(
            [
                record["suite_id"],
                record["task_id"],
                lesson["title"],
                lesson["scope"],
                " ".join(lesson.get("trigger_terms", [])),
            ]
        ).lower()
        index_vocabulary = pack_words(index_text)
        rows.append(
            {
                "sequence": record["sequence"],
                "suite_id": record["suite_id"],
                "task_id": record["task_id"],
                "score_passed": bool(record["score_passed"]),
                "title": lesson["title"],
                "characters": len(serialized),
                "words": len(re.findall(r"\b\w+\b", serialized)),
                "trigger_terms": len(lesson.get("trigger_terms", [])),
                "index_vocabulary": len(index_vocabulary),
                "index_terms": json.dumps(sorted(index_vocabulary)),
                "retrieval_count": 0,
            }
        )
    return rows


def hybrid_retrievals(
    results: dict[tuple[str, str, str, str], dict[str, Any]],
    traces: dict[tuple[str, str, str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in sorted(results):
        approach, arm, suite, task = key
        if approach != "hybrid_packs" or arm != "evolved":
            continue
        context = traces[key]["retained_context"]
        try:
            parsed = json.loads(context)
            lessons = parsed["activegraph_query_output"]["lessons"]
        except (TypeError, json.JSONDecodeError, KeyError):
            lessons = []
        for rank, lesson in enumerate(lessons, start=1):
            source_task = str(lesson.get("task_id", ""))
            heldout_repo = task.split("__", 1)[0] if "__" in task else task
            source_repo = source_task.split("__", 1)[0] if "__" in source_task else source_task
            rows.append(
                {
                    "heldout_suite_id": suite,
                    "heldout_task_id": task,
                    "rank": rank,
                    "source_suite_id": lesson.get("suite_id"),
                    "source_task_id": source_task,
                    "score_passed": bool(lesson.get("score_passed")),
                    "title": lesson.get("title"),
                    "same_suite": lesson.get("suite_id") == suite,
                    "same_repository_prefix": heldout_repo == source_repo,
                    "heldout_score": results[key]["score"] / results[key]["maximum_score"],
                }
            )
    return rows


def hybrid_expression(
    run_root: Path, corpus: list[dict[str, Any]], retrievals: list[dict[str, Any]], traces: dict[tuple[str, str, str, str], dict[str, Any]]
) -> dict[str, Any]:
    state = final_state(run_root, "hybrid_packs")
    manifest = read_json(state / "evolution_manifest.json")
    evolved_contexts = [
        row["context_bytes"]
        for (approach, arm, _, _), row in traces.items()
        if approach == "hybrid_packs" and arm == "evolved"
    ]
    per_task = Counter((row["heldout_suite_id"], row["heldout_task_id"]) for row in retrievals)
    unique = {row["source_task_id"] for row in retrievals}
    total = len(corpus)
    return {
        "approach_id": "hybrid_packs",
        "artifact_bytes": manifest["artifact_bytes"],
        "eligible_payload_bytes": sum(row["characters"] for row in corpus),
        "delivered_context_bytes": mean(evolved_contexts),
        "storage_reach": mean(evolved_contexts) / manifest["artifact_bytes"],
        "eligible_payload_reach": mean(evolved_contexts) / sum(row["characters"] for row in corpus),
        "semantic_units_total": total,
        "semantic_units_exposed_per_task": mean(per_task.values()),
        "semantic_unit_reach_per_task": mean(per_task.values()) / total,
        "fully_visible_units": mean(per_task.values()),
        "corpus_units_exposed_across_probe": len(unique),
        "corpus_unit_reach_across_probe": len(unique) / total,
        "adaptivity_gap": len(unique) / total - mean(per_task.values()) / total,
        "expression_mode": "adaptive: task-dependent top-three retrieval",
        "runtime_activation": "automatic pre-task ActiveGraph retrieval",
        "actor_invocable_retained_capabilities": 0,
        "notes": "Lesson is the semantic unit. The Pack runs before the actor, but is not an actor-callable tool.",
    }


def hybrid_counterfactual_retrieval(
    corpus: list[dict[str, Any]],
    results: dict[tuple[str, str, str, str], dict[str, Any]],
    traces: dict[tuple[str, str, str, str], dict[str, Any]],
) -> dict[str, Any]:
    documents = [set(json.loads(row["index_terms"])) for row in corpus]
    document_frequency: Counter[str] = Counter(term for document in documents for term in document)
    document_count = len(documents)
    average_document_length = mean(len(document) for document in documents)
    query_keys = [
        key
        for key in sorted(results)
        if key[0] == "hybrid_packs" and key[1] == "evolved"
    ]
    output: dict[str, Any] = {}
    for method in ("overlap", "cosine", "jaccard", "bm25"):
        selected_indices: list[int] = []
        for key in query_keys:
            query = pack_words(traces[key]["task_prompt"])
            scored: list[tuple[float, int]] = []
            for index, document in enumerate(documents):
                intersection = query & document
                if method == "overlap":
                    score = float(len(intersection))
                elif method == "cosine":
                    score = (
                        len(intersection) / math.sqrt(len(query) * len(document))
                        if query and document
                        else 0.0
                    )
                elif method == "jaccard":
                    union = query | document
                    score = len(intersection) / len(union) if union else 0.0
                else:
                    k1 = 1.2
                    b = 0.75
                    length_normalizer = 1.0 - b + b * len(document) / average_document_length
                    score = sum(
                        math.log(
                            1.0
                            + (document_count - document_frequency[term] + 0.5)
                            / (document_frequency[term] + 0.5)
                        )
                        * (k1 + 1.0)
                        / (1.0 + k1 * length_normalizer)
                        for term in intersection
                    )
                scored.append((score, index))
            ranked = sorted(scored, key=lambda row: (-row[0], row[1]))
            selected_indices.extend([index for score, index in ranked if score > 0.0][:3])
        counts = Counter(corpus[index]["task_id"] for index in selected_indices)
        failure_slots = sum(not corpus[index]["score_passed"] for index in selected_indices)
        top_two = counts.most_common(2)
        output[method] = {
            "retrieval_slots": len(selected_indices),
            "failure_slots": failure_slots,
            "failure_fraction": failure_slots / len(selected_indices),
            "unique_lessons": len(counts),
            "top_two_lessons": top_two,
            "top_two_fraction": sum(count for _, count in top_two) / len(selected_indices),
        }
    output["interpretation"] = (
        "Offline re-ranking only. It measures retrieval composition under the same 19 prompts; "
        "it does not estimate downstream task performance."
    )
    return output


def expression_table(profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keys = (
        "approach_id",
        "artifact_bytes",
        "eligible_payload_bytes",
        "delivered_context_bytes",
        "storage_reach",
        "eligible_payload_reach",
        "semantic_units_total",
        "semantic_units_exposed_per_task",
        "semantic_unit_reach_per_task",
        "corpus_units_exposed_across_probe",
        "corpus_unit_reach_across_probe",
        "adaptivity_gap",
        "expression_mode",
        "procedures",
        "capabilities",
        "evidence_receipts",
        "runtime_activation",
        "actor_invocable_retained_capabilities",
        "notes",
    )
    return [{key: profile.get(key) for key in keys} for profile in profiles]


def normalized_score(row: dict[str, Any]) -> float:
    return row["score"] / row["maximum_score"]


def equivalent_control_analysis(
    results: dict[tuple[str, str, str, str], dict[str, Any]],
    traces: dict[tuple[str, str, str, str], dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    conditions = tuple(itertools.product(APPROACHES, NO_CONTEXT_ARMS))
    task_rows: list[dict[str, Any]] = []
    long_rows: list[dict[str, Any]] = []
    pair_rows: list[dict[str, Any]] = []
    summary: dict[str, Any] = {}
    global_fixed_pass = 0
    global_fixed_fail = 0
    global_variable = 0
    evolved_outside_range: list[dict[str, Any]] = []
    for suite in SUITES:
        tasks = sorted({key[3] for key in results if key[2] == suite})
        within_variances: list[float] = []
        task_score_rows: list[list[float]] = []
        variable = 0
        all_requests_identical = True
        for task in tasks:
            scores = [normalized_score(results[(approach, arm, suite, task)]) for approach, arm in conditions]
            task_score_rows.append(scores)
            hashes = [traces[(approach, arm, suite, task)]["first_request_sha256"] for approach, arm in conditions]
            unique_scores = sorted(set(scores))
            unique_hashes = sorted({value for value in hashes if value is not None})
            is_variable = len(unique_scores) > 1
            variable += int(is_variable)
            global_variable += int(is_variable)
            global_fixed_pass += int(not is_variable and unique_scores == [1.0])
            global_fixed_fail += int(not is_variable and unique_scores == [0.0])
            all_requests_identical = all_requests_identical and len(unique_hashes) == 1
            within_variances.append(statistics.variance(scores))
            task_rows.append(
                {
                    "suite_id": suite,
                    "task_id": task,
                    "identical_first_request": len(unique_hashes) == 1,
                    "unique_first_request_hashes": len(unique_hashes),
                    "outcome_variable": is_variable,
                    "minimum_score": min(scores),
                    "maximum_score": max(scores),
                    "score_range": max(scores) - min(scores),
                    "scores": json.dumps(scores),
                }
            )
            for (approach, arm), score, request_hash in zip(conditions, scores, hashes):
                long_rows.append(
                    {
                        "suite_id": suite,
                        "task_id": task,
                        "condition_type": "equivalent_no_context",
                        "approach_id": approach,
                        "arm": arm,
                        "score": score,
                        "equivalent_minimum": min(scores),
                        "equivalent_maximum": max(scores),
                        "inside_equivalent_range": True,
                        "departure_from_equivalent_range": 0.0,
                        "first_request_sha256": request_hash,
                    }
                )
            for approach in APPROACHES:
                evolved_score = normalized_score(results[(approach, "evolved", suite, task)])
                departure = (
                    evolved_score - max(scores)
                    if evolved_score > max(scores)
                    else evolved_score - min(scores)
                    if evolved_score < min(scores)
                    else 0.0
                )
                inside = departure == 0.0
                evolved_row = {
                    "suite_id": suite,
                    "task_id": task,
                    "condition_type": "evolved",
                    "approach_id": approach,
                    "arm": "evolved",
                    "score": evolved_score,
                    "equivalent_minimum": min(scores),
                    "equivalent_maximum": max(scores),
                    "inside_equivalent_range": inside,
                    "departure_from_equivalent_range": departure,
                    "first_request_sha256": traces[(approach, "evolved", suite, task)][
                        "first_request_sha256"
                    ],
                }
                long_rows.append(evolved_row)
                if not inside:
                    evolved_outside_range.append(evolved_row)
        pseudo_means = {
            f"{approach}/{arm}": mean(
                normalized_score(results[(approach, arm, suite, task)]) for task in tasks
            )
            for approach, arm in conditions
        }
        pair_deltas: list[float] = []
        for left, right in itertools.combinations(conditions, 2):
            delta = pseudo_means[f"{left[0]}/{left[1]}"] - pseudo_means[f"{right[0]}/{right[1]}"]
            pair_deltas.append(delta)
            pair_rows.append(
                {
                    "suite_id": suite,
                    "left_condition": f"{left[0]}/{left[1]}",
                    "right_condition": f"{right[0]}/{right[1]}",
                    "left_mean": pseudo_means[f"{left[0]}/{left[1]}"],
                    "right_mean": pseudo_means[f"{right[0]}/{right[1]}"],
                    "delta": delta,
                    "absolute_delta": abs(delta),
                }
            )
        paired_standard_error = math.sqrt(sum(2.0 * variance for variance in within_variances)) / len(tasks)
        approximate_mde = (Z_95 + Z_80_POWER) * paired_standard_error
        task_means = [mean(row) for row in task_score_rows]
        grand_mean = mean(task_means)
        ratings_per_task = len(conditions)
        mean_square_between = (
            ratings_per_task
            * sum((task_mean - grand_mean) ** 2 for task_mean in task_means)
            / (len(tasks) - 1)
            if len(tasks) > 1
            else 0.0
        )
        mean_square_within = (
            sum(
                sum((score - mean(score_row)) ** 2 for score in score_row)
                for score_row in task_score_rows
            )
            / (len(tasks) * (ratings_per_task - 1))
        )
        icc_denominator = mean_square_between + (ratings_per_task - 1) * mean_square_within
        icc_1_1 = (
            (mean_square_between - mean_square_within) / icc_denominator
            if icc_denominator
            else 1.0
        )
        discordances: list[bool] = []
        for left, right in itertools.combinations(conditions, 2):
            for task in tasks:
                discordances.append(
                    normalized_score(results[(left[0], left[1], suite, task)])
                    != normalized_score(results[(right[0], right[1], suite, task)])
                )
        summary[suite] = {
            "tasks": len(tasks),
            "identical_first_requests_for_every_task": all_requests_identical,
            "variable_tasks": variable,
            "variable_task_fraction": variable / len(tasks),
            "equivalent_condition_means": pseudo_means,
            "empirical_null_minimum_mean": min(pseudo_means.values()),
            "empirical_null_maximum_mean": max(pseudo_means.values()),
            "empirical_null_maximum_absolute_delta": max(abs(value) for value in pair_deltas),
            "empirical_null_p95_absolute_delta": nearest_rank_percentile(
                (abs(value) for value in pair_deltas), 0.95
            ),
            "empirical_null_p95_method": "nearest-rank over 15 absolute pairwise label deltas",
            "pairwise_task_discordance": mean(float(value) for value in discordances),
            "paired_standard_error_from_equivalent_arms": paired_standard_error,
            "approximate_80pct_power_mde": approximate_mde,
            "icc_1_1": icc_1_1,
            "icc_mean_square_between_tasks": mean_square_between,
            "icc_mean_square_within_tasks": mean_square_within,
            "minimum_two_sided_sign_test_p_if_all_tasks_favor_one_arm": 2 ** (1 - len(tasks)),
            "note": "MDE is a post-hoc normal approximation from within-task variance across six equivalent arms.",
        }
    summary["all_families"] = {
        "tasks": len(task_rows),
        "variable_tasks": global_variable,
        "fixed_pass_tasks": global_fixed_pass,
        "fixed_fail_tasks": global_fixed_fail,
        "stable_tasks": global_fixed_pass + global_fixed_fail,
        "evolved_task_architecture_results_outside_task_specific_equivalent_range": len(
            evolved_outside_range
        ),
        "outside_range_results": evolved_outside_range,
        "interpretation": (
            "Variable tasks estimate baseline instability. Stable pass/fail tasks are not "
            "information-free: they provide one-sided opportunities to detect regressions or gains."
        ),
    }
    return task_rows, long_rows, pair_rows, summary


def sham_analysis(
    results: dict[tuple[str, str, str, str], dict[str, Any]],
    traces: dict[tuple[str, str, str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for suite in SUITES:
        tasks = sorted({key[3] for key in results if key[2] == suite})
        for approach in APPROACHES:
            evolved = mean(normalized_score(results[(approach, "evolved", suite, task)]) for task in tasks)
            ablation = mean(
                normalized_score(results[(approach, "cold_ablation", suite, task)]) for task in tasks
            )
            sham = mean(
                normalized_score(results[(approach, "sham_improvement_control", suite, task)])
                for task in tasks
            )
            token_density: dict[str, float] = {}
            context_bytes: dict[str, float] = {}
            first_tokens: dict[str, float] = {}
            for arm in ("evolved", "sham_improvement_control"):
                densities: list[float] = []
                bytes_rows: list[int] = []
                input_rows: list[int] = []
                for task in tasks:
                    current = traces[(approach, arm, suite, task)]
                    no_context_tokens = mean(
                        traces[(base_approach, base_arm, suite, task)]["first_input_tokens"] or 0
                        for base_approach in APPROACHES
                        for base_arm in NO_CONTEXT_ARMS
                    )
                    byte_count = current["context_bytes"]
                    input_count = current["first_input_tokens"] or 0
                    if byte_count:
                        densities.append((input_count - no_context_tokens) / byte_count)
                    bytes_rows.append(byte_count)
                    input_rows.append(input_count)
                token_density[arm] = mean(densities)
                context_bytes[arm] = mean(bytes_rows)
                first_tokens[arm] = mean(input_rows)
            rows.append(
                {
                    "suite_id": suite,
                    "approach_id": approach,
                    "evolved_score": evolved,
                    "ablation_score": ablation,
                    "sham_score": sham,
                    "evolved_minus_ablation": evolved - ablation,
                    "sham_minus_ablation": sham - ablation,
                    "evolved_minus_sham": evolved - sham,
                    "sham_harm_share_of_evolved_minus_sham": (
                        max(0.0, ablation - sham) / (evolved - sham) if evolved > sham else 0.0
                    ),
                    "evolved_mean_context_bytes": context_bytes["evolved"],
                    "sham_mean_context_bytes": context_bytes["sham_improvement_control"],
                    "evolved_mean_first_input_tokens": first_tokens["evolved"],
                    "sham_mean_first_input_tokens": first_tokens["sham_improvement_control"],
                    "evolved_incremental_tokens_per_context_byte": token_density["evolved"],
                    "sham_incremental_tokens_per_context_byte": token_density["sham_improvement_control"],
                    "sham_to_evolved_token_density_ratio": (
                        token_density["sham_improvement_control"] / token_density["evolved"]
                        if token_density["evolved"]
                        else 0.0
                    ),
                }
            )
    return rows


def behavior_mediation(
    results: dict[tuple[str, str, str, str], dict[str, Any]],
    traces: dict[tuple[str, str, str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for suite in SUITES:
        tasks = sorted({key[3] for key in results if key[2] == suite})
        for approach in APPROACHES:
            per_task: list[dict[str, float]] = []
            for task in tasks:
                evolved = traces[(approach, "evolved", suite, task)]
                baseline = {
                    metric: mean(
                        float(traces[(base_approach, base_arm, suite, task)][metric])
                        for base_approach in APPROACHES
                        for base_arm in NO_CONTEXT_ARMS
                    )
                    for metric in ("model_calls", "tool_calls", "input_tokens", "output_tokens", "cost_usd")
                }
                per_task.append(
                    {
                        metric: float(evolved[metric]) - baseline[metric]
                        for metric in ("model_calls", "tool_calls", "input_tokens", "output_tokens", "cost_usd")
                    }
                )
            rows.append(
                {
                    "suite_id": suite,
                    "approach_id": approach,
                    "tasks": len(tasks),
                    "score_delta_vs_pooled_no_context": mean(
                        normalized_score(results[(approach, "evolved", suite, task)])
                        - mean(
                            normalized_score(results[(base_approach, base_arm, suite, task)])
                            for base_approach in APPROACHES
                            for base_arm in NO_CONTEXT_ARMS
                        )
                        for task in tasks
                    ),
                    "model_call_delta_vs_pooled_no_context": mean(
                        row["model_calls"] for row in per_task
                    ),
                    "tool_call_delta_vs_pooled_no_context": mean(row["tool_calls"] for row in per_task),
                    "input_token_delta_vs_pooled_no_context": mean(
                        row["input_tokens"] for row in per_task
                    ),
                    "output_token_delta_vs_pooled_no_context": mean(
                        row["output_tokens"] for row in per_task
                    ),
                    "cost_delta_vs_pooled_no_context": mean(row["cost_usd"] for row in per_task),
                }
            )
    return rows


def development_process(run_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for approach in APPROACHES:
        state = final_state(run_root, approach)
        records = state / "lineage" / "records"
        for path in sorted(records.glob("*.json")):
            record = read_json(path)
            architecture = record.get("architecture_result", {})
            if approach == "workspace_v1_2":
                native_usage = architecture.get("usage") or {}
                accepted = int(architecture.get("accepted_generations", 0)) > 0
                author_requests = int(native_usage.get("llm_calls", 0))
                author_input_tokens = int(native_usage.get("input_tokens", 0))
                author_output_tokens = int(native_usage.get("output_tokens", 0))
                author_cost = float(native_usage.get("provider_estimated_cost_usd", 0.0))
            elif approach == "minimal_v2":
                native_import = architecture.get("native_import") or {}
                accepted = bool(native_import.get("retained"))
                author_requests = int(architecture.get("model_calls", 0))
                author_input_tokens = 0
                author_output_tokens = 0
                author_cost = 0.0
            else:
                author_usage = architecture.get("author_usage") or {}
                accepted = bool(architecture.get("accepted"))
                author_requests = int(author_usage.get("requests", 0))
                author_input_tokens = int(author_usage.get("input_tokens", 0))
                author_output_tokens = int(author_usage.get("output_tokens", 0))
                author_cost = float(author_usage.get("estimated_cost_usd", 0.0))
            evolution = architecture.get("evolution") or {}
            rows.append(
                {
                    "approach_id": approach,
                    "sequence": record.get("sequence"),
                    "suite_id": record.get("suite_id"),
                    "task_id": record.get("task_id"),
                    "score_passed": record.get("score_passed"),
                    "mutation_accepted": accepted,
                    "author_requests": author_requests,
                    "author_input_tokens": author_input_tokens,
                    "author_output_tokens": author_output_tokens,
                    "author_cost_usd": author_cost,
                    "evolution_reason": evolution.get("reason"),
                    "author_feedback": json.dumps(evolution.get("author_feedback", [])),
                }
            )
    return rows


def path_content_map(root: Path) -> dict[str, str]:
    output: dict[str, str] = {}
    if not root.is_dir():
        return output
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        output[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return output


def mutation_accepted(approach: str, architecture: dict[str, Any]) -> bool:
    if approach == "workspace_v1_2":
        return int(architecture.get("accepted_generations", 0)) > 0
    if approach == "minimal_v2":
        return bool((architecture.get("native_import") or {}).get("retained"))
    return bool(architecture.get("accepted"))


def state_growth(run_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    development_root = run_root / "development" / "replication-01"
    for approach in APPROACHES:
        previous_files: dict[str, str] = {}
        previous_artifact_bytes = 0
        for generation in sorted((development_root / approach).glob("generation-*")):
            state = generation / "state"
            if not state.is_dir() or not (state / "evolution_manifest.json").is_file():
                continue
            manifest = read_json(state / "evolution_manifest.json")
            record_paths = sorted((state / "lineage" / "records").glob("*.json"))
            if not record_paths:
                continue
            record = read_json(record_paths[-1])
            architecture = record.get("architecture_result", {})
            row: dict[str, Any] = {
                "approach_id": approach,
                "sequence": record["sequence"],
                "suite_id": record["suite_id"],
                "task_id": record["task_id"],
                "score_passed": bool(record["score_passed"]),
                "mutation_accepted": mutation_accepted(approach, architecture),
                "artifact_bytes": manifest["artifact_bytes"],
                "artifact_byte_delta": manifest["artifact_bytes"] - previous_artifact_bytes,
                "semantic_units": 0,
                "procedures": 0,
                "capabilities": 0,
                "evidence_receipts": 0,
                "pack_source_bytes": 0,
                "pack_version": "",
                "files_added": 0,
                "files_modified": 0,
                "files_deleted": 0,
                "changed_paths": "[]",
            }
            if approach == "workspace_v1_2":
                workspace = state / "final_workspace"
                current_files = path_content_map(workspace)
                added = sorted(set(current_files) - set(previous_files))
                deleted = sorted(set(previous_files) - set(current_files))
                modified = sorted(
                    path
                    for path in set(current_files) & set(previous_files)
                    if current_files[path] != previous_files[path]
                )
                row.update(
                    {
                        "semantic_units": len(safe_workspace_rows(workspace)),
                        "files_added": len(added),
                        "files_modified": len(modified),
                        "files_deleted": len(deleted),
                        "changed_paths": json.dumps(added + modified + deleted),
                    }
                )
                previous_files = current_files
            elif approach == "minimal_v2":
                export = read_json(state / "state_export.json")
                procedures = len(export.get("procedures", []))
                capabilities = len(export.get("capabilities", []))
                receipts = len(export.get("evidence_receipts", []))
                row.update(
                    {
                        "semantic_units": procedures + capabilities + receipts,
                        "procedures": procedures,
                        "capabilities": capabilities,
                        "evidence_receipts": receipts,
                    }
                )
            else:
                registry = read_json(state / "registry.json")
                adopted = registry.get("adopted", [])
                source_bytes = 0
                version = ""
                if adopted:
                    pack_root = state / adopted[-1]["path"]
                    source = pack_root / "__init__.py"
                    source_bytes = source.stat().st_size if source.is_file() else 0
                    version = adopted[-1]["version"]
                accepted_records = [
                    read_json(path)
                    for path in (state / "lineage" / "records").glob("*.json")
                    if (read_json(path).get("architecture_result") or {}).get("accepted")
                ]
                row.update(
                    {
                        "semantic_units": len(accepted_records),
                        "pack_source_bytes": source_bytes,
                        "pack_version": version,
                    }
                )
            rows.append(row)
            previous_artifact_bytes = manifest["artifact_bytes"]
    return rows


def summarize_hybrid_memory(
    corpus: list[dict[str, Any]], retrievals: list[dict[str, Any]]
) -> dict[str, Any]:
    counts = Counter(row["source_task_id"] for row in retrievals)
    for row in corpus:
        row["retrieval_count"] = counts[row["task_id"]]
    passing = [row for row in corpus if row["score_passed"]]
    failing = [row for row in corpus if not row["score_passed"]]
    failed_slots = sum(not row["score_passed"] for row in retrievals)
    same_suite = sum(row["same_suite"] for row in retrievals)
    same_repo = sum(row["same_repository_prefix"] for row in retrievals)
    top_two = counts.most_common(2)
    total_slots = len(retrievals)
    hhi = sum((count / total_slots) ** 2 for count in counts.values()) if total_slots else 0.0
    vocabulary_sizes = [float(row["index_vocabulary"]) for row in corpus]
    retrieval_counts = [float(row["retrieval_count"]) for row in corpus]
    failure_flags = [float(not row["score_passed"]) for row in corpus]
    tasks = len({(row["heldout_suite_id"], row["heldout_task_id"]) for row in retrievals})
    failing_selection_rate = failed_slots / (len(failing) * tasks)
    passing_selection_rate = (total_slots - failed_slots) / (len(passing) * tasks)
    adjusted_regression = ols_retrieval_on_vocabulary_and_failure(
        vocabulary_sizes, failure_flags, retrieval_counts
    )
    adjusted_regression.update(
        conditional_vocabulary_permutation_test(
            vocabulary_sizes, failure_flags, retrieval_counts
        )
    )
    return {
        "corpus_lessons": len(corpus),
        "passing_lessons": len(passing),
        "failing_lessons": len(failing),
        "failing_corpus_fraction": len(failing) / len(corpus),
        "passing_mean_characters": mean(row["characters"] for row in passing),
        "failing_mean_characters": mean(row["characters"] for row in failing),
        "failing_to_passing_character_ratio": (
            mean(row["characters"] for row in failing) / mean(row["characters"] for row in passing)
        ),
        "passing_mean_words": mean(row["words"] for row in passing),
        "failing_mean_words": mean(row["words"] for row in failing),
        "passing_mean_index_vocabulary": mean(row["index_vocabulary"] for row in passing),
        "failing_mean_index_vocabulary": mean(row["index_vocabulary"] for row in failing),
        "failing_to_passing_index_vocabulary_ratio": (
            mean(row["index_vocabulary"] for row in failing)
            / mean(row["index_vocabulary"] for row in passing)
        ),
        "retrieval_slots": total_slots,
        "failing_retrieval_slots": failed_slots,
        "failing_retrieval_fraction": failed_slots / total_slots,
        "failing_mean_retrievals_per_lesson": mean(row["retrieval_count"] for row in failing),
        "passing_mean_retrievals_per_lesson": mean(row["retrieval_count"] for row in passing),
        "failing_lesson_task_selection_rate": failing_selection_rate,
        "passing_lesson_task_selection_rate": passing_selection_rate,
        "failure_to_passing_selection_rate_ratio": failing_selection_rate / passing_selection_rate,
        "failure_retrieval_enrichment": (
            (failed_slots / total_slots) / (len(failing) / len(corpus))
        ),
        "index_vocabulary_retrieval_pearson": pearson(vocabulary_sizes, retrieval_counts),
        "index_vocabulary_retrieval_spearman": spearman(vocabulary_sizes, retrieval_counts),
        "passing_index_vocabulary_retrieval_spearman": spearman(
            [float(row["index_vocabulary"]) for row in passing],
            [float(row["retrieval_count"]) for row in passing],
        ),
        "failing_index_vocabulary_retrieval_spearman": spearman(
            [float(row["index_vocabulary"]) for row in failing],
            [float(row["retrieval_count"]) for row in failing],
        ),
        "retrieval_on_index_vocabulary_and_failure_ols": adjusted_regression,
        "same_suite_retrieval_slots": same_suite,
        "same_repository_retrieval_slots": same_repo,
        "unique_lessons_retrieved": len(counts),
        "corpus_coverage_across_probe": len(counts) / len(corpus),
        "top_two_lessons": top_two,
        "top_two_retrieval_fraction": sum(count for _, count in top_two) / total_slots,
        "retrieval_hhi": hhi,
        "retrieval_effective_number_of_lessons": 1.0 / hhi if hhi else 0.0,
        "mechanism_note": (
            "The Pack ranks set overlap over suite, task id, title, scope, and trigger terms. "
            "Longer indexed vocabulary increases opportunities for overlap but does not add term-frequency weight."
        ),
    }


def development_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for approach in APPROACHES:
        selected = [row for row in rows if row["approach_id"] == approach]
        costs = [row["author_cost_usd"] for row in selected]
        requests = [row["author_requests"] for row in selected]
        output[approach] = {
            "records": len(selected),
            "accepted": sum(row["mutation_accepted"] is True for row in selected),
            "rejected": sum(row["mutation_accepted"] is False for row in selected),
            "score_passed": sum(row["score_passed"] is True for row in selected),
            "accepted_after_pass": sum(
                row["mutation_accepted"] is True and row["score_passed"] is True for row in selected
            ),
            "accepted_after_failure": sum(
                row["mutation_accepted"] is True and row["score_passed"] is False for row in selected
            ),
            "passing_tasks": sum(row["score_passed"] is True for row in selected),
            "failing_tasks": sum(row["score_passed"] is False for row in selected),
            "first_five_mean_author_cost": mean(costs[:5]),
            "last_five_mean_author_cost": mean(costs[-5:]),
            "first_five_mean_author_requests": mean(requests[:5]),
            "last_five_mean_author_requests": mean(requests[-5:]),
            "note": "Sequence is confounded with task identity and difficulty.",
        }
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Study artifact root (defaults to the parent of analysis/).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "generated",
    )
    args = parser.parse_args()
    run_root = args.run_root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    results = result_index(run_root)
    traces = build_trace_index(run_root, results)
    corpus = hybrid_corpus(run_root)
    retrievals = hybrid_retrievals(results, traces)
    profiles = [
        workspace_expression(run_root),
        minimal_expression(run_root),
        hybrid_expression(run_root, corpus, retrievals, traces),
    ]
    noise_tasks, task_level_noise, empirical_null_pairs, noise_summary = equivalent_control_analysis(
        results, traces
    )
    shams = sham_analysis(results, traces)
    behavior = behavior_mediation(results, traces)
    development = development_process(run_root)
    growth = state_growth(run_root)
    memory_summary = summarize_hybrid_memory(corpus, retrievals)
    retrieval_counterfactuals = hybrid_counterfactual_retrieval(corpus, results, traces)

    write_csv(output_dir / "expression-profile.csv", expression_table(profiles))
    write_csv(output_dir / "equivalent-control-tasks.csv", noise_tasks)
    write_csv(output_dir / "task-level-noise-and-evolved.csv", task_level_noise)
    write_csv(output_dir / "empirical-null-pairwise-deltas.csv", empirical_null_pairs)
    write_csv(output_dir / "sham-control.csv", shams)
    write_csv(output_dir / "behavior-mediation.csv", behavior)
    write_csv(output_dir / "hybrid-lesson-corpus.csv", corpus)
    write_csv(output_dir / "hybrid-retrieval-slots.csv", retrievals)
    write_csv(output_dir / "development-process.csv", development)
    write_csv(output_dir / "state-growth.csv", growth)

    summary = {
        "status": "exploratory_posthoc",
        "run_root": str(run_root),
        "source_dataset": "results-probe-adjudicated.jsonl",
        "source_dataset_sha256": hashlib.sha256(
            (run_root / "results-probe-adjudicated.jsonl").read_bytes()
        ).hexdigest(),
        "expression_profiles": [{key: value for key, value in row.items() if key != "visible_files"} for row in profiles],
        "equivalent_control_noise": noise_summary,
        "hybrid_memory": memory_summary,
        "hybrid_retrieval_counterfactuals": retrieval_counterfactuals,
        "development_process": development_summary(development),
        "generated_tables": sorted(path.name for path in output_dir.glob("*.csv")),
    }
    (output_dir / "posthoc-metrics.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
