from __future__ import annotations

import json
import unittest
from pathlib import Path

from research.calibration import balanced_replacements, stratum_replacements

ROOT = Path(__file__).resolve().parents[1]


class CalibrationSelectionTests(unittest.TestCase):
    def test_replacements_are_order_invariant_and_balance_repositories(self) -> None:
        records = [
            {"instance_id": "a1", "repo": "a"},
            {"instance_id": "a2", "repo": "a"},
            {"instance_id": "a3", "repo": "a"},
            {"instance_id": "b1", "repo": "b"},
            {"instance_id": "b2", "repo": "b"},
            {"instance_id": "b3", "repo": "b"},
            {"instance_id": "c1", "repo": "c"},
            {"instance_id": "c2", "repo": "c"},
        ]
        kwargs = {
            "selected_ids": ["a1", "a2", "b1", "c1"],
            "excluded_ids": ["a1", "b1"],
            "count": 2,
            "seed": "test-seed",
        }
        forward = balanced_replacements(records, **kwargs)
        reverse = balanced_replacements(reversed(records), **kwargs)
        self.assertEqual(forward, reverse)
        self.assertEqual(forward[0][0], "b")
        self.assertEqual(len(set(forward)), 2)
        self.assertFalse(set(forward) & set(kwargs["selected_ids"]))

    def test_swe_manifest_records_every_calibration_replacement(self) -> None:
        manifest = json.loads((ROOT / "research/selections/swe_verified.json").read_text())
        calibration = manifest["calibration"]
        excluded = {row["id"] for row in calibration["excluded"]}
        replacements = {row["replacement"] for row in calibration["excluded"]}
        selected = set(manifest["development"] + manifest["evaluation"])
        self.assertEqual(len(excluded), 5)
        self.assertEqual(len(replacements), 5)
        self.assertFalse(excluded & selected)
        self.assertLessEqual(replacements, selected)
        self.assertEqual(calibration["replacement_seed"], "ouroboros-hard-v1-swe-calibration-replacement-v1")

    def test_stratum_replacements_preserve_difficulty_and_category(self) -> None:
        records = [
            {"id": "selected", "difficulty": "medium", "category": "debugging"},
            {"id": "other", "difficulty": "hard", "category": "debugging"},
            {"id": "candidate-b", "difficulty": "medium", "category": "debugging"},
            {"id": "candidate-a", "difficulty": "medium", "category": "debugging"},
        ]
        forward = stratum_replacements(
            records,
            selected_ids=["selected"],
            excluded_ids=["selected"],
            strata=["difficulty", "category"],
            seed="test-seed",
        )
        reverse = stratum_replacements(
            reversed(records),
            selected_ids=["selected"],
            excluded_ids=["selected"],
            strata=["difficulty", "category"],
            seed="test-seed",
        )
        self.assertEqual(forward, reverse)
        self.assertIn(forward[0], {"candidate-a", "candidate-b"})

    def test_terminal_manifest_records_the_score_blind_replacement(self) -> None:
        manifest = json.loads((ROOT / "research/selections/terminal_bench_2.json").read_text())
        calibration = manifest["calibration"]
        excluded = calibration["excluded"]
        selected = {row["id"]: row for row in manifest["development"] + manifest["evaluation"]}

        self.assertEqual(calibration["seed"], "ouroboros-hard-v1-terminal2-calibration-replacement-v1")
        self.assertEqual(len(excluded), 2)
        replacements = {row["id"]: row["replacement"] for row in excluded}
        self.assertEqual(replacements["build-cython-ext"], "custom-memory-heap-crash")
        self.assertEqual(replacements["schemelike-metacircular-eval"], "kv-store-grpc")
        self.assertNotIn("build-cython-ext", selected)
        self.assertNotIn("schemelike-metacircular-eval", selected)
        replacement = selected["custom-memory-heap-crash"]
        self.assertEqual((replacement["difficulty"], replacement["category"]), ("medium", "debugging"))
        replacement = selected["kv-store-grpc"]
        self.assertEqual((replacement["difficulty"], replacement["category"]), ("medium", "software-engineering"))


if __name__ == "__main__":
    unittest.main()
