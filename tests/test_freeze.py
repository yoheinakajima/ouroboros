from __future__ import annotations

import unittest
from pathlib import Path

from research.freeze import build_lock, inspect_selections

ROOT = Path(__file__).resolve().parents[1]


class FreezeTests(unittest.TestCase):
    def test_local_no_account_selections_are_score_blind_and_locked_for_calibration(self) -> None:
        report = inspect_selections(ROOT, profile="local_no_account")
        self.assertTrue(report["valid"], report)
        self.assertTrue(report["calibration_ready"], report)
        self.assertEqual(
            set(report["statuses"]),
            {"ouro_swe_50", "ouro_terminal_12", "ouro_activegraph_50"},
        )

    def test_global_selections_are_valid_but_not_yet_frozen(self) -> None:
        report = inspect_selections(ROOT)
        self.assertTrue(report["valid"], report)
        self.assertTrue(report["calibration_ready"], report)
        self.assertFalse(report["frozen"])
        self.assertEqual(report["issues"], [])

    def test_frontier_selections_are_locked_but_keep_external_prerequisites(self) -> None:
        report = inspect_selections(ROOT, profile="external_data_or_compute")
        self.assertTrue(report["valid"], report)
        self.assertTrue(report["calibration_ready"], report)
        self.assertTrue(all("external" in status for status in report["statuses"].values()))

    def test_protocol_lock_is_deterministic(self) -> None:
        first = build_lock(ROOT)
        second = build_lock(ROOT)
        self.assertEqual(first, second)
        self.assertEqual(len(first["root_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
