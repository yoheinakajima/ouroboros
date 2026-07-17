#!/usr/bin/env python3
"""Documentation-grounded LLM author for governed ActiveGraph pack evolution.

The author is allowed to *propose* complete pack source. It is never release
authority: ``HybridOuroboros`` still applies the static membrane, manager-
private trials, incumbent comparison, byte pinning, and adoption decision.
Every run saves the exact public request, documentation snapshot, LLM trace,
proposal, private-suite receipt, evaluation, and organism state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from activegraph import Graph, Runtime, llm_behavior
from activegraph.llm import AnthropicProvider, OpenAIProvider
from pydantic import BaseModel, Field, model_validator

from experiments.hybrid_ouroboros import (
    Case,
    HybridOuroboros,
    PackDraft,
    ReleasePolicy,
    evaluate_graph_assertions,
)

DEFAULT_ACTIVEGRAPH_DOCS = Path(
    os.environ.get(
        "ACTIVEGRAPH_DOCS_ROOT",
        str(Path(__file__).resolve().parents[2] / "activegraph" / "docs"),
    )
)
DEFAULT_DOC_PATHS = (
    "guides/authoring-packs.md",
    "concepts/behaviors.md",
    "concepts/graph.md",
    "concepts/type-system.md",
    "concepts/relations.md",
    "concepts/policies.md",
    "concepts/patterns.md",
    "cookbook/common-patterns.md",
    "guides/fork-test-promote.md",
    "reference/api/packs.md",
    "reference/api/runtime.md",
    "reference/api/sandbox.md",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_text(canonical_json(value))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_env_file(path: Path) -> list[str]:
    """Load names from a small dotenv subset without exposing values."""

    loaded: list[str] = []
    if not path.is_file():
        return loaded
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        name, separator, value = line.partition("=")
        name = name.strip()
        if not separator or not name.replace("_", "a").isalnum() or name[0].isdigit():
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if name not in os.environ:
            os.environ[name] = value
            loaded.append(name)
    return loaded


class BehaviorCase(BaseModel):
    id: str
    payload: dict[str, Any]
    expected: Any
    expected_graph: dict[str, Any] | None = None

    def core_case(self) -> Case:
        return Case(self.id, dict(self.payload), self.expected, self.expected_graph)


class ResearchTask(BaseModel):
    id: str
    title: str
    category: str
    objective: str
    behavior_contract: str
    constraints: list[str] = Field(default_factory=list)
    public_cases: list[BehaviorCase]
    private_cases: list[BehaviorCase]
    transfer_cases: list[BehaviorCase] = Field(default_factory=list)

    def author_view(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "objective": self.objective,
            "behavior_contract": self.behavior_contract,
            "constraints": self.constraints,
            "public_cases": [case.model_dump(mode="json") for case in self.public_cases],
            "case_execution": (
                "Public cases execute in listed order in one fresh ActiveGraph runtime. "
                "Manager-private cases execute in a different fresh runtime and are not shown."
            ),
        }


class PackProposal(BaseModel):
    """Structured source bundle returned by the model author."""

    name: str = Field(description="Lowercase ActiveGraph pack identifier.")
    version: str = Field(default="1.0.0")
    description: str
    files: dict[str, str] = Field(description="Complete UTF-8 pack files; __init__.py is required.")
    behaviors: list[str]
    object_types: list[str] = Field(default_factory=list)
    relation_types: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    settings_schema: str = ""
    capabilities: list[dict[str, str]] = Field(
        default_factory=list,
        description=(
            "External provider authorities only, never summaries of event behavior. "
            "Keep empty unless the task explicitly authorizes an external capability; "
            "authorized rows require provider, capability, risk_class, and credential_ref."
        ),
    )
    design_summary: str
    documentation_used: list[str] = Field(default_factory=list)

    def draft(self) -> PackDraft:
        # ActiveGraph's manifest surface represents the shipped EmptySettings
        # sentinel as no named settings schema. Python source may still use
        # ``settings_schema=EmptySettings`` on the Pack itself.
        manifest_settings = "" if self.settings_schema in {"", "EmptySettings"} else self.settings_schema
        return PackDraft(
            name=self.name,
            version=self.version,
            description=self.description,
            files=dict(self.files),
            behaviors=tuple(self.behaviors),
            object_types=tuple(self.object_types),
            relation_types=tuple(self.relation_types),
            tools=tuple(self.tools),
            settings_schema=manifest_settings,
            capabilities=tuple(dict(item) for item in self.capabilities),
        )


class PackSetProposal(BaseModel):
    """One architecture-level mutation containing one or more composed Packs."""

    packs: list[PackProposal] = Field(min_length=1, max_length=6)
    design_summary: str
    documentation_used: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_names(self) -> "PackSetProposal":
        names = [pack.name for pack in self.packs]
        if len(set(names)) != len(names):
            raise ValueError("a Pack set may not contain duplicate names")
        return self

    def drafts(self) -> tuple[PackDraft, ...]:
        return tuple(pack.draft() for pack in self.packs)


class ResearchBudget(BaseModel):
    """Deliberately generous per-run ceiling; the recorder makes spend visible."""

    model: str = "gpt-5.6-sol"
    max_cost_usd: float = 30.0
    max_llm_calls: int = 12
    max_output_tokens: int = 40_000
    author_timeout_seconds: float = 900.0
    trial_timeout_seconds: float = 90.0
    max_events: int = 10_000
    max_behavior_calls: int = 2_000
    max_author_attempts: int = Field(default=4, ge=1, le=10)


@dataclass(frozen=True)
class DocumentationCorpus:
    root: str
    repository_commit: str
    corpus_hash: str
    character_count: int
    documents: tuple[dict[str, Any], ...]
    rendered: str

    def index(self) -> dict[str, Any]:
        return {
            "root": self.root,
            "repository_commit": self.repository_commit,
            "corpus_hash": self.corpus_hash,
            "character_count": self.character_count,
            "documents": list(self.documents),
        }


def _git_commit_for_docs(docs_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(docs_root.parent), "rev-parse", "HEAD"],
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def build_documentation_corpus(
    docs_root: str | Path,
    *,
    paths: tuple[str, ...] = DEFAULT_DOC_PATHS,
    max_characters: int = 120_000,
) -> DocumentationCorpus:
    root = Path(docs_root).resolve()
    rendered_parts: list[str] = []
    records: list[dict[str, Any]] = []
    total = 0
    for relative in paths:
        path = (root / relative).resolve()
        if root not in path.parents or not path.is_file():
            raise FileNotFoundError(f"ActiveGraph documentation missing: {relative}")
        text = path.read_text(encoding="utf-8")
        addition = f"\n\n===== ACTIVEGRAPH DOC: {relative} =====\n\n{text}"
        if total + len(addition) > max_characters:
            raise ValueError(
                f"documentation corpus exceeds {max_characters} characters at {relative}; "
                "choose an explicit smaller corpus rather than silently truncating"
            )
        rendered_parts.append(addition)
        total += len(addition)
        records.append({"path": relative, "characters": len(text), "sha256": sha256_text(text)})
    rendered = "".join(rendered_parts).lstrip()
    return DocumentationCorpus(
        root=str(root),
        repository_commit=_git_commit_for_docs(root),
        corpus_hash=sha256_text(rendered),
        character_count=len(rendered),
        documents=tuple(records),
        rendered=rendered,
    )


def pack_author_prompt(
    task: ResearchTask,
    corpus: DocumentationCorpus,
    *,
    repair_feedback: tuple[str, ...] = (),
) -> str:
    task_json = json.dumps(task.author_view(), indent=2, sort_keys=True, ensure_ascii=False)
    feedback = ""
    if repair_feedback:
        rendered = "\n".join(f"- {item}" for item in repair_feedback)
        feedback = f"""

