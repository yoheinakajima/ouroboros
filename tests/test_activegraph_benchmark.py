from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from research.activegraph_benchmark import TASKS, build_cases, build_catalog, materialize, verify

ROOT = Path(__file__).resolve().parents[1]


class ActiveGraphBenchmarkTests(unittest.TestCase):
    def test_catalog_has_two_development_and_three_disjoint_evaluation_tasks(self) -> None:
        catalog = build_catalog()
        self.assertEqual(len(catalog["development"]), 2)
        self.assertEqual(len(catalog["evaluation"]), 3)
        self.assertFalse(set(catalog["development"]) & set(catalog["evaluation"]))
        self.assertTrue(all(row["public_checks"] == 20 for row in catalog["tasks"]))
        self.assertTrue(all(row["sealed_checks"] == 30 for row in catalog["tasks"]))

    def test_every_task_has_exactly_fifty_diverse_checks_and_restart_replay(self) -> None:
        for task in TASKS:
            with self.subTest(task=task.id):
                cases = build_cases(task)
                self.assertEqual(len(cases), 50)
                self.assertEqual(sum(row["visibility"] == "public" for row in cases), 20)
                sealed = [row for row in cases if row["visibility"] == "sealed"]
                self.assertEqual(
                    {row["category"] for row in sealed},
                    {
                        "typed_state",
                        "relations",
                        "policy",
                        "composition",
                        "adversarial",
                        "restart_replay",
                    },
                )
                transfer = [row for row in cases if row["split"] == "transfer"]
                self.assertEqual(transfer[4]["payload"]["operation_id"], transfer[5]["payload"]["operation_id"])
                self.assertNotEqual(transfer[5]["payload"], transfer[6]["payload"])

    def test_seed_is_twenty_and_fixture_oracle_is_fifty(self) -> None:
        report = verify()
        self.assertTrue(report["passed"])
        self.assertEqual(report["model_calls"], 0)
        self.assertTrue(all(row["seed_score"] == 20 for row in report["tasks"]))
        self.assertTrue(all(row["oracle_score"] == 50 for row in report["tasks"]))

    def test_materialized_agent_workspace_contains_no_sealed_cases(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            materialize(root, image="sha256:" + "0" * 64)
            for task in TASKS:
                workspace = root / task.id / "workspace"
                public = json.loads((workspace / "public_cases.json").read_text(encoding="utf-8"))
                self.assertEqual(len(public), 20)
                self.assertTrue(all(row["visibility"] == "public" for row in public))
                self.assertFalse((workspace / "cases.json").exists())
                self.assertFalse((workspace / "grader").exists())

    def test_local_study_probe_is_a_subset_of_held_out_manifests(self) -> None:
        study = json.loads((ROOT / "research/local_study.json").read_text(encoding="utf-8"))
        swe = json.loads((ROOT / "research/selections/swe_verified.json").read_text(encoding="utf-8"))
        terminal = json.loads((ROOT / "research/selections/terminal_bench_2.json").read_text(encoding="utf-8"))
        activegraph = json.loads((ROOT / "research/selections/activegraph_50.json").read_text(encoding="utf-8"))
        probe = study["recursive_probe"]
        self.assertLessEqual(set(probe["swe_verified"]), set(swe["evaluation"]))
        self.assertLessEqual(
            set(probe["terminal_bench_2"]),
            {row["id"] for row in terminal["evaluation"]},
        )
        self.assertLessEqual(set(probe["activegraph_50"]), set(activegraph["evaluation"]))

    def test_selection_manifest_pins_generator_runtime_and_task_contracts(self) -> None:
        selection = json.loads((ROOT / "research/selections/activegraph_50.json").read_text(encoding="utf-8"))
        for key in ("generator", "runtime", "agent_documentation"):
            path = ROOT / selection[key]["path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), selection[key]["sha256"])
        dockerfile = ROOT / selection["container"]["dockerfile"]
        self.assertEqual(
            hashlib.sha256(dockerfile.read_bytes()).hexdigest(),
            selection["container"]["dockerfile_sha256"],
        )
        catalog = {row["id"]: row for row in build_catalog()["tasks"]}
        for task_id, hashes in selection["task_hashes"].items():
            self.assertEqual(catalog[task_id]["contract_sha256"], hashes["contract_sha256"])
            self.assertEqual(catalog[task_id]["cases_sha256"], hashes["cases_sha256"])


if __name__ == "__main__":
    unittest.main()
