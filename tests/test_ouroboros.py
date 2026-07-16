"""End-to-end and unit tests for the Ouroboros workspace-evolution engine.

Most tests drive a deterministic ScriptedProvider so real tool bodies,
subprocess execution, evaluation, and the ActiveGraph trace are exercised
without a live model. One optional test runs a live model end-to-end when
ANTHROPIC_API_KEY is set.

Run:  python -m pytest tests/test_ouroboros.py -v
"""

from __future__ import annotations

import contextlib
import json
import os
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import ouroboros as ob  # noqa: E402
from activegraph.store.sqlite import SQLiteEventStore  # noqa: E402
from activegraph.llm.types import LLMMessage, ToolCall  # noqa: E402

import scripted_provider as sp  # noqa: E402


# ---------------------------------------------------------------------------
# Real workspace content used by the scripted builder
# ---------------------------------------------------------------------------

CLI_AGENT = '''import json
import sys
from calc.ops import add, mul, sub


def handle(task):
    parts = str(task).split()
    if not parts:
        return {"result": None, "error": "empty task"}
    op = parts[0]
    nums = [int(x) for x in parts[1:]]
    if op == "add":
        return {"result": add(*nums), "op": "add"}
    if op == "mul":
        return {"result": mul(*nums), "op": "mul"}
    if op == "sub" and len(nums) == 2:
        return {"result": sub(nums[0], nums[1]), "op": "sub"}
    return {"result": None, "error": "unknown op: " + op}


def main():
    raw = sys.stdin.read()
    payload = json.loads(raw) if raw.strip() else {}
    if not isinstance(payload, dict):
        payload = {"task": str(payload)}
    print(json.dumps(handle(payload.get("task", ""))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

CLI_OPS = '''def add(*nums):
    return sum(nums)


def mul(*nums):
    result = 1
    for n in nums:
        result *= n
    return result


def sub(a, b):
    return a - b
'''

CLI_INIT = '"""calc package."""\n'

CLI_TEST = '''import json
import subprocess
import sys


