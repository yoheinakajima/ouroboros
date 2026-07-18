from __future__ import annotations

import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from typing import Any

from activegraph.llm import LLMResponse
from pydantic import ValidationError

from experiments.hybrid_ouroboros import Case, HybridOuroboros, PackDraft
from research.adapters.common import HybridPacksAdapter, MinimalV2Adapter
from research.curriculum import build_manifest, hash_artifact, validate_manifest, write_manifest
from research.lineage import (
    CONTEXT_INTERFACE,
    DevelopmentEvidence,
    DevelopmentLesson,
    PublicScoreReceipt,
    ReflectionBudget,
    _copy_prior_lineage,
    _hybrid_task,
    _sanitize_hybrid_organism,
    apply_minimal_lesson,
    extract_attempt_evidence,
    reflect_evidence,
)


def evidence(*, passed: bool = True, task_id: str = "dev-task") -> DevelopmentEvidence:
    return DevelopmentEvidence(
        suite_id="ouro_swe_50",
        task_id=task_id,
        parent_run_id=f"run-{task_id}",
        approach_id="minimal_v2",
        arm="cold",
        public_instruction="Repair the public behavior and run focused tests.",
        agent_status="completed",
        agent_summary="Inspected the implementation and validated a focused change.",
        agent_evidence=["focused tests passed"],
        owned_artifact_excerpt="diff --git a/a.py b/a.py\n",
        owned_artifact_sha256="a" * 64,
        owned_artifact_bytes=28,
        score=PublicScoreReceipt(
            grader_id="official",
            grader_revision="revision-1",
            primary_score=1.0 if passed else 0.0,
            passed=passed,
            receipt_sha256="b" * 64,
        ),
        source_hashes={"agent_trace": "c" * 64, "grader_receipt": "b" * 64},
        created_at="2026-07-17T00:00:00+00:00",
    )


def lesson() -> DevelopmentLesson:
    return DevelopmentLesson(
        title="Inspect invariants before editing",
        scope="Use focused inspection and differential checks when repairing unfamiliar software behavior.",
        trigger_terms=["debug", "regression", "invariant"],
        steps=["Inspect the failing path.", "Make one coherent change."],
        pitfalls=["Do not infer success from a plausible patch."],
        validation=["Run focused tests and one direct reproduction."],
        confidence="high",
    )


