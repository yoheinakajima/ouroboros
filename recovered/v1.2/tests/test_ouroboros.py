from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stderr
from decimal import Decimal
from io import StringIO
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ouroboros as ouro  # noqa: E402
from activegraph.llm import LLMResponse, ToolCall  # noqa: E402
from activegraph.llm.errors import LLMBehaviorError  # noqa: E402


def response(*, parsed=None, tool_calls=None, model="scripted-model"):
    return LLMResponse(
        raw_text="",
        parsed=parsed,
        input_tokens=10,
        output_tokens=5,
        cost_usd=Decimal("0"),
        latency_seconds=0.001,
        model=model,
        finish_reason="tool_use" if tool_calls else "end_turn",
        tool_calls=tool_calls,
    )


class ScriptedProvider:
    default_model = "scripted-model"

    def __init__(self, contract, actions=None, fail_generations=None, exhaust_generations=None):
        self.contract = contract
        self.actions = actions or {}
        self.fail_generations = set(fail_generations or [])
        self.exhaust_generations = set(exhaust_generations or [])
        self.builder_calls = {}
        self.call_count = 0
        self.judge_calls = 0
        self.last_private_tests = []

    def complete(self, **kwargs):
        self.call_count += 1
        schema = kwargs.get("output_schema")
        model = kwargs.get("model") or self.default_model
        if schema is ouro.ObjectiveContract:
            return response(parsed=self.contract, model=model)
        if schema is ouro.PrivateSuite:
            if "web" in self.contract.objective.lower():
                private_tests = [
                    ouro.ExecutableTest(
                        id="private-ready-one",
                        kind="entrypoint",
                        description="Entrypoint handles a non-URL readiness probe",
                        stdin={"input": "private readiness one"},
                        expected_exit=0,
                    ),
                    ouro.ExecutableTest(
                        id="private-ready-two",
                        kind="entrypoint",
                        description="Entrypoint handles a second non-URL readiness probe",
                        stdin={"input": "private readiness two"},
                        expected_exit=0,
                    ),
                ]
            else:
                private_tests = [
                    ouro.ExecutableTest(
                        id="private-mixed-case",
                        kind="entrypoint",
                        description="Transforms a mixed-case input with whitespace",
                        stdin={"input": " mixed Case "},
                        stdout_contains=["MIXED CASE"],
                        json_equals={"result": "MIXED CASE"},
                    ),
                    ouro.ExecutableTest(
                        id="private-unicode",
                        kind="entrypoint",
                        description="Transforms Unicode without losing characters",
                        stdin={"input": "café 東京"},
                        stdout_contains=["CAFÉ 東京"],
                        json_equals={"result": "CAFÉ 東京"},
                    ),
                ]
            self.last_private_tests = private_tests
            return response(
                parsed=ouro.PrivateSuite(
                    private_tests=private_tests,
                    coverage_notes=["different inputs from public tests"],
                ),
                model=model,
            )
        if schema is ouro.SuiteReview:
            smoke = self.contract.protocol_smoke_input
            if smoke is None:
                smoke = next(
                    (
                        test.stdin
                        for test in self.contract.public_tests
                        if test.kind == "entrypoint" and test.stdin is not None
                    ),
                    {"input": "scripted smoke"},
                )
            return response(
                parsed=ouro.SuiteReview(
                    public_tests=self.contract.public_tests,
                    private_tests=self.last_private_tests,
                    protocol_smoke_input=smoke,
                    findings=["scripted suites are internally consistent"],
                ),
                model=model,
            )
        if schema is ouro.BuilderSubmission:
            text = "\n".join(str(getattr(message, "content", "")) for message in kwargs.get("messages", []))
            matches = re.findall(r'"generation"\s*:\s*(\d+)', text)
            generation = max(int(value) for value in matches) if matches else 1
            if generation in self.fail_generations:
                raise ConnectionError(f"injected builder failure for generation {generation}")
            turn = self.builder_calls.get(generation, 0)
            self.builder_calls[generation] = turn + 1
            if generation in self.exhaust_generations:
                return response(
                    tool_calls=[
                        ToolCall(
                            id=f"g{generation}-exhaust-{turn}",
                            name="list_tree",
                            args={"path": ""},
                        )
                    ],
                    model=model,
                )
            if turn == 0:
                calls = [
                    ToolCall(id=f"g{generation}-c{index}", name=name, args=args)
                    for index, (name, args) in enumerate(self.actions.get(generation, []), 1)
                ]
                return response(tool_calls=calls, model=model)
            return response(
                parsed=ouro.BuilderSubmission(
                    summary=f"scripted generation {generation}",
                    evidence=["workspace tools completed", "declared tests executed"],
                    next_strategy="inspect any remaining behavioral gaps",
                ),
                model=model,
            )
        if schema is ouro.JudgeResult:
            self.judge_calls += 1
            text = "\n".join(
                str(getattr(message, "content", ""))
                for message in kwargs.get("messages", [])
            )
            case_ids = sorted(
                set(re.findall(r"rubric-\d{3}-view-[12]", text))
            )
            return response(
                parsed=ouro.JudgeResult(
                    scores=[
                        ouro.JudgeCaseScore(
                            case_id=case_id,
                            a_score=90,
                            b_score=90,
                            severe_regression_side="neither",
                            rationale="Both are scored against absolute anchors; deterministic tests distinguish them.",
                        )
                        for case_id in case_ids
                    ],
                    summary="The executed evidence is suitable for the kernel decision.",
                ),
                model=model,
            )
        raise AssertionError(f"unexpected output schema: {schema}")

    def estimate_cost(self, **kwargs):
        return Decimal("0")

    def count_tokens(self, **kwargs):
        return 100


class OpenAICompatibilityTests(unittest.TestCase):
    def test_gpt_5_6_tool_calls_disable_reasoning_only_when_required(self):
        calls = []

        class Completions:
            def create(self, **kwargs):
                calls.append(kwargs)
                return kwargs

        class Client:
            def __init__(self):
                self.chat = type("Chat", (), {"completions": Completions()})()

        proxy = ouro.OpenAICompatibilityClient(Client())
        proxy.chat.completions.create(model="gpt-5.6-sol", tools=[{"type": "function"}])
        proxy.chat.completions.create(model="gpt-5.6-sol", messages=[])
        proxy.chat.completions.create(model="gpt-4o", tools=[{"type": "function"}])

        self.assertEqual(calls[0]["reasoning_effort"], "none")
        self.assertNotIn("reasoning_effort", calls[1])
        self.assertNotIn("reasoning_effort", calls[2])


