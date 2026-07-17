#!/usr/bin/env python3
"""Validate the benchmark catalog and recorded-run evidence without model calls."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from research.hybrid_author import load_task


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_json(value: Any) -> str:
    return _sha256_text(_canonical(value))


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
    curated_ids = [item["id"] for item in curated.get("runs", [])]
    if len(curated_ids) != len(set(curated_ids)):
        raise ValueError("curated evidence run ids must be unique")
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
                raise ValueError(f"graph-audited run lacks result: {item['id']}")
            hybrid_rows.append(_validate_hybrid_run(result_path))
        elif item["validity"] == "valid_portable_pilot":
            if result_path is None:
                raise ValueError(f"portable run lacks result: {item['id']}")
            if item["approach"] == "hybrid_docs_grounded_pack":
                portable_rows.append(_validate_hybrid_run(result_path))
            elif item["approach"] == "minimal_v2_pure_capability":
                portable_rows.append(_validate_minimal_run(result_path))
            else:
                raise ValueError(f"unknown portable approach: {item['approach']}")

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
