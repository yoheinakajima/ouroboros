from __future__ import annotations

import asyncio
import importlib.util
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

HARBOR_AVAILABLE = importlib.util.find_spec("harbor") is not None


@unittest.skipUnless(HARBOR_AVAILABLE, "Harbor is installed in the isolated benchmark environment")
class HarborAgentTests(unittest.TestCase):
    def test_scripted_run_uses_one_persistent_environment_without_credentials(self) -> None:
        from activegraph.llm import LLMResponse, ToolCall
        from harbor.models.agent.context import AgentContext

        from research.harbor_agent import OuroborosHarborAgent

        class Provider:
            calls = 0

            def count_tokens(self, **_kwargs):
                return 10

            def estimate_cost(self, **_kwargs):
                return Decimal("0.01")

            def complete(self, **_kwargs):
                self.calls += 1
                if self.calls == 1:
                    return LLMResponse(
                        raw_text="",
                        parsed=None,
                        input_tokens=10,
                        output_tokens=5,
                        cost_usd=Decimal("0.001"),
                        latency_seconds=0.01,
                        model="gpt-5.6-sol",
                        finish_reason="tool_use",
                        tool_calls=[ToolCall(id="tool-1", name="run_command", args={"command": "echo ready"})],
                    )
                return LLMResponse(
                    raw_text=json.dumps(
                        {"status": "completed", "summary": "scripted smoke complete", "evidence": ["echo ready"]}
                    ),
                    parsed=None,
                    input_tokens=10,
                    output_tokens=8,
                    cost_usd=Decimal("0.002"),
                    latency_seconds=0.01,
                    model="gpt-5.6-sol",
                    finish_reason="stop",
                )

        class Environment:
            def __init__(self):
                self.commands: list[str] = []

            async def exec(self, *, command: str, timeout_sec: int):
                self.commands.append(command)
                self.timeout_sec = timeout_sec
                return SimpleNamespace(return_code=0, stdout="ready\n", stderr="")

        provider = Provider()
        environment = Environment()
        context = AgentContext()
        with tempfile.TemporaryDirectory() as temporary:
            logs = Path(temporary)
            agent = OuroborosHarborAgent(
                logs_dir=logs,
                model_name="gpt-5.6-sol",
                approach_id="minimal_v2",
                arm="cold",
                repository=Path(__file__).resolve().parents[1].as_posix(),
            )
            with patch("research.harbor_agent.provider_for", return_value=provider):
                asyncio.run(agent.run("Run the scripted smoke.", environment, context))
            trace = [json.loads(line) for line in (logs / "trace.jsonl").read_text().splitlines()]

        self.assertEqual(environment.commands, ["echo ready"])
        self.assertEqual(provider.calls, 2)
        self.assertEqual([row["sequence"] for row in trace], [1, 2, 3])
        self.assertEqual(context.metadata["status"], "completed")
        self.assertTrue(context.metadata["persistent_environment"])
        self.assertFalse(context.metadata["provider_credentials_forwarded"])


if __name__ == "__main__":
    unittest.main()