def base_contract(required=None, tests=None, objective="Build a working multi-file uppercase CLI"):
    return ouro.ObjectiveContract(
        objective=objective,
        deliverable_kind="cli application",
        capability_requirements=["execute a CLI", "produce objective-specific output"],
        public_behavior_spec=["Read JSON from stdin", "Return JSON backed by executed code"],
        entrypoint_protocol="json-stdin/json-stdout",
        required_artifacts=required or ["ouroboros.json", "SELF.md", "MEMORY.md"],
        public_tests=tests or [
            ouro.ExecutableTest(
                id="uppercase-cli",
                kind="entrypoint",
                description="The actual CLI uppercases its input",
                stdin={"input": "hello"},
                stdout_contains=["HELLO"],
                json_equals={"result": "HELLO"},
            )
        ],
        qualitative_rubric=["Correct executable behavior", "Robustness", "Coherent maintainable architecture"],
        success_threshold=70,
        stopping_condition="Stop at the configured generation budget after promotion decisions.",
    )


APP_SOURCE = '''#!/usr/bin/env python3
import json
import sys
from logic import transform

payload = json.loads(sys.stdin.read() or "{}")
print(json.dumps({"result": transform(str(payload.get("input", ""))) }))
'''

LOGIC_SOURCE = '''def transform(value: str) -> str:
    return value.strip().upper()
'''

TEST_SOURCE = '''import unittest
from logic import transform

class TransformTest(unittest.TestCase):
    def test_uppercase(self):
        self.assertEqual(transform(" hello "), "HELLO")
'''


def manifest(entry="app.py"):
    return json.dumps(
        {
            "schema_version": 1,
            "language": "python",
            "entrypoint": ["python", entry],
            "test_command": ["python", "-m", "unittest", "-q"],
            "input_protocol": "json-stdin",
            "output_protocol": "json-stdout",
            "environment": {},
        },
        indent=2,
    )


def successful_actions(extra=None):
    rows = [
        ("write_file", {"path": "logic.py", "content": LOGIC_SOURCE}),
        ("write_file", {"path": "app.py", "content": APP_SOURCE}),
        ("write_file", {"path": "test_app.py", "content": TEST_SOURCE}),
        ("write_file", {"path": "ouroboros.json", "content": manifest()}),
        ("write_file", {"path": "SELF.md", "content": "# Self\n\nMulti-file CLI with tested uppercase transformation.\n"}),
        ("write_file", {"path": "MEMORY.md", "content": "# Memory\n\nExecutable checks are stronger than prose claims.\n"}),
        ("delete_file", {"path": "agent.py"}),
    ]
    rows.extend(extra or [])
    rows.extend(
        [
            ("run_command", {"argv": ["python", "-m", "unittest", "-q"], "timeout_seconds": 15}),
            (
                "submit_candidate",
                {
                    "summary": "Implemented and tested a restructured multi-file CLI",
                    "evidence": ["unittest exit code 0", "manifest points to app.py"],
                    "next_strategy": "add more behavioral cases",
                },
            ),
        ]
    )
    return rows


def make_config(
    root: Path,
    run_id: str,
    *,
    generations=1,
    seed_dir=None,
    allow_network=False,
    max_tool_turns=40,
    max_cost_usd=10.0,
):
    run_dir = root / run_id
    run_dir.mkdir(parents=True)
    return ouro.RunConfig(
        objective="Build a working multi-file uppercase CLI",
        generations=generations,
        run_root=root,
        run_dir=run_dir,
        run_id=run_id,
        seed_dir=seed_dir,
        allow_network=allow_network,
        allow_pip=False,
        provider="anthropic",
        model=None,
        max_tool_turns=max_tool_turns,
        max_tool_calls_per_turn=4,
        max_llm_calls=0,
        max_cost_usd=max_cost_usd,
        max_files=500,
        max_workspace_bytes=5 * 1024 * 1024,
        command_timeout=20,
        test_timeout=10,
        llm_timeout=600,
        memory_mb=1024,
        max_public_regression=0.05,
        max_private_regression=0.05,
        win_margin=2.0,
        export_contract=None,
        quiet=True,
        cli_args={"scripted": True},
    )


class CoreEvolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="ouro-tests-core-")
        cls.root = Path(cls.temp.name)
        cls.provider = ScriptedProvider(
            base_contract(required=["ouroboros.json", "SELF.md", "MEMORY.md", "app.py", "logic.py"]),
            actions={1: successful_actions()},
        )
        cls.config = make_config(cls.root, "multi-file", generations=1)
        cls.result, cls.runtime = ouro.run_engine(cls.config, cls.provider)
        cls.canary = ouro.state().private_canary

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_01_multifile_growth_is_executable(self):
        self.assertEqual(self.result["status"], "completed")
        self.assertEqual(self.result["accepted_generations"], 1)
        final = self.config.run_dir / "final_workspace"
        self.assertTrue((final / "app.py").is_file())
        self.assertTrue((final / "logic.py").is_file())
        proc = subprocess.run(
            [sys.executable, "app.py"],
            cwd=final,
            input=json.dumps({"input": "evidence"}),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["result"], "EVIDENCE")

    def test_02_workspace_restructured_and_manifest_updated(self):
        final = self.config.run_dir / "final_workspace"
        self.assertFalse((final / "agent.py").exists())
        value = json.loads((final / "ouroboros.json").read_text())
        self.assertEqual(value["entrypoint"], ["python", "app.py"])

    def test_03_hidden_canary_never_reaches_builder_or_public_artifacts(self):
        trace = self.config.run_dir / "trace.sqlite"
        conn = sqlite3.connect(trace)
        requested = "\n".join(
            row[0] for row in conn.execute("SELECT payload FROM events WHERE type='llm.requested'")
        )
        conn.close()
        self.assertNotIn(self.canary, requested)
        paths = [
            self.config.run_dir / "objective_contract.json",
            self.config.run_dir / "public_suite.json",
            self.config.run_dir / "generations" / "g001" / "public_results.json",
            self.config.run_dir / "generations" / "g001" / "tool_session.json",
            self.config.run_dir / "final_workspace" / "SELF.md",
            self.config.run_dir / "final_workspace" / "MEMORY.md",
        ]
        for path in paths:
            self.assertNotIn(self.canary, path.read_text(encoding="utf-8"), str(path))

    def test_04_activegraph_trace_integrity_and_lineage(self):
        trace = self.config.run_dir / "trace.sqlite"
        conn = sqlite3.connect(trace)
        self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        event_types = [row[0] for row in conn.execute("SELECT type FROM events ORDER BY seq")]
        payloads = [row[0] for row in conn.execute("SELECT payload FROM events")]
        conn.close()
        self.assertIn("tool.requested", event_types)
        self.assertIn("tool.responded", event_types)
        self.assertEqual(event_types.count(ouro.TERMINAL_EVENT), 1)
        self.assertTrue(any('"type":"file_change"' in payload.replace(" ", "") for payload in payloads))
        self.assertTrue(any('"type":"modified_by"' in payload.replace(" ", "") for payload in payloads))
        lineage = [json.loads(line) for line in (self.config.run_dir / "lineage.jsonl").read_text().splitlines()]
        self.assertTrue(any(row.get("record_type") == "candidate_decision" and row.get("accepted") for row in lineage))

    def test_05_complete_bundle_is_present(self):
        required = [
            "manifest.json",
            "objective_contract.json",
            "public_suite.json",
            "private_suite_receipt.json",
            "history.json",
            "lineage.jsonl",
            "promotion.json",
            "result.json",
            "trace.sqlite",
            "seed_workspace",
            "final_workspace",
        ]
        for relative in required:
            self.assertTrue((self.config.run_dir / relative).exists(), relative)

    def test_05b_private_suite_is_persisted_but_public_surfaces_are_redacted(self):
        private_suite = json.loads(
            (self.config.run_dir / "private" / "private_suite.json").read_text()
        )
        receipt = json.loads(
            (self.config.run_dir / "private_suite_receipt.json").read_text()
        )
        payload = private_suite["tests"]
        self.assertTrue(private_suite["manager_reviewed"])
        self.assertTrue(
            (self.config.run_dir / "private" / "suite_review.json").is_file()
        )
        self.assertEqual(receipt["suite_hash"], ouro.sha256_json(payload))
        public_signatures = {
            ouro.test_semantic_signature(test)
            for test in ouro.state().contract.public_tests
        }
        private_signatures = {
            ouro.test_semantic_signature(ouro.ExecutableTest.model_validate(test))
            for test in payload
        }
        self.assertTrue(private_signatures.isdisjoint(public_signatures))
        redacted = (
            self.config.run_dir / "generations" / "g001" / "private_results.json"
        ).read_text()
        self.assertNotIn("stdout_tail", redacted)
        self.assertNotIn(self.canary, redacted)
        for path in self.config.run_dir.rglob("*"):
            if path.is_file():
                self.assertNotIn(self.canary.encode(), path.read_bytes(), str(path))

    def test_05c_builder_receives_manifest_and_live_budget_contract(self):
        conn = sqlite3.connect(self.config.run_dir / "trace.sqlite")
        payload = conn.execute(
            "SELECT payload FROM events WHERE type=? ORDER BY seq LIMIT 1",
            (f"{ouro.EVENT_PREFIX}.build.requested",),
        ).fetchone()[0]
        conn.close()
        value = json.loads(payload)
        self.assertIn("argv", value["workspace_manifest_contract"]["input_protocol_values"])
        self.assertIn("stdout", value["workspace_manifest_contract"]["output_protocol_values"])
        self.assertEqual(value["budget"]["tool_turns_limit"], self.config.max_tool_turns)
        tool_session = json.loads(
            (self.config.run_dir / "generations" / "g001" / "tool_session.json").read_text()
        )
        self.assertTrue(
            all("ouroboros_budget" in row["result"] for row in tool_session["records"])
        )
        usage = json.loads((self.config.run_dir / "usage.json").read_text())
        self.assertEqual(usage["llm_calls"], self.provider.call_count)
        self.assertEqual(usage["llm_attempts"], self.provider.call_count)
        self.assertEqual(usage["failed_llm_attempts"], 0)
        self.assertEqual(usage["calls_by_phase"]["suite_review"], 1)

    def test_05d_judge_payload_is_per_case_balanced_and_has_no_private_scores(self):
        contract = ouro.state().contract.model_copy(deep=True)
        contract.qualitative_rubric = ["one", "two", "three", "four"]
        cases, mapping = ouro.build_judge_cases(
            contract, {"artifact": "x"}, {"artifact": "y"}, "balance-run", 1
        )
        self.assertEqual(sum(mapping.values()), 4)
        self.assertEqual(len(cases), 8)
        for index in range(1, 5):
            views = [
                mapping[f"rubric-{index:03d}-view-1"],
                mapping[f"rubric-{index:03d}-view-2"],
            ]
            self.assertEqual(sorted(views), [False, True])
        conn = sqlite3.connect(self.config.run_dir / "trace.sqlite")
        payloads = [
            row[0]
            for row in conn.execute(
                "SELECT payload FROM events WHERE type=? ORDER BY seq",
            (f"{ouro.EVENT_PREFIX}.judge.requested",),
            )
        ]
        conn.close()
        self.assertEqual(len(payloads), 2)
        self.assertEqual(self.provider.judge_calls, 2)
        decoded = [json.loads(payload) for payload in payloads]
        self.assertEqual(
            {item["independent_batch"] for item in decoded}, {1, 2}
        )
        case_sets = [
            {case["case_id"] for case in item["cases"]} for item in decoded
        ]
        self.assertTrue(case_sets[0].isdisjoint(case_sets[1]))
        self.assertEqual(set.union(*case_sets), set(ouro.state()._comparison_context["judge_mapping"]))
        for payload in payloads:
            self.assertNotIn("sealed_behavior_pass_rate", payload)
            self.assertIn('"cases"', payload)

    def test_05e_deterministic_dominance_cannot_be_vetoed_by_one_bad_label(self):
        candidate = {
            "public": {"score": 1.0, "hard_gates_passed": True},
            "private": {"score": 1.0},
        }
        incumbent = {
            "public": {"score": 0.0, "hard_gates_passed": False},
            "private": {"score": 0.0},
        }
        judge = {
            "candidate_wins": 3,
            "incumbent_wins": 1,
            "candidate_severe_regression": True,
            "worst_delta": -97.0,
        }
        accepted, reason, metrics = ouro.decide_promotion(
            candidate, incumbent, judge, 80.0, 18.0
        )
        self.assertTrue(accepted)
        self.assertEqual(reason, "execution-grounded deterministic dominance")
        self.assertTrue(metrics["deterministic_dominance"])


