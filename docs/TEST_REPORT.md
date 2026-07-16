# Ouroboros test report

Observed behavior of the workspace-evolution engine (`ouroboros.py`), not a
specification. Every command below was run and its result recorded.

## Environment

| | |
|---|---|
| Date | 2026-07-16 |
| Python | 3.11.15 |
| Platform | Linux-6.18.5-x86_64-with-glibc2.39 |
| activegraph | 1.10.0 |
| pydantic | 2.13.4 |
| anthropic (SDK) | 0.117.0 |
| engine source SHA-256 | `801a7245a4283b71c80b1d2705019e6fb8039ebce951164dd9e1ed691ae02921` |
| `ANTHROPIC_API_KEY` | not set in this environment |

Sizes: `ouroboros.py` 4485 lines; `tests/test_ouroboros.py` 1240; `tests/scripted_provider.py` 219; preserved baseline `experiments/baselines/text_policy_v0.py` 2946.

## How the tests exercise the real system

Most tests drive a deterministic `ScriptedProvider` (implements the ActiveGraph
`LLMProvider` protocol) that scripts the model's tool calls and structured
outputs. **Only the model is scripted** — the tool bodies, the workspace-root
path guard, the subprocess sandbox, all public/private test execution, the
promotion rule, finalization, and the `trace.sqlite` event log are the real
engine code paths. The scripted builder issues real `write_file` / `run_command`
/ `submit_candidate` calls that the runtime dispatches through the real tools,
which really mutate the candidate workspace and are really re-executed in clean
subprocesses during evaluation.

## Commands and results

### Full suite

```
$ python -m pytest tests/test_ouroboros.py -v
19 passed, 1 skipped in 5.77s
```

The 1 skip is the live-model end-to-end test (`test_live_end_to_end_multifile`),
skipped because `ANTHROPIC_API_KEY` is not set here. See "Live end-to-end" below.

| # | Test | Requirement covered | Result |
|---|------|--------------------|--------|
| 1 | `test_multifile_growth` | Multi-file growth; success not satisfied by prose | PASS |
| 2 | `test_workspace_restructuring` | Delete/replace seed entrypoint; update manifest; new entrypoint works | PASS |
| 3 | `test_actual_web_behavior` | Real HTTP fixture; `--allow-network`; agent fetches and cites content | PASS |
| 4 | `test_fetch_url_disabled_without_flag` | `fetch_url` refused without `--allow-network` | PASS |
| 5 | `test_existing_project_evolution` | `--seed-dir`; improve an intentionally failing project | PASS |
| 6 | `test_hidden_test_isolation` | Private canary never leaks to builder-visible surfaces | PASS |
| 7 | `test_noop_rejected_without_judge` | Unchanged tree rejected without a judge call | PASS |
| 8 | `test_failure_finalization` | Builder failure after 1 accepted gen → complete bundle; `final_workspace` = latest incumbent | PASS |
| 9 | `test_long_history_bounded_view` | 55 generations; full history grows; builder view bounded; no private leak | PASS |
| 10 | `test_run_uniqueness` | Separate run IDs/traces; stable content hashes | PASS |
| 11 | `test_activegraph_integrity` | Trace loads; tool calls recorded; file changes linked to versions; lineage; one terminal event | PASS |
| 12 | `test_meta_candidate` | `next_ouroboros.py` recorded as release candidate; live engine untouched | PASS |
| 13 | `test_decide_promotion_rules` | Promotion rule: wins/losses, hard-gate override, regression blocks | PASS |
| 14 | `test_score_judgement_balanced_mapping` | Blinded A/B → candidate/incumbent mapping; missing-case detection | PASS |
| 15 | `test_path_guard` | Absolute/`..`/drive/NUL/symlink-escape all rejected | PASS |
| 16 | `test_manifest_validation` | Manifest schema + entrypoint/protocol/env validation | PASS |
| 17 | `test_apply_unified_patch` | Unified-diff apply; non-matching context reported not applied | PASS |
| 18 | `test_tree_hash_is_path_content_based` | `workspace-sha256` from sorted paths + content, not absolute paths | PASS |
| 19 | `test_describe_and_export_contract` | `--describe` contract surface | PASS |
| 20 | `test_live_end_to_end_multifile` | Live model, multi-file evolution end-to-end | SKIPPED (no API key) |

Requirements #1–#11 from the task's TESTS section map to tests as: 1→#1, 2→#2,
3→#3(+#4), 4→#5, 5→#6, 6→#7, 7→#8, 8→#9, 9→#10, 10→#11, 11→#12.

### Demo run bundle (inspected)

A representative run kept for inspection (scripted provider, one promoted
generation):

