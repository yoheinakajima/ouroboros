from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class LocalStudyProtocolTests(unittest.TestCase):
    def test_all_three_approaches_run_all_three_separate_families(self) -> None:
        study = json.loads((ROOT / "research/local_study.json").read_text(encoding="utf-8"))
        self.assertEqual(
            study["approaches"],
            ["workspace_v1_2", "minimal_v2", "hybrid_packs"],
        )
        self.assertEqual(
            [suite["id"] for suite in study["suites"]],
            ["ouro_swe_50", "ouro_terminal_12", "ouro_activegraph_50"],
        )
        self.assertTrue(study["comparison_rules"]["family_scores_remain_separate"])
        self.assertTrue(study["comparison_rules"]["no_general_intelligence_score"])

    def test_primary_uplift_and_controls_are_frozen(self) -> None:
        study = json.loads((ROOT / "research/local_study.json").read_text(encoding="utf-8"))
        arms = {row["id"] for row in study["arms"]}
        self.assertEqual(
            arms,
            {"cold", "evolved", "cold_ablation", "sham_improvement_control"},
        )
        self.assertIn(
            "same task and seed",
            study["comparison_rules"]["primary_architecture_delta"],
        )
        recursive = next(row for row in study["run_stages"] if row["id"] == "recursive_claim")
        self.assertEqual(recursive["replications"], 5)
        self.assertIn("fixed five replications", recursive["stop_rule"])
        curriculum = next(row for row in study["run_stages"] if row["id"] == "development_curriculum")
        self.assertEqual(
            curriculum["approaches"],
            ["workspace_v1_2", "minimal_v2", "hybrid_packs"],
        )
        self.assertIn("independent lineage", curriculum["replications"])

    def test_only_locally_runnable_suites_are_included(self) -> None:
        study = json.loads((ROOT / "research/local_study.json").read_text(encoding="utf-8"))
        suite_ids = {suite["id"] for suite in study["suites"]}
        self.assertFalse(
            suite_ids
            & {
                "ouro_mle_6",
                "ouro_rebench_2",
                "ouro_paperbench_code_dev_2",
            }
        )


if __name__ == "__main__":
    unittest.main()
