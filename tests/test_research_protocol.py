from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ouroboros import ExampleCase  # noqa: E402
from research.hybrid_author import load_task  # noqa: E402
from research.minimal_adapter import prepare_splits  # noqa: E402
from research.validate_research import validate_repository  # noqa: E402


class ResearchProtocolTests(unittest.TestCase):
    def test_minimal_adapter_uses_the_exact_benchmark_hidden_split(self):
        task = load_task(ROOT / "research" / "tasks" / "nested_record_normalizer.json")
        raw = json.loads((ROOT / "research" / "examples" / "nested_record_normalizer.json").read_text())
        examples = [ExampleCase.model_validate(item) for item in raw]
        training, heldout = prepare_splits(task, examples)
        self.assertEqual((len(training), len(heldout)), (4, 4))

    def test_catalog_and_indexed_evidence_are_internally_consistent(self):
        summary = validate_repository(ROOT)
        self.assertEqual(summary["benchmark_tasks"], 9)
        self.assertEqual(
            summary["implemented_tasks"],
            ["nested_record_normalizer", "stateful_usage_tracker", "dependency_release_planner"],
        )
        self.assertEqual(len(summary["valid_graph_audited_hybrid_runs"]), 2)
        self.assertEqual(len(summary["valid_portable_runs"]), 2)
        self.assertTrue(
            all(row["model"] == "gpt-5.6-sol" for row in summary["valid_graph_audited_hybrid_runs"])
        )


if __name__ == "__main__":
    unittest.main()