MANAGER FEEDBACK FROM THE PRIOR REJECTED PROPOSAL
{rendered}

Repair the proposal using only this feedback and the public task. A private
suite exists, but its exact cases and failure details remain sealed. Do not
guess or request them.
"""
    return f"""You are the implementation author inside a governed recursive-improvement experiment.

Your job is to return a COMPLETE, IMPORTABLE SET of one to six ActiveGraph Pack source bundles for the public task
below. Use one Pack when one coherent behavior domain is enough. Use multiple Packs when independently meaningful
event-driven components, typed domains, or policies need to compose. The entire set is trialed and adopted atomically.
You may author real event-driven behaviors, typed graph objects, relations, settings, prompts, and policies.
Use the supplied ActiveGraph documentation as the API authority. Do not rely on remembered APIs when the
documentation gives an exact contract.

AUTHORITY BOUNDARY
- You only propose source. Deterministic manager code decides whether it is imported, trialed, or adopted.
- Use pack-aware decorators from activegraph.packs, never global decorators from activegraph.
- The manager generates manifest.toml. Do not include it in files.
- No filesystem, network, subprocess, environment, clock, randomness, dynamic execution, reflection, or secrets.
- No Python or pack dependencies beyond activegraph and pydantic.
- Do not request tools or external capabilities unless the task explicitly requires them.
- The output capabilities field declares external provider authority, not event input/output behavior; keep it empty
  for every current benchmark task.
