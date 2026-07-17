"""Self-contained evaluator for the locally owned ActiveGraph-50 tasks.

This module is copied into public and sealed task workspaces.  It deliberately
has no import from the Ouroboros research harness so the same bytes run inside
the pinned benchmark container.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

from activegraph import Event, Graph, Runtime
from activegraph.packs import Pack

REQUEST_EVENT = "ouro.benchmark.requested"
RESULT_EVENT = "ouro.benchmark.completed"


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def load_candidate(root: str | Path) -> Pack:
    package = Path(root).resolve() / "candidate_pack"
    source = package / "__init__.py"
    if not source.is_file():
        raise FileNotFoundError("submission must contain candidate_pack/__init__.py")
    module_name = "_ouro_activegraph_candidate_" + uuid.uuid4().hex
    spec = importlib.util.spec_from_file_location(module_name, source, submodule_search_locations=[str(package)])
    if spec is None or spec.loader is None:
        raise RuntimeError("candidate pack could not be imported")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(module_name, None)
    packs = [value for value in vars(module).values() if isinstance(value, Pack)]
    unique = {id(value): value for value in packs}
    if len(unique) != 1:
        raise ValueError("candidate module must expose exactly one ActiveGraph Pack")
    return next(iter(unique.values()))


def surface_gate(pack: Pack, contract: dict[str, Any]) -> dict[str, Any]:
    actual_objects = sorted(item.name for item in pack.object_types)
    actual_relations = sorted(item.name for item in pack.relation_types)
    expected_objects = sorted(contract["object_keys"])
    expected_relations = sorted(contract["relation_types"])
    schema_fields = {item.name: sorted(item.schema.model_fields) for item in pack.object_types}
    relation_endpoints = {
        item.name: {
            "source_types": sorted(item.source_types),
            "target_types": sorted(item.target_types),
        }
        for item in pack.relation_types
    }
    expected_fields = {name: sorted(fields) for name, fields in contract["object_fields"].items()}
    actual_field_types: dict[str, dict[str, str]] = {}
    for item in pack.object_types:
        properties = item.schema.model_json_schema().get("properties", {})
        rows: dict[str, str] = {}
        for field_name, schema in properties.items():
            kind = str(schema.get("type", ""))
            if kind == "array" and schema.get("items", {}).get("type") == "string":
                kind = "string_array"
            rows[field_name] = kind
        actual_field_types[item.name] = rows
    expected_endpoints = {
        name: {
            "source_types": sorted(spec["source_types"]),
            "target_types": sorted(spec["target_types"]),
        }
        for name, spec in contract["relation_types"].items()
    }
    deterministic = (
        bool(pack.behaviors)
        and not pack.tools
        and not pack.prompts
        and not any("llm" in type(item).__name__.lower() for item in pack.behaviors)
    )
    checks = {
        "pack_name": pack.name == contract["pack_name"],
        "object_types": actual_objects == expected_objects,
        "object_schema_fields": schema_fields == expected_fields,
        "object_schema_types": actual_field_types == contract["object_field_types"],
        "relation_types": actual_relations == expected_relations,
        "relation_endpoints": relation_endpoints == expected_endpoints,
        "deterministic_surface": deterministic,
    }
    return {"passed": all(checks.values()), "checks": checks}


def _emit(graph: Graph, payload: dict[str, Any]) -> None:
    graph.emit(
        Event(
            id=graph.ids.event(),
            type=REQUEST_EVENT,
            payload=payload,
            actor="sealed_grader",
            timestamp=graph.clock.now(),
        )
    )


def _logical_object(item: Any, object_keys: dict[str, str]) -> dict[str, Any]:
    key_field = object_keys.get(item.type)
    if key_field is None or key_field not in item.data:
        logical_key = f"<unrecognized:{item.id}>"
    else:
        logical_key = item.data[key_field]
    return {
        "type": item.type,
        "key": logical_key,
        "data": item.data,
        "version": item.version,
    }


def graph_snapshot(graph: Graph, contract: dict[str, Any]) -> dict[str, Any]:
    object_keys = contract["object_keys"]
    objects = [_logical_object(item, object_keys) for item in graph.all_objects()]
    objects.sort(key=lambda row: (row["type"], canonical_json(row["key"])))
    by_id = {item.id: _logical_object(item, object_keys) for item in graph.all_objects()}
    relations: list[dict[str, Any]] = []
    for item in graph.all_relations():
        source = by_id.get(item.source, {"type": "<missing>", "key": item.source})
        target = by_id.get(item.target, {"type": "<missing>", "key": item.target})
        relations.append(
            {
                "type": item.type,
                "source": [source["type"], source["key"]],
                "target": [target["type"], target["key"]],
                "data": item.data,
            }
        )
    relations.sort(key=canonical_json)
    return {"objects": objects, "relations": relations}


def _new_runtime(pack: Pack, database: Path, run_id: str) -> Runtime:
    runtime = Runtime(
        Graph(run_id=run_id),
        behaviors=[],
        persist_to=str(database),
        budget={"max_events": 20_000, "max_behavior_calls": 5_000},
    )
    runtime.load_pack(pack)
    return runtime


def _reload_runtime(pack: Pack, database: Path, run_id: str) -> Runtime:
    runtime = Runtime.load(str(database), run_id=run_id, behaviors=[])
    runtime.load_pack(pack)
    return runtime


def evaluate(
    *,
    submission: str | Path,
    contract: dict[str, Any],
    cases: list[dict[str, Any]],
    public_only: bool = False,
) -> dict[str, Any]:
    pack = load_candidate(submission)
    gate = surface_gate(pack, contract)
    selected = [row for row in cases if row["visibility"] == "public"] if public_only else cases
    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="ouro-activegraph-eval-") as temporary:
        temporary_root = Path(temporary)
        for split in ("public", "private", "transfer"):
            split_cases = [row for row in selected if row["split"] == split]
            if not split_cases:
                continue
            database = temporary_root / f"{split}.db"
            run_id = f"{contract['task_id']}_{split}_{uuid.uuid4().hex}"
            runtime = _new_runtime(pack, database, run_id)
            restart_after = int(contract.get("restart_after", {}).get(split, 0))
            for index, case in enumerate(split_cases, start=1):
                if restart_after and index == restart_after + 1:
                    runtime.save_state()
                    runtime = _reload_runtime(pack, database, run_id)
                start = len(runtime.graph.events)
                payload = dict(case["payload"])
                payload["request_id"] = uuid.uuid4().hex
                _emit(runtime.graph, payload)
                runtime.run_until_idle()
                outputs = [
                    event.payload.get("output")
                    for event in runtime.graph.events[start:]
                    if event.type == RESULT_EVENT and event.payload.get("request_id") == payload["request_id"]
                ]
                output_passed = len(outputs) == 1 and outputs[0] == case["expected"]
                snapshot_passed = True
                if case.get("expected_snapshot") is not None:
                    snapshot_passed = graph_snapshot(runtime.graph, contract) == case["expected_snapshot"]
                failures = [event for event in runtime.graph.events[start:] if event.type == "behavior.failed"]
                passed = output_passed and snapshot_passed and not failures
                rows.append(
                    {
                        "id": case["id"],
                        "split": split,
                        "visibility": case["visibility"],
                        "category": case["category"],
                        "passed": passed,
                        "output_passed": output_passed,
                        "snapshot_passed": snapshot_passed,
                        "result_count": len(outputs),
                        "behavior_failures": len(failures),
                    }
                )
    category_scores: dict[str, dict[str, int]] = {}
    for row in rows:
        score = category_scores.setdefault(row["category"], {"passed": 0, "total": 0})
        score["total"] += 1
        score["passed"] += int(row["passed"])
    raw_passed = sum(int(row["passed"]) for row in rows)
    hard_gate_passed = bool(gate["passed"])
    score = raw_passed if hard_gate_passed else 0
    return {
        "task_id": contract["task_id"],
        "score": score,
        "raw_checks_passed": raw_passed,
        "total": len(rows),
        "passed": score == len(rows),
        "hard_gate": gate,
        "categories": category_scores,
        "rows": rows,
    }


def run_cli(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--public-only", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = evaluate(
        submission=args.submission,
        contract=json.loads(args.contract.read_text(encoding="utf-8")),
        cases=json.loads(args.cases.read_text(encoding="utf-8")),
        public_only=args.public_only,
    )
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(run_cli())
