# Ouroboros

Ouroboros is an open-ended **software-workspace evolution** engine. You give it
a vague one-line objective; it compiles that objective into an *executable
evaluation contract*, materializes a tiny seed workspace, and then repeatedly
lets a powerful LLM autonomously build inside a candidate workspace — inspecting,
creating, rewriting, moving, and deleting files, running commands and tests as it
goes. Each candidate is judged by deterministic hard gates, public and private
behavioral tests run in clean subprocesses, and a blinded qualitative judge. A
candidate is **promoted only when execution-grounded evidence shows an
improvement**, and the promoted workspace becomes the next incumbent.

There is **no human code-review step inside the evolution loop**. The engine
kernel (`ouroboros.py`) is a single, copyable, dependency-light Python file and
is immutable for the duration of a run. A workspace may propose a
`next_ouroboros.py`, which is recorded as a *release candidate* for a manager to
test and promote through ordinary version control — never hot-swapped into the
running kernel.

Everything is recorded natively in [ActiveGraph](https://pypi.org/project/activegraph/):
every LLM call, tool call, file change, command, test result, evaluation,
rejection, and promotion, in one immutable run bundle with a unique
`trace.sqlite` per invocation.

> This is the successor to the v0 *text-policy mutator*. See
> [`docs/MIGRATION.md`](docs/MIGRATION.md) for the pivot rationale and
> [`experiments/baselines/text_policy_v0.py`](experiments/baselines/text_policy_v0.py)
> for the preserved baseline.

## Install

```bash
pip install "activegraph[anthropic]"
export ANTHROPIC_API_KEY="sk-ant-..."
```

Python 3.11+. The only third-party imports are `activegraph`, `pydantic`, and
(transitively) the Anthropic SDK. The engine imports no local modules and can be
copied anywhere as a single file.

## Quick start

```bash
# Evolve a workspace from the embedded seed toward an objective
python ouroboros.py "Build a small CLI calculator" --generations 5

# Grant extra capabilities
python ouroboros.py "Build a web research agent" \
    --generations 5 --allow-network --allow-pip

# Evolve an existing project instead of the embedded seed
python ouroboros.py "Make the tests pass and harden the parser" \
    --seed-dir path/to/project/ --generations 4

# Inspect the engine contract without running
python ouroboros.py --describe

# Compile an objective to a contract and exit (no evolution)
python ouroboros.py "Build a JSON todo CLI" \
    --export-objective-contract contract.json
```

Every run writes an immutable bundle under `.ouroboros/runs/<run-id>/` and prints
`OUROBOROS_RESULT_JSON=<path>` on completion. The default mode needs only an API
key and is safe to run in a disposable container.

## How one generation works

```
incumbent workspace
      │  clone into a clean candidate directory
      ▼
build session ── LLM builder with tools ──────────────────────────┐
      │  list_tree · read_file · write_file · apply_patch          │ many
      │  delete_file · make_directory · run_command · fetch_url    │ tool
      │  submit_candidate(summary, evidence, next_strategy)        │ turns
      ▼                                                            ┘
validate manifest + workspace (path/symlink/size guards)
      ▼
evaluate (in clean subprocesses):
   1. hard gates      manifest valid · entrypoint exists · program starts ·
                      protocol valid · declared tests run · required artifacts
   2. behavioral      public tests (visible) + private tests (hidden)
   3. blinded judge   rubric anchors, balanced A/B, anonymized transcripts
      ▼
decide (deterministic): reject tree/behavior no-ops before judging;
   promote only on more meaningful wins than losses, no severe regression,
   and satisfied qualitative bar. Hard-gate failures cannot be overridden.
      ▼
promote → candidate becomes the next incumbent   (or reject → keep incumbent)
```

## The workspace manifest

Each workspace owns a manifest, `ouroboros.json`, which the candidate may rewrite
(including changing the entrypoint and whole architecture). The kernel validates
it before any execution.

```json
{
  "schema_version": 1,
  "language": "python",
  "entrypoint": ["python", "agent.py"],
  "test_command": ["python", "test_agent.py"],
  "input_protocol": "json-stdin",
  "output_protocol": "json-stdout",
  "environment": {}
}
```

Supported `input_protocol`: `json-stdin`, `text-stdin`, `argv`, `none`.
Supported `output_protocol`: `json-stdout`, `text-stdout`, `none`.
The entrypoint and test command must invoke `python`/`python3` (script or `-m`
module) that resolves inside the workspace.

## Execution grounding

The evaluator distinguishes **actual execution from textual claims**. Public and
private tests are `TestCaseSpec`s executed in fresh subprocess copies of the
workspace:

| kind | what it does |
|------|--------------|
| `entrypoint_io` | runs the entrypoint, feeds stdin, checks stdout/exit/JSON |
| `state_persistence` | invokes the program **twice**, verifies state carried across runs |
| `command` | runs the declared test command (or entrypoint) with args |
| `http_request` | starts the entrypoint as a server on `$PORT`, makes a real HTTP request |
| `python_call` | imports and calls the public API via a snippet |
| `artifact` | checks required files exist / contain expected content |

A prose description of a capability never satisfies a capability test.

## Capabilities and isolation

Candidate code runs in constrained subprocesses: `shell=False`, argv arrays, a
stripped environment (no inherited API keys), a workspace-local `HOME`/`TMPDIR`,
its own process group, and CPU / address-space / file-size / open-file limits
(POSIX `RLIMIT_*`, where supported). Output is size-capped. On macOS, commands
are additionally wrapped in a Seatbelt (`sandbox-exec`) profile that hides the
real home directory, makes the filesystem read-only outside the candidate
workspace, and denies networking unless `--allow-network` is set — defense in
depth on top of the portable controls.

- **Network** is off by default. `fetch_url` is disabled and proxy variables are
  stripped from subprocess environments unless `--allow-network` is passed.
- **Package installation** (`pip`, `uv`, `poetry`, `npm`, …) is blocked unless
  `--allow-pip` is passed.

The candidate cannot reach the private test directory, the outer trace database,
other generations' workspaces, parent-environment secrets, or the run's promotion
logic — the path guard rejects absolute paths, `..` traversal, drive letters, NUL
bytes, and symlink escapes, and command/file access to the run bundle is refused.

> This is **constrained execution, not a hardened sandbox**. On an open host, raw
> sockets are not firewalled by stripping proxy variables. Run in a disposable
> container. See [`docs/TEST_REPORT.md`](docs/TEST_REPORT.md) for the specific,
> evidence-backed limitations.

## Self-improvement state

`SELF.md` and `MEMORY.md` are ordinary mutable workspace files. The builder reads
them at the start of each generation and may update them. They are promoted only
as part of a workspace that passes the full evaluation — there is no special,
unmeasured acceptance path for self-advice.

## History compaction

Full exact history is retained permanently in `trace.sqlite`, `history.json`,
`lineage.jsonl`, and per-generation artifacts. The builder sees a bounded
hierarchical view: the latest 3 generations in full public detail, the preceding
7 as compact summaries, and everything older folded recursively into a single
archive summary. Private test prompts, IDs, scores, deltas, and judge material
never enter the builder-visible view.

## Meta-evolution

Give Ouroboros an objective about improving itself and the workspace may produce
`next_ouroboros.py`. It is **never** executed or hot-swapped into the running
kernel; it is recorded in `promotion.json` as an `engine_meta_candidate` release
candidate for a manager to run through the release suite and promote in a
subsequent Git commit.

## The run bundle

```
.ouroboros/runs/<run-id>/
    manifest.json               reproducibility + engine/provider metadata + hashes
    objective_contract.json     the public compiled contract
    public_suite.json           public executable tests
    private_suite_receipt.json  sealed hash receipt (hidden tests withheld here)
    history.json                full exact generation history
    lineage.jsonl               append-only lineage records
    promotion.json              manager release handoff + release candidates
    result.json                 terminal status + summary + paths
    trace.sqlite                ActiveGraph event log (unique per run)
    seed_workspace/             generation-0 tree
    final_workspace/            latest ACCEPTED incumbent (never a failed candidate)
    private/                    manager-only: hidden suite + per-gen private results
    generations/
        g000/  workspace/ tree.json execution.json
        g001/  candidate/ tree.json diff.json tool_session.json
               public_results.json private_results.json evaluation.json
        ...
```

Every workspace version has a stable content ID
`workspace-sha256-<tree-hash>`, computed from sorted relative paths plus file
content hashes (never absolute paths). Runs never overwrite each other.

Terminal status is always exactly one of: `baseline_only`, `completed`,
`failed`, `budget_exhausted`, `unsupported`. A complete bundle and exactly one
terminal `ouro.v0.run.finished` event are produced on **every** path, including
mid-run LLM failure, timeout, and budget exhaustion.

A *recoverable* builder failure in one generation — the model runs out of tool
turns or returns unparseable/schema-violating final output — is rejected as a
single generation and the run continues to the next generation, rather than
ending the whole run. Provider/network/budget failures still finalize.

## Inspecting a trace

```bash
activegraph inspect "sqlite:///$(pwd)/.ouroboros/runs/<run-id>/trace.sqlite"
```

Application events are namespaced `ouro.v0.*`. Modeled object types include
`objective_contract`, `workspace_version`, `file_blob`, `build_session`,
`file_change`, `command_run`, `public_test_suite`, `private_test_suite`,
`test_result`, `evaluation`, `history_summary`, `release_candidate`, and
`run_summary`, linked by `derived_from`, `contains`, `modified_by`,
`executed_as`, `evaluated_by`, `superseded_by`, `summarized_by`, and
`proposed_as` relations.

## Manager / release model

The engine never mutates its own repository working copy. Within a run it accepts
progressively better workspaces; the final incumbent lands in
`final_workspace/`, and `promotion.json` is the handoff to a manager — it is not
an automatic release. The manager is the sole release authority: it retains and
verifies the bundle, runs its own release suite, and applies accepted changes
through version control.

## Tests

```bash
python -m pytest tests/test_ouroboros.py -v
```

Most tests drive a deterministic scripted provider so the real tool bodies,
subprocess execution, evaluation, and ActiveGraph trace are exercised without a
live model. One optional test runs a live model end-to-end when
`ANTHROPIC_API_KEY` is set. See [`docs/TEST_REPORT.md`](docs/TEST_REPORT.md) for
the full report, commands, and observed behavior.

## CLI reference

```
python ouroboros.py "OBJECTIVE" [options]

  --generations N            number of evolution generations (default 5; 0 = baseline only)
  --allow-network            enable fetch_url and network env passthrough
  --allow-pip                enable package-installation commands
  --seed-dir DIR             evolve an existing project instead of the embedded seed
  --provider {anthropic,openai}   LLM provider (default anthropic)
  --model NAME               provider model (default: provider default)
  --run-root DIR             where run bundles are written (default .ouroboros/runs)
  --run-id ID                explicit run id (default: timestamp + random)
  --max-tool-turns N         builder tool turns per generation (default 40)
  --command-timeout S        per-command wall-clock cap (default 60s)
  --test-timeout S           per-test wall-clock cap (default 30s)
  --max-run-seconds S        whole-run wall-clock budget (default 3600s)
  --max-cost-usd USD         cost ceiling in USD (optional; safe to set)
  --max-workspace-files N    workspace file-count cap (default 400)
  --max-workspace-bytes N    workspace byte cap (default 8_000_000)
  --describe                 print the engine contract as JSON and exit
  --export-objective-contract PATH   compile the objective, write contract, exit
  --quiet / --json           output controls
```
