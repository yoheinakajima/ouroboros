from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ouroboros import ExampleCase  # noqa: E402
from research import validate_research as research_validation  # noqa: E402
from research.hybrid_author import load_task  # noqa: E402
from research.minimal_adapter import prepare_splits  # noqa: E402
from research.validate_research import validate_repository  # noqa: E402


class ResearchProtocolTests(unittest.TestCase):
    @staticmethod
    def _copy_protocol_repository(destination: Path) -> None:
        (destination / "research").mkdir(parents=True)
        (destination / "evidence").mkdir()
        for relative in ("research/benchmark.json", "research/run_index.json", "evidence/pilot_summary.json"):
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        shutil.copytree(ROOT / "research" / "tasks", destination / "research" / "tasks")
        shutil.copy2(ROOT / "TEST_REPORT.md", destination / "TEST_REPORT.md")

    @staticmethod
    def _read_json(path: Path):
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _write_json(path: Path, value) -> None:
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

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
        self.assertTrue(
            all(
                row["source_result_sha256"].startswith("sha256:")
                for row in summary["valid_graph_audited_hybrid_runs"] + summary["valid_portable_runs"]
            )
        )

    def test_curated_fallback_is_limited_to_declared_local_or_release_raw_artifacts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._copy_protocol_repository(root)
            index_path = root / "research" / "run_index.json"
            index = self._read_json(index_path)
            index["raw_artifacts"] = "committed"
            self._write_json(index_path, index)
            with self.assertRaisesRegex(ValueError, "result is missing or escapes the repository"):
                validate_repository(root)

    def test_curated_fallback_rejects_missing_or_invalid_source_hash(self):
        for source_hash in (None, "bcb2cd379cda2c4d"):
            with self.subTest(source_hash=source_hash), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                self._copy_protocol_repository(root)
                summary_path = root / "evidence" / "pilot_summary.json"
                summary = self._read_json(summary_path)
                row = next(item for item in summary["runs"] if item["id"] == "hybrid-usage-gpt56-v4")
                if source_hash is None:
                    row.pop("source_result_sha256")
                else:
                    row["source_result_sha256"] = source_hash
                self._write_json(summary_path, summary)
                with self.assertRaisesRegex(ValueError, "invalid source_result_sha256"):
                    validate_repository(root)

    def test_curated_fallback_rejects_index_summary_mismatch(self):
        for field, value in (("task", "wrong-task"), ("approach", "wrong-approach")):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                self._copy_protocol_repository(root)
                summary_path = root / "evidence" / "pilot_summary.json"
                summary = self._read_json(summary_path)
                row = next(item for item in summary["runs"] if item["id"] == "hybrid-usage-gpt56-v4")
                row[field] = value
                self._write_json(summary_path, summary)
                with self.assertRaisesRegex(ValueError, f"run-index/curated {field} mismatch"):
                    validate_repository(root)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._copy_protocol_repository(root)
            summary_path = root / "evidence" / "pilot_summary.json"
            summary = self._read_json(summary_path)
            summary["primary_model"] = "wrong-model"
            self._write_json(summary_path, summary)
            with self.assertRaisesRegex(ValueError, "benchmark/curated primary_model mismatch"):
                validate_repository(root)

    def test_curated_fallback_rejects_invalid_scores_and_cost(self):
        for field, value in (("public", "3"), ("private", "5/4"), ("transfer", None), ("cost_usd", -1)):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                self._copy_protocol_repository(root)
                summary_path = root / "evidence" / "pilot_summary.json"
                summary = self._read_json(summary_path)
                row = next(item for item in summary["runs"] if item["id"] == "hybrid-usage-gpt56-v4")
                row[field] = value
                self._write_json(summary_path, summary)
                expected = "invalid cost_usd" if field == "cost_usd" else f"invalid {field} score"
                with self.assertRaisesRegex(ValueError, expected):
                    validate_repository(root)

    def test_raw_result_must_match_curated_hash_and_fields(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._copy_protocol_repository(root)
            index = self._read_json(root / "research" / "run_index.json")
            index_row = next(item for item in index["runs"] if item["id"] == "hybrid-usage-gpt56-v4")
            result_path = root / index_row["result"]
            result_path.parent.mkdir(parents=True)
            result_path.write_text("{}\n", encoding="utf-8")

            summary_path = root / "evidence" / "pilot_summary.json"
            summary = self._read_json(summary_path)
            curated_row = next(item for item in summary["runs"] if item["id"] == index_row["id"])
            actual_hash = "sha256:" + hashlib.sha256(result_path.read_bytes()).hexdigest()
            curated_row["source_result_sha256"] = actual_hash
            self._write_json(summary_path, summary)
            raw_row = {
                "approach": "hybrid_docs_grounded_pack",
                "task_id": "stateful_usage_tracker",
                "public": "3/3",
                "private": "4/4",
                "transfer": "3/3",
                "cost_usd": "0.160610",
                "model": "gpt-5.6-sol",
            }
            with mock.patch.object(research_validation, "_validate_hybrid_run", return_value=raw_row):
                validate_repository(root)

            curated_row["source_result_sha256"] = "sha256:" + "0" * 64
            self._write_json(summary_path, summary)
            with (
                mock.patch.object(research_validation, "_validate_hybrid_run", return_value=raw_row),
                self.assertRaisesRegex(ValueError, "raw-result hash mismatch"),
            ):
                validate_repository(root)

            curated_row["source_result_sha256"] = actual_hash
            self._write_json(summary_path, summary)
            mismatched = {**raw_row, "public": "2/3"}
            with (
                mock.patch.object(research_validation, "_validate_hybrid_run", return_value=mismatched),
                self.assertRaisesRegex(ValueError, "raw-result/curated public mismatch"),
            ):
                validate_repository(root)


if __name__ == "__main__":
    unittest.main()
