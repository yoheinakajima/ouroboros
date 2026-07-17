"""Subprocess integration tests for persistent CLI behavior."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "todo.py"


class TodoCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.state = Path(self.temporary.name) / "state.json"

    def run_cli(self, *args: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(ENTRYPOINT), "--data-file", str(self.state), *args],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        self.assertEqual(expected, result.returncode, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stdout + result.stderr)
        return result

    def test_add_list_done_stats_persist(self) -> None:
        self.assertIn("Added #1: Buy milk", self.run_cli("add", "  Buy milk  ").stdout)
        self.assertIn("Added #2: Write tests", self.run_cli("add", "Write tests").stdout)
        listing = self.run_cli("list").stdout
        self.assertIn("[ ] #1 Buy milk", listing)
        self.assertIn("[ ] #2 Write tests", listing)
        self.assertIn("Completed #1: Buy milk", self.run_cli("done", "1").stdout)
        self.assertIn("[x] #1 Buy milk", self.run_cli("list").stdout)
        stats = self.run_cli("stats").stdout
        self.assertIn("Total: 2", stats)
        self.assertIn("Pending: 1", stats)
        self.assertIn("Completed: 1", stats)
        state = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(3, state["next_id"])

    def test_errors(self) -> None:
        missing = self.run_cli("done", "404", expected=1)
        self.assertIn("Error: todo #404 not found", missing.stdout)
        blank = self.run_cli("add", "   ", expected=2)
        self.assertIn("Error:", blank.stdout)
        self.assertFalse(self.state.exists())
        self.state.write_text("not JSON", encoding="utf-8")
        malformed = self.run_cli("list", expected=1)
        self.assertIn("Error:", malformed.stdout)
        self.assertEqual("not JSON", self.state.read_text(encoding="utf-8"))

    def test_empty_and_already_done(self) -> None:
        self.assertEqual("No todos.\n", self.run_cli("list").stdout)
        self.run_cli("add", "one")
        self.run_cli("done", "1")
        self.assertIn("already completed", self.run_cli("done", "1", expected=1).stdout)

    def test_invalid_arguments_are_usage_errors(self) -> None:
        result = self.run_cli("done", "zero", expected=2)
        self.assertIn("Error:", result.stdout)
        result = subprocess.run([sys.executable, str(ENTRYPOINT)], cwd=ROOT,
                                text=True, capture_output=True, check=False)
        self.assertEqual(2, result.returncode)
        self.assertIn("Error:", result.stdout)


if __name__ == "__main__":
    unittest.main()