class IsolationAndControlTests(unittest.TestCase):
    def test_06_tool_paths_and_secret_environment_are_confined(self):
        with tempfile.TemporaryDirectory(prefix="ouro-isolation-") as temporary:
            root = Path(temporary)
            cfg = make_config(root, "isolation", generations=0)
            candidate = cfg.run_dir / "candidate"
            candidate.mkdir()
            old_state = ouro._STATE
            ouro._STATE = ouro.RunState(config=cfg, candidate_path=candidate)
            os.environ["TEST_SECRET_TOKEN"] = "must-not-leak"
            try:
                outcome = ouro.read_file_tool.fn(ouro.ReadFileInput(path="../outside"), None)
                self.assertFalse(outcome.ok)
                env = ouro.sanitized_environment(candidate)
                self.assertNotIn("TEST_SECRET_TOKEN", env)
                blocked = ouro.execute_process(["curl", "https://example.com"], candidate)
                self.assertTrue(blocked["policy_blocked"])
                if Path("/usr/bin/sandbox-exec").exists():
                    secret_file = Path.home() / ".ouroboros-sandbox-probe"
                    secret_file.write_text("not-readable-from-candidate")
                    try:
                        read_attempt = ouro.execute_process(
                            ["python", "-c", f"open({str(secret_file)!r}).read()"],
                            candidate,
                        )
                        self.assertNotEqual(read_attempt["exit_code"], 0)
                        self.assertNotIn("not-readable-from-candidate", read_attempt["stdout_tail"])
                    finally:
                        secret_file.unlink(missing_ok=True)
            finally:
                os.environ.pop("TEST_SECRET_TOKEN", None)
                ouro._STATE = old_state

    def test_07_noop_rejected_before_judge(self):
        with tempfile.TemporaryDirectory(prefix="ouro-noop-") as temporary:
            root = Path(temporary)
            provider = ScriptedProvider(
                base_contract(required=["ouroboros.json", "SELF.md", "MEMORY.md"]),
                actions={
                    1: [
                        (
                            "submit_candidate",
                            {
                                "summary": "unchanged",
                                "evidence": ["none"],
                                "next_strategy": "make a real change",
                            },
                        )
                    ]
                },
            )
            cfg = make_config(root, "noop", generations=1)
            result, _ = ouro.run_engine(cfg, provider)
            self.assertEqual(result["rejected_generations"], 1)
            self.assertEqual(provider.judge_calls, 0)
            evaluation = json.loads((cfg.run_dir / "generations" / "g001" / "evaluation.json").read_text())
            self.assertIn("no-op", evaluation["reason"])

    def test_08_failure_finalization_keeps_latest_accepted_incumbent(self):
        with tempfile.TemporaryDirectory(prefix="ouro-failure-") as temporary:
            root = Path(temporary)
            provider = ScriptedProvider(
                base_contract(required=["ouroboros.json", "SELF.md", "MEMORY.md", "app.py", "logic.py"]),
                actions={1: successful_actions()},
                fail_generations={2},
            )
            cfg = make_config(root, "failure-after-accept", generations=2)
            result, _ = ouro.run_engine(cfg, provider)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["accepted_generations"], 1)
            final = cfg.run_dir / "final_workspace"
            self.assertTrue((final / "logic.py").exists())
            self.assertFalse((final / "agent.py").exists())
            conn = sqlite3.connect(cfg.run_dir / "trace.sqlite")
            terminal_count = conn.execute("SELECT COUNT(*) FROM events WHERE type=?", (ouro.TERMINAL_EVENT,)).fetchone()[0]
            conn.close()
            self.assertEqual(terminal_count, 1)

    def test_09_long_history_is_exact_but_builder_view_bounded(self):
        history = []
        for generation in range(50):
            history.append(
                {
                    "generation": generation,
                    "accepted": generation % 3 == 0,
                    "reason": "synthetic result " + ("x" * 100),
                    "submission": {"summary": "s" * 500, "next_strategy": "n" * 500},
                    "candidate": {
                        "public": {"score": generation / 50, "test_results": [{"id": "p", "stdout_tail": "y" * 1000}]},
                        "private": {"score": 0.5, "secret": f"private-{generation}"},
                    },
                    "tree_changes": [{"path": f"f{generation}.py", "change": "added"}],
                }
            )
        view = ouro.builder_history_view(history)
        encoded = json.dumps(view)
        self.assertEqual(len(history), 50)
        self.assertLessEqual(len(view["latest_full"]), 3)
        self.assertLessEqual(len(view["preceding_compact"]), 7)
        self.assertEqual(view["archive_summary"]["generation_count"], 40)
        self.assertLess(len(encoded), ouro.MAX_HISTORY_CONTEXT_CHARS + 2000)
        self.assertNotIn("private-", encoded)

    def test_09b_artifact_contract_normalization_drops_prose_alternatives(self):
        self.assertEqual(
            ouro.normalize_required_artifacts(
                [
                    "ouroboros.json",
                    "main.py or equivalent entrypoint file",
                    "At least one additional module file",
                    "README.md with usage instructions",
                ]
            ),
            ["ouroboros.json", "README.md"],
        )


