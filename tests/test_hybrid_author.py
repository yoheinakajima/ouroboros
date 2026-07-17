from __future__ import annotations

import json
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from activegraph.llm import LLMResponse  # noqa: E402

from research.hybrid_author import (  # noqa: E402
    PackProposal,
    PackSetProposal,
    ResearchBudget,
    author_evaluate_and_record,
    build_documentation_corpus,
    load_task,
)

PACK_SOURCE = '''from __future__ import annotations

from pydantic import BaseModel, Field
from activegraph.packs import ObjectType, Pack, behavior


class UsageCounter(BaseModel):
    tenant: str
    total: int = Field(ge=0)


@behavior(name="record_usage", on=["hybrid.task.requested"])
def record_usage(event, graph, ctx):
    if event.payload.get("operation") != "record_usage":
        return
    tenant = str(event.payload["tenant"])
    amount = int(event.payload["amount"])
    limit = int(event.payload["limit"])
    counters = [
        item for item in ctx.view.objects(type="usage_counter")
        if item.data.get("tenant") == tenant
    ]
    if counters:
        total = int(counters[0].data["total"]) + amount
        graph.patch_object(counters[0].id, {"total": total})
    else:
        total = amount
        graph.add_object("usage_counter", {"tenant": tenant, "total": total})
    graph.emit(
        "hybrid.task.completed",
        {
            "request_id": event.payload["request_id"],
            "output": {"tenant": tenant, "total": total, "over_limit": total > limit},
        },
    )


PACK = Pack(
    name="usage_tracker",
    version="1.0.0",
    description="Tracks cumulative usage per tenant in typed graph objects.",
    object_types=(ObjectType(name="usage_counter", schema=UsageCounter),),
    behaviors=(record_usage,),
)
'''


class ScriptedProvider:
    default_model = "scripted-pack-author"

    def __init__(self, proposal: PackSetProposal | list[PackSetProposal]) -> None:
        self.proposals = list(proposal) if isinstance(proposal, list) else [proposal]
        self.calls: list[dict[str, Any]] = []

    def recognizes_model(self, model: str) -> bool:
        return True

    def supports_native_structured_output(self, model: str) -> bool:
        return False

    def complete(self, **kwargs: Any) -> LLMResponse:
        self.calls.append(kwargs)
        if not self.proposals:
            raise AssertionError("scripted proposal sequence exhausted")
        proposal = self.proposals.pop(0)
        return LLMResponse(
            raw_text=proposal.model_dump_json(),
            parsed=proposal,
            input_tokens=1_000,
            output_tokens=500,
            cost_usd=Decimal("0.25"),
            latency_seconds=0.01,
            model=str(kwargs.get("model", self.default_model)),
            finish_reason="stop",
            tool_calls=None,
        )

    def estimate_cost(self, *, input_tokens: int, output_tokens: int, model: str) -> Decimal:
        return Decimal("0.25")

    def count_tokens(self, *, system: str, messages: list[Any], model: str) -> int:
        return 1_000