class DevelopmentEvidenceTests(unittest.TestCase):
    def test_allowlist_rejects_hidden_or_extra_evaluator_material(self) -> None:
        payload = evidence().model_dump(mode="json")
        payload["hidden_evaluator_content_exposed"] = True
        with self.assertRaisesRegex(ValidationError, "hidden evaluator"):
            DevelopmentEvidence.model_validate(payload)

        payload = evidence().model_dump(mode="json")
        payload["hidden_tests"] = ["secret expected value"]
        with self.assertRaisesRegex(ValidationError, "Extra inputs"):
            DevelopmentEvidence.model_validate(payload)

    def test_source_hash_names_reject_private_manager_surfaces(self) -> None:
        payload = evidence().model_dump(mode="json")
        for denied in ("private_cases", "hidden_test_log_hash", "manager_expected_outputs"):
            payload["source_hashes"] = {denied: "d" * 64}
            with self.assertRaisesRegex(ValidationError, "not allowed"):
                DevelopmentEvidence.model_validate(payload)

    def test_reflection_is_one_recorded_structured_model_call(self) -> None:
        expected = lesson()

        class Provider:
            default_model = "scripted-reflector"

            def __init__(self) -> None:
                self.calls: list[dict[str, Any]] = []

            def recognizes_model(self, model: str) -> bool:
                return True

            def supports_native_structured_output(self, model: str) -> bool:
                return True

            def complete(self, **kwargs: Any) -> LLMResponse:
                self.calls.append(kwargs)
                return LLMResponse(
                    raw_text=expected.model_dump_json(),
                    parsed=expected,
                    input_tokens=100,
                    output_tokens=50,
                    cost_usd=Decimal("0.01"),
                    latency_seconds=0.01,
                    model="scripted-reflector",
                    finish_reason="stop",
                    tool_calls=None,
                )

            def estimate_cost(self, *, input_tokens: int, output_tokens: int, model: str) -> Decimal:
                return Decimal("0.01")

            def count_tokens(self, *, system: str, messages: list[Any], model: str) -> int:
                return 100

        provider = Provider()
        with tempfile.TemporaryDirectory() as temporary:
            reflected, summary = reflect_evidence(
                evidence(),
                run_dir=Path(temporary) / "reflection",
                provider=provider,
                budget=ReflectionBudget(model="scripted-reflector", max_cost_usd=1),
            )

        self.assertEqual(reflected, expected)
        self.assertEqual(summary["usage"]["model_calls"], 1)
        self.assertEqual(len(provider.calls), 1)

    def test_extract_attempt_evidence_uses_only_public_attempt_surfaces(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run = root / "run"
            workspace = run / "workspace/candidate_pack"
            workspace.mkdir(parents=True)
            artifact = workspace / "__init__.py"
            artifact.write_text("PACK = object()\n", encoding="utf-8")
            task = {
                "suite_id": "ouro_activegraph_50",
                "task_id": "incident_coordination",
                "prompt": "Public task prompt",
                "image": "sha256:" + "0" * 64,
            }
            (root / "task.json").write_text(json.dumps(task), encoding="utf-8")
            (run / "trace.jsonl").write_text('{"type":"model_complete"}\n', encoding="utf-8")
            (run / "outcome.json").write_text(
                json.dumps(
                    {
                        "status": "completed",
                        "summary": "Implemented a candidate.",
                        "evidence": ["public tests passed"],
                    }
                ),
                encoding="utf-8",
            )
            (run / "attempt.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "run_id": "incident-r1",
                        "approach_id": "hybrid_packs",
                        "study_id": "common_outcome",
                        "suite_id": "ouro_activegraph_50",
                        "task_id": "incident_coordination",
                        "arm": "cold",
                        "replication": 1,
                        "seed": 101,
                        "model": "gpt-5.6-terra",
                        "task_image_digest": "sha256:" + "0" * 64,
                        "approach_source_hashes": {},
                        "started_at": "2026-07-17T00:00:00+00:00",
                        "finished_at": "2026-07-17T00:00:01+00:00",
                        "status": "completed",
                        "usage": {},
                        "trace_path": "trace.jsonl",
                        "submission_path": "workspace",
                    }
                ),
                encoding="utf-8",
            )
            score = run / "score.json"
            score.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "run_id": "incident-r1",
                        "grader_id": "ouro_activegraph_50",
                        "grader_revision": "1.0.0",
                        "primary_score": 42.0,
                        "passed": False,
                        "components": {"sealed_detail_that_must_not_enter_prompt": "hidden-ish"},
                    }
                ),
                encoding="utf-8",
            )

            extracted = extract_attempt_evidence(
                root,
                run_dir=run,
                task_json=root / "task.json",
                score_json=score,
            )

        self.assertEqual(extracted.suite_id, "ouro_activegraph_50")
        self.assertEqual(extracted.approach_id, "hybrid_packs")
        self.assertEqual(extracted.public_instruction, "Public task prompt")
        self.assertEqual(extracted.score.primary_score, 42.0)
        self.assertEqual(extracted.owned_artifact_excerpt, "PACK = object()\n")
        self.assertNotIn("components", extracted.model_dump_json())
        self.assertNotIn("sealed_detail", extracted.model_dump_json())