def main():
    out = subprocess.run(
        [sys.executable, "agent.py"],
        input=json.dumps({"task": "add 2 3"}),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert out.returncode == 0, out.stderr
    data = json.loads(out.stdout)
    assert data["result"] == 5, data
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

CLI_MANIFEST = json.dumps(
    {
        "schema_version": 1,
        "language": "python",
        "entrypoint": ["python", "agent.py"],
        "test_command": ["python", "test_agent.py"],
        "input_protocol": "json-stdin",
        "output_protocol": "json-stdout",
        "environment": {},
    },
    indent=2,
) + "\n"

SELF_UPDATE = "# SELF\n\n## Current architecture\nMulti-file calc CLI: agent.py + calc/ package.\n"
MEMORY_UPDATE = "# MEMORY\n\n- g1: real ops beat echo; the evaluator executes code.\n"


def cli_files():
    return {
        "agent.py": CLI_AGENT,
        "calc/__init__.py": CLI_INIT,
        "calc/ops.py": CLI_OPS,
        "test_agent.py": CLI_TEST,
        "ouroboros.json": CLI_MANIFEST,
        "SELF.md": SELF_UPDATE,
        "MEMORY.md": MEMORY_UPDATE,
    }


def cli_public_tests():
    return [
        ob.TestCaseSpec(
            id="add",
            kind="entrypoint_io",
            description="add two integers",
            stdin_payloads=[json.dumps({"task": "add 2 3"})],
            expect=ob.TestExpectation(
                stdout_is_json=True, stdout_json_keys=["result"], stdout_contains=["5"]
            ),
        ),
        ob.TestCaseSpec(
            id="mul",
            kind="entrypoint_io",
            description="multiply two integers",
            stdin_payloads=[json.dumps({"task": "mul 4 5"})],
            expect=ob.TestExpectation(stdout_is_json=True, stdout_contains=["20"]),
        ),
    ]


def cli_private_tests(canary: str = ""):
    notes = "hidden transfer cases" + (f" [{canary}]" if canary else "")
    return sp.private_suite(
        [
            ob.TestCaseSpec(
                id="priv_sub",
                kind="entrypoint_io",
                description="subtract" + (f" {canary}" if canary else ""),
                stdin_payloads=[json.dumps({"task": "sub 10 4"})],
                expect=ob.TestExpectation(stdout_contains=["6"]),
            ),
            ob.TestCaseSpec(
                id="priv_add",
                kind="entrypoint_io",
                stdin_payloads=[json.dumps({"task": "add 7 8"})],
                expect=ob.TestExpectation(stdout_contains=["15"]),
            ),
        ],
        design_notes=notes,
    )


def cli_builder_script():
    return [
        [
            sp.write_turn(cli_files()),
            [("run_command", {"argv": ["python", "test_agent.py"]})],
            sp.submit_turn(
                "Built a multi-file calc CLI (agent.py + calc/ops.py).",
                "test_agent.py passes; add/mul produce correct JSON results.",
                "Add division and input validation next.",
            ),
        ]
    ]


def run_scenario(
    run_root: Path,
    provider,
    *,
    objective: str,
    generations: int = 1,
    allow_network: bool = False,
    allow_pip: bool = False,
    seed_dir: Path | None = None,
    run_id: str = "",
    max_tool_turns: int = 12,
):
    configuration = ob.EngineConfig(
        objective=objective,
        generations=generations,
        allow_network=allow_network,
        allow_pip=allow_pip,
        seed_dir=seed_dir,
        run_root=run_root,
        run_id=run_id,
        max_tool_turns=max_tool_turns,
        llm_retry_attempts=1,
        quiet=True,
    )
    return ob.run_ouroboros(configuration, provider=provider, cli_args=["<test>"])


def load_events(result):
    store = SQLiteEventStore(result["paths"]["trace"], run_id=result["run_id"])
    try:
        return list(store.iter_events())
    finally:
        store.close()


# ---------------------------------------------------------------------------
# 1. Multi-file growth
# ---------------------------------------------------------------------------


def test_multifile_growth(tmp_path):
    provider = sp.ScriptedProvider(
        contract=sp.contract(objective="Build a small CLI calculator", public_tests=cli_public_tests()),
        private=cli_private_tests(),
        builder_generations=cli_builder_script(),
    )
    result = run_scenario(tmp_path, provider, objective="Build a small CLI calculator")

    assert result["status"] == "completed", result["reason"]
    assert result["generations_promoted"] == 1
    final = Path(result["paths"]["final_workspace"])
    source_files = sorted(
        rel for rel, _ in ob.iter_workspace_files(final) if rel.endswith(".py")
    )
    assert "agent.py" in source_files and "calc/ops.py" in source_files
    assert len(source_files) >= 3, source_files

    # Success is grounded in execution, not prose: the CLI actually runs.
    out = ob.sandboxed_run(
        ["python", "agent.py"],
        cwd=final,
        stdin_text=json.dumps({"task": "add 40 2"}),
        timeout=20,
    )
    assert out["ok"] and json.loads(out["stdout"])["result"] == 42

    # The public evaluation for the promoted candidate really passed.
    g1_public = json.loads((Path(result["paths"]["run_dir"]) / "generations" / "g001" / "public_results.json").read_text())
    assert g1_public["public"]["passed"] == g1_public["public"]["total"] == 2


# ---------------------------------------------------------------------------
# 2. Workspace restructuring: replace the seed entrypoint
# ---------------------------------------------------------------------------

APP_MAIN = '''import json
import sys
from app.core import solve


def main():
    raw = sys.stdin.read()
    payload = json.loads(raw) if raw.strip() else {}
    task = payload.get("task", "") if isinstance(payload, dict) else str(payload)
    print(json.dumps(solve(task)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

APP_CORE = '''def solve(task):
    parts = str(task).split()
    if len(parts) == 3 and parts[0] == "add":
        return {"result": int(parts[1]) + int(parts[2])}
    return {"result": None}
'''

APP_SELFTEST = '''import json
import subprocess
import sys

out = subprocess.run(
    [sys.executable, "-m", "app.main"],
    input=json.dumps({"task": "add 1 2"}),
    capture_output=True,
    text=True,
    timeout=30,
)
assert out.returncode == 0, out.stderr
assert json.loads(out.stdout)["result"] == 3
print("ok")
'''

APP_MANIFEST = json.dumps(
    {
        "schema_version": 1,
        "language": "python",
        "entrypoint": ["python", "-m", "app.main"],
        "test_command": ["python", "app/selftest.py"],
        "input_protocol": "json-stdin",
        "output_protocol": "json-stdout",
        "environment": {},
    },
    indent=2,
) + "\n"


def test_workspace_restructuring(tmp_path):
    builder = [
        [
            sp.write_turn(
                {
                    "app/__init__.py": '"""app package."""\n',
                    "app/core.py": APP_CORE,
                    "app/main.py": APP_MAIN,
                    "app/selftest.py": APP_SELFTEST,
                    "ouroboros.json": APP_MANIFEST,
                }
            )
            + [("delete_file", {"path": "agent.py"}), ("delete_file", {"path": "test_agent.py"})],
            [("run_command", {"argv": ["python", "app/selftest.py"]})],
            sp.submit_turn(
                "Replaced the flat agent.py with an app/ package and a new entrypoint.",
                "app/selftest.py passes; ouroboros.json entrypoint now points at app/main.py.",
                "Add more operations.",
            ),
        ]
    ]
    public = [
        ob.TestCaseSpec(
            id="add",
            kind="entrypoint_io",
            stdin_payloads=[json.dumps({"task": "add 1 2"})],
            expect=ob.TestExpectation(stdout_is_json=True, stdout_contains=["3"]),
        )
    ]
    private = sp.private_suite(
        [
            ob.TestCaseSpec(
                id="priv_add",
                kind="entrypoint_io",
                stdin_payloads=[json.dumps({"task": "add 10 20"})],
                expect=ob.TestExpectation(stdout_contains=["30"]),
            )
        ]
    )
    provider = sp.ScriptedProvider(
        contract=sp.contract(objective="Restructure into a package", public_tests=public),
        private=private,
        builder_generations=builder,
    )
    result = run_scenario(tmp_path, provider, objective="Restructure into a package")

    assert result["status"] == "completed", result["reason"]
    assert result["generations_promoted"] == 1
    final = Path(result["paths"]["final_workspace"])
    manifest = json.loads((final / "ouroboros.json").read_text())
    assert manifest["entrypoint"] == ["python", "-m", "app.main"]
    assert not (final / "agent.py").exists()
    assert (final / "app" / "main.py").exists()
    out = ob.sandboxed_run(
        ["python", "-m", "app.main"], cwd=final, stdin_text=json.dumps({"task": "add 5 6"}), timeout=20
    )
    assert out["ok"] and json.loads(out["stdout"])["result"] == 11


# ---------------------------------------------------------------------------
# 3. Actual web behavior against a local HTTP fixture
# ---------------------------------------------------------------------------

WEB_CANARY = "OUROBOROS_FIXTURE_c0ffee42"

WEB_AGENT = '''import json
import sys
import urllib.request


def handle(payload):
    url = payload.get("url")
    task = payload.get("task", "")
    if not url:
        return {"error": "no url provided", "task": task}
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            body = response.read().decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}
    return {"task": task, "url": url, "content": body[:500], "length": len(body)}


def main():
    raw = sys.stdin.read()
    payload = json.loads(raw) if raw.strip() else {}
    if not isinstance(payload, dict):
        payload = {"task": str(payload)}
    print(json.dumps(handle(payload)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


@contextlib.contextmanager
def http_fixture(body: str):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            payload = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):  # silence
            return

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = HTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}/doc"
    finally:
        server.shutdown()
        server.server_close()