class HybridAuthorTests(unittest.TestCase):
    def test_relational_benchmark_task_is_well_formed(self):
        task = load_task(ROOT / "research" / "tasks" / "dependency_release_planner.json")
        self.assertEqual(task.category, "typed_relational_workflow")
        self.assertEqual((len(task.public_cases), len(task.private_cases), len(task.transfer_cases)), (5, 5, 4))
        self.assertEqual(task.public_cases[1].expected_graph["relation_type_counts"]["depends_on"], 1)

    def test_empty_settings_is_canonicalized_for_the_manager_manifest(self):
        proposal = PackProposal(
            name="example_pack",
            version="1.0.0",
            description="Example.",
            files={"__init__.py": "pass\n"},
            behaviors=[],
            settings_schema="EmptySettings",
            design_summary="Example.",
        )
        self.assertEqual(proposal.draft().settings_schema, "")

    def test_documentation_corpus_is_exact_and_fails_instead_of_truncating(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "guide.md").write_text("pack docs\n", encoding="utf-8")
            corpus = build_documentation_corpus(root, paths=("guide.md",), max_characters=1_000)
            self.assertEqual(corpus.documents[0]["path"], "guide.md")
            self.assertIn("pack docs", corpus.rendered)
            with self.assertRaises(ValueError):
                build_documentation_corpus(root, paths=("guide.md",), max_characters=5)

    def test_scripted_llm_author_is_recorded_then_governed_and_adopted(self):
        proposal = PackSetProposal(
            packs=[
                PackProposal(
                    name="usage_tracker",
                    version="1.0.0",
                    description="Tracks cumulative usage per tenant in typed graph objects.",
                    files={"__init__.py": PACK_SOURCE},
                    behaviors=["record_usage"],
                    object_types=["usage_counter"],
                    design_summary="One typed counter object per tenant; deterministic patches preserve state.",
                )
            ],
            design_summary="One typed counter Pack; deterministic patches preserve state.",
            documentation_used=["guide.md"],
        )
        provider = ScriptedProvider(proposal)
        task_path = ROOT / "research" / "tasks" / "stateful_usage_tracker.json"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            docs = root / "docs_source"
            docs.mkdir()
            (docs / "guide.md").write_text("Use activegraph.packs decorators.\n", encoding="utf-8")
            run_dir = root / "run"
            result = author_evaluate_and_record(
                load_task(task_path),
                docs_root=docs,
                run_dir=run_dir,
                provider=provider,
                budget=ResearchBudget(model="scripted-pack-author", max_cost_usd=1),
                doc_paths=("guide.md",),
            )
            self.assertTrue(result["accepted"], result)
            self.assertEqual(result["evolution"]["public_candidate"], "3/3")
            self.assertEqual(result["evolution"]["private_candidate"], "4/4")
            self.assertEqual(result["organism_after_restart"]["loaded"], ["usage_tracker@1.0.0"])
            self.assertTrue(result["research_success"])
            self.assertEqual(result["transfer"]["passed"], 3)
            self.assertEqual(len(provider.calls), 1)
            self.assertTrue((run_dir / "author.trace.sqlite").is_file())
            self.assertTrue((run_dir / "author.events.jsonl").is_file())
            self.assertTrue((run_dir / "proposal.json").is_file())
            self.assertTrue((run_dir / "manager" / "private_cases.json").is_file())
            author_surfaces = "\n".join(
                (run_dir / name).read_text(encoding="utf-8")
                for name in ("request.public.json", "author.events.jsonl", "proposal.json")
            )
            self.assertNotIn("private-acme", author_surfaces)
            self.assertNotIn('"tenant":"acme"', author_surfaces)
            saved = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["author"]["documentation"]["documents"][0]["path"], "guide.md")

    def test_rejected_pack_is_repaired_without_private_case_feedback(self):
        unsafe = PackSetProposal(
            packs=[
                PackProposal(
                    name="usage_tracker",
                    version="1.0.0",
                    description="Unsafe first attempt.",
                    files={"__init__.py": "import os\n"},
                    behaviors=[],
                    design_summary="Incorrectly requests environment authority.",
                )
            ],
            design_summary="Incorrectly requests environment authority.",
        )
        repaired = PackSetProposal(
            packs=[
                PackProposal(
                    name="usage_tracker",
                    version="1.0.0",
                    description="Tracks cumulative usage per tenant in typed graph objects.",
                    files={"__init__.py": PACK_SOURCE},
                    behaviors=["record_usage"],
                    object_types=["usage_counter"],
                    design_summary="Repaired within the declared authority boundary.",
                )
            ],
            design_summary="Repaired within the declared authority boundary.",
        )
        provider = ScriptedProvider([unsafe, repaired])
        task = load_task(ROOT / "research" / "tasks" / "stateful_usage_tracker.json")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            docs = root / "docs_source"
            docs.mkdir()
            (docs / "guide.md").write_text("Use activegraph.packs decorators.\n", encoding="utf-8")
            result = author_evaluate_and_record(
                task,
                docs_root=docs,
                run_dir=root / "run",
                provider=provider,
                budget=ResearchBudget(
                    model="scripted-pack-author",
                    max_cost_usd=1,
                    max_author_attempts=2,
                ),
                doc_paths=("guide.md",),
            )
            self.assertTrue(result["research_success"], result)
            self.assertEqual(result["author"]["attempt_count"], 2)
            self.assertEqual(result["author"]["usage"]["requests"], 2)
            self.assertEqual(result["author_attempts"][0]["evolution"]["reason"], "static policy rejected proposal")
            second_call = json.dumps(provider.calls[1], default=str)
            self.assertIn("import 'os' denied", second_call)
            self.assertNotIn("private-acme", second_call)
            self.assertTrue((root / "run" / "author.attempts.json").is_file())


if __name__ == "__main__":
    unittest.main()