class NativeLineageTests(unittest.TestCase):
    def test_prior_detailed_lineage_is_copied_into_next_export(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parent = root / "parent"
            record = parent / "lineage/records/001-first.json"
            record.parent.mkdir(parents=True)
            record.write_text('{"sequence": 1}\n', encoding="utf-8")
            next_state = root / "next"
            next_state.mkdir()
            _copy_prior_lineage(parent, next_state)

            copied = next_state / "lineage/records/001-first.json"
            self.assertEqual(copied.read_bytes(), record.read_bytes())

    def test_minimal_retains_only_passing_external_procedures(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            passed_state = root / "passed"
            apply_minimal_lesson(evidence=evidence(), lesson=lesson(), output_state=passed_state)
            export = json.loads((passed_state / "state_export.json").read_text(encoding="utf-8"))
            manifest = validate_manifest(passed_state, approach_id="minimal_v2")
            prepared = MinimalV2Adapter(model="test", retained_state=passed_state).prepare(
                task={"prompt": "debug a regression"}, arm="evolved", seed=7
            )

            failed_state = root / "failed"
            apply_minimal_lesson(
                evidence=evidence(passed=False, task_id="failed-task"),
                lesson=lesson(),
                output_state=failed_state,
            )
            failed_export = json.loads((failed_state / "state_export.json").read_text(encoding="utf-8"))

        self.assertEqual(manifest.development_task_ids, ["dev-task"])
        self.assertEqual(len(export["procedures"]), 1)
        self.assertEqual(export["procedures"][0]["evidence"], "sha256:" + "b" * 64)
        self.assertIn("Inspect invariants before editing", prepared.retained_context)
        self.assertEqual(failed_export["procedures"], [])
        self.assertEqual(failed_export["evidence_receipts"], ["sha256:" + "b" * 64])

    def test_minimal_lineage_is_append_only_and_parent_hash_pinned(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "first"
            second = root / "second"
            apply_minimal_lesson(evidence=evidence(), lesson=lesson(), output_state=first)
            apply_minimal_lesson(
                evidence=evidence(task_id="dev-task-2"),
                lesson=lesson().model_copy(update={"title": "Validate before claiming completion"}),
                output_state=second,
                parent_state=first,
            )
            manifest = validate_manifest(second, approach_id="minimal_v2")

        self.assertEqual(manifest.development_task_ids, ["dev-task", "dev-task-2"])
        self.assertEqual(manifest.parent_run_ids, ["run-dev-task", "run-dev-task-2"])

    def test_cross_approach_evidence_requires_explicit_unscored_calibration(self) -> None:
        workspace_evidence = evidence().model_copy(update={"approach_id": "workspace_v1_2"})
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(ValueError, "may not inherit development evidence"):
                apply_minimal_lesson(
                    evidence=workspace_evidence,
                    lesson=lesson(),
                    output_state=root / "rejected",
                )
            accepted = root / "accepted"
            apply_minimal_lesson(
                evidence=workspace_evidence,
                lesson=lesson(),
                output_state=accepted,
                allow_cross_approach_calibration=True,
            )
            record_path = next((accepted / "lineage/records").glob("*.json"))
            record = json.loads(record_path.read_text(encoding="utf-8"))

        self.assertTrue(record["cross_approach_calibration"])
        self.assertEqual(record["source_approach_id"], "workspace_v1_2")
        self.assertEqual(record["retained_approach_id"], "minimal_v2")

    def test_hybrid_task_requires_real_query_behavior_and_typed_state(self) -> None:
        row = {
            "suite_id": "ouro_swe_50",
            "task_id": "dev-task",
            "score_passed": True,
            "lesson": lesson().model_dump(mode="json"),
        }
        task = _hybrid_task([row])

        self.assertEqual(task.public_cases[0].payload["operation"], "development_guidance")
        self.assertEqual(task.public_cases[0].expected_graph, {"object_type_counts": {"guidance_query": 1}})
        self.assertIn("exactly one complete ActiveGraph Pack", task.objective)
        self.assertEqual(len(task.private_cases), 1)
        self.assertEqual(len(task.transfer_cases), 1)

    def test_hybrid_adapter_executes_pack_on_a_temporary_copy(self) -> None:
        expected = {"lessons": [{"title": "Inspect invariants before editing"}]}
        source = '''from pydantic import BaseModel
from activegraph.packs import ObjectType, Pack, behavior


class GuidanceQuery(BaseModel):
    query: str


@behavior(name="development_guidance", on=["hybrid.task.requested"])
def development_guidance(event, graph, ctx):
    if event.payload.get("operation") != "development_guidance":
        return
    graph.add_object("guidance_query", {"query": str(event.payload.get("query", ""))})
    graph.emit(
        "hybrid.task.completed",
        {
            "request_id": event.payload["request_id"],
            "output": {"lessons": [{"title": "Inspect invariants before editing"}]},
        },
    )


PACK = Pack(
    name="development_playbook",
    version="1.0.0",
    description="Retrieves evaluated development guidance.",
    behaviors=(development_guidance,),
    object_types=(
        ObjectType(
            name="guidance_query",
            schema=GuidanceQuery,
            description="One recorded guidance retrieval query.",
        ),
    ),
)
'''
        draft = PackDraft(
            name="development_playbook",
            version="1.0.0",
            description="Retrieves evaluated development guidance.",
            files={"__init__.py": source},
            behaviors=("development_guidance",),
            object_types=("guidance_query",),
        )
        case = Case(
            "guidance",
            {"operation": "development_guidance", "query": "regression", "limit": 1},
            expected,
            {"object_type_counts": {"guidance_query": 1}},
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            native = root / "native"
            report = HybridOuroboros(native).evolve(
                objective="Acquire a tested development guidance behavior.",
                draft=draft,
                public_cases=[case],
                private_cases=[case.__class__("private-guidance", case.payload, case.expected, case.expected_graph)],
            )
            self.assertTrue(report.accepted)
            state = root / "state"
            state.mkdir()
            _sanitize_hybrid_organism(native, state)
            manifest = build_manifest(
                state,
                approach_id="hybrid_packs",
                mutation_unit="atomic set of complete hash-pinned ActiveGraph Packs",
                development_suites=["ouro_swe_50"],
                development_task_ids=["dev-task"],
                parent_run_ids=["run-dev-task"],
                feedback_policy="public_plus_score_receipt",
            )
            write_manifest(state, manifest)
            before = hash_artifact(state)
            prepared = HybridPacksAdapter(model="test", retained_state=state).prepare(
                task={"prompt": "debug this regression"}, arm="evolved", seed=9
            )
            after = hash_artifact(state)
            registry = json.loads((state / "registry.json").read_text(encoding="utf-8"))

        self.assertEqual(registry["research_context_interface"], CONTEXT_INTERFACE)
        self.assertIn("activegraph_query_output", prepared.retained_context)
        self.assertIn('"credentials_forwarded": false', prepared.retained_context)
        self.assertIn("Inspect invariants before editing", prepared.retained_context)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