def test_actual_web_behavior(tmp_path):
    with http_fixture(f"Reference document. {WEB_CANARY}. End.") as url:
        web_manifest = json.dumps(
            {
                "schema_version": 1,
                "language": "python",
                "entrypoint": ["python", "agent.py"],
                "test_command": [],
                "input_protocol": "json-stdin",
                "output_protocol": "json-stdout",
                "environment": {},
            },
            indent=2,
        ) + "\n"
        builder = [
            [
                [("fetch_url", {"url": url})],
                sp.write_turn({"agent.py": WEB_AGENT, "ouroboros.json": web_manifest}),
                [("run_command", {"argv": ["python", "agent.py"], "stdin": json.dumps({"task": "read", "url": url})})],
                sp.submit_turn(
                    "Agent fetches the given URL and returns the retrieved content.",
                    f"Confirmed via fetch_url and run_command that the document contains {WEB_CANARY}.",
                    "Add summarization.",
                ),
            ]
        ]
        public = [
            ob.TestCaseSpec(
                id="fetch_doc",
                kind="entrypoint_io",
                description="fetch the reference document and return its content",
                stdin_payloads=[json.dumps({"task": "summarize", "url": url})],
                expect=ob.TestExpectation(stdout_is_json=True, stdout_contains=[WEB_CANARY]),
            )
        ]
        private = sp.private_suite(
            [
                ob.TestCaseSpec(
                    id="priv_fetch",
                    kind="entrypoint_io",
                    stdin_payloads=[json.dumps({"task": "again", "url": url})],
                    expect=ob.TestExpectation(stdout_contains=[WEB_CANARY]),
                )
            ]
        )
        provider = sp.ScriptedProvider(
            contract=sp.contract(
                objective="Build a web research agent", deliverable_kind="agent", public_tests=public
            ),
            private=private,
            builder_generations=builder,
        )
        result = run_scenario(
            tmp_path, provider, objective="Build a web research agent", allow_network=True
        )

    assert result["status"] == "completed", result["reason"]
    assert result["generations_promoted"] == 1
    # The promoted candidate's public test really fetched the fixture and
    # cited its canary content.
    g1_public = json.loads(
        (Path(result["paths"]["run_dir"]) / "generations" / "g001" / "public_results.json").read_text()
    )
    fetch_case = next(item for item in g1_public["public"]["results"] if item["id"] == "fetch_doc")
    assert fetch_case["passed"], fetch_case
    assert WEB_CANARY in fetch_case["stdout_tail"]
    # fetch_url was recorded as a tool call in the trace.
    events = load_events(result)
    tool_names = [
        e.payload.get("tool")
        for e in events
        if e.type == "tool.requested"
    ]
    assert "fetch_url" in tool_names


def test_fetch_url_disabled_without_flag(tmp_path):
    # Without --allow-network the builder's fetch_url must be refused, and a
    # candidate that depends on it cannot pass — but the run still finalizes.
    builder = [
        [
            [("fetch_url", {"url": "http://127.0.0.1:9/doc"})],
            sp.submit_turn("noop", "fetch blocked", "n/a"),
        ]
    ]
    provider = sp.ScriptedProvider(
        contract=sp.contract(objective="net", public_tests=cli_public_tests()),
        private=cli_private_tests(),
        builder_generations=builder,
    )
    result = run_scenario(tmp_path, provider, objective="net", allow_network=False)
    events = load_events(result)
    fetch_responses = [
        e for e in events if e.type == "tool.responded" and e.payload.get("tool") == "fetch_url"
    ]
    assert fetch_responses
    output = fetch_responses[0].payload.get("output") or {}
    assert output.get("ok") is False and "allow-network" in output.get("error", "")


# ---------------------------------------------------------------------------
# 4. Existing-project evolution via --seed-dir
# ---------------------------------------------------------------------------

def _calc_agent(expr: str) -> str:
    return '''import json
import sys


def handle(task):
    parts = str(task).split()
    if len(parts) == 3 and parts[0] == "add":
        return {"result": %s}
    return {"result": None}


def main():
    raw = sys.stdin.read()
    payload = json.loads(raw) if raw.strip() else {}
    task = payload.get("task", "") if isinstance(payload, dict) else str(payload)
    print(json.dumps(handle(task)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''' % expr


BUGGY_AGENT = _calc_agent("int(parts[1]) + int(parts[2]) + 1")  # off-by-one bug
FIXED_AGENT = _calc_agent("int(parts[1]) + int(parts[2])")


def test_existing_project_evolution(tmp_path):
    seed = tmp_path / "buggy_project"
    seed.mkdir()
    (seed / "agent.py").write_text(BUGGY_AGENT)
    (seed / "ouroboros.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "language": "python",
                "entrypoint": ["python", "agent.py"],
                "test_command": [],
                "input_protocol": "json-stdin",
                "output_protocol": "json-stdout",
                "environment": {},
            },
            indent=2,
        )
    )
    builder = [
        [
            sp.write_turn({"agent.py": FIXED_AGENT}),
            sp.submit_turn("Fixed the off-by-one bug in add.", "add 2 2 now returns 4.", "Add tests."),
        ]
    ]
    public = [
        ob.TestCaseSpec(
            id="add_correct",
            kind="entrypoint_io",
            stdin_payloads=[json.dumps({"task": "add 2 2"})],
            expect=ob.TestExpectation(stdout_is_json=True, stdout_contains=["4"], stdout_not_contains=["5"]),
        )
    ]
    private = sp.private_suite(
        [
            ob.TestCaseSpec(
                id="priv_add",
                kind="entrypoint_io",
                stdin_payloads=[json.dumps({"task": "add 5 5"})],
                expect=ob.TestExpectation(stdout_contains=["10"], stdout_not_contains=["11"]),
            )
        ]
    )
    provider = sp.ScriptedProvider(
        contract=sp.contract(objective="Fix the failing project", public_tests=public),
        private=private,
        builder_generations=builder,
    )
    result = run_scenario(tmp_path / "out", provider, objective="Fix the failing project", seed_dir=seed)

    assert result["status"] == "completed", result["reason"]
    assert result["generations_promoted"] == 1
    # The seed genuinely failed at generation 0; the fix genuinely passed.
    g0 = json.loads((Path(result["paths"]["run_dir"]) / "generations" / "g000" / "execution.json").read_text())
    assert g0["public"]["passed"] == 0
    final = Path(result["paths"]["final_workspace"])
    out = ob.sandboxed_run(
        ["python", "agent.py"], cwd=final, stdin_text=json.dumps({"task": "add 2 2"}), timeout=20
    )
    assert json.loads(out["stdout"])["result"] == 4


# ---------------------------------------------------------------------------
# 5. Hidden-test isolation (canary)
# ---------------------------------------------------------------------------

HIDDEN_CANARY = "CANARY_ZZZ_9f3a1b7c_HIDDEN_DO_NOT_LEAK"


