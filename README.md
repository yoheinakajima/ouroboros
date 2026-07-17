# Ouroboros v1.2

Ouroboros is a one-file evolutionary environment for software workspaces. Give
`ouroboros.py` a vague objective; it compiles the objective into an executable
contract, gives an LLM a seed workspace plus filesystem and command tools,
evaluates each resulting tree, and promotes only candidates supported by
execution-grounded evidence.

The engine is intentionally a single copyable script. A candidate can become a
multi-file application and may replace every seed file, but it cannot replace
the running kernel. If it creates `next_ouroboros.py`, that file is recorded as
a manager-reviewed release candidate in `promotion.json`.

## Install and run

Python 3.11 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY="..."

python ouroboros.py "Build a reliable multi-file research CLI" --generations 5
```

Other supported forms:

```bash
python ouroboros.py "Improve this project" --seed-dir existing_project/
python ouroboros.py "Build a web research agent" --allow-network --allow-pip
python ouroboros.py --describe
python ouroboros.py "Build a small JSON CLI" \
  --export-objective-contract contract.json --generations 0
```

Use `--provider openai` after installing `activegraph[openai]` and setting
`OPENAI_API_KEY`. Every invocation receives a unique run directory by default;
an explicitly reused `--run-id` fails rather than overwriting evidence.

For example, a cost-capped run with the current flagship OpenAI model is:

```bash
set -a; source .env; set +a
python ouroboros.py "Build a robust persistent argv todo CLI" \
  --provider openai --model gpt-5.6-sol \
  --generations 1 --max-cost-usd 5
```

The engine never forwards provider credentials to candidate subprocesses.

## How a generation works

1. An ActiveGraph `@llm_behavior` compiles the objective into a typed public
   `ObjectiveContract`. A separate manager-only behavior authors non-duplicate
   private tests.
2. An independent manager-only suite reviewer recomputes exact expectations,
   repairs invalid protocol fixtures, and returns corrected public/private
   suites. Deterministic structural validation then rejects contradictory,
   wrapped, impossible, or undeclared-dependency tests. Private material is
   persisted under `private/` and represented publicly only by a sealed receipt.
   JSON-shaped suite output containing only bounded string concatenation or
   repetition is repaired by a non-executing literal parser; other malformed
   output gets one literal-only retry before the run fails.
3. The incumbent is cloned into a clean candidate directory.
4. A multi-turn ActiveGraph builder inspects, edits, deletes, restructures, and
   tests the candidate through runtime-owned tools. It must explicitly call
   `submit_candidate`.
5. The kernel validates `ouroboros.json`, artifacts, paths, budgets, startup
   using a contract-valid smoke input, and a declared test command that proves
   at least one test executed.
6. Public and private tests execute against clean incumbent and candidate
   copies. Two isolated blinded judge calls see opposite A/B positions for each
   criterion, but no lineage, diff, hypothesis, private scores, or mapping.
7. Deterministic promotion logic enforces hard gates and regression bounds. A
   candidate that strictly dominates executable evidence cannot be vetoed by a
   contradictory judge label; otherwise mirrored qualitative thresholds,
   meaningful wins, and worst-case safety apply. There is no human review
   inside the loop.

The builder-visible history contains the latest three generations in detail,
the preceding seven as structured summaries, and one folded archive summary.
`history.json`, `lineage.jsonl`, generation artifacts, and `trace.sqlite` retain
the exact full record.

## Workspace contract

Every candidate owns `ouroboros.json`:

```json
{
  "schema_version": 1,
  "language": "python",
  "entrypoint": ["python", "agent.py"],
  "test_command": ["python", "-m", "unittest", "-q"],
  "input_protocol": "json-stdin",
  "output_protocol": "json-stdout",
  "environment": {}
}
```

The manifest may change completely between generations. Commands are argv
arrays and are executed with `shell=False` from the candidate root. Secret-like
environment keys are rejected.

Input protocols are `json-stdin`, `text-stdin`, `argv`, and `none`; output
protocols are `json-stdout`, `text-stdout`, `stdout`, and `none`. Objective
tests can execute entrypoints, arbitrary argv commands, Python imports, local
HTTP servers, file assertions, or ordered state-persistence sequences.

The builder tools are `list_tree`, `read_file`, `write_file`, `apply_patch`,
`delete_file`, `make_directory`, `run_command`, `fetch_url`, and
`submit_candidate`. Paths reject absolute names, `..`, symlinks, and root
escapes. Command-created file changes are detected by before/after tree hashes.
The exact manifest schema and live remaining budget accompany the build request
and every tool result. Tool, model-call, token, time, workspace, and estimated
dollar caps are enforced independently; usage is durably checkpointed. The
usage record distinguishes total LLM attempts, failed attempts, and successful
calls by phase so malformed provider output remains visible in the audit trail.
If a provider throws away usage metadata before literal repair, the attempt is
explicitly marked unmetered rather than reported as zero-cost evidence.

## Evidence bundle

Each run writes:

```text
.ouroboros/runs/<run-id>/
  manifest.json
  objective_contract.json
  public_suite.json
  private_suite_receipt.json
  usage.json
  history.json
  lineage.jsonl
  promotion.json
  result.json
  trace.sqlite
  private/
    private_suite.json
    suite_review.json
    results/
  seed_workspace/
  final_workspace/
  generations/
    g000/{workspace/,tree.json,execution.json}
    g001/{candidate/,diff.json,tool_session.json,
          public_results.json,private_results.json,evaluation.json}
