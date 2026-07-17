from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from research.attempt_runner import TaskSpec, run_attempt
from research.broker import BrokerBudget, CompletionRequest, CompletionResponse
from research.grading import GraderSpec
from research.sandbox import SandboxResult

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "example.invalid/task@sha256:" + "a" * 64
GRADER_IMAGE = "example.invalid/grader@sha256:" + "b" * 64


class ScriptedInference:
    def __init__(self) -> None:
        self.calls = 0

    def quote_max_cost(self, request: CompletionRequest) -> float:
        return 0.0

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.calls += 1
        if self.calls == 1:
            return CompletionResponse(
                text="",
                input_tokens=10,
                output_tokens=5,
                cost_usd=0,
                tool_calls=(
                    {
                        "id": "call-1",
                        "name": "write_file",
                        "args": {"path": "answer.json", "text": "{\"value\": 42}\n"},
                    },
                ),
            )
        return CompletionResponse(
            text=json.dumps({"status": "completed", "summary": "done", "evidence": ["answer.json"]}),
            input_tokens=20,
            output_tokens=10,
            cost_usd=0,
        )


class FakeGraderSandbox:
    def run_grader(self, **kwargs):  # type: ignore[no-untyped-def]
        actual = json.loads((Path(kwargs["submission"]) / "answer.json").read_text())
        passed = actual == {"value": 42}
        score = {
            "run_id": kwargs["environment"]["OUROBOROS_RUN_ID"],
            "grader_id": "fixture",
            "grader_revision": "v1",
            "primary_score": float(passed),
            "passed": passed,
        }
        (Path(kwargs["output_workspace"]) / "score.json").write_text(json.dumps(score), encoding="utf-8")
        return SandboxResult(
            command=tuple(kwargs["command"]),
            image=kwargs["image"],
            returncode=0,
            stdout="",
            stderr="",
            duration_seconds=0.01,
            timed_out=False,
            output_truncated=False,
            container_name="fake-grader",
        )


class AttemptRunnerTests(unittest.TestCase):
    def test_shared_runner_records_attempt_grade_and_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "seed"
            workspace.mkdir()
            (workspace / "README.md").write_text("Write answer.json", encoding="utf-8")
            grader = root / "grader"
            grader.mkdir()
            (grader / "grader.py").write_text("# manager only\n", encoding="utf-8")
            run_dir = root / "runs" / "run-1"
            result = run_attempt(
                repository=ROOT,
                approach_id="minimal_v2",
                arm="cold",
                task_spec=TaskSpec(
                    suite_id="fixture",
                    task_id="answer",
                    prompt="Write answer.json containing value 42.",
                    image=IMAGE,
                ),
                task_workspace=workspace,
                grader_spec=GraderSpec(
                    grader_id="fixture",
                    grader_revision="v1",
                    image=GRADER_IMAGE,
                    command=["python", "grader.py"],
                    minimum_score=0,
                    maximum_score=1,
                ),
                grader_workspace=grader,
                run_dir=run_dir,
                retained_state=None,
                sham_context=None,
                provider_name="openai",
                model="test-model",
                seed=7,
                replication=1,
                budget=BrokerBudget(0, 60, 4, 20_000, 10),
                inference_provider=ScriptedInference(),
                grader_sandbox=FakeGraderSandbox(),
            )
            attempt = json.loads((run_dir / "attempt.json").read_text())
            audit = json.loads((run_dir / "audit.json").read_text())
        self.assertEqual(result["primary_score"], 1.0)
        self.assertTrue(result["passed"])
        self.assertEqual(attempt["usage"]["model_calls"], 2)
        self.assertTrue(audit["valid"])


if __name__ == "__main__":
    unittest.main()
