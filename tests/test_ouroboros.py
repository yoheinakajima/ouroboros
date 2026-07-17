from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from decimal import Decimal
from pathlib import Path
from typing import Any

from activegraph.llm import LLMResponse, ToolCall

import ouroboros
from ouroboros import (
    AgentResult,
    Config,
    ExampleCase,
    MutationDraft,
    Ouroboros,
    load_env_file,
    validate_mutation,
)


def response(*, parsed: Any = None, tool_calls: list[ToolCall] | None = None) -> LLMResponse:
    return LLMResponse(
        raw_text="" if parsed is not None else "tool",
        parsed=parsed,
        input_tokens=20,
        output_tokens=10,
        cost_usd=Decimal("0.001"),
        latency_seconds=0.01,
        model="test-model",
        finish_reason="tool_calls" if tool_calls else "stop",
        tool_calls=tool_calls,
    )


class ScriptedProvider:
    default_model = "test-model"

    def __init__(self, responses: list[LLMResponse]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def complete(self, **kwargs: Any) -> LLMResponse:
        self.calls.append(kwargs)
        if not self.responses:
            raise AssertionError("scripted provider exhausted")
        return self.responses.pop(0)

    def estimate_cost(self, *, input_tokens: int, output_tokens: int, model: str) -> Decimal:
        return Decimal("0.001")

    def count_tokens(self, *, system: str, messages: list[Any], model: str) -> int:
        return 100

    def recognizes_model(self, model: str) -> bool:
        return True

    def supports_native_structured_output(self, model: str) -> bool:
        return True


class OuroborosTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.workspace = self.root / "workspace"
        self.state = self.root / "state"
        self.workspace.mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def config(self) -> Config:
        return Config(
            workspace=self.workspace,
            state_dir=self.state,
            provider="openai",
            model="test-model",
            max_tool_turns=8,
            command_timeout=30,
        )

    def test_goal_trace_evaluation_and_procedure_learning(self) -> None:
        provider = ScriptedProvider(
            [
                response(
                    parsed=AgentResult(
                        status="completed",
                        summary="Delivered the answer.",
                        evidence=["direct result"],
                        procedure_name="verify then answer",
                        procedure_trigger_terms=["verify", "answer"],
                        procedure_steps=["Check the evidence.", "Return the result."],
                    )
                )
            ]
        )
        organism = Ouroboros(self.config(), llm_provider=provider)
        result = organism.run_goal("Verify and answer this question")

        self.assertTrue(result["passed"])
        self.assertTrue(result["procedure_id"])
        self.assertEqual(result["response"], "Delivered the answer.")
        types = [event.type for event in organism.runtime.graph.events]
        self.assertIn("llm.requested", types)
        self.assertIn("llm.responded", types)
        self.assertIn("context.read", types)
        self.assertEqual(len(ouroboros.graph_objects(organism.runtime, "goal")), 1)
        self.assertEqual(len(ouroboros.graph_objects(organism.runtime, "evaluation")), 1)
        self.assertEqual(len(ouroboros.graph_objects(organism.runtime, "procedure")), 1)

    def test_coding_agent_tool_loop_edits_workspace_and_check_is_authority(self) -> None:
        provider = ScriptedProvider(
            [
                response(
                    tool_calls=[
                        ToolCall(
                            id="write-1",
                            name="write_file",
                            args={"path": "answer.txt", "content": "working\n"},
                        )
                    ]
                ),
                response(
                    parsed=AgentResult(
                        status="completed",
                        summary="Created answer.txt.",
                        evidence=["write_file succeeded"],
                    )
                ),
            ]
        )
        organism = Ouroboros(self.config(), llm_provider=provider)
        result = organism.run_goal(
            "Create answer.txt containing working",
            check_command=[
                sys.executable,
                "-c",
                "from pathlib import Path; assert Path('answer.txt').read_text() == 'working\\n'",
            ],
        )

        self.assertTrue(result["passed"])
        self.assertEqual((self.workspace / "answer.txt").read_text(), "working\n")
        self.assertEqual(result["check"]["data"]["exit_code"], 0)
        types = [event.type for event in organism.runtime.graph.events]
        self.assertIn("tool.requested", types)
        self.assertIn("tool.responded", types)

    def test_failed_external_check_overrules_agent_claim_and_blocks_learning(self) -> None:
        provider = ScriptedProvider(
            [
                response(
                    parsed=AgentResult(
                        status="completed",
                        summary="I claim success.",
                        procedure_name="unearned",
                        procedure_trigger_terms=["claim"],
                        procedure_steps=["Claim it worked."],
                    )
                )
            ]
        )
        organism = Ouroboros(self.config(), llm_provider=provider)
        result = organism.run_goal(
            "Do something verifiable",
            check_command=[sys.executable, "-c", "raise SystemExit(7)"],
        )

        self.assertFalse(result["passed"])
        self.assertEqual(result["check"]["data"]["exit_code"], 7)
        self.assertEqual(ouroboros.graph_objects(organism.runtime, "procedure"), [])

    def test_restart_retrieves_learned_procedure(self) -> None:
        first_provider = ScriptedProvider(
            [
                response(
                    parsed=AgentResult(
                        status="completed",
                        summary="Fixed it.",
                        procedure_name="python traceback repair",
                        procedure_trigger_terms=["python", "traceback", "repair"],
                        procedure_steps=["Read the traceback.", "Run the focused test."],
                    )
                )
            ]
        )
        first = Ouroboros(self.config(), llm_provider=first_provider)
        self.assertTrue(first.run_goal("Repair this Python traceback")["passed"])

        second_provider = ScriptedProvider(
            [
                response(
                    parsed=AgentResult(
                        status="completed",
                        summary="Used prior experience.",
                    )
                )
            ]
        )
        second = Ouroboros(self.config(), llm_provider=second_provider)
        result = second.run_goal("Repair another Python traceback")

        self.assertTrue(result["passed"])
        rendered = "\n".join(
            str(message.content)
            for call in second_provider.calls
            for message in call.get("messages", [])
        )
        self.assertIn("python traceback repair", rendered)
        self.assertEqual(second.runtime.run_id, first.runtime.run_id)

    def test_procedure_ablation_preserves_state_but_hides_retrieval(self) -> None:
        first_provider = ScriptedProvider(
            [
                response(
                    parsed=AgentResult(
                        status="completed",
                        summary="Learned it.",
                        procedure_name="private repair method",
                        procedure_trigger_terms=["repair"],
                        procedure_steps=["Use the retained method."],
                    )
                )
            ]
        )
        first = Ouroboros(self.config(), llm_provider=first_provider)
        self.assertTrue(first.run_goal("Repair the fixture")["passed"])

        ablated_config = self.config()
        ablated_config.use_procedures = False
        second_provider = ScriptedProvider(
            [response(parsed=AgentResult(status="completed", summary="Cold result."))]
        )
        second = Ouroboros(ablated_config, llm_provider=second_provider)
        self.assertEqual(second.relevant_procedures("repair"), [])
        self.assertIn("private repair method", second.summary()["procedures"])
        second.run_goal("Repair another fixture")
        rendered = "\n".join(
            str(message.content)
            for call in second_provider.calls
            for message in call.get("messages", [])
        )
        self.assertNotIn("private repair method", rendered)

    def test_promotion_ablation_does_not_import_retained_capability(self) -> None:
        provider = ScriptedProvider([response(parsed=self.slug_draft())])
        promoted = Ouroboros(self.config(), llm_provider=provider)
        self.assertTrue(promoted.teach("Learn slugification", self.slug_cases())["promoted"])

        ablated = Ouroboros(
            self.config(),
            llm_provider=ScriptedProvider([]),
            load_promotions=False,
        )
        self.assertNotIn("slugify_text", ablated.host.capabilities)
        self.assertIn("slugify_text", ablated.summary()["capabilities"])
        self.assertFalse(ablated.summary()["promotion_loading_enabled"])

    def slug_cases(self) -> list[ExampleCase]:
        return [
            ExampleCase(input={"text": "Hello World"}, expected={"value": "hello-world"}),
            ExampleCase(input={"text": "Already-slug"}, expected={"value": "already-slug"}),
            ExampleCase(input={"text": "Spaces   Here"}, expected={"value": "spaces-here"}),
            ExampleCase(input={"text": "Symbols & More!"}, expected={"value": "symbols-more"}),
            ExampleCase(input={"text": "  Trim Me  "}, expected={"value": "trim-me"}),
            ExampleCase(input={"text": "MIXED_case"}, expected={"value": "mixed-case"}),
        ]

    def slug_draft(self) -> MutationDraft:
        return MutationDraft(
            capability_name="slugify_text",
            description="Convert text to a lowercase ASCII-style slug.",
            implementation_source=(
                "import re\n\n"
                "def implementation(payload):\n"
                "    text = str(payload.get('text', '')).lower()\n"
                "    value = re.sub(r'[^a-z0-9]+', '-', text).strip('-')\n"
                "    return {'value': value}\n"
            ),
            rationale="A general regex transformation covers the examples.",
        )

    def test_teach_trials_promotes_invokes_and_survives_restart(self) -> None:
        provider = ScriptedProvider([response(parsed=self.slug_draft())])
        organism = Ouroboros(self.config(), llm_provider=provider)
        result = organism.teach("Learn a reliable slugify capability", self.slug_cases())

        self.assertTrue(result["promoted"], result)
        self.assertEqual(result["training_count"], 3)
        self.assertEqual(result["heldout_count"], 3)
        invocation = organism.host.invoke_capability(
            "slugify_text", {"text": "A New Example!!!"}
        )
        self.assertTrue(invocation.ok)
        self.assertEqual(invocation.data["result"], {"value": "a-new-example"})
        self.assertIn("promote.applied", [event.type for event in organism.runtime.graph.events])

        reuse_provider = ScriptedProvider(
            [
                response(
                    tool_calls=[
                        ToolCall(
                            id="cap-1",
                            name="invoke_capability",
                            args={
                                "capability": "slugify_text",
                                "payload": {"text": "Used By Agent"},
                            },
                        )
                    ]
                ),
                response(
                    parsed=AgentResult(
                        status="completed",
                        summary="The promoted capability returned used-by-agent.",
                        evidence=["invoke_capability succeeded"],
                    )
                ),
            ]
        )
        reopened = Ouroboros(self.config(), llm_provider=reuse_provider)
        self.assertIn("slugify_text", reopened.host.capabilities)
        again = reopened.host.invoke_capability("slugify_text", {"text": "Restart Works"})
        self.assertEqual(again.data["result"], {"value": "restart-works"})
        reused = reopened.run_goal("Use the learned slugifier on Used By Agent")
        self.assertTrue(reused["passed"])
        self.assertIn("used-by-agent", reused["response"])

    def test_heldout_failure_rejects_mutation_without_parent_promotion(self) -> None:
        training, heldout = Ouroboros.split_examples(self.slug_cases())
        lookup = {
            case.input["text"]: case.expected["value"]
            for case in training
        }
        bad_source = (
            "def implementation(payload):\n"
            f"    known = {lookup!r}\n"
            "    return {'value': known.get(payload.get('text'), 'wrong')}\n"
        )
        draft = MutationDraft(
            capability_name="memorized_slug",
            description="Bad memorizer.",
            implementation_source=bad_source,
            rationale="Overfit on purpose for the test.",
        )
        provider = ScriptedProvider([response(parsed=draft)])
        organism = Ouroboros(self.config(), llm_provider=provider)
        result = organism.teach("Try to memorize slug examples", training + heldout)

        self.assertFalse(result["promoted"])
        self.assertEqual(result["stage"], "heldout_trial")
        self.assertNotIn("memorized_slug", organism.host.capabilities)
        self.assertNotIn("promote.applied", [event.type for event in organism.runtime.graph.events])

    def test_static_mutation_gate_rejects_external_effect_imports(self) -> None:
        draft = MutationDraft(
            capability_name="unsafe_tool",
            description="Unsafe",
            implementation_source=(
                "import os\n\n"
                "def implementation(payload):\n"
                "    return {'home': os.environ.get('HOME')}\n"
            ),
            rationale="Unsafe",
        )
        failures = validate_mutation(draft)
        self.assertIn("import 'os' is not allowed", failures)

    def test_dotenv_loader_never_overwrites_existing_values(self) -> None:
        env_file = self.root / ".env"
        env_file.write_text("OURO_TEST_A='from-file'\nexport OURO_TEST_B=second\n")
        old_a = os.environ.get("OURO_TEST_A")
        old_b = os.environ.get("OURO_TEST_B")
        try:
            os.environ["OURO_TEST_A"] = "existing"
            os.environ.pop("OURO_TEST_B", None)
            loaded = load_env_file(env_file)
            self.assertEqual(os.environ["OURO_TEST_A"], "existing")
            self.assertEqual(os.environ["OURO_TEST_B"], "second")
            self.assertEqual(loaded, ["OURO_TEST_B"])
        finally:
            if old_a is None:
                os.environ.pop("OURO_TEST_A", None)
            else:
                os.environ["OURO_TEST_A"] = old_a
            if old_b is None:
                os.environ.pop("OURO_TEST_B", None)
            else:
                os.environ["OURO_TEST_B"] = old_b

    def test_secret_files_are_hidden_from_model_file_and_command_tools(self) -> None:
        secret = self.workspace / ".env"
        secret.write_text("FAKE_API_KEY=do-not-read\n")
        organism = Ouroboros(self.config(), llm_provider=ScriptedProvider([]))

        listing = organism.host.list_files(".")
        self.assertNotIn(".env", listing.data["files"])
        with self.assertRaisesRegex(ValueError, "private credentials"):
            organism.host.read_file(".env")
        self.assertNotIn("FAKE_API_KEY", json.dumps(organism.host.command_environment()))
        if Path("/usr/bin/sandbox-exec").exists():
            command = organism.host.run_command(
                ouroboros.RunCommandInput(
                    argv=[
                        sys.executable,
                        "-c",
                        "from pathlib import Path; Path('.env').read_text()",
                    ]
                )
            )
            self.assertFalse(command.ok, command)
            self.assertEqual(command.data.get("isolation"), "macos-seatbelt")
            devnull = organism.host.run_command(
                ouroboros.RunCommandInput(
                    argv=[
                        sys.executable,
                        "-c",
                        "open('/dev/null', 'w').write('ok')",
                    ]
                )
            )
            self.assertTrue(devnull.ok, devnull)

    def test_inspect_is_offline_and_does_not_reload_mutation_code(self) -> None:
        provider = ScriptedProvider(
            [response(parsed=AgentResult(status="completed", summary="Hello"))]
        )
        organism = Ouroboros(self.config(), llm_provider=provider)
        organism.run_goal("Say hello", mode="chat")
        old_openai = os.environ.pop("OPENAI_API_KEY", None)
        old_anthropic = os.environ.pop("ANTHROPIC_API_KEY", None)
        old_cwd = Path.cwd()
        try:
            os.chdir(self.root)
            output = io.StringIO()
            with redirect_stdout(output):
                code = ouroboros.main(
                    [
                        "--inspect",
                        "--workspace",
                        str(self.workspace),
                        "--state-dir",
                        str(self.state),
                    ]
                )
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output.getvalue())["run_id"], organism.runtime.run_id)
        finally:
            os.chdir(old_cwd)
            if old_openai is not None:
                os.environ["OPENAI_API_KEY"] = old_openai
            if old_anthropic is not None:
                os.environ["ANTHROPIC_API_KEY"] = old_anthropic

    def test_summary_is_graph_derived_and_has_no_pack_library_dependency(self) -> None:
        provider = ScriptedProvider(
            [response(parsed=AgentResult(status="completed", summary="Hello"))]
        )
        organism = Ouroboros(self.config(), llm_provider=provider)
        organism.run_goal("Say hello", mode="chat")
        summary = organism.summary()

        self.assertEqual(summary["run_id"], organism.runtime.run_id)
        self.assertEqual(summary["objects"]["attempt"], 1)
        requirements = (Path(__file__).parents[1] / "requirements.txt").read_text()
        self.assertNotIn("activegraph-packs", requirements)
        self.assertNotIn("activegraph_packs", Path(ouroboros.__file__).read_text())


if __name__ == "__main__":
    unittest.main()
