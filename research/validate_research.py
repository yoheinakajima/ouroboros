#!/usr/bin/env python3
"""Validate the benchmark catalog and recorded-run evidence without model calls."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from research.hybrid_author import load_task

_CURATED_APPROACH_ALIASES = {
    "hybrid_docs_grounded_pack": "hybrid_packs",
    "minimal_v2_pure_capability": "minimal_v2",
}
_SCORE_PATTERN = re.compile(r"(0|[1-9][0-9]*)/([1-9][0-9]*)\Z")
_SOURCE_HASH_PATTERN = re.compile(r"sha256:[0-9a-f]{64}\Z")


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_json(value: Any) -> str:
    return _sha256_text(_canonical(value))


def _sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _require_path(
    root: Path,
    raw: str | None,
    label: str,
    *,
    allow_missing: bool = False,
) -> Path | None:
    if raw is None:
        return None
    path = (root / raw).resolve()
    if root not in path.parents:
        raise ValueError(f"{label} is missing or escapes the repository: {raw}")
    if not path.is_file():
        if allow_missing:
            return None
        raise ValueError(f"{label} is missing or escapes the repository: {raw}")
    return path


def _validate_hybrid_run(result_path: Path) -> dict[str, Any]:
    run_root = result_path.parent
    result = _read_json(result_path)
    if result.get("approach") != "hybrid_docs_grounded_pack":
        raise ValueError(f"unexpected approach in {result_path}")
    if not result.get("research_success"):
        raise ValueError(f"indexed valid hybrid run is not successful: {result_path}")

    artifacts = result.get("artifacts", {})
    private_cases = _read_json(run_root / artifacts.get("private_cases", "manager/private_cases.json"))
    transfer_cases = _read_json(run_root / artifacts.get("transfer_cases", "manager/transfer_cases.json"))
    private_receipt = _read_json(run_root / artifacts.get("private_suite_receipt", "private_suite_receipt.json"))
    transfer_receipt = _read_json(run_root / artifacts.get("transfer_suite_receipt", "transfer_suite_receipt.json"))
    if private_receipt["suite_hash"] != _sha256_json(private_cases):
        raise ValueError(f"private-suite hash mismatch: {result_path}")
    if transfer_receipt["suite_hash"] != _sha256_json(transfer_cases):
        raise ValueError(f"transfer-suite hash mismatch: {result_path}")

    author_root = (run_root / artifacts.get("proposal", "proposal.json")).parent
    corpus = (author_root / "docs" / "corpus.md").read_text(encoding="utf-8")
    docs_index = _read_json(author_root / "docs" / "index.json")
    if docs_index["corpus_hash"] != _sha256_text(corpus):
        raise ValueError(f"documentation corpus hash mismatch: {result_path}")

    author_surface = "\n".join(
        (author_root / relative).read_text(encoding="utf-8")
        for relative in ("request.public.json", "author.events.jsonl", "proposal.json")
    )
    hidden_ids = [case["id"] for case in private_cases + transfer_cases]
    leaked = [case_id for case_id in hidden_ids if case_id in author_surface]
    if leaked:
        raise ValueError(f"hidden case ids leaked into author surface: {leaked}")

    public_score = result["evolution"]["public_candidate"]
    private_score = result["evolution"]["private_candidate"]
    transfer = result["transfer"]
    return {
        "approach": result["approach"],
        "task_id": result["task_id"],
        "public": public_score,
        "private": private_score,
        "transfer": f"{transfer['passed']}/{transfer['total']}",
        "cost_usd": result["author"]["usage"]["estimated_cost_usd"],
        "model": result["author"]["model"],
    }


def _validate_minimal_run(result_path: Path) -> dict[str, Any]:
    run_root = result_path.parent
    result = _read_json(result_path)
    if result.get("approach") != "minimal_v2_pure_capability" or not result.get("research_success"):
        raise ValueError(f"indexed valid minimal run is not successful: {result_path}")
    private_cases = _read_json(run_root / "manager" / "private_cases.json")
    transfer_cases = _read_json(run_root / "manager" / "transfer_cases.json")
    private_receipt = _read_json(run_root / "private_suite_receipt.json")
    transfer_receipt = _read_json(run_root / "transfer_suite_receipt.json")
    if private_receipt["suite_hash"] != _sha256_json(private_cases):
        raise ValueError(f"minimal private-suite hash mismatch: {result_path}")
    if transfer_receipt["suite_hash"] != _sha256_json(transfer_cases):
        raise ValueError(f"minimal transfer-suite hash mismatch: {result_path}")
    author_surface = "\n".join(
        (run_root / relative).read_text(encoding="utf-8")
        for relative in ("request.public.json", "author.events.jsonl")
    )
    hidden_ids = [case["id"] for case in private_cases + transfer_cases]
    leaked = [case_id for case_id in hidden_ids if case_id in author_surface]
    if leaked:
        raise ValueError(f"minimal hidden case ids leaked into author surface: {leaked}")
    transfer = result["transfer"]
    return {
        "approach": result["approach"],
        "task_id": result["task_id"],
        "public": f"{result['teach']['training_count']}/{result['teach']['training_count']}",
        "private": f"{result['teach']['heldout_count']}/{result['teach']['heldout_count']}",
        "transfer": f"{transfer['passed']}/{transfer['total']}",
        "cost_usd": result["author"]["usage"]["estimated_cost_usd"],
        "model": result["author"]["model"],
    }


def _validate_score(value: Any, *, run_id: str, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"curated run {run_id} has invalid {field} score: {value!r}")
    match = _SCORE_PATTERN.fullmatch(value)
    if match is None or int(match.group(1)) > int(match.group(2)):
        raise ValueError(f"curated run {run_id} has invalid {field} score: {value!r}")
    return value


def _validate_cost(value: Any, *, run_id: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError(f"curated run {run_id} has invalid cost_usd: {value!r}")
    try:
        cost = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"curated run {run_id} has invalid cost_usd: {value!r}") from exc
    if not cost.is_finite() or cost < 0:
        raise ValueError(f"curated run {run_id} has invalid cost_usd: {value!r}")
    return cost


def _validate_curated_run(
    index_row: dict[str, Any],
    curated_row: dict[str, Any] | None,
    primary_model: Any,
    *,
    raw_row: dict[str, Any] | None = None,
    raw_result_path: Path | None = None,
) -> dict[str, Any]:
    """Validate and normalize one public summary row, reconciling raw evidence when present."""

    run_id = index_row["id"]
    if curated_row is None:
        raise ValueError(f"valid indexed run is absent from curated evidence: {run_id}")
    if curated_row.get("id") != run_id:
        raise ValueError(f"run-index/curated id mismatch for {run_id}")
    if not isinstance(index_row.get("result"), str) or not index_row["result"]:
        raise ValueError(f"valid indexed run has no result path: {run_id}")

    expected_approach = _CURATED_APPROACH_ALIASES.get(index_row.get("approach"))
    if expected_approach is None or curated_row.get("approach") != expected_approach:
        raise ValueError(f"run-index/curated approach mismatch for {run_id}")
    if curated_row.get("task") != index_row.get("task"):
        raise ValueError(f"run-index/curated task mismatch for {run_id}")
    if not isinstance(primary_model, str) or not primary_model.strip():
        raise ValueError("curated evidence primary_model must be a non-empty string")

    public = _validate_score(curated_row.get("public"), run_id=run_id, field="public")
    private = _validate_score(curated_row.get("private"), run_id=run_id, field="private")
    transfer = _validate_score(curated_row.get("transfer"), run_id=run_id, field="transfer")
    cost = _validate_cost(curated_row.get("cost_usd"), run_id=run_id)
    source_hash = curated_row.get("source_result_sha256")
    if not isinstance(source_hash, str) or _SOURCE_HASH_PATTERN.fullmatch(source_hash) is None:
        raise ValueError(f"curated run {run_id} has invalid source_result_sha256: {source_hash!r}")

    normalized = {
        "approach": index_row["approach"],
        "task_id": index_row["task"],
        "public": public,
        "private": private,
        "transfer": transfer,
        "cost_usd": curated_row["cost_usd"],
        "model": primary_model,
        "source_result_sha256": source_hash,
    }
    if raw_row is None:
        if raw_result_path is not None:
            raise ValueError(f"internal raw-evidence reconciliation error for {run_id}")
        return normalized
    if raw_result_path is None:
        raise ValueError(f"internal raw-evidence reconciliation error for {run_id}")

    actual_hash = _sha256_file(raw_result_path)
    if actual_hash != source_hash:
        raise ValueError(
            f"raw-result hash mismatch for {run_id}: expected {source_hash}, got {actual_hash}"
        )
    comparisons = {
        "approach": (raw_row.get("approach"), normalized["approach"]),
        "task_id": (raw_row.get("task_id"), normalized["task_id"]),
        "public": (raw_row.get("public"), normalized["public"]),
        "private": (raw_row.get("private"), normalized["private"]),
        "transfer": (raw_row.get("transfer"), normalized["transfer"]),
        "model": (raw_row.get("model"), normalized["model"]),
    }
    for field, (actual, expected) in comparisons.items():
        if actual != expected:
            raise ValueError(
                f"raw-result/curated {field} mismatch for {run_id}: expected {expected!r}, got {actual!r}"
            )
    raw_cost = _validate_cost(raw_row.get("cost_usd"), run_id=run_id)
    if raw_cost != cost:
        raise ValueError(
            f"raw-result/curated cost_usd mismatch for {run_id}: "
            f"expected {curated_row['cost_usd']!r}, got {raw_row.get('cost_usd')!r}"
        )
    return normalized


def validate_repository(root: str | Path) -> dict[str, Any]:
    repository = Path(root).resolve()
    benchmark = _read_json(repository / "research" / "benchmark.json")
    task_ids = [item["id"] for item in benchmark["tasks"]]
    if len(task_ids) != len(set(task_ids)):
        raise ValueError("benchmark task ids must be unique")
    implemented: list[str] = []
    for item in benchmark["tasks"]:
        task_file = item.get("task_file")
        if item["status"] == "implemented" and not task_file:
            raise ValueError(f"implemented task has no task_file: {item['id']}")
        if task_file:
            path = _require_path(repository, task_file, f"task {item['id']}")
            task = load_task(path)
            if task.id != item["id"]:
                raise ValueError(f"catalog/task id mismatch for {item['id']}")
            implemented.append(task.id)

    run_index = _read_json(repository / "research" / "run_index.json")
    curated_path = _require_path(repository, run_index.get("curated_summary"), "curated summary")
    curated = _read_json(curated_path) if curated_path else {}
    if curated.get("status") != "pilot_mechanism_evidence":
        raise ValueError("curated evidence must identify itself as pilot mechanism evidence")
    if curated.get("primary_model") != benchmark.get("primary_model"):
        raise ValueError("benchmark/curated primary_model mismatch")
    curated_ids = [item["id"] for item in curated.get("runs", [])]
    if len(curated_ids) != len(set(curated_ids)):
        raise ValueError("curated evidence run ids must be unique")
    curated_by_id = {item["id"]: item for item in curated.get("runs", [])}
    run_ids = [item["id"] for item in run_index["runs"]]
    if len(run_ids) != len(set(run_ids)):
        raise ValueError("run index ids must be unique")
    hybrid_rows: list[dict[str, Any]] = []
    portable_rows: list[dict[str, Any]] = []
    for item in run_index["runs"]:
        result_path = _require_path(
            repository,
            item.get("result"),
            f"run {item['id']} result",
            allow_missing=run_index.get("raw_artifacts") == "local_or_tagged_release_assets",
        )
        _require_path(repository, item.get("evidence"), f"run {item['id']} evidence")
        if item["validity"] == "valid_graph_audited_pilot":
            if result_path is None:
                hybrid_rows.append(
                    _validate_curated_run(item, curated_by_id.get(item["id"]), curated.get("primary_model"))
                )
            else:
                raw_row = _validate_hybrid_run(result_path)
                hybrid_rows.append(
                    _validate_curated_run(
                        item,
                        curated_by_id.get(item["id"]),
                        curated.get("primary_model"),
                        raw_row=raw_row,
                        raw_result_path=result_path,
                    )
                )
        elif item["validity"] == "valid_portable_pilot":
            if result_path is None:
                portable_rows.append(
                    _validate_curated_run(item, curated_by_id.get(item["id"]), curated.get("primary_model"))
                )
            else:
                if item["approach"] == "hybrid_docs_grounded_pack":
                    raw_row = _validate_hybrid_run(result_path)
                elif item["approach"] == "minimal_v2_pure_capability":
                    raw_row = _validate_minimal_run(result_path)
                else:
                    raise ValueError(f"unknown portable approach: {item['approach']}")
                portable_rows.append(
                    _validate_curated_run(
                        item,
                        curated_by_id.get(item["id"]),
                        curated.get("primary_model"),
                        raw_row=raw_row,
                        raw_result_path=result_path,
                    )
                )

    return {
        "benchmark_tasks": len(task_ids),
        "implemented_tasks": implemented,
        "indexed_runs": len(run_ids),
        "curated_evidence_runs": len(curated_ids),
        "valid_graph_audited_hybrid_runs": hybrid_rows,
        "valid_portable_runs": portable_rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    print(json.dumps(validate_repository(args.root), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