- Behavior bodies must be deterministic and store durable state in the ActiveGraph graph, never module globals.
- Inside a behavior, read existing state with ctx.view.objects(type=...) and filter Object.data fields in Python;
  the behavior graph argument is the write surface. A View ``where`` path would be ``data.<field>``, not ``<field>``.
- Every source bundle must export exactly one module-level Pack whose name/version/description and declared surface
  exactly match that bundle's output.
- Packs in the proposed set may compose through explicit ActiveGraph events. Do not use imports between proposal
  bundles or hidden module-global coupling.
- If the Python Pack uses ActiveGraph's EmptySettings sentinel, return settings_schema as an empty string because
  the manager manifest represents EmptySettings as no named schema.
- Prefer a compact __init__.py unless multiple files materially clarify the behavior.
- Every response to hybrid.task.requested must preserve event.payload.request_id in hybrid.task.completed.
- Public expected_graph checks are normative: they inspect materialized
  objects, versions, and relations after each case.
- Public examples are evidence, not the complete specification. Generalize to unseen inputs and state sequences.

PUBLIC TASK
{task_json}

DOCUMENTATION SNAPSHOT
repository commit: {corpus.repository_commit or 'unavailable'}
corpus hash: {corpus.corpus_hash}
{corpus.rendered}
{feedback}
"""


def _event_json(event: Any) -> dict[str, Any]:
    return {
        "id": event.id,
        "type": event.type,
        "payload": event.payload,
        "actor": event.actor,
        "frame_id": event.frame_id,
        "caused_by": event.caused_by,
        "timestamp": event.timestamp,
    }


def _usage_summary(events: list[Any]) -> dict[str, Any]:
    requests = [event for event in events if event.type == "llm.requested"]
    responses = [event for event in events if event.type == "llm.responded"]
    input_tokens = 0
    output_tokens = 0
    cost = Decimal("0")
    models: list[str] = []
    for event in responses:
        payload = event.payload
        input_tokens += int(payload.get("input_tokens", 0) or 0)
        output_tokens += int(payload.get("output_tokens", 0) or 0)
        try:
            cost += Decimal(str(payload.get("cost_usd", "0") or "0"))
        except Exception:
            pass
        model = str(payload.get("model", ""))
        if model and model not in models:
            models.append(model)
    return {
        "requests": len(requests),
        "responses": len(responses),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost_usd": str(cost),
        "models": models,
    }


def author_pack(
    task: ResearchTask,
    *,
    docs_root: str | Path,
    run_dir: str | Path,
    provider: Any,
    budget: ResearchBudget,
    doc_paths: tuple[str, ...] = DEFAULT_DOC_PATHS,
    repair_feedback: tuple[str, ...] = (),
) -> tuple[PackSetProposal, dict[str, Any]]:
    output_root = Path(run_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    corpus = build_documentation_corpus(docs_root, paths=doc_paths)
    private_payload = [case.model_dump(mode="json") for case in task.private_cases]
    transfer_payload = [case.model_dump(mode="json") for case in task.transfer_cases]
    public_request = task.author_view()
    write_json(output_root / "request.public.json", public_request)
    write_json(
        output_root / "private_suite_receipt.json",
        {"sealed": True, "case_count": len(private_payload), "suite_hash": sha256_json(private_payload)},
    )
    write_json(
        output_root / "transfer_suite_receipt.json",
        {"sealed": True, "case_count": len(transfer_payload), "suite_hash": sha256_json(transfer_payload)},
    )
    write_json(output_root / "docs" / "index.json", corpus.index())
    (output_root / "docs" / "corpus.md").write_text(corpus.rendered, encoding="utf-8")

    prompt = pack_author_prompt(task, corpus, repair_feedback=repair_feedback)

    @llm_behavior(
        name="research.hybrid_pack_author",
        on=["goal.created"],
        description=prompt,
        output_schema=PackSetProposal,
        model=budget.model,
        temperature=0.1,
        max_tokens=budget.max_output_tokens,
        timeout_seconds=budget.author_timeout_seconds,
        creates=["pack_draft"],
    )
    def pack_author(event: Any, graph: Any, ctx: Any, llm_output: PackSetProposal) -> None:
        graph.add_object("pack_draft", llm_output.model_dump(mode="json"))

    run_id = "hybrid_author_" + uuid.uuid4().hex
    runtime = Runtime(
        Graph(run_id=run_id),
        behaviors=[pack_author],
        persist_to=str(output_root / "author.trace.sqlite"),
        llm_provider=provider,
        budget={
            "max_cost_usd": budget.max_cost_usd,
            "max_llm_calls": budget.max_llm_calls,
            "max_events": budget.max_events,
            "max_behavior_calls": budget.max_behavior_calls,
            "max_seconds": budget.author_timeout_seconds + 30,
        },
    )
    started = time.monotonic()
    runtime.run_goal(task.objective, actor="research_manager")
    elapsed = time.monotonic() - started
    events = list(runtime.graph.events)
    with (output_root / "author.events.jsonl").open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(canonical_json(_event_json(event)) + "\n")
    drafts = runtime.graph.objects(type="pack_draft")
    failures = [
        {"behavior": failure.behavior, "reason": failure.reason, "message": failure.message}
        for failure in runtime.errors
    ]
    summary = {
        "run_id": run_id,
        "task_id": task.id,
        "started_at": utc_now(),
        "elapsed_seconds": round(elapsed, 6),
        "model": budget.model,
        "budget": budget.model_dump(mode="json"),
        "documentation": corpus.index(),
        "usage": _usage_summary(events),
        "event_count": len(events),
        "failures": failures,
        "status": "completed" if len(drafts) == 1 and not failures else "failed",
        "repair_feedback": list(repair_feedback),
    }
    write_json(output_root / "author.summary.json", summary)
    if len(drafts) != 1 or failures:
        raise RuntimeError(f"pack author failed: drafts={len(drafts)} failures={failures}")
    proposal = PackSetProposal.model_validate(drafts[0].data)
    write_json(output_root / "proposal.json", proposal.model_dump(mode="json"))
    # The exact private suite is manager evidence and is written only after the
    # model call has completed. It never enters the prompt or author trace.
    write_json(output_root / "manager" / "private_cases.json", private_payload)
    write_json(output_root / "manager" / "transfer_cases.json", transfer_payload)
    return proposal, summary


class _OpenAICompletionsProxy:
    def __init__(self, target: Any) -> None:
        self._target = target

    def create(self, **kwargs: Any) -> Any:
        model = str(kwargs.get("model", ""))
        if kwargs.get("tools") and model.startswith("gpt-5.6"):
            kwargs.setdefault("reasoning_effort", "none")
        return self._target.create(**kwargs)


class _OpenAIChatProxy:
    def __init__(self, target: Any) -> None:
        self._target = target
        self.completions = _OpenAICompletionsProxy(target.completions)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._target, name)


class _OpenAIClientProxy:
    def __init__(self, client: Any) -> None:
        self._client = client
        self.chat = _OpenAIChatProxy(client.chat)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)


def provider_for(name: str) -> Any:
    if name == "anthropic":
        return AnthropicProvider()
    if name != "openai":
        raise ValueError(f"unknown provider: {name}")
    from openai import OpenAI

    return OpenAIProvider(
        client=_OpenAIClientProxy(OpenAI()),
        pricing={
            "gpt-5.6-sol": {"input": "5", "output": "30"},
            "gpt-5.6-terra": {"input": "2.5", "output": "15"},
            "gpt-5.6-luna": {"input": "1", "output": "6"},
            "gpt-4o": {"input": "2.5", "output": "10"},
        },
    )


def author_evaluate_and_record(
    task: ResearchTask,
    *,
    docs_root: str | Path,
    run_dir: str | Path,
    provider: Any,
    budget: ResearchBudget,
    doc_paths: tuple[str, ...] = DEFAULT_DOC_PATHS,
) -> dict[str, Any]:
    root = Path(run_dir).resolve()
    write_json(
        root / "run.manifest.json",
        {
            "schema_version": 1,
            "approach": "hybrid_docs_grounded_pack",
            "task_id": task.id,
            "created_at": utc_now(),
            "budget": budget.model_dump(mode="json"),
        },
    )
    organism = HybridOuroboros(
        root / "organism",
        policy=ReleasePolicy(trial_timeout_seconds=budget.trial_timeout_seconds),
    )
    attempt_rows: list[dict[str, Any]] = []
    repair_feedback: tuple[str, ...] = ()
    total_cost = Decimal("0")
    total_requests = 0
    proposal: PackSetProposal | None = None
    report = None
    author_summary: dict[str, Any] = {}
    final_author_root = root
    for attempt_number in range(1, budget.max_author_attempts + 1):
        remaining_cost = max(0.0, budget.max_cost_usd - float(total_cost))
        remaining_calls = max(0, budget.max_llm_calls - total_requests)
        if remaining_cost <= 0 or remaining_calls <= 0:
            break
        attempt_root = root if attempt_number == 1 else root / "repair_attempts" / f"{attempt_number:03d}"
        attempt_budget = budget.model_copy(
            update={"max_cost_usd": remaining_cost, "max_llm_calls": remaining_calls}
        )
        proposal, author_summary = author_pack(
            task,
            docs_root=docs_root,
            run_dir=attempt_root,
            provider=provider,
            budget=attempt_budget,
            doc_paths=doc_paths,
            repair_feedback=repair_feedback,
        )
        usage = author_summary["usage"]
        total_cost += Decimal(str(usage["estimated_cost_usd"]))
        total_requests += int(usage["requests"])
        report = organism.evolve_set(
            objective=task.objective,
            drafts=proposal.drafts(),
            public_cases=(case.core_case() for case in task.public_cases),
            private_cases=(case.core_case() for case in task.private_cases),
        )
        attempt_rows.append(
            {
                "attempt": attempt_number,
                "author_root": attempt_root.relative_to(root).as_posix() or ".",
                "author": author_summary,
                "evolution": report.to_dict(),
            }
        )
        final_author_root = attempt_root
        if report.accepted:
            break
        repair_feedback = report.author_feedback
        if not repair_feedback:
            break
    if proposal is None or report is None:
        raise RuntimeError("author budget exhausted before a proposal could be evaluated")
    aggregate_author = dict(author_summary)
    aggregate_author["attempt_count"] = len(attempt_rows)
    aggregate_author["usage"] = {
        "requests": sum(int(row["author"]["usage"]["requests"]) for row in attempt_rows),
        "responses": sum(int(row["author"]["usage"]["responses"]) for row in attempt_rows),
        "input_tokens": sum(int(row["author"]["usage"]["input_tokens"]) for row in attempt_rows),
        "output_tokens": sum(int(row["author"]["usage"]["output_tokens"]) for row in attempt_rows),
        "estimated_cost_usd": str(total_cost),
        "models": sorted({model for row in attempt_rows for model in row["author"]["usage"]["models"]}),
    }
    write_json(root / "author.attempts.json", attempt_rows)
    final_prefix = final_author_root.relative_to(root).as_posix()
    artifact_prefix = "" if final_prefix == "." else final_prefix + "/"
    result = {
        "approach": "hybrid_docs_grounded_pack",
        "task_id": task.id,
        "accepted": report.accepted,
        "evolution": report.to_dict(),
        "author": aggregate_author,
        "author_attempts": attempt_rows,
        "proposal_design_summary": proposal.design_summary,
        "organism_before_restart": organism.identity(),
        "artifacts": {
            "author_trace": artifact_prefix + "author.trace.sqlite",
            "author_events": artifact_prefix + "author.events.jsonl",
            "proposal": artifact_prefix + "proposal.json",
            "private_suite_receipt": artifact_prefix + "private_suite_receipt.json",
            "private_cases": artifact_prefix + "manager/private_cases.json",
            "transfer_suite_receipt": artifact_prefix + "transfer_suite_receipt.json",
            "transfer_cases": artifact_prefix + "manager/transfer_cases.json",
            "author_attempts": "author.attempts.json",
            "organism": "organism/",
        },
    }
    if report.accepted:
        restarted = organism.restart()
        result["organism_after_restart"] = restarted.identity()
        transfer_rows: list[dict[str, Any]] = []
        for case in task.transfer_cases:
            try:
                actual = restarted.invoke(case.payload, actor="research_transfer")
                graph_evidence = evaluate_graph_assertions(restarted.runtime.graph, case.expected_graph)
                passed = actual == case.expected and graph_evidence["all_passed"]
                error = ""
            except Exception as exc:
                actual = None
                passed = False
                graph_evidence = {"all_passed": False, "checks": []}
                error = f"{type(exc).__name__}: {exc}"
            transfer_rows.append(
                {
                    "id": case.id,
                    "passed": passed,
                    "actual": actual,
                    "expected": case.expected,
                    "graph": graph_evidence,
                    "error": error,
                }
            )
        result["transfer"] = {
            "passed": sum(1 for row in transfer_rows if row["passed"]),
            "total": len(transfer_rows),
            "all_passed": all(row["passed"] for row in transfer_rows),
            "rows": transfer_rows,
        }
    result["research_success"] = bool(
        report.accepted and result.get("transfer", {}).get("all_passed", not task.transfer_cases)
    )
    write_json(root / "result.json", result)
    return result


def load_task(path: str | Path) -> ResearchTask:
    return ResearchTask.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--docs-root", type=Path, default=DEFAULT_ACTIVEGRAPH_DOCS)
    parser.add_argument("--provider", choices=("openai", "anthropic"), default="openai")
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--max-cost-usd", type=float, default=30.0)
    parser.add_argument("--max-llm-calls", type=int, default=12)
    parser.add_argument("--max-output-tokens", type=int, default=40_000)
    parser.add_argument("--max-events", type=int, default=10_000)
    parser.add_argument("--max-behavior-calls", type=int, default=2_000)
    parser.add_argument("--author-timeout", type=float, default=900.0)
    parser.add_argument("--trial-timeout", type=float, default=90.0)
    parser.add_argument("--max-author-attempts", type=int, default=4)
    args = parser.parse_args(argv)
    load_env_file(Path(".env"))
    budget = ResearchBudget(
        model=args.model,
        max_cost_usd=args.max_cost_usd,
        max_llm_calls=args.max_llm_calls,
        max_output_tokens=args.max_output_tokens,
        max_events=args.max_events,
        max_behavior_calls=args.max_behavior_calls,
        author_timeout_seconds=args.author_timeout,
        trial_timeout_seconds=args.trial_timeout,
        max_author_attempts=args.max_author_attempts,
    )
    result = author_evaluate_and_record(
        load_task(args.task),
        docs_root=args.docs_root,
        run_dir=args.run_dir,
        provider=provider_for(args.provider),
        budget=budget,
    )
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result["research_success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