def test_hidden_test_isolation(tmp_path):
    provider = sp.ScriptedProvider(
        contract=sp.contract(objective="Build a calculator", public_tests=cli_public_tests()),
        private=cli_private_tests(canary=HIDDEN_CANARY),
        builder_generations=cli_builder_script(),
    )
    result = run_scenario(tmp_path, provider, objective="Build a calculator")
    assert result["status"] == "completed", result["reason"]
    run_dir = Path(result["paths"]["run_dir"])

    # Sanity: the canary really is in the manager-only private area.
    assert HIDDEN_CANARY in (run_dir / "private" / "private_suite.json").read_text()

    # It must NOT appear on any builder-visible or public surface.
    builder_visible: list[Path] = [
        run_dir / "objective_contract.json",
        run_dir / "public_suite.json",
        run_dir / "history.json",
        run_dir / "private_suite_receipt.json",
        run_dir / "manifest.json",
        run_dir / "promotion.json",
        run_dir / "result.json",
    ]
    final = run_dir / "final_workspace"
    builder_visible += [final / "SELF.md", final / "MEMORY.md"]
    for path in run_dir.glob("generations/*/tool_session.json"):
        builder_visible.append(path)
    for path in run_dir.glob("generations/*/public_results.json"):
        builder_visible.append(path)
    for path in run_dir.glob("generations/*/tree.json"):
        builder_visible.append(path)
    for path in builder_visible:
        if path.exists():
            assert HIDDEN_CANARY not in path.read_text(), f"canary leaked into {path}"

    # The builder's prompts and tool outputs in the trace must be clean too.
    events = load_events(result)
    for event in events:
        if event.type in ("llm.requested", "llm.responded"):
            if event.payload.get("behavior") in ("ouro_builder", "ouro_compile_contract"):
                assert HIDDEN_CANARY not in json.dumps(event.payload, default=str)
        if event.type == "tool.responded":
            assert HIDDEN_CANARY not in json.dumps(event.payload, default=str)


# ---------------------------------------------------------------------------
# 6. No-op rejection without a judge call
# ---------------------------------------------------------------------------


def test_noop_rejected_without_judge(tmp_path):
    builder = [[sp.submit_turn("no changes", "identical tree", "n/a")]]
    provider = sp.ScriptedProvider(
        contract=sp.contract(objective="calc", public_tests=cli_public_tests()),
        private=cli_private_tests(),
        builder_generations=builder,
    )
    result = run_scenario(tmp_path, provider, objective="calc", generations=1)
    assert result["status"] == "completed"
    assert result["generations_promoted"] == 0
    history = json.loads((Path(result["paths"]["run_dir"]) / "history.json").read_text())
    assert history[0]["stage"] == "tree_noop"
    # The judge was never invoked for a no-op.
    assert "JudgeVerdict" not in provider.calls
    events = load_events(result)
    judge_requests = [
        e for e in events if e.type == "llm.requested" and e.payload.get("behavior") == "ouro_judge"
    ]
    assert judge_requests == []


# ---------------------------------------------------------------------------
# 7. Failure finalization: builder fails after one accepted generation
# ---------------------------------------------------------------------------


def test_failure_finalization(tmp_path):
    provider = sp.ScriptedProvider(
        # High threshold so generation 1 is promoted but does NOT trip the
        # stopping condition — the run must reach generation 2 to fail.
        contract=sp.contract(
            objective="calc", public_tests=cli_public_tests(), success_threshold=95
        ),
        private=cli_private_tests(),
        builder_generations=cli_builder_script(),  # only generation 0 scripted
        builder_raise_on_gen=1,  # generation 1 (0-indexed) crashes hard
    )
    result = run_scenario(tmp_path, provider, objective="calc", generations=3)

    assert result["status"] == "failed", result
    assert result["generations_promoted"] == 1
    run_dir = Path(result["paths"]["run_dir"])
    # Complete bundle exists on the failure path.
    for name in (
        "manifest.json",
        "objective_contract.json",
        "history.json",
        "lineage.jsonl",
        "promotion.json",
        "result.json",
        "trace.sqlite",
    ):
        assert (run_dir / name).exists(), name
    assert (run_dir / "seed_workspace").is_dir()
    final = run_dir / "final_workspace"
    assert final.is_dir()
    # final_workspace equals the latest ACCEPTED incumbent (generation 1), not
    # the partially built failed candidate.
    g1_tree = json.loads((run_dir / "generations" / "g001" / "tree.json").read_text())
    assert ob.workspace_id(final) == g1_tree["workspace_id"]
    # Exactly one terminal event.
    events = load_events(result)
    terminal = [e for e in events if e.type == ob.E_RUN_FINISHED]
    assert len(terminal) == 1
    assert terminal[0].payload["status"] == "failed"


# ---------------------------------------------------------------------------
# 8. Long history: full record grows, builder view stays bounded (synthetic)
# ---------------------------------------------------------------------------


def _synthetic_entry(generation: int) -> dict:
    return {
        "generation": generation,
        "decision": "promoted" if generation % 2 == 0 else "rejected",
        "stage": "evaluation",
        "public_reason": f"generation {generation} reason",
        "full_reason": f"generation {generation} full reason " + HIDDEN_CANARY,
        "builder_summary": f"summary {generation}",
        "next_strategy": f"strategy {generation}",
        "candidate_workspace_id": f"workspace-sha256-{generation:064d}",
        "public_tests_compact": {"candidate_passed": 3, "total": 3},
        "judge_average_delta": 1.5,
        "judge_candidate_absolute": 80,
        "files_changed": 4,
        "private": {  # private detail must never reach the builder view
            "candidate_rate": 0.9,
            "incumbent_rate": 0.5,
            "newly_passing": [f"priv_{generation}_" + HIDDEN_CANARY],
            "newly_failing": [],
        },
        "recorded_at": "2026-01-01T00:00:00+00:00",
    }


def test_long_history_bounded_view():
    entries: list[dict] = []
    sizes: list[int] = []
    for generation in range(1, 56):
        entries.append(_synthetic_entry(generation))
        archive = ob.refold_archive(entries)
        view = ob.builder_history_view(entries, archive)
        sizes.append(len(ob.canonical_json(view)))

        assert len(view["recent_full"]) <= ob.HISTORY_RECENT_FULL
        assert len(view["compact"]) <= ob.HISTORY_MID_COMPACT

    # Full exact history is retained.
    assert len(entries) == 55
    final_archive = ob.refold_archive(entries)
    final_view = ob.builder_history_view(entries, final_archive)
    assert final_view["total_generations_recorded"] == 55
    assert final_view["archive"]["generations"] == 55 - (
        ob.HISTORY_RECENT_FULL + ob.HISTORY_MID_COMPACT
    )

    # The builder view stays bounded even as history grows to 55 generations.
    assert max(sizes[9:]) < 3 * min(sizes[9:]) + 4000
    assert sizes[-1] < 12_000

    # No private field leaks into the builder-visible view.
    blob = ob.canonical_json(final_view)
    assert HIDDEN_CANARY not in blob
    assert "newly_failing" not in blob and "incumbent_rate" not in blob


