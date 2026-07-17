from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from research.curriculum import build_manifest, validate_manifest, write_manifest


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


if __name__ == "__main__":
    unittest.main()
