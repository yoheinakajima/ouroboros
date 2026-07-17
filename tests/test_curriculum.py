from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from activegraph import Graph, Runtime

from research.curriculum import (
    build_manifest,
    export_minimal_state,
    validate_manifest,
    write_manifest,
)


class CurriculumManifestTests(unittest.TestCase):
    def test_manifest_hash_pins_evolved_state_and_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            (state / "MEMORY.md").write_text("Retained repair procedure.\n", encoding="utf-8")
            manifest = build_manifest(
                state,
                approach_id="workspace_v1_2",
                mutation_unit="arbitrary workspace tree",
                development_suites=["ouro_swe_50"],
                development_task_ids=["dev-1"],
                parent_run_ids=["run-1"],
                feedback_policy="public_plus_score_receipt",
            )
            write_manifest(state, manifest)
            validated = validate_manifest(state, approach_id="workspace_v1_2")
        self.assertEqual(validated.artifact_sha256, manifest.artifact_sha256)
        self.assertFalse(validated.hidden_evaluator_content_exposed)

    def test_post_manifest_mutation_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            artifact = state / "state_export.json"
            artifact.write_text("{}\n", encoding="utf-8")
            manifest = build_manifest(
                state,
                approach_id="minimal_v2",
                mutation_unit="evaluated procedure or pure deterministic capability",
                development_suites=["ouro_terminal_12"],
                development_task_ids=["dev-1"],
                parent_run_ids=["run-1"],
                feedback_policy="public_only",
            )
            write_manifest(state, manifest)
            artifact.write_text('{"changed": true}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "drift"):
                validate_manifest(state, approach_id="minimal_v2")

    def test_private_or_grader_material_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            private = state / "private"
            private.mkdir()
            (private / "cases.json").write_text("[]\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "private/evaluator"):
                build_manifest(
                    state,
                    approach_id="hybrid_packs",
                    mutation_unit="atomic set of complete hash-pinned ActiveGraph Packs",
                    development_suites=["ouro_activegraph_50"],
                    development_task_ids=["incident_coordination"],
                    parent_run_ids=["run-1"],
                    feedback_policy="public_only",
                )

    def test_native_minimal_state_exports_only_bounded_context(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            (state / "organism.json").write_text(
                json.dumps({"engine_version": "2.0.0-minimal", "run_id": "test-run"}),
                encoding="utf-8",
            )
            runtime = Runtime(Graph(run_id="test-run"), behaviors=[], persist_to=str(state / "trace.sqlite"))
            runtime.graph.add_object(
                "procedure",
                {
                    "name": "inspect before editing",
                    "trigger_terms": ["debug"],
                    "steps": ["Read the failing path.", "Run a focused check."],
                    "evidence": "verified development attempt",
                    "private_case": "must not be exported",
                },
            )
            runtime.graph.add_object(
                "mutation_trial",
                {"evaluation_receipt": "sha256:" + "a" * 64, "hidden_cases": ["not exported"]},
            )
            runtime.graph.add_object(
                "promotion",
                {
                    "status": "active",
                    "capability_name": "normalize",
                    "description": "Normalize a record.",
                    "pack_name": "normalize_pack",
                    "bundle_hash": "sha256:" + "b" * 64,
                    "root": "/private/author/path",
                },
            )
            runtime.save_state()

            exported = json.loads(export_minimal_state(state).read_text(encoding="utf-8"))

        self.assertEqual(exported["procedures"][0]["name"], "inspect before editing")
        self.assertNotIn("private_case", exported["procedures"][0])
        self.assertNotIn("root", exported["capabilities"][0])
        self.assertEqual(exported["evidence_receipts"], ["sha256:" + "a" * 64])


if __name__ == "__main__":
    unittest.main()
