#!/usr/bin/env python3
"""Run a portable research task through the minimal-v2 mutation interface."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from ouroboros import Config, ExampleCase, Ouroboros, load_env_file
from research.hybrid_author import ResearchTask, load_task, sha256_json, utc_now, write_json


def prepare_splits(
    task: ResearchTask, examples: list[ExampleCase]
) -> tuple[list[ExampleCase], list[ExampleCase]]:
    """Require minimal-v2's hidden split to equal the benchmark split exactly."""

    training, heldout = Ouroboros.split_examples(examples)
    public = [
        ExampleCase(input=case.payload, expected=case.expected)
        for case in task.public_cases
    ]
    private = [
        ExampleCase(input=case.payload, expected=case.expected)
        for case in task.private_cases
    ]
    def encode(rows: list[ExampleCase]) -> list[str]:
        return sorted(sha256_json(row.model_dump(mode="json")) for row in rows)
    if encode(training) != encode(public) or encode(heldout) != encode(private):
        raise ValueError(
            "minimal-v2's deterministic hash split does not match the task's public/private split"
        )
    return training, heldout


def _usage(events: list[Any]) -> dict[str, Any]:
    responses = [event for event in events if event.type == "llm.responded"]
    return {
        "requests": sum(event.type == "llm.requested" for event in events),
        "responses": len(responses),
        "input_tokens": sum(int(event.payload.get("input_tokens", 0) or 0) for event in responses),
        "output_tokens": sum(int(event.payload.get("output_tokens", 0) or 0) for event in responses),
        "estimated_cost_usd": str(
            sum((float(event.payload.get("cost_usd", 0) or 0) for event in responses), start=0.0)
        ),
        "models": sorted({str(event.payload.get("model", "")) for event in responses}),
    }


def run_minimal_task(
    task: ResearchTask,
    examples: list[ExampleCase],
    *,
    run_dir: str | Path,
    model: str,
    max_cost_usd: float,
) -> dict[str, Any]:
    root = Path(run_dir).resolve()
    if root.exists() and any(root.iterdir()):
        raise FileExistsError(f"run directory is not empty: {root}")
    root.mkdir(parents=True, exist_ok=True)
    training, heldout = prepare_splits(task, examples)
    private_payload = [case.model_dump(mode="json") for case in task.private_cases]
    transfer_payload = [case.model_dump(mode="json") for case in task.transfer_cases]
    author_goal = "\n\n".join(
        [task.objective, task.behavior_contract, "Constraints: " + "; ".join(task.constraints)]
    )
    write_json(
        root / "run.manifest.json",
        {
            "schema_version": 1,
            "approach": "minimal_v2_pure_capability",
            "task_id": task.id,
            "created_at": utc_now(),
            "budget": {"model": model, "max_cost_usd": max_cost_usd},
        },
    )
    write_json(
        root / "request.public.json",
        {
            "goal": author_goal,
            "training_examples": [case.model_dump(mode="json") for case in training],
            "heldout_count": len(heldout),
        },
    )
    write_json(
        root / "private_suite_receipt.json",
        {"sealed": True, "case_count": len(private_payload), "suite_hash": sha256_json(private_payload)},
    )
    write_json(
        root / "transfer_suite_receipt.json",
        {"sealed": True, "case_count": len(transfer_payload), "suite_hash": sha256_json(transfer_payload)},
    )

    config = Config(
        workspace=root / "workspace",
        state_dir=root / "organism",
        provider="openai",
        model=model,
        max_cost_usd=max_cost_usd,
    )
    organism = Ouroboros(config)
    started = time.monotonic()
    teach_result = organism.teach(author_goal, examples)
    elapsed = time.monotonic() - started
    author_events = list(organism.runtime.graph.events)
    with (root / "author.events.jsonl").open("w", encoding="utf-8") as handle:
        for event in author_events:
            handle.write(json.dumps(event.to_dict(), sort_keys=True, separators=(",", ":"), default=str) + "\n")
    write_json(root / "manager" / "private_cases.json", private_payload)
    write_json(root / "manager" / "transfer_cases.json", transfer_payload)

    result: dict[str, Any] = {
        "approach": "minimal_v2_pure_capability",
        "task_id": task.id,
        "teach": teach_result,
        "author": {
            "model": model,
            "elapsed_seconds": round(elapsed, 6),
            "usage": _usage(author_events),
        },
        "organism_before_restart": organism.summary(),
        "artifacts": {
            "trace": "organism/trace.sqlite",
            "author_events": "author.events.jsonl",
            "private_cases": "manager/private_cases.json",
            "transfer_cases": "manager/transfer_cases.json"
        },
    }
    if teach_result.get("promoted"):
        restarted = Ouroboros(config)
        capability_name = str(teach_result["capability_name"])
        rows: list[dict[str, Any]] = []
        for case in task.transfer_cases:
            invoked = restarted.host.invoke_capability(capability_name, case.payload)
            actual = invoked.data.get("result") if invoked.ok else None
            rows.append(
                {
                    "id": case.id,
                    "passed": invoked.ok and actual == case.expected,
                    "actual": actual,
                    "expected": case.expected,
                    "error": "" if invoked.ok else invoked.message,
                }
            )
        result["organism_after_restart"] = restarted.summary()
        result["transfer"] = {
            "passed": sum(row["passed"] for row in rows),
            "total": len(rows),
            "all_passed": all(row["passed"] for row in rows),
            "rows": rows,
        }
    result["research_success"] = bool(
        teach_result.get("promoted") and result.get("transfer", {}).get("all_passed")
    )
    write_json(root / "result.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--examples", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--max-cost-usd", type=float, default=10.0)
    args = parser.parse_args(argv)
    load_env_file(Path(".env"))
    raw_examples = json.loads(args.examples.read_text(encoding="utf-8"))
    examples = [ExampleCase.model_validate(item) for item in raw_examples]
    result = run_minimal_task(
        load_task(args.task),
        examples,
        run_dir=args.run_dir,
        model=args.model,
        max_cost_usd=args.max_cost_usd,
    )
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result["research_success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
