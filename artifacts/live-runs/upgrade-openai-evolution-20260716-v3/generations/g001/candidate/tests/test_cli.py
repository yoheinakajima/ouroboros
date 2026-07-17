"""End-to-end tests for the public argv interface."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "todo.py"


class TodoCLITest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name) / "nested" / "todos.json"

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(LAUNCHER), "--data-file", str(self.state), *args],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )

    def assert_success(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")

    def test_full_persistent_workflow(self) -> None:
        first = self.run_cli("add", " Buy milk ")
        second = self.run_cli("add", "Write tests")
        self.assert_success(first)
        self.assert_success(second)
        self.assertEqual(first.stdout, "Added todo 1: Buy milk\n")
        self.assertEqual(second.stdout, "Added todo 2: Write tests\n")

        result = self.run_cli("done", "1")
        self.assert_success(result)
        self.assertEqual(result.stdout, "Completed todo 1: Buy milk\n")
        pending = self.run_cli("list")
        self.assertEqual(pending.stdout, "[ ] 2: Write tests\n")
        all_items = self.run_cli("list", "--all")
        self.assertEqual(all_items.stdout, "[x] 1: Buy milk\n[ ] 2: Write tests\n")
        stats = self.run_cli("stats")
        self.assertEqual(stats.stdout, "Total: 2\nPending: 1\nCompleted: 1\n")

        state = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(state["next_id"], 3)
        self.assertEqual(len(state["todos"]), 2)

    def test_missing_store_is_empty_and_not_created_by_read(self) -> None:
        listing = self.run_cli("list")
        stats = self.run_cli("stats")
        self.assert_success(listing)
        self.assertEqual(listing.stdout, "No pending todos.\n")
        self.assertEqual(stats.stdout, "Total: 0\nPending: 0\nCompleted: 0\n")
        self.assertFalse(self.state.exists())

    def test_blank_unknown_and_repeated_completion_fail(self) -> None:
        blank = self.run_cli("add", "   ")
        self.assertEqual(blank.returncode, 2)
        self.assertIn("cannot be blank", blank.stderr)
        missing = self.run_cli("done", "999")
        self.assertEqual(missing.returncode, 2)
        self.assertIn("does not exist", missing.stderr)
        self.assert_success(self.run_cli("add", "task"))
        self.assert_success(self.run_cli("done", "1"))
        repeated = self.run_cli("done", "1")
        self.assertEqual(repeated.returncode, 2)
        self.assertIn("already completed", repeated.stderr)

    def test_malformed_state_has_clean_error_and_is_unchanged(self) -> None:
        self.state.parent.mkdir(parents=True)
        original = "{bad json\n"
        self.state.write_text(original, encoding="utf-8")
        result = self.run_cli("stats")
        self.assertEqual(result.returncode, 2)
        self.assertIn("not valid JSON", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(self.state.read_text(encoding="utf-8"), original)

    def test_malformed_id_is_usage_error(self) -> None:
        result = self.run_cli("done", "abc")
        self.assertEqual(result.returncode, 2)
        self.assertIn("positive integer", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_help_documents_commands(self) -> None:
        result = subprocess.run([sys.executable, str(LAUNCHER), "--help"], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0)
        for command in ("add", "list", "done", "stats"):
            self.assertIn(command, result.stdout)


if __name__ == "__main__":
    unittest.main()