class AdditionalEndToEndTests(unittest.TestCase):
    def test_10_repeated_runs_are_unique_with_stable_seed_hashes(self):
        with tempfile.TemporaryDirectory(prefix="ouro-unique-") as temporary:
            root = Path(temporary)
            results = []
            for run_id in ("same-input-a", "same-input-b"):
                provider = ScriptedProvider(base_contract(required=["ouroboros.json", "SELF.md", "MEMORY.md"]))
                cfg = make_config(root, run_id, generations=0)
                result, _ = ouro.run_engine(cfg, provider)
                results.append((result, cfg))
            self.assertNotEqual(results[0][0]["run_id"], results[1][0]["run_id"])
            promotions = [json.loads((cfg.run_dir / "promotion.json").read_text()) for _, cfg in results]
            self.assertEqual(promotions[0]["seed_content_id"], promotions[1]["seed_content_id"])
            self.assertNotEqual(results[0][1].run_dir / "trace.sqlite", results[1][1].run_dir / "trace.sqlite")

    def test_11_existing_project_evolves_from_seed_dir(self):
        with tempfile.TemporaryDirectory(prefix="ouro-existing-") as temporary:
            root = Path(temporary)
            seed = root / "existing"
            seed.mkdir()
            (seed / "app.py").write_text(
                'import json,sys\np=json.loads(sys.stdin.read() or "{}")\nprint(json.dumps({"result":"wrong"}))\n'
            )
            (seed / "ouroboros.json").write_text(manifest())
            provider = ScriptedProvider(
                base_contract(required=["ouroboros.json", "SELF.md", "MEMORY.md", "app.py", "logic.py"]),
                actions={1: successful_actions(extra=[])},
            )
            cfg = make_config(root, "existing-evolution", generations=1, seed_dir=seed)
            result, _ = ouro.run_engine(cfg, provider)
            self.assertEqual(result["accepted_generations"], 1)
            final = cfg.run_dir / "final_workspace"
            proc = subprocess.run([sys.executable, "app.py"], cwd=final, input='{"input":"fixed"}', text=True, stdout=subprocess.PIPE, timeout=5)
            self.assertEqual(json.loads(proc.stdout)["result"], "FIXED")

    def test_12_meta_candidate_is_recorded_without_overwriting_engine(self):
        with tempfile.TemporaryDirectory(prefix="ouro-meta-") as temporary:
            root = Path(temporary)
            original_hash = ouro.engine_source_hash()
            contract = base_contract(required=["ouroboros.json", "SELF.md", "MEMORY.md", "app.py", "logic.py", "next_ouroboros.py"])
            actions = successful_actions(extra=[("write_file", {"path": "next_ouroboros.py", "content": "# manager-reviewed engine candidate\nprint('next')\n"})])
            provider = ScriptedProvider(contract, actions={1: actions})
            cfg = make_config(root, "meta", generations=1)
            result, _ = ouro.run_engine(cfg, provider)
            self.assertEqual(result["accepted_generations"], 1)
            promotion = json.loads((cfg.run_dir / "promotion.json").read_text())
            self.assertIsNotNone(promotion["next_ouroboros"])
            self.assertTrue(promotion["next_ouroboros"]["manager_release_suite_required"])
            self.assertEqual(ouro.engine_source_hash(), original_hash)

    def test_13_actual_web_behavior_uses_local_http_fixture(self):
        marker = "retrieved-fixture-content-7319"

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                body = marker.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_port}/fact"
        fetcher = '''#!/usr/bin/env python3
import json
import sys
import urllib.request
p = json.loads(sys.stdin.read() or "{}")
url = str(p.get("url", p.get("input", "")))
if url.startswith("http://") or url.startswith("https://"):
    with urllib.request.urlopen(url, timeout=3) as response:
        value = response.read().decode()
else:
    value = "ready"
print(json.dumps({"result": value, "source": url if url.startswith("http") else None}))
'''
        try:
            with tempfile.TemporaryDirectory(prefix="ouro-web-") as temporary:
                root = Path(temporary)
                test = ouro.ExecutableTest(
                    id="real-fetch",
                    kind="entrypoint",
                    description="Fetch a real local HTTP endpoint and cite its content",
                    stdin={"url": url},
                    stdout_contains=[marker, url],
                )
                contract = base_contract(
                    objective="Build an agent that fetches a web page and cites retrieved content",
                    required=["ouroboros.json", "SELF.md", "MEMORY.md", "fetcher.py"],
                    tests=[test],
                )
                actions = [
                    ("write_file", {"path": "fetcher.py", "content": fetcher}),
                    (
                        "write_file",
                        {
                            "path": "test_fetcher.py",
                            "content": """import json, subprocess, sys, unittest

class FetcherTest(unittest.TestCase):
    def test_readiness(self):
        proc = subprocess.run([sys.executable, "fetcher.py"], input=json.dumps({"input": "ready"}), text=True, capture_output=True)
        self.assertEqual(json.loads(proc.stdout)["result"], "ready")
""",
                        },
                    ),
                    ("write_file", {"path": "ouroboros.json", "content": manifest("fetcher.py")}),
                    ("write_file", {"path": "SELF.md", "content": "# Self\n\nHTTP retrieval agent.\n"}),
                    ("write_file", {"path": "MEMORY.md", "content": "# Memory\n\nCite retrieved bytes.\n"}),
                    ("delete_file", {"path": "agent.py"}),
                    ("submit_candidate", {"summary": "real fetcher", "evidence": ["HTTP fixture test"], "next_strategy": "more status handling"}),
                ]
                provider = ScriptedProvider(contract, actions={1: actions})
                cfg = make_config(root, "web", generations=1, allow_network=True)
                cfg.objective = contract.objective
                result, _ = ouro.run_engine(cfg, provider)
                self.assertEqual(result["accepted_generations"], 1)
                proc = subprocess.run(
                    [sys.executable, "fetcher.py"],
                    cwd=cfg.run_dir / "final_workspace",
                    input=json.dumps({"url": url}),
                    text=True,
                    stdout=subprocess.PIPE,
                    timeout=5,
                )
                self.assertIn(marker, proc.stdout)
                self.assertIn(url, proc.stdout)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