# ---------------------------------------------------------------------------
# 9. Run uniqueness
# ---------------------------------------------------------------------------


def test_run_uniqueness(tmp_path):
    def make_provider():
        return sp.ScriptedProvider(
            contract=sp.contract(objective="calc", public_tests=cli_public_tests()),
            private=cli_private_tests(),
            builder_generations=cli_builder_script(),
        )

    result_a = run_scenario(tmp_path / "runs", make_provider(), objective="calc")
    result_b = run_scenario(tmp_path / "runs", make_provider(), objective="calc")

    assert result_a["run_id"] != result_b["run_id"]
    assert result_a["paths"]["run_dir"] != result_b["paths"]["run_dir"]
    assert result_a["paths"]["trace"] != result_b["paths"]["trace"]

    # Content-addressed identity is stable where content is identical.
    seed_a = ob.workspace_id(Path(result_a["paths"]["run_dir"]) / "seed_workspace")
    seed_b = ob.workspace_id(Path(result_b["paths"]["run_dir"]) / "seed_workspace")
    assert seed_a == seed_b
    manifest_a = json.loads((Path(result_a["paths"]["run_dir"]) / "manifest.json").read_text())
    manifest_b = json.loads((Path(result_b["paths"]["run_dir"]) / "manifest.json").read_text())
    assert manifest_a["engine"]["source_sha256"] == manifest_b["engine"]["source_sha256"]
    # The promoted workspace is content-identical across identical runs.
    assert result_a["final_workspace_id"] == result_b["final_workspace_id"]


# ---------------------------------------------------------------------------
# 10. ActiveGraph integrity
# ---------------------------------------------------------------------------


def test_activegraph_integrity(tmp_path):
    provider = sp.ScriptedProvider(
        contract=sp.contract(objective="calc", public_tests=cli_public_tests()),
        private=cli_private_tests(),
        builder_generations=cli_builder_script(),
    )
    result = run_scenario(tmp_path, provider, objective="calc")
    events = load_events(result)
    assert events, "trace did not load any events"

    by_type: dict[str, int] = {}
    for event in events:
        by_type[event.type] = by_type.get(event.type, 0) + 1

    # Tool calls are recorded as request/response pairs.
    assert by_type.get("tool.requested", 0) >= 1
    assert by_type.get("tool.responded", 0) >= 1
    # LLM calls are recorded.
    assert by_type.get("llm.requested", 0) >= 3  # contract, private, builder, judge

    # Object graph: collect object.created payloads by type.
    objects: dict[str, list[dict]] = {}
    object_index: dict[str, dict] = {}
    for event in events:
        if event.type == "object.created":
            obj = event.payload["object"]
            objects.setdefault(obj["type"], []).append(obj)
            object_index[obj["id"]] = obj
    for required in (
        ob.OBJ["run"],
        ob.OBJ["objective_contract"],
        ob.OBJ["workspace_version"],
        ob.OBJ["file_blob"],
        ob.OBJ["build_session"],
        ob.OBJ["file_change"],
        ob.OBJ["command_run"],
        ob.OBJ["public_test_suite"],
        ob.OBJ["private_test_suite"],
        ob.OBJ["test_result"],
        ob.OBJ["evaluation"],
        ob.OBJ["history_summary"],
        ob.OBJ["run_summary"],
    ):
        assert objects.get(required), f"missing object type {required}"

    relations = [
        event.payload["relation"]
        for event in events
        if event.type == "relation.created"
    ]

    def edges(rel_type: str):
        return [r for r in relations if r["type"] == rel_type]

    # file_blob objects are linked to a workspace_version via `contains`.
    workspace_ids = {obj["id"] for obj in objects[ob.OBJ["workspace_version"]]}
    blob_ids = {obj["id"] for obj in objects[ob.OBJ["file_blob"]]}
    contains_edges = edges("contains")
    blob_linked = any(
        edge["source"] in workspace_ids and edge["target"] in blob_ids
        for edge in contains_edges
    )
    assert blob_linked, "no workspace_version -> file_blob contains edge"

    # file_change objects are linked to a build_session via `contains`.
    session_ids = {obj["id"] for obj in objects[ob.OBJ["build_session"]]}
    change_ids = {obj["id"] for obj in objects[ob.OBJ["file_change"]]}
    change_linked = any(
        edge["source"] in session_ids and edge["target"] in change_ids
        for edge in contains_edges
    )
    assert change_linked, "no build_session -> file_change edge"

    # workspace_version -> build_session `modified_by` lineage exists.
    assert any(
        edge["source"] in workspace_ids and edge["target"] in session_ids
        for edge in edges("modified_by")
    )

    # Every evaluated candidate has an evaluation lineage edge (`evaluated_by`).
    assert edges("evaluated_by")
    # A promoted candidate supersedes its parent (`superseded_by`).
    assert edges("superseded_by")

    # Exactly one terminal event.
    assert by_type.get(ob.E_RUN_FINISHED, 0) == 1

    # History compaction is recorded.
    assert by_type.get(ob.E_HISTORY_COMPACTED, 0) >= 1


# ---------------------------------------------------------------------------
# 11. Meta candidate: produce next_ouroboros.py without overwriting the kernel
# ---------------------------------------------------------------------------

