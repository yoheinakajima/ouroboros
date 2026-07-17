from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from research.broker import (
    AuthorityBroker,
    AuthorityDenied,
    BrokerBudget,
    BrokerConfig,
    BrokerError,
    BudgetExhausted,
    CompletionRequest,
    CompletionResponse,
    verify_journal,
)
from research.sandbox import SandboxLimits, SandboxResult

IMAGE = "example.invalid/task@sha256:" + "a" * 64


class FakeSandbox:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def run(self, **kwargs):  # type: ignore[no-untyped-def]
        self.calls.append(kwargs)
        return SandboxResult(
            command=tuple(kwargs["command"]),
            image=kwargs["image"],
            returncode=0,
            stdout="ok\n",
            stderr="",
            duration_seconds=0.01,
            timed_out=False,
            output_truncated=False,
            container_name="fake",
        )


class FakeProvider:
    def quote_max_cost(self, request: CompletionRequest) -> float:
        return 0.25

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        return CompletionResponse(text="done", input_tokens=10, output_tokens=2, cost_usd=0.2)


class OverrunProvider(FakeProvider):
    def complete(self, request: CompletionRequest) -> CompletionResponse:
        return CompletionResponse(text="too much", input_tokens=10, output_tokens=6, cost_usd=0.5)


class BrokerTests(unittest.TestCase):
    def make_broker(
        self, root: Path, *, tool_calls: int = 10, model_calls: int = 2
    ) -> tuple[AuthorityBroker, FakeSandbox]:
        workspace = root / "workspace"
        workspace.mkdir()
        trace = root / "manager" / "trace.jsonl"
        sandbox = FakeSandbox()
        broker = AuthorityBroker(
            BrokerConfig(
                workspace=workspace,
                trace_path=trace,
                image=IMAGE,
                budget=BrokerBudget(
                    max_cost_usd=1,
                    max_wall_seconds=60,
                    max_model_calls=model_calls,
                    max_output_tokens=20,
                    max_tool_calls=tool_calls,
                ),
                sandbox_limits=SandboxLimits(),
            ),
            sandbox=sandbox,  # type: ignore[arg-type]
            provider=FakeProvider(),
        )
        return broker, sandbox

    def test_files_commands_and_inference_share_one_budget_and_hash_chain(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            broker, sandbox = self.make_broker(root)
            broker.write_file("src/example.py", "value = 1\n")
            self.assertEqual(broker.read_file("src/example.py"), "value = 1\n")
            broker.replace_file("src/example.py", "1", "2")
            self.assertEqual(broker.list_files(), ["src/example.py"])
            command = broker.run_command(("python", "-m", "pytest", "-q"))
            completion = broker.model_complete(
                CompletionRequest(
                    messages=({"role": "user", "content": "solve"},),
                    model="test-model",
                    max_output_tokens=5,
                )
            )
            verified = verify_journal(root / "manager" / "trace.jsonl")
        self.assertEqual(command.stdout, "ok\n")
        self.assertEqual(completion.text, "done")
        self.assertEqual(len(sandbox.calls), 1)
        self.assertEqual(verified["entries"], 6)
        self.assertEqual(broker.usage.tool_calls, 5)
        self.assertEqual(broker.usage.model_calls, 1)
        self.assertEqual(broker.usage.cost_usd, 0.2)

    def test_denies_path_escapes_private_names_and_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            broker, _ = self.make_broker(root)
            outside = root / "outside.txt"
            outside.write_text("private", encoding="utf-8")
            (root / "workspace" / "link").symlink_to(outside)
            for path in ("../outside.txt", ".env", ".grader/answer", "link"):
                with self.subTest(path=path), self.assertRaises(AuthorityDenied):
                    broker.read_file(path)

    def test_budget_denials_are_recorded_and_cannot_be_retried_for_free(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            broker, _ = self.make_broker(root, tool_calls=1, model_calls=0)
            broker.list_files()
            with self.assertRaises(BudgetExhausted):
                broker.list_files()
            with self.assertRaises(BudgetExhausted):
                broker.model_complete(
                    CompletionRequest(
                        messages=({"role": "user", "content": "solve"},),
                        model="test-model",
                        max_output_tokens=5,
                    )
                )
            rows = [json.loads(line) for line in (root / "manager" / "trace.jsonl").read_text().splitlines()]
        self.assertEqual([row["operation"] for row in rows], ["list_files", "budget_denied", "budget_denied"])

    def test_provider_overrun_is_rejected_but_actual_usage_stays_auditable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            broker, _ = self.make_broker(root)
            broker.provider = OverrunProvider()
            with self.assertRaisesRegex(BrokerError, "actual usage was retained"):
                broker.model_complete(
                    CompletionRequest(
                        messages=({"role": "user", "content": "solve"},),
                        model="test-model",
                        max_output_tokens=5,
                    )
                )
            verified = verify_journal(root / "manager" / "trace.jsonl")
        self.assertEqual(verified["entries"], 1)
        self.assertEqual(broker.usage.model_calls, 1)
        self.assertEqual(broker.usage.output_tokens, 6)
        self.assertEqual(broker.usage.cost_usd, 0.5)


if __name__ == "__main__":
    unittest.main()