```
$ python - <<'PY'
# scripted multi-file CLI objective, run_id="demo-multifile-cli"
PY
status: completed | promoted: 1 / attempted: 1
final_workspace_id: workspace-sha256-89d05830a4c9348f44e78bc...
```

Bundle at `demo_runs/demo-multifile-cli/` (git-ignored; regenerate with the
snippet in "Reproducing"). Full layout produced:

```
manifest.json  objective_contract.json  public_suite.json
private_suite_receipt.json  history.json  lineage.jsonl
promotion.json  result.json  trace.sqlite
seed_workspace/{agent.py,ouroboros.json,SELF.md,MEMORY.md,test_agent.py}
final_workspace/{agent.py,calc/__init__.py,calc/ops.py,ouroboros.json,SELF.md,MEMORY.md,test_agent.py}
private/{private_suite.json,private_results_g000.json,private_results_g001.json}
generations/g000/{workspace/,tree.json,execution.json}
generations/g001/{candidate/,tree.json,diff.json,tool_session.json,
                  public_results.json,private_results.json,evaluation.json}
```

The seed (echo agent) fails the public tests at generation 0; the promoted
candidate is a genuine multi-file package (`agent.py` + `calc/ops.py` +
`calc/__init__.py`) whose CLI really runs:

```
g001 evaluation reason: wins=4 losses=0, public 2/2, judge avg +0.0
final_workspace CLI: {"task":"add 40 2"} -> {"result": 42, "op": "add"}
```

### Trace integrity (inspected)

```
$ activegraph inspect "sqlite:///$(pwd)/demo_runs/demo-multifile-cli/trace.sqlite"
run_id:           demo-multifile-cli
state:            idle
events_processed: 143
recent events (last 20): ... ouro.v0.candidate.promoted ... ouro.v0.run.finished ... runtime.idle
```

Event/object/relation census for that run (via `SQLiteEventStore.iter_events`):

- **143 total events**; `llm.requested` 7 (contract, private, 4 builder tool
  turns + 1 final, judge), `tool.requested`/`tool.responded` 9 each,
  `object.created` 34, `relation.created` 41, `ouro.v0.run.finished` **1**.
- **Objects created:** `run` 1, `objective_contract` 1, `public_test_suite` 1,
  `private_test_suite` 1, `workspace_version` 2, `file_blob` 12,
  `build_session` 1, `file_change` 7, `command_run` 1, `test_result` 4,
  `evaluation` 1, `history_summary` 1, `run_summary` 1.
- **Relations:** `contains` 23, `derived_from` 1, `modified_by` 1,
  `executed_as` 4, `evaluated_by` 8, `superseded_by` 1, `summarized_by` 2,
  `proposed_as` 1.

`test_activegraph_integrity` asserts each required object type exists, that
`workspace_version → file_blob` and `build_session → file_change` `contains`
edges exist, that `modified_by`/`evaluated_by`/`superseded_by` lineage edges
exist, and that exactly one `ouro.v0.run.finished` event is present.

### Terminal-status paths (inspected)

- `--generations 0` (or scripted equivalent) → **`baseline_only`**, 0 promoted,
  complete bundle.
- Scripted no-op submission → **`completed`** with the single generation rejected
  at stage `tree_noop`, and `test_noop_rejected_without_judge` confirms
  `ouro_judge` never fired (no `llm.requested` with `behavior=ouro_judge`).
- Injected builder crash after one accepted generation → **`failed`**, complete
  bundle, `final_workspace` byte-equal to the generation-1 accepted tree, exactly
  one terminal event.
- Missing `ANTHROPIC_API_KEY` with the real provider → **`failed`** with reason
  "ANTHROPIC_API_KEY is not set" and a complete `result.json` (observed via the
  `--export-objective-contract` CLI path, which returned a `failed` result and a
  written bundle rather than crashing).

### CLI paths (inspected)

```
$ python ouroboros.py --describe            # exit 0, prints engine contract JSON
$ python ouroboros.py                        # exit 2, "an objective is required"
$ python ouroboros.py --export-objective-contract contract.json "Build a JSON todo CLI"
    # no API key here -> compiles nothing, writes a failed bundle, reports it
```

### Live end-to-end

