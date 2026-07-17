from __future__ import annotations

import unittest
from pathlib import Path

from research.contracts import AttemptRecord, ResourceUsage, ScoreRecord
from research.readiness import inspect_readiness

ROOT = Path(__file__).resolve().parents[1]


class ResearchReadinessTests(unittest.TestCase):
    def test_local_catalog_is_frozen_and_execution_enabled(self) -> None:
        report = inspect_readiness(ROOT)
        codes = {item["code"] for item in report["issues"]}
        self.assertTrue(report["structurally_valid"], report)
        self.assertTrue(report["execution_enabled"])
        self.assertNotIn("execution_disabled", codes)
        self.assertNotIn("suite_revision_unpinned", codes)
        self.assertNotIn("hardening_incomplete", codes)
        self.assertNotIn("broker_not_ready", codes)
        self.assertTrue(report["selection_report"]["calibration_ready"])
        self.assertTrue(report["selection_report"]["frozen"])
        self.assertEqual(report["approaches"], ["hybrid_packs", "minimal_v2", "workspace_v1_2"])

    def test_attempt_and_score_contracts_keep_claims_separate(self) -> None:
        attempt = AttemptRecord(
            run_id="run-1",
            approach_id="minimal_v2",
            study_id="common_outcome",
            suite_id="ouro_swe_50",
            task_id="task-1",
            arm="cold",
            replication=1,
            seed=7,
            model="test-model",
            task_image_digest="sha256:image",
            approach_source_hashes={"ouroboros.py": "sha256:source"},
            started_at="2026-01-01T00:00:00Z",
            finished_at="2026-01-01T00:01:00Z",
            status="completed",
            usage=ResourceUsage(model_calls=1),
            trace_path="runs/run-1/trace.jsonl",
        )
        score = ScoreRecord(
            run_id=attempt.run_id,
            grader_id="official",
            grader_revision="abc123",
            primary_score=0.0,
            passed=False,
        )
        self.assertEqual(score.run_id, attempt.run_id)
        self.assertFalse(score.passed)


if __name__ == "__main__":
    unittest.main()
