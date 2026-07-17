from __future__ import annotations

import unittest

from research.comparison import ResultRow, compare


def row(*, task: str, arm: str, score: float, approach: str = "minimal_v2") -> ResultRow:
    return ResultRow(
        approach_id=approach,
        suite_id="ouro_activegraph_50",
        task_id=task,
        arm=arm,
        seed=1,
        replication=1,
        score=score,
        maximum_score=50,
        cost_usd=1,
        wall_seconds=10,
    )


class ComparisonTests(unittest.TestCase):
    def test_positive_paired_uplift_is_reported_without_cross_suite_aggregation(self) -> None:
        rows = []
        for task in ("a", "b", "c"):
            rows.extend(
                [
                    row(task=task, arm="evolved", score=45),
                    row(task=task, arm="cold_ablation", score=20),
                    row(task=task, arm="sham_improvement_control", score=22),
                ]
            )
        report = compare(rows, bootstrap_samples=500)
        result = report["families"]["ouro_activegraph_50"]["minimal_v2"]
        self.assertEqual(result["evolved_minus_cold_ablation"]["status"], "better")
        self.assertGreater(result["evolved_minus_sham"]["mean_normalized_delta"], 0)
        self.assertTrue(report["family_scores_separate"])

    def test_overlap_is_inconclusive_and_invalid_infrastructure_is_retained(self) -> None:
        rows = [
            row(task="a", arm="evolved", score=30),
            row(task="a", arm="cold_ablation", score=20),
            row(task="b", arm="evolved", score=10),
            row(task="b", arm="cold_ablation", score=20),
            ResultRow(
                approach_id="minimal_v2",
                suite_id="ouro_activegraph_50",
                task_id="broken",
                arm="evolved",
                seed=1,
                replication=1,
                score=0,
                maximum_score=50,
                valid=False,
                invalid_reason="grader infrastructure defect",
            ),
        ]
        report = compare(rows, bootstrap_samples=500)
        result = report["families"]["ouro_activegraph_50"]["minimal_v2"]
        self.assertEqual(result["evolved_minus_cold_ablation"]["status"], "no_detected_winner")
        self.assertEqual(report["invalid_infrastructure_rows_retained"], 1)

    def test_recursive_claim_requires_sham_interval_not_only_positive_mean(self) -> None:
        rows = []
        for task, sham_score in (("a", 10), ("b", 49), ("c", 10)):
            rows.extend(
                [
                    row(task=task, arm="evolved", score=45),
                    row(task=task, arm="cold_ablation", score=20),
                    row(task=task, arm="sham_improvement_control", score=sham_score),
                ]
            )
        report = compare(rows, bootstrap_samples=500)
        claim = report["recursive_claims"]["minimal_v2"]
        self.assertFalse(claim["strong_evidence_threshold_met"])
        self.assertEqual(claim["qualifying_families"], [])


if __name__ == "__main__":
    unittest.main()