`test_live_end_to_end_multifile` runs a real 2-generation evolution of "a
command-line to-do list tool that stores tasks as JSON on stdin/stdout" against
the Anthropic API and asserts a terminal status in
{`completed`,`baseline_only`,`budget_exhausted`}, exactly one terminal event, and
a materialized `final_workspace`. **It was not executed in this environment
because `ANTHROPIC_API_KEY` is not set.** To run it:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python -m pytest tests/test_ouroboros.py::test_live_end_to_end_multifile -v
# or directly:
python ouroboros.py "Build a command-line to-do list tool (JSON stdin/stdout)" --generations 3
```

## Reproducing

```bash
pip install "activegraph[anthropic]" pytest
python -m pytest tests/test_ouroboros.py -v          # 19 pass, 1 skip (no key)
```

To regenerate the inspected demo bundle:

```bash
python - <<'PY'
import sys; sys.path.insert(0, "tests")
from pathlib import Path
import scripted_provider as sp, test_ouroboros as t
prov = sp.ScriptedProvider(
    contract=sp.contract(objective="Build a small CLI calculator that adds and multiplies",
                         public_tests=t.cli_public_tests()),
    private=t.cli_private_tests(), builder_generations=t.cli_builder_script())
res = t.run_scenario(Path("demo_runs"), prov,
    objective="Build a small CLI calculator that adds and multiplies", run_id="demo-multifile-cli")
print(res["status"], res["paths"]["run_dir"])
PY
activegraph inspect "sqlite:///$(pwd)/demo_runs/demo-multifile-cli/trace.sqlite"
```

## Remaining limitations (specific, evidence-backed)

1. **Constrained execution, not a hardened sandbox.** Isolation is a stripped
   environment + POSIX `RLIMIT_*` + workspace-rooted path guard + process-group
   kills. Network-off works by stripping proxy variables and gating
   `fetch_url`/`pip`; it does **not** firewall raw sockets. Evidence:
   `test_actual_web_behavior` reaches `127.0.0.1` over loopback with
   `--allow-network`, and the same loopback path is not blocked by the
   network-off env stripping. Run in a disposable container.

2. **`RLIMIT_AS` is coarse and POSIX-only.** The default 1024 MB address-space
   cap was verified sufficient for plain-Python candidates in this environment,
   but memory-hungry candidates (large imports, `pip`-installed native deps) can
   fail to start under it, and on non-POSIX platforms `resource` is absent so no
   memory/CPU/file-size limits are applied at all (the engine degrades to
   timeout-only). Not exercised: candidates that legitimately need >1 GB.

3. **Python-only.** `validate_manifest_data` rejects any `language` other than
   `python` and requires the entrypoint/test command to invoke `python`/`python3`.
   Evidence: `test_manifest_validation` asserts a `ruby` manifest is rejected.
   Other languages are out of scope for this kernel.

4. **`apply_patch` is a tolerant custom applier, not GNU patch.** It matches hunk
   context with ±200-line drift search and has limited trailing-newline handling.
   Evidence: `test_apply_unified_patch` confirms a clean apply and that
   non-matching context is reported (not silently applied), but complex
   multi-hunk or fuzzy patches may be rejected — the builder is expected to fall
   back to `write_file` for whole-file rewrites (and does so in every scripted
   scenario).

5. **Scripted-provider coverage ≠ live-model coverage.** 19 tests prove the
   *engine mechanics* (tools, evaluation, gates, promotion, isolation, trace,
   finalization) with a deterministic model. They do **not** demonstrate that a
   live model reliably drives multi-generation improvement — that is what the
   skipped `test_live_end_to_end_multifile` covers, and it was not run here for
   lack of an API key. The end-to-end learning claim is therefore untested in
   this environment.

6. **`http_request` tests assume a `$PORT`-honoring server that binds fast.** The
   harness starts the entrypoint, injects `PORT`, and waits up to ~15 s for the
   port. Servers that read the port from elsewhere, bind slowly, or never open
   the socket fail the gate. Not exercised: frameworks with non-`$PORT`
   conventions.

7. **`state_persistence` verification is heuristic.** It invokes the program
   twice and checks that declared expectations hold and (when
   `changes_across_runs` is set) that outputs differ across runs; it does not
   model arbitrary state semantics. A program can persist state the harness does
   not probe.

8. **Judge blinding limits deterministic judge-driven tests.** Because the A/B
   mapping is a hash of `run_id:generation:case_id` and `run_id` is random, tests
   cannot force a specific judge-driven candidate regression end-to-end; the
   judge scoring/mapping and the severe-regression promotion block are therefore
   covered by unit tests (`test_score_judgement_balanced_mapping`,
   `test_decide_promotion_rules`) rather than a live judge scenario.

9. **Whole-workspace re-hash on every write.** `write_file` recomputes workspace
   integrity (a full tree hash) after each write for budget enforcement — O(files)
   per write. Fine at the default 400-file / 8 MB caps; not tuned for very large
   trees.

10. **Long-history bounding is proven synthetically.** `test_long_history_bounded_view`
    drives the compaction functions over 55 generations and asserts the
    builder-visible view stays bounded (<12 KB) and private-free while the exact
    history grows to 55 — but it does not run 55 real LLM-backed generations.