class UpgradeRegressionTests(unittest.TestCase):
    def test_14_argv_stdout_manifest_reaches_judge_and_promotes(self):
        cli_source = '''#!/usr/bin/env python3
import json
import sys

if "--help" in sys.argv:
    print("usage: todo.py echo TEXT")
elif len(sys.argv) >= 3 and sys.argv[1] == "echo":
    print(" ".join(sys.argv[2:]).upper())
else:
    payload = json.loads(sys.stdin.read() or "{}")
    print(json.dumps({"result": str(payload.get("input", "")).strip().upper()}))
'''
        argv_manifest = json.dumps(
            {
                "schema_version": 1,
                "language": "python",
                "entrypoint": ["python", "todo.py"],
                "test_command": ["python", "-m", "unittest", "-q"],
                "input_protocol": "argv",
                "output_protocol": "stdout",
                "environment": {},
            },
            indent=2,
        )
        contract = base_contract(
            objective="Build a robust argv command-line application",
            required=["ouroboros.json", "SELF.md", "MEMORY.md", "todo.py"],
            tests=[
                ouro.ExecutableTest(
                    id="argv-echo",
                    kind="command",
                    description="The argv CLI executes a real subcommand",
                    argv=["python", "todo.py", "echo", "hello world"],
                    stdout_contains=["HELLO WORLD"],
                )
            ],
        )
        contract.entrypoint_protocol = "argv/stdout"
        contract.qualitative_rubric = ["correctness", "robustness", "usability", "architecture"]
        actions = [
            ("write_file", {"path": "todo.py", "content": cli_source}),
            (
                "write_file",
                {
                    "path": "test_todo.py",
                    "content": """import subprocess, sys, unittest

class TodoTest(unittest.TestCase):
    def test_help(self):
        proc = subprocess.run([sys.executable, "todo.py", "--help"], text=True, capture_output=True)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("usage:", proc.stdout)
""",
                },
            ),
            ("write_file", {"path": "ouroboros.json", "content": argv_manifest}),
            ("write_file", {"path": "SELF.md", "content": "# Self\n\nArgv CLI.\n"}),
            ("write_file", {"path": "MEMORY.md", "content": "# Memory\n\nExpose --help.\n"}),
            ("delete_file", {"path": "agent.py"}),
            ("run_command", {"argv": ["python", "todo.py", "--help"]}),
            (
                "submit_candidate",
                {
                    "summary": "implemented argv CLI",
                    "evidence": ["--help and echo execute"],
                    "next_strategy": "add commands",
                },
            ),
        ]
        with tempfile.TemporaryDirectory(prefix="ouro-argv-") as temporary:
            root = Path(temporary)
            provider = ScriptedProvider(contract, actions={1: actions})
            cfg = make_config(root, "argv", generations=1)
            cfg.objective = contract.objective
            result, _ = ouro.run_engine(cfg, provider)
            self.assertEqual(result["accepted_generations"], 1)
            self.assertEqual(provider.judge_calls, 2)
            final_manifest = ouro.load_manifest(cfg.run_dir / "final_workspace")
            self.assertEqual(final_manifest.input_protocol, "argv")
            self.assertEqual(final_manifest.output_protocol, "stdout")

    def test_15_capability_gate_stops_before_private_or_builder_spend(self):
        contract = base_contract(objective="Fetch live website content")
        contract.capability_requirements = ["network_access"]
        with tempfile.TemporaryDirectory(prefix="ouro-capability-") as temporary:
            root = Path(temporary)
            provider = ScriptedProvider(contract)
            cfg = make_config(root, "unsupported", generations=1)
            cfg.objective = contract.objective
            result, _ = ouro.run_engine(cfg, provider)
            self.assertEqual(result["status"], "unsupported")
            self.assertEqual(provider.call_count, 1)
            self.assertEqual(provider.builder_calls, {})
            self.assertTrue((cfg.run_dir / "final_workspace" / "agent.py").exists())

    def test_16_recoverable_builder_exhaustion_rejects_then_continues(self):
        with tempfile.TemporaryDirectory(prefix="ouro-recover-") as temporary:
            root = Path(temporary)
            contract = base_contract(
                required=["ouroboros.json", "SELF.md", "MEMORY.md", "app.py", "logic.py"]
            )
            provider = ScriptedProvider(
                contract,
                actions={2: successful_actions()},
                exhaust_generations={1},
            )
            cfg = make_config(root, "recover", generations=2, max_tool_turns=2)
            result, runtime = ouro.run_engine(cfg, provider)
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["rejected_generations"], 1)
            self.assertEqual(result["accepted_generations"], 1)
            self.assertTrue(any(error.reason == "tool.max_turns_exhausted" for error in runtime.errors))
            history = json.loads((cfg.run_dir / "history.json").read_text())
            self.assertIn("failed recoverably", history[1]["reason"])

    def test_17_runtime_budget_has_parallel_margin_and_cost_taxonomy(self):
        with tempfile.TemporaryDirectory(prefix="ouro-cost-") as temporary:
            root = Path(temporary)
            cfg = make_config(root, "cost", generations=2, max_tool_turns=5, max_cost_usd=0.5)
            budget = ouro.derived_runtime_budget(cfg)
            self.assertEqual(budget["max_tool_calls"], 40)
            self.assertEqual(budget["max_llm_calls"], 22)
            self.assertGreaterEqual(budget["max_seconds"], cfg.llm_timeout * 12)

            class ExpensiveProvider(ScriptedProvider):
                def estimate_cost(self, **kwargs):
                    return Decimal("1")

            provider = ExpensiveProvider(base_contract())
            result, _ = ouro.run_engine(cfg, provider)
            self.assertEqual(result["status"], "budget_exhausted")
            self.assertEqual(result["usage"]["llm_calls"], 0)
            self.assertEqual(len(json.loads((cfg.run_dir / "history.json").read_text())), 1)
            for behavior in (
                ouro.compile_objective,
                ouro.compile_private_suite,
                ouro.review_test_suites,
                ouro.build_workspace,
                ouro.judge_workspace,
            ):
                self.assertEqual(behavior.timeout_seconds, cfg.llm_timeout)

    def test_18_run_id_collision_is_clean_and_non_destructive(self):
        with tempfile.TemporaryDirectory(prefix="ouro-collision-") as temporary:
            root = Path(temporary)
            existing = root / "collision"
            existing.mkdir()
            marker = existing / "marker.txt"
            marker.write_text("unchanged")
            stderr = StringIO()
            with redirect_stderr(stderr):
                exit_code = ouro.main(
                    ["objective", "--run-root", str(root), "--run-id", "collision"]
                )
            self.assertEqual(exit_code, 2)
            self.assertIn("already exists", stderr.getvalue())
            self.assertEqual(marker.read_text(), "unchanged")

    def test_19_state_persistence_runs_ordered_steps_in_one_clean_workspace(self):
        source = '''#!/usr/bin/env python3
import json
import pathlib
import sys

path = pathlib.Path("state.json")
values = json.loads(path.read_text()) if path.exists() else []
if sys.argv[1] == "add":
    values.append(sys.argv[2])
    path.write_text(json.dumps(values))
    print("added")
elif sys.argv[1] == "list":
    print(json.dumps({"items": values}))
'''
        with tempfile.TemporaryDirectory(prefix="ouro-state-") as temporary:
            root = Path(temporary)
            run_root = root / "runs"
            cfg = make_config(run_root, "state", generations=0)
            workspace = root / "workspace"
            workspace.mkdir()
            (workspace / "stateful.py").write_text(source)
            (workspace / "ouroboros.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "language": "python",
                        "entrypoint": ["python", "stateful.py"],
                        "test_command": ["python", "-m", "unittest", "-q"],
                        "input_protocol": "argv",
                        "output_protocol": "stdout",
                        "environment": {},
                    }
                )
            )
            test = ouro.ExecutableTest(
                id="persists",
                kind="state_persistence",
                description="A value written by one process is visible to a later process",
                steps=[
                    ouro.StateStep(
                        argv=["python", "stateful.py", "add", "durable"],
                        stdout_contains=["added"],
                    ),
                    ouro.StateStep(
                        argv=["python", "stateful.py", "list"],
                        json_equals={"items": ["durable"]},
                    ),
                ],
            )
            old_state = ouro._STATE
            ouro._STATE = ouro.RunState(config=cfg, candidate_path=workspace)
            try:
                evidence = ouro.execute_test(workspace, ouro.load_manifest(workspace), test)
            finally:
                ouro._STATE = old_state
            self.assertTrue(evidence["passed"], evidence)
            self.assertEqual(len(evidence["steps"]), 2)

    def test_20_protocol_gate_uses_contract_valid_smoke_input(self):
        source = '''#!/usr/bin/env python3
import json
import sys

payload = json.loads(sys.stdin.read())
if not isinstance(payload.get("task"), str) or not isinstance(payload.get("files"), dict):
    raise SystemExit(2)
print(json.dumps({"files": payload["files"]}))
'''
        with tempfile.TemporaryDirectory(prefix="ouro-smoke-") as temporary:
            root = Path(temporary)
            workspace = root / "workspace"
            workspace.mkdir()
            (workspace / "agent.py").write_text(source)
            (workspace / "ouroboros.json").write_text(manifest("agent.py"))
            contract = base_contract(
                tests=[
                    ouro.ExecutableTest(
                        id="schema-input",
                        kind="entrypoint",
                        description="Accept the contract request schema",
                        stdin={"task": "preserve files", "files": {"a.py": "x=1\n"}},
                        json_equals={"files": {"a.py": "x=1\n"}},
                    )
                ]
            )
            cfg = make_config(root, "smoke", generations=0)
            old_state = ouro._STATE
            ouro._STATE = ouro.RunState(config=cfg, contract=contract)
            try:
                passed, evidence = ouro.protocol_gate(
                    workspace, ouro.load_manifest(workspace), contract
                )
            finally:
                ouro._STATE = old_state
            self.assertTrue(passed, evidence)
            expected = json.dumps(contract.public_tests[0].stdin)
            self.assertEqual(
                evidence["smoke_input_sha256"],
                ouro.sha256_bytes(expected.encode()),
            )

    def test_21_declared_unittest_must_discover_a_test(self):
        source = '''#!/usr/bin/env python3
import json
import sys
p = json.loads(sys.stdin.read() or "{}")
print(json.dumps({"result": str(p.get("input", "")).upper()}))
'''
        with tempfile.TemporaryDirectory(prefix="ouro-discovery-") as temporary:
            root = Path(temporary)
            workspace = root / "workspace"
            workspace.mkdir()
            (workspace / "agent.py").write_text(source)
            (workspace / "ouroboros.json").write_text(manifest("agent.py"))
            (workspace / "SELF.md").write_text("# Self\n")
            (workspace / "MEMORY.md").write_text("# Memory\n")
            contract = base_contract()
            cfg = make_config(root, "discovery", generations=0)
            old_state = ouro._STATE
            ouro._STATE = ouro.RunState(config=cfg, contract=contract)
            try:
                empty = ouro.evaluate_workspace(
                    workspace, contract.public_tests, "empty-tests", True
                )
                (workspace / "test_agent.py").write_text(
                    "import unittest\n"
                    "class T(unittest.TestCase):\n"
                    "    def test_one(self): self.assertTrue(True)\n"
                )
                discovered = ouro.evaluate_workspace(
                    workspace, contract.public_tests, "one-test", True
                )
            finally:
                ouro._STATE = old_state
            self.assertFalse(empty["hard_gates"]["declared_tests_discovered"])
            self.assertIn("at least one test", "; ".join(empty["hard_gate_errors"]))
            self.assertTrue(discovered["hard_gates"]["declared_tests_discovered"])
            self.assertEqual(discovered["declared_test"]["discovered_tests"], 1)

    def test_22_suite_structure_rejects_wrappers_and_contradictions(self):
        with tempfile.TemporaryDirectory(prefix="ouro-suite-") as temporary:
            root = Path(temporary)
            cfg = make_config(root, "suite", generations=0)
            old_state = ouro._STATE
            ouro._STATE = ouro.RunState(config=cfg)
            try:
                invalid = [
                    ouro.ExecutableTest(
                        id="wrapped",
                        kind="entrypoint",
                        description="bad wrapper",
                        stdin={"content": '{"input":"hello"}', "mode": "evaluate"},
                    )
                ]
                with self.assertRaisesRegex(ValueError, "serialized JSON"):
                    ouro.normalize_test_suite(
                        invalid, split="public", minimum=1, maximum=12
                    )
                contradictory = ouro.ExecutableTest(
                    id="contradictory",
                    kind="entrypoint",
                    description="cannot both contain and omit a value",
                    stdout_contains=["ready"],
                    stdout_not_contains=["ready"],
                )
                self.assertTrue(ouro.test_definition_errors(contradictory))
                pytest_test = ouro.ExecutableTest(
                    id="pytest",
                    kind="command",
                    description="undeclared dependency",
                    argv=["python", "-m", "pytest", "-q"],
                )
                self.assertIn(
                    "package installation is disabled",
                    "; ".join(ouro.test_definition_errors(pytest_test)),
                )
                serialized = ouro.ExecutableTest(
                    id="serialized-json",
                    kind="entrypoint",
                    description="model serialized a JSON protocol fixture",
                    stdin='{"input":"hello"}',
                )
                normalized = ouro.normalize_test_suite(
                    [serialized],
                    split="public",
                    minimum=1,
                    maximum=12,
                    input_protocol="json-stdin-stdout",
                )
                self.assertEqual(normalized[0].stdin, {"input": "hello"})
            finally:
                ouro._STATE = old_state

    def test_23_manager_review_repairs_compiled_suite_before_execution(self):
        wrapped = ouro.ExecutableTest(
            id="wrapped-public",
            kind="entrypoint",
            description="compiler emitted a serialized wrapper",
            stdin={"content": '{"input":"hello"}', "mode": "evaluate"},
            json_equals={"result": "HELLO"},
        )
        contract = base_contract(tests=[wrapped])

        class RepairingProvider(ScriptedProvider):
            def complete(self, **kwargs):
                if kwargs.get("output_schema") is ouro.SuiteReview:
                    self.call_count += 1
                    return response(
                        parsed=ouro.SuiteReview(
                            public_tests=[
                                ouro.ExecutableTest(
                                    id="repaired-public",
                                    kind="entrypoint",
                                    description="uses the actual request schema",
                                    stdin={"input": "hello"},
                                    json_equals={"result": "HELLO"},
                                )
                            ],
                            private_tests=self.last_private_tests,
                            protocol_smoke_input={"input": "reviewed smoke"},
                            findings=["unwrapped serialized public stdin"],
                        )
                    )
                return super().complete(**kwargs)

        with tempfile.TemporaryDirectory(prefix="ouro-review-") as temporary:
            root = Path(temporary)
            provider = RepairingProvider(contract)
            cfg = make_config(root, "suite-review", generations=0)
            result, _ = ouro.run_engine(cfg, provider)
            self.assertEqual(result["status"], "baseline_only")
            reviewed = json.loads(
                (cfg.run_dir / "objective_contract.json").read_text()
            )
            self.assertEqual(
                reviewed["public_tests"][0]["stdin"], {"input": "hello"}
            )
            self.assertEqual(
                reviewed["protocol_smoke_input"], {"input": "reviewed smoke"}
            )
            audit = json.loads(
                (cfg.run_dir / "private" / "suite_review.json").read_text()
            )
            self.assertIn("unwrapped serialized public stdin", audit["findings"])

    def test_24_manager_suite_parse_failure_retries_once_and_is_accounted(self):
        contract = base_contract()

        class MalformedPrivateOnceProvider(ScriptedProvider):
            def __init__(self, value):
                super().__init__(value)
                self.failed_private_once = False

            def complete(self, **kwargs):
                if (
                    kwargs.get("output_schema") is ouro.PrivateSuite
                    and not self.failed_private_once
                ):
                    self.failed_private_once = True
                    self.call_count += 1
                    raise LLMBehaviorError(
                        "llm.parse_error",
                        "model returned a code expression inside JSON",
                        payload_extras={"raw_text": '"stdin": "x" * 10000'},
                    )
                return super().complete(**kwargs)

        with tempfile.TemporaryDirectory(prefix="ouro-suite-retry-") as temporary:
            root = Path(temporary)
            provider = MalformedPrivateOnceProvider(contract)
            cfg = make_config(root, "suite-retry", generations=0)
            result, runtime = ouro.run_engine(cfg, provider)
            self.assertEqual(result["status"], "baseline_only")
            self.assertTrue(
                any(
                    error.behavior == "compile_private_suite"
                    and error.reason == "llm.parse_error"
                    for error in runtime.errors
                )
            )
            usage = result["usage"]
            self.assertEqual(usage["llm_attempts"], 4)
            self.assertEqual(usage["failed_llm_attempts"], 1)
            self.assertEqual(usage["llm_calls"], 3)
            self.assertEqual(usage["attempts_by_phase"]["private_suite"], 2)
            self.assertEqual(
                usage["failed_attempts_by_phase"]["private_suite"], 1
            )
            conn = sqlite3.connect(cfg.run_dir / "trace.sqlite")
            private_requests = [
                json.loads(row[0])
                for row in conn.execute(
                    "SELECT payload FROM events WHERE type=? ORDER BY seq",
                    (f"{ouro.EVENT_PREFIX}.private.requested",),
                )
            ]
            conn.close()
            self.assertEqual(len(private_requests), 2)
            self.assertEqual(private_requests[1]["retry"], 1)
            self.assertTrue(
                private_requests[1]["literal_json_contract"][
                    "all_values_must_be_literal_json"
                ]
            )

    def test_25_bounded_literal_expression_repair_never_executes_code(self):
        raw_suite = '''```json
{
  "coverage_notes": ["bounded expression fixture"],
  "private_tests": [
    {
      "id": "private-repeat-one",
      "kind": "entrypoint",
      "description": "repeated lowercase input",
      "stdin": {"input": "m" * 5},
      "json_equals": {"result": "M".repeat(5)}
    },
    {
      "id": "private-repeat-two",
      "kind": "entrypoint",
      "description": "concatenated mixed input",
      "stdin": {"input": "ab" + "cd"},
      "json_equals": {"result": "AB" + "CD"}
    }
  ]
}
```'''
        repaired = ouro.repair_structured_expression_response(
            raw_suite, ouro.PrivateSuite
        )
        self.assertIsInstance(repaired, ouro.PrivateSuite)
        self.assertEqual(repaired.private_tests[0].stdin, {"input": "mmmmm"})
        self.assertEqual(
            repaired.private_tests[0].json_equals, {"result": "MMMMM"}
        )
        malicious = (
            '{"coverage_notes": [], "private_tests": '
            '__import__("os").system("touch should-not-exist")}'
        )
        self.assertIsNone(
            ouro.repair_structured_expression_response(
                malicious, ouro.PrivateSuite
            )
        )
        oversized = raw_suite.replace('"m" * 5', '"m" * 1000000000')
        self.assertIsNone(
            ouro.repair_structured_expression_response(
                oversized, ouro.PrivateSuite
            )
        )

        class ExpressionPrivateProvider(ScriptedProvider):
            def __init__(self, value):
                super().__init__(value)
                self.emitted_expression = False

            def complete(self, **kwargs):
                schema = kwargs.get("output_schema")
                if schema is ouro.PrivateSuite and not self.emitted_expression:
                    self.emitted_expression = True
                    self.call_count += 1
                    raise LLMBehaviorError(
                        "llm.parse_error",
                        "model returned bounded literal expressions",
                        payload_extras={"raw_text": raw_suite},
                    )
                if schema is ouro.SuiteReview:
                    self.last_private_tests = ouro.state().private_tests
                return super().complete(**kwargs)

        with tempfile.TemporaryDirectory(prefix="ouro-expression-repair-") as temporary:
            root = Path(temporary)
            provider = ExpressionPrivateProvider(base_contract())
            cfg = make_config(root, "expression-repair", generations=0)
            result, runtime = ouro.run_engine(cfg, provider)
            self.assertEqual(result["status"], "baseline_only")
            self.assertFalse(runtime.errors)
            usage = result["usage"]
            self.assertEqual(usage["llm_attempts"], 3)
            self.assertEqual(usage["llm_calls"], 3)
            self.assertEqual(usage["failed_llm_attempts"], 0)
            self.assertEqual(usage["repaired_llm_outputs"], 1)
            self.assertEqual(usage["unmetered_llm_attempts"], 1)
            conn = sqlite3.connect(cfg.run_dir / "trace.sqlite")
            repaired_events = conn.execute(
                "SELECT COUNT(*) FROM events WHERE type=?",
                (f"{ouro.EVENT_PREFIX}.llm.output_repaired",),
            ).fetchone()[0]
            conn.close()
            self.assertEqual(repaired_events, 1)
            self.assertFalse((Path.cwd() / "should-not-exist").exists())


if __name__ == "__main__":
    unittest.main()