```

`workspace-sha256-<digest>` IDs use sorted relative paths and content hashes;
absolute locations never affect identity. `final_workspace` always contains the
latest accepted incumbent, including after model failure or budget exhaustion.
Finalization is idempotent and emits exactly one `ouro.v0.run.terminal` event.

Inspect a trace with:

```bash
activegraph inspect sqlite:///.ouroboros/runs/<run-id>/trace.sqlite
```

For an absolute path use four slashes, for example
`sqlite:////tmp/ouro-run/trace.sqlite`.

## Safety boundary

This is constrained execution, not a universal hostile-code sandbox. All
subprocesses receive a scrubbed environment, candidate cwd, argv-only launch,
wall/CPU/memory/output limits, and no provider credentials. On macOS, Seatbelt
also hides the user's home, makes only the candidate writable, and denies
network access unless enabled. On hosts without an OS sandbox provider, the
portable controls cannot stop malicious code from using direct syscalls to read
otherwise accessible files or open raw sockets; use a disposable container or
VM for untrusted objectives. `--allow-pip` installs into candidate-local
`.ouroboros_deps`, which counts against workspace budgets.

## Tests

```bash
python -m unittest -v tests.test_ouroboros
```

The deterministic suite covers multi-file growth, entrypoint replacement, a
real local HTTP fetch, imported project repair, sealed-test isolation, pre-judge
no-op rejection, stateful argv workflows, capability gating, recoverable
builder exhaustion, budget/cost taxonomy, balanced judging, deterministic
dominance, failure finalization, history compaction, unique runs, ActiveGraph
trace integrity, manager-only suite review, schema-valid protocol smoke inputs,
nonzero test discovery, bounded suite-generation recovery, failed-call usage
accounting, non-executing literal-expression repair, and manager-only
meta-evolution handoff. See
[`TEST_REPORT.md`](TEST_REPORT.md) for the observed commands and artifacts.
The exact-prompt coding-agent/chatbot experiment is documented in
[`CAPABILITY_TEST_REPORT.md`](CAPABILITY_TEST_REPORT.md).

The preserved historical function-mutator is
[`experiments/baselines/text_policy_v0.py`](experiments/baselines/text_policy_v0.py).
The architectural change is documented in [`docs/MIGRATION.md`](docs/MIGRATION.md).
