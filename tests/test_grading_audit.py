from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from research.audit import seal_attempt_bundle
from research.broker import AuthorityBroker, BrokerBudget, BrokerConfig
from research.contracts import AttemptRecord, ResourceUsage
from research.grading import GraderSpec, SealedGrader
from research.sandbox import SandboxResult

IMAGE = "example.invalid/grader@sha256:" + "b" * 64


class FakeGraderSandbox:
    def __init__(self, agent_workspace: Path) -> None:
        self.agent_workspace = agent_workspace
        self.mounted: Path | None = None

    def run_grader(self, **kwargs):  # type: ignore[no-untyped-def]
        workspace = Path(kwargs["grader_workspace"])
        self.mounted = workspace
        if workspace == self.agent_workspace or self.agent_workspace in workspace.parents:
            raise AssertionError("grader received the agent workspace")
        run_id = kwargs["environment"]["OUROBOROS_RUN_ID"]
        score = {
            "run_id": run_id,
            "grader_id": "fixture",
            "grader_revision": "abc123",
            "primary_score": 0.75,
            "passed": True,
            "components": {"checks": 3},
        }
        (Path(kwargs["output_workspace"]) / "score.json").write_text(json.dumps(score), encoding="utf-8")
        return SandboxResult(
            command=tuple(kwargs["command"]),
            image=kwargs["image"],
            returncode=0,
            stdout="graded\n",
            stderr="",
            duration_seconds=0.1,
            timed_out=False,
            output_truncated=False,
            container_name="grader",
        )


class GradingAuditTests(unittest.TestCase):
    def test_sealed_grader_uses_a_distinct_tree_and_pins_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            agent = root / "agent"
            agent.mkdir()
            (agent / "solution.py").write_text("VALUE = 1\n", encoding="utf-8")
            grader_workspace = root / "sealed_grader"
            grader_workspace.mkdir()
            (grader_workspace / "hidden.txt").write_text("EVALUATOR_CANARY", encoding="utf-8")
            sandbox = FakeGraderSandbox(agent)
            score = SealedGrader(
                GraderSpec(
                    grader_id="fixture",
                    grader_revision="abc123",
                    image=IMAGE,
                    command=["python", "grader.py"],
                    minimum_score=0,
                    maximum_score=1,
                ),
                sandbox=sandbox,  # type: ignore[arg-type]
            ).grade(
                run_id="run-1",
                grader_workspace=grader_workspace,
                submission=agent,
                output_dir=root / "result" / "grader",
            )
            receipt = json.loads((root / "result" / "grader" / "grader_receipt.json").read_text())
        self.assertEqual(score.primary_score, 0.75)
        self.assertEqual(sandbox.mounted, grader_workspace.resolve())
        self.assertEqual(receipt["image"], IMAGE)

    def test_attempt_audit_matches_broker_usage_and_detects_private_canary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / "bundle"
            workspace = root / "workspace"
            workspace.mkdir()
            trace = bundle / "trace.jsonl"
            broker = AuthorityBroker(
                BrokerConfig(
                    workspace=workspace,
                    trace_path=trace,
                    image="example.invalid/task@sha256:" + "a" * 64,
                    budget=BrokerBudget(
                        max_cost_usd=0,
                        max_wall_seconds=60,
                        max_model_calls=0,
                        max_output_tokens=0,
                        max_tool_calls=2,
                    ),
                )
            )
            broker.list_files()
            usage = broker.usage
            now = datetime.now(UTC).isoformat()
            attempt = AttemptRecord(
                run_id="run-1",
                approach_id="minimal_v2",
                study_id="common_outcome",
                suite_id="fixture",
                task_id="task",
                arm="cold",
                replication=1,
                seed=1,
                model="test",
                task_image_digest="sha256:image",
                approach_source_hashes={"source": "sha256:x"},
                started_at=now,
                finished_at=now,
                status="completed",
                usage=ResourceUsage.model_validate(usage.model_dump()),
                trace_path="trace.jsonl",
            )
            (bundle / "attempt.json").write_text(attempt.model_dump_json(indent=2), encoding="utf-8")
            report = seal_attempt_bundle(bundle, forbidden_canaries=("EVALUATOR_CANARY",))
            (bundle / "leak.txt").write_text("EVALUATOR_CANARY", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "canary"):
                seal_attempt_bundle(bundle, forbidden_canaries=("EVALUATOR_CANARY",))
        self.assertTrue(report["valid"])
        self.assertEqual(report["journal"]["entries"], 1)


if __name__ == "__main__":
    unittest.main()
