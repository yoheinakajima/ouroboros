from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class HardBenchmarkDesignTests(unittest.TestCase):
    def test_hard_suite_is_diverse_verifiable_and_execution_locked(self) -> None:
        design = json.loads((ROOT / "research" / "hard_benchmark.json").read_text(encoding="utf-8"))
        self.assertFalse(design["execution_enabled"])
        suites = {suite["id"]: suite for suite in design["suites"]}
        self.assertEqual(len(suites), len(design["suites"]))
        self.assertGreaterEqual(len(suites), 6)
        self.assertEqual(suites["ouro_swe_50"]["development_instances"], 20)
        self.assertEqual(suites["ouro_swe_50"]["evaluation_instances"], 50)
        self.assertIn("Docker", suites["ouro_swe_50"]["isolation"])
        self.assertEqual(suites["ouro_activegraph_50"]["score"].split(",")[0], "checks passed / 50")
        self.assertTrue(all(len(suite["upstream_revision"]) == 40 for suite in suites.values()))
        self.assertEqual(suites["ouro_terminal_12"]["source"].split("/")[-1], "terminal-bench-2")
        self.assertEqual(design["common_budget"]["max_cost_usd"], 50.0)

    def test_recursive_study_requires_cold_and_sham_controls(self) -> None:
        design = json.loads((ROOT / "research" / "hard_benchmark.json").read_text(encoding="utf-8"))
        studies = {study["id"]: study for study in design["studies"]}
        self.assertEqual(
            studies["recursive_uplift"]["required_arms"],
            ["evolved", "cold_ablation", "sham_improvement_control"],
        )
        self.assertIn("paired", studies["recursive_uplift"]["primary_metric"])

    def test_common_broker_keeps_credentials_and_graders_outside_candidates(self) -> None:
        broker = json.loads((ROOT / "research" / "broker_protocol.json").read_text(encoding="utf-8"))
        operations = {item["name"] for item in broker["operations"]}
        self.assertEqual(
            operations,
            {"list_files", "read_file", "write_file", "replace_file", "run_command", "model_complete"},
        )
        self.assertIn("provider_credentials", broker["forbidden_surfaces"])
        self.assertIn("evaluator_container", broker["forbidden_surfaces"])
        self.assertEqual(broker["implementation_status"], "ready")


if __name__ == "__main__":
    unittest.main()
