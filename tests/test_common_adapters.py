from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from research.adapters.common import HybridPacksAdapter, MinimalV2Adapter, WorkspaceV12Adapter
from research.broker import (
    AuthorityBroker,
    BrokerBudget,
    BrokerConfig,
    CompletionRequest,
    CompletionResponse,
)
from research.sandbox import SandboxResult

IMAGE = "example.invalid/task@sha256:" + "a" * 64


class ScriptedInference:
    def __init__(self, responses: list[CompletionResponse]) -> None:
        self.responses = responses

    def quote_max_cost(self, request: CompletionRequest) -> float:
        return 0.1

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        if not self.responses:
            raise AssertionError("scripted inference exhausted")
        return self.responses.pop(0)


class ScriptedSandbox:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def run(self, **kwargs):  # type: ignore[no-untyped-def]
        self.calls.append(kwargs)
        return SandboxResult(
            command=tuple(kwargs["command"]),
            image=kwargs["image"],
            returncode=0,
            stdout="1 passed\n",
            stderr="",
            duration_seconds=0.01,
            timed_out=False,
            output_truncated=False,
            container_name="fake",
        )


def response(*, text: str = "", call: dict[str, object] | None = None) -> CompletionResponse:
    return CompletionResponse(
        text=text,
        input_tokens=10,
        output_tokens=5,
        cost_usd=0.05,
        tool_calls=(call,) if call else (),
    )


class CommonAdapterTests(unittest.TestCase):
    def test_shared_agent_uses_only_brokered_files_commands_and_inference(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "workspace"
            workspace.mkdir()
            state = root / "state"
            state.mkdir()
            (state / "MEMORY.md").write_text("Run a focused check after editing.\n", encoding="utf-8")
            sandbox = ScriptedSandbox()
            provider = ScriptedInference(
                [
                    response(
                        call={
                            "id": "write-1",
                            "name": "write_file",
                            "args": {"path": "answer.py", "text": "ANSWER = 42\n"},
                        }
                    ),
                    response(
                        call={
                            "id": "run-1",
                            "name": "run_command",
                            "args": {"argv": ["python", "-m", "pytest", "-q"]},
                        }
                    ),
                    response(text='{"status":"completed","summary":"fixed","evidence":["1 passed"]}'),
                ]
            )
            broker = AuthorityBroker(
                BrokerConfig(
                    workspace=workspace,
                    trace_path=root / "manager" / "trace.jsonl",
                    image=IMAGE,
                    budget=BrokerBudget(
                        max_cost_usd=1,
                        max_wall_seconds=60,
                        max_model_calls=5,
                        max_output_tokens=30_000,
                        max_tool_calls=10,
                    ),
                ),
                sandbox=sandbox,  # type: ignore[arg-type]
                provider=provider,
            )
            adapter = WorkspaceV12Adapter(model="test-model", retained_state=state)
            prepared = adapter.prepare(task={"prompt": "Create answer.py"}, arm="evolved", seed=7)
            outcome = adapter.run(prepared, broker)
            answer_text = (workspace / "answer.py").read_text()
        self.assertEqual(outcome.status, "completed")
        self.assertEqual(outcome.turns, 3)
        self.assertEqual(outcome.tool_calls, 2)
        self.assertEqual(answer_text, "ANSWER = 42\n")
        self.assertEqual(len(sandbox.calls), 1)

    def test_all_arm_semantics_are_explicit_and_state_hash_survives_ablation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = root / "state"
            state.mkdir()
            (state / "MEMORY.md").write_text("useful retained method", encoding="utf-8")
            sham = root / "sham.txt"
            sham.write_text("unrelated retained method", encoding="utf-8")
            adapter = WorkspaceV12Adapter(model="test", retained_state=state, sham_context=sham)
            evolved = adapter.prepare(task={"prompt": "task"}, arm="evolved", seed=1)
            ablated = adapter.prepare(task={"prompt": "task"}, arm="cold_ablation", seed=1)
            cold = adapter.prepare(task={"prompt": "task"}, arm="cold", seed=1)
            control = adapter.prepare(task={"prompt": "task"}, arm="sham_improvement_control", seed=1)
        self.assertEqual(evolved.retained_state_hash, ablated.retained_state_hash)
        self.assertTrue(evolved.retained_state_exposed)
        self.assertFalse(ablated.retained_state_exposed)
        self.assertFalse(cold.retained_state_present)
        self.assertFalse(cold.retained_state_exposed)
        self.assertEqual(control.retained_context, "unrelated retained method")
        self.assertIsNotNone(evolved.exposed_context_sha256)
        self.assertIsNotNone(control.exposed_context_sha256)
        self.assertEqual(control.exposed_context_bytes, len("unrelated retained method"))
        self.assertIsNone(ablated.exposed_context_sha256)

    def test_architecture_specific_state_exports_are_strictly_projected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            minimal = root / "minimal"
            minimal.mkdir()
            (minimal / "state_export.json").write_text(
                json.dumps(
                    {
                        "procedures": [{"name": "focused repair"}],
                        "capabilities": ["normalizer"],
                        "private_history": "must not render",
                    }
                ),
                encoding="utf-8",
            )
            hybrid = root / "hybrid"
            pack = hybrid / "adopted" / "planner" / "1"
            pack.mkdir(parents=True)
            (pack / "manifest.toml").write_text('[pack]\nname="planner"\n', encoding="utf-8")
            (pack / "__init__.py").write_text("def reusable_planning_method(): return 'plan'\n", encoding="utf-8")
            (hybrid / "registry.json").write_text(
                json.dumps(
                    {
                        "adopted": [
                            {
                                "name": "planner",
                                "version": "1.0.0",
                                "bundle_hash": "sha256:x",
                                "path": "adopted/planner/1",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            minimal_prepared = MinimalV2Adapter(model="test", retained_state=minimal).prepare(
                task={"prompt": "task"}, arm="evolved", seed=1
            )
            hybrid_prepared = HybridPacksAdapter(model="test", retained_state=hybrid).prepare(
                task={"prompt": "task"}, arm="evolved", seed=1
            )
        self.assertIn("focused repair", minimal_prepared.retained_context)
        self.assertNotIn("private_history", minimal_prepared.retained_context)
        self.assertIn("planner", hybrid_prepared.retained_context)
        self.assertIn("reusable_planning_method", hybrid_prepared.retained_context)
        self.assertEqual(
            {
                MinimalV2Adapter(model="x").descriptor.broker_protocol_version,
                HybridPacksAdapter(model="x").descriptor.broker_protocol_version,
                WorkspaceV12Adapter(model="x").descriptor.broker_protocol_version,
            },
            {"1.0"},
        )


if __name__ == "__main__":
    unittest.main()