NEXT_ENGINE = '''#!/usr/bin/env python3
"""Proposed next Ouroboros engine (candidate). Not executed by this run."""


def main():
    print("next ouroboros stub")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def test_meta_candidate(tmp_path):
    engine_path = Path(ob.__file__).resolve()
    engine_sha_before = ob.sha256_bytes(engine_path.read_bytes())

    files = dict(cli_files())
    files[ob.META_CANDIDATE_FILENAME] = NEXT_ENGINE
    builder = [
        [
            sp.write_turn(files),
            sp.submit_turn(
                "Improved the workspace and proposed a next_ouroboros.py engine candidate.",
                "test_agent.py passes; next_ouroboros.py added as a release candidate.",
                "Manager should run the engine release suite on next_ouroboros.py.",
            ),
        ]
    ]
    provider = sp.ScriptedProvider(
        contract=sp.contract(objective="Improve Ouroboros itself", public_tests=cli_public_tests()),
        private=cli_private_tests(),
        builder_generations=builder,
    )
    result = run_scenario(tmp_path, provider, objective="Improve Ouroboros itself")

    assert result["status"] == "completed", result["reason"]
    run_dir = Path(result["paths"]["run_dir"])
    assert (run_dir / "final_workspace" / ob.META_CANDIDATE_FILENAME).exists()

    promotion = json.loads((run_dir / "promotion.json").read_text())
    candidates = promotion["release_candidates"]
    assert candidates and candidates[0]["kind"] == "engine_meta_candidate"
    assert candidates[0]["path"].endswith(ob.META_CANDIDATE_FILENAME)

    # The live engine file was NOT overwritten.
    assert ob.sha256_bytes(engine_path.read_bytes()) == engine_sha_before

    # It is recorded as a release_candidate object in the graph.
    events = load_events(result)
    rc_objects = [
        e.payload["object"]
        for e in events
        if e.type == "object.created" and e.payload["object"]["type"] == ob.OBJ["release_candidate"]
    ]
    assert rc_objects, "release_candidate object was not recorded in the trace"


# ---------------------------------------------------------------------------
# Unit tests: promotion rule, judge scoring, path guard, manifest, patching
# ---------------------------------------------------------------------------


def _delta(candidate_passed, incumbent_passed, total, newly_passing=None, newly_failing=None):
    return {
        "incumbent_passed": incumbent_passed,
        "candidate_passed": candidate_passed,
        "total": total,
        "incumbent_rate": incumbent_passed / total if total else 1.0,
        "candidate_rate": candidate_passed / total if total else 1.0,
        "newly_passing": newly_passing or [],
        "newly_failing": newly_failing or [],
    }


def _judgement(avg, worst, cwins, iwins, cabs=80):
    return {
        "average_delta": avg,
        "worst_delta": worst,
        "candidate_wins": cwins,
        "incumbent_wins": iwins,
        "candidate_absolute": cabs,
        "incumbent_absolute": cabs - avg,
    }


@pytest.fixture()
def default_config():
    prev = ob._STATE
    ob._STATE = ob.RunState(
        config=ob.EngineConfig(objective="x"),
        run_dir=Path("/tmp/ouro-unit"),
        work_root=Path("/tmp/ouro-unit-w"),
        private_dir=Path("/tmp/ouro-unit-p"),
        trace_path=Path("/tmp/ouro-unit/trace.sqlite"),
    )
    yield
    ob._STATE = prev


def test_decide_promotion_rules(default_config):
    gates_pass = {"passed": True, "gates": []}
    gates_fail = {"passed": False, "gates": [{"id": "program_starts", "passed": False}]}

    # Clean win: public tests newly pass, judge neutral.
    accepted, _ = ob.decide_promotion(
        tree_changed=True,
        gates=gates_pass,
        public_delta=_delta(2, 0, 2, newly_passing=["add", "mul"]),
        private_delta=_delta(2, 0, 2, newly_passing=["p1", "p2"]),
        judgement=_judgement(0.0, 0.0, 0, 0),
    )
    assert accepted

    # Tree no-op never promotes.
    accepted, reason = ob.decide_promotion(
        tree_changed=False, gates=gates_pass,
        public_delta=_delta(2, 0, 2, newly_passing=["add"]),
        private_delta=_delta(2, 2, 2), judgement=_judgement(5, 5, 2, 0),
    )
    assert not accepted and "no-op" in reason

    # Hard-gate failure cannot be overridden by a strong judge score.
    accepted, reason = ob.decide_promotion(
        tree_changed=True, gates=gates_fail,
        public_delta=_delta(2, 0, 2, newly_passing=["add", "mul"]),
        private_delta=_delta(2, 2, 2), judgement=_judgement(50, 50, 2, 0),
    )
    assert not accepted and "hard gates" in reason

    # Public regression blocks promotion.
    accepted, reason = ob.decide_promotion(
        tree_changed=True, gates=gates_pass,
        public_delta=_delta(1, 2, 3, newly_failing=["mul"]),
        private_delta=_delta(3, 3, 3), judgement=_judgement(10, 5, 3, 0),
    )
    assert not accepted

    # Severe qualitative worst-case regression blocks promotion.
    accepted, reason = ob.decide_promotion(
        tree_changed=True, gates=gates_pass,
        public_delta=_delta(2, 2, 2), private_delta=_delta(2, 2, 2),
        judgement=_judgement(1.0, -40.0, 2, 1),
    )
    assert not accepted and "worst-case" in reason

    # No net wins → rejected.
    accepted, reason = ob.decide_promotion(
        tree_changed=True, gates=gates_pass,
        public_delta=_delta(2, 2, 2), private_delta=_delta(2, 2, 2),
        judgement=_judgement(0.0, 0.0, 1, 1),
    )
    assert not accepted


def test_score_judgement_balanced_mapping():
    verdict = ob.JudgeVerdict(
        scores=[
            ob.JudgeCaseScore(case_id="c1", a_score=90, b_score=40, rationale="x"),
            ob.JudgeCaseScore(case_id="c2", a_score=30, b_score=70, rationale="y"),
        ],
        summary="ok",
    )
    # c1 mapping=candidate -> candidate is A (90 vs 40).
    # c2 mapping=incumbent -> candidate is B (70 vs 30).
    mapping = {"c1": "candidate", "c2": "incumbent"}
    summary, error = ob.score_judgement(verdict, mapping, ["c1", "c2"])
    assert error == ""
    by_case = {row["case_id"]: row for row in summary["cases"]}
    assert by_case["c1"]["candidate_score"] == 90 and by_case["c1"]["incumbent_score"] == 40
    assert by_case["c2"]["candidate_score"] == 70 and by_case["c2"]["incumbent_score"] == 30
    assert summary["candidate_wins"] == 2 and summary["incumbent_wins"] == 0

    # Missing case is reported.
    _, error = ob.score_judgement(verdict, mapping, ["c1", "c2", "c3"])
    assert "c3" in error


def test_path_guard(tmp_path):
    root = tmp_path / "ws"
    root.mkdir()
    (root / "ok.py").write_text("x = 1")
    good, reason = ob.resolve_workspace_path(root, "ok.py")
    assert good is not None and reason == ""
    for bad in ["/etc/passwd", "../escape", "a/../../b", "C:\\win", "x\x00y"]:
        resolved, reason = ob.resolve_workspace_path(root, bad)
        assert resolved is None, bad

    # Symlink escape is rejected.
    outside = tmp_path / "secret.txt"
    outside.write_text("secret")
    link = root / "link.txt"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlinks not supported here")
    resolved, reason = ob.resolve_workspace_path(root, "link.txt")
    assert resolved is None and "escape" in reason


def test_manifest_validation(default_config):
    good = {
        "schema_version": 1,
        "language": "python",
        "entrypoint": ["python", "agent.py"],
        "test_command": [],
        "input_protocol": "json-stdin",
        "output_protocol": "json-stdout",
        "environment": {},
    }
    manifest, error = ob.validate_manifest_data(good)
    assert manifest is not None and error == ""
    bad_cases = [
        {**good, "entrypoint": []},
        {**good, "entrypoint": ["bash", "x.sh"]},
        {**good, "language": "ruby"},
        {**good, "input_protocol": "smoke-signals"},
        {**good, "environment": {"PATH": "/evil"}},
        {**good, "schema_version": 99},
    ]
    for case in bad_cases:
        manifest, error = ob.validate_manifest_data(case)
        assert manifest is None and error, case


def test_apply_unified_patch():
    original = "line1\nline2\nline3\n"
    patch = "@@ -1,3 +1,3 @@\n line1\n-line2\n+LINE_TWO\n line3\n"
    patched, error = ob.apply_unified_patch(original, patch)
    assert error == "" and patched == "line1\nLINE_TWO\nline3\n"
    # Non-matching context is reported, not silently applied.
    bad_patch = "@@ -1,2 +1,2 @@\n nope\n-missing\n+x\n"
    patched, error = ob.apply_unified_patch(original, bad_patch)
    assert patched is None and error

    # Regression: a hunk whose first body line is a deletion of "--..." or an
    # addition of "++..." must not be silently dropped.
    original2 = "---\ntitle: x\n"
    patched, error = ob.apply_unified_patch(original2, "@@ -1,1 +0,0 @@\n----\n")
    # The literal "---" separator line is removed (not silently kept).
    assert error == "" and patched == "title: x\n", (patched, error)

    original3 = "x = 1\n"
    patched, error = ob.apply_unified_patch(original3, "@@ -1,0 +1,1 @@\n+++added\n")
    assert error == "" and patched == "++added\nx = 1\n", (patched, error)


def test_find_symlinks_skips_ignored_dirs(tmp_path):
    root = tmp_path / "ws"
    (root / ".ouro_home").mkdir(parents=True)
    (root / "real").mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("x")
    try:
        # A symlink inside a skipped dir must NOT be reported (it is never
        # copied into the bundle or evaluated candidate).
        (root / ".ouro_home" / "link").symlink_to(outside)
        # A symlink in the real tree MUST be reported.
        (root / "real" / "escape").symlink_to(outside)
    except OSError:
        pytest.skip("symlinks not supported here")
    found = ob.find_symlinks(root)
    assert "real/escape" in found
    assert not any(f.startswith(".ouro_home") for f in found), found
    # workspace_integrity therefore does not spuriously fail on sandbox dirs.
    prev = ob._STATE
    ob._STATE = ob.RunState(
        config=ob.EngineConfig(objective="x"),
        run_dir=tmp_path / "rd",
        work_root=tmp_path / "wr",
        private_dir=tmp_path / "pd",
        trace_path=tmp_path / "rd" / "t.sqlite",
    )
    try:
        # Only the .ouro_home symlink present -> integrity should be clean.
        (root / "real" / "escape").unlink()
        assert ob.workspace_integrity(root)["ok"] is True
    finally:
        ob._STATE = prev


def test_tree_hash_is_path_content_based(tmp_path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    for root in (a, b):
        (root / "pkg").mkdir(parents=True)
        (root / "agent.py").write_text("print('hi')\n")
        (root / "pkg" / "mod.py").write_text("VALUE = 1\n")
    assert ob.workspace_id(a) == ob.workspace_id(b)
    assert ob.workspace_id(a).startswith("workspace-sha256-")
    (b / "agent.py").write_text("print('changed')\n")
    assert ob.workspace_id(a) != ob.workspace_id(b)


def test_describe_and_export_contract(tmp_path, monkeypatch):
    described = ob.describe()
    assert described["engine_version"] == ob.ENGINE_VERSION
    assert "submit_candidate" in described["builder_tools"]
    assert set(ob.TERMINAL_STATUSES) == set(described["terminal_statuses"])


def test_validate_contract_rejects_duplicate_ids():
    dup_test = sp.contract(
        objective="x",
        public_tests=[
            ob.TestCaseSpec(id="t", kind="entrypoint_io"),
            ob.TestCaseSpec(id="t", kind="entrypoint_io"),
        ],
    )
    problems = ob.validate_contract(dup_test)
    assert any("duplicate test id" in p for p in problems)

    dup_rubric = sp.contract(
        objective="x",
        public_tests=[ob.TestCaseSpec(id="t", kind="entrypoint_io")],
        rubric=[
            ob.RubricCriterion(id="r", criterion="a", anchors="0/50/100"),
            ob.RubricCriterion(id="r", criterion="b", anchors="0/50/100"),
        ],
    )
    problems = ob.validate_contract(dup_rubric)
    assert any("duplicate rubric id" in p for p in problems)


def test_entrypoint_module_path_guard(tmp_path):
    root = tmp_path / "ws"
    (root / "app").mkdir(parents=True)
    (root / "app" / "main.py").write_text("print('x')")
    ok, _ = ob.entrypoint_target_exists(root, ["python", "-m", "app.main"])
    assert ok
    # A crafted module name cannot escape the workspace or pass the gate.
    for bad in ["..//..//x", "../evil", "/etc/passwd"]:
        ok, reason = ob.entrypoint_target_exists(root, ["python", "-m", bad])
        assert not ok, bad


# ---------------------------------------------------------------------------
# Regression: D1 (cost-cap crash), D2 (dead failure router), turn budget, ports
# ---------------------------------------------------------------------------


class _FakeCountClient:
    """Minimal stand-in for anthropic.Anthropic that records count_tokens args."""

    def __init__(self, *, raise_on_call: bool = False):
        import types as _types

        self.captured = None
        self.raise_on_call = raise_on_call
        self.messages = _types.SimpleNamespace(count_tokens=self._count)

    def _count(self, **kwargs):
        import types as _types

        if self.raise_on_call:
            raise RuntimeError("simulated count_tokens failure")
        self.captured = kwargs
        return _types.SimpleNamespace(input_tokens=123)


def test_d1_count_tokens_never_sends_tool_role():
    # The upstream bug: count_tokens serialized role="tool" and the Anthropic
    # API 400s. The fix routes messages through the same converter as the send
    # path, so no "tool" role ever reaches the API.
    fake = _FakeCountClient()
    provider = ob.CostSafeAnthropicProvider(client=fake)
    messages = [
        LLMMessage(role="user", content="build it"),
        LLMMessage(
            role="assistant",
            content="",
            tool_calls=(ToolCall(id="tu_1", name="write_file", args={"path": "a.py"}),),
        ),
        LLMMessage(role="tool", content='{"ok": true}', tool_use_id="tu_1", tool_name="write_file"),
    ]
    tokens = provider.count_tokens(system="sys", messages=messages, model="claude-opus-4-8")
    assert tokens == 123
    assert fake.captured is not None, "the real count path did not run"
    roles = [m["role"] for m in fake.captured["messages"]]
    assert "tool" not in roles
    assert set(roles) <= {"user", "assistant"}


def test_d1_count_tokens_falls_back_without_raising():
    # A failure in the count path must not kill the behavior; it returns a
    # conservative local estimate instead.
    provider = ob.CostSafeAnthropicProvider(client=_FakeCountClient(raise_on_call=True))
    tokens = provider.count_tokens(
        system="a" * 40,
        messages=[LLMMessage(role="tool", content="b" * 40, tool_use_id="t")],
        model="claude-opus-4-8",
    )
    assert tokens > 0


def test_d1_cost_capped_run_completes(tmp_path):
    # With a cost cap set, the runtime's pre-call cost gate calls count_tokens
    # every turn. The run must complete rather than crash on the tool turns.
    provider = sp.ScriptedProvider(
        contract=sp.contract(objective="calc", public_tests=cli_public_tests()),
        private=cli_private_tests(),
        builder_generations=cli_builder_script(),
    )
    configuration = ob.EngineConfig(
        objective="calc",
        generations=1,
        run_root=tmp_path / "runs",
        max_tool_turns=12,
        llm_retry_attempts=1,
        max_cost_usd=5.0,
        quiet=True,
    )
    result = ob.run_ouroboros(configuration, provider=provider, cli_args=["<test>"])
    assert result["status"] == "completed", result["reason"]
    assert result["generations_promoted"] == 1


def test_d2_recoverable_builder_failure_continues(tmp_path):
    # Generation 1's builder exhausts its tool turns (never submits); the run
    # must reject that one generation and continue to generation 2, not die.
    exhaust = [[("list_tree", {"path": ""})] for _ in range(8)]
    provider = sp.ScriptedProvider(
        contract=sp.contract(objective="calc", public_tests=cli_public_tests()),
        private=cli_private_tests(),
        builder_generations=[exhaust, cli_builder_script()[0]],
    )
    result = run_scenario(tmp_path, provider, objective="calc", generations=2, max_tool_turns=4)

    assert result["status"] == "completed", result["reason"]
    assert result["generations_promoted"] == 1, result
    history = json.loads((Path(result["paths"]["run_dir"]) / "history.json").read_text())
    stages = {row["generation"]: row["stage"] for row in history}
    assert stages.get(1) == "builder_failure"
    assert history[-1]["decision"] == "promoted"
    # The recovered failure is recorded, and the run has exactly one terminal event.
    assert any(f["reason"] == "tool.max_turns_exhausted" for f in result["llm_failures"])
    events = load_events(result)
    assert len([e for e in events if e.type == ob.E_RUN_FINISHED]) == 1
    # Final workspace is the promoted generation-2 tree.
    g2 = json.loads((Path(result["paths"]["run_dir"]) / "generations" / "g002" / "tree.json").read_text())
    assert ob.workspace_id(Path(result["paths"]["final_workspace"])) == g2["workspace_id"]


def test_turn_budget_reserves_final_response(tmp_path):
    # A builder that uses exactly max_tool_turns tool turns (submitting on the
    # last) must still get a turn for its final structured response. Without the
    # reserved +1 this would exhaust and promote nothing.
    four_turn_script = [
        [
            sp.write_turn(cli_files()),
            [("run_command", {"argv": ["python", "test_agent.py"]})],
            [("run_command", {"argv": ["python", "agent.py"], "stdin": json.dumps({"task": "add 1 1"})})],
            sp.submit_turn("built calc in exactly four tool turns", "tests pass", "n/a"),
        ]
    ]
    provider = sp.ScriptedProvider(
        contract=sp.contract(objective="calc", public_tests=cli_public_tests()),
        private=cli_private_tests(),
        builder_generations=four_turn_script,
    )
    result = run_scenario(tmp_path, provider, objective="calc", generations=1, max_tool_turns=4)
    assert result["status"] == "completed", result["reason"]
    assert result["generations_promoted"] == 1


def test_normalize_required_artifacts():
    out = ob.normalize_required_artifacts(
        [
            "agent.py",
            "src/calc/ops.py",
            "a main.py entrypoint or equivalent",
            "a module that exposes solve() in solver.py",
            "some prose with no path at all",
            "../escape.py",
            "/abs/path.py",
        ]
    )
    assert "agent.py" in out and "src/calc/ops.py" in out
    assert "solver.py" in out  # single salvageable token from prose
    assert not any("main.py" in item for item in out)  # 'or equivalent' dropped
    assert not any(".." in item or item.startswith("/") for item in out)


# ---------------------------------------------------------------------------
# Optional: live model end-to-end (only when ANTHROPIC_API_KEY is available)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set; skipping live end-to-end evolution",
)
def test_live_end_to_end_multifile(tmp_path):
    configuration = ob.EngineConfig(
        objective="Build a command-line to-do list tool that stores tasks as JSON on stdin/stdout",
        generations=2,
        run_root=tmp_path / "runs",
        max_tool_turns=30,
        max_run_seconds=900,
        quiet=True,
        model=os.environ.get("ANTHROPIC_MODEL"),
    )
    result = ob.run_ouroboros(configuration, cli_args=["<live>"])
    assert result["status"] in ("completed", "baseline_only", "budget_exhausted"), result["reason"]
    # Whatever the outcome, the bundle is complete and has exactly one terminal event.
    events = load_events(result)
    assert len([e for e in events if e.type == ob.E_RUN_FINISHED]) == 1
    assert Path(result["paths"]["final_workspace"]).is_dir()
