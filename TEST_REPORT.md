# Ouroboros v1.1 upgrade and release-candidate test report

Date: 2026-07-16  
Host: macOS, Python 3.11.15  
ActiveGraph: 1.10.0  
Live provider/model: OpenAI / `gpt-5.6-sol`

## Recommendation

Work from this Codex-authored v1.1 kernel. It closes the defects in the Replit
report, preserves the single-file ActiveGraph architecture, and has a complete
current-source live promotion. The Claude version remains useful as a
comparison artifact, but is not the stronger base: the Codex kernel has the
broader tested evaluator, immutable evidence bundle, manager-only private suite,
explicit capability gate, and durable cost/accounting path.

## Outcome

The deterministic suite passes 25/25 tests. Ruff and Python compilation pass.
The final scratch live run attempted one generation and promoted one generation:

| Signal | Incumbent | Candidate |
|---|---:|---:|
| Public executable tests | 3/8 (0.375) | 8/8 (1.0) |
| Manager-private tests | 1/5 (0.2) | 5/5 (1.0) |
| Mirrored qualitative score | 10.0 | 96.5 |
| Hard gates | fail | pass |

The kernel recorded `execution-grounded deterministic dominance`. The candidate
won all six mirrored rubric aggregates, its worst qualitative delta was +62,
and there were no meaningful losses. Its final content ID is
`workspace-sha256-b9e29c93d1d614090d95e5847ddc7533f3b811f3ced489c7d8a18d1cb62802ba`.

- [Final result](artifacts/live-runs/upgrade-openai-evolution-20260716-v3/result.json)
- [Promotion record](artifacts/live-runs/upgrade-openai-evolution-20260716-v3/promotion.json)
- [Evaluation](artifacts/live-runs/upgrade-openai-evolution-20260716-v3/generations/g001/evaluation.json)
- [Trace](artifacts/live-runs/upgrade-openai-evolution-20260716-v3/trace.sqlite)
- [Promoted workspace](artifacts/live-runs/upgrade-openai-evolution-20260716-v3/final_workspace/)

## Replit finding closure

| Finding | Resolution | Coverage/evidence |
|---|---|---|
| C1 manifest schema rejected valid argv/stdout candidates | Added `argv` and `stdout`, publishes the exact manifest contract to the builder, and validates submission early so it can self-correct | `test_14_argv_stdout_manifest_reaches_judge_and_promotes`; live candidate uses argv/stdout |
| C2 tool budget assumed one tool per turn and was shared badly | Runtime budget is generations × turns × calls-per-turn; per-generation counters are separate | `test_17_runtime_budget_has_parallel_margin_and_cost_taxonomy` |
| C3 builder could not see its budget | Initial request and every tool result contain live used/remaining counters | `test_05c_builder_receives_manifest_and_live_budget_contract`; 28/140 live tool calls |
| C4 dead `behavior.failed` path/status ambiguity | Removed the dead subscriber; runtime failures are handled after ActiveGraph returns, recoverable builder failures reject only that generation, and cost exhaustion has its own terminal status | `test_08`, `test_16`, `test_17` |
| C5 no cost cap or ledger | Added model-call, token, time, tool, and dollar controls plus durable `usage.json` accounting by phase | Final live run: 15 model calls, 206,561 input tokens, 12,703 output tokens, estimated $1.413895 under a $5 cap |
| C6 capabilities were prose only | Compiler emits canonical capability flags and the kernel blocks unsupported network/package objectives before private-suite or builder spend | `test_15_capability_gate_stops_before_private_or_builder_spend` |
| C7 private tests cloned public tests, leaked details, and influenced judge | Separate private-suite LLM behavior; semantic clone removal; exact suite and results only under manager `private/`; public artifacts use receipts/digests; judge receives no private pass rates | `test_03`, `test_05b`, `test_05d`; live semantic clone count 0 |
| C8 preflight could leave empty history | Finalization always writes a non-empty auditable history row and complete top-level bundle | preflight/bundle tests |
| C9 run collisions and dead code | Reused run IDs fail cleanly without a traceback or mutation; dead branch removed | `test_18_run_id_collision_is_clean_and_non_destructive` |

The event namespace remains `ouro.v0` because that is the original protocol
contract, not an implementation version. Engine version is independently
reported as `1.1.0-workspace`.

## Additional upgrades

- Ordered `state_persistence` tests execute multiple processes in one isolated
  workspace, making durable state observable instead of inferred.
- Private tests are normalized to at least two distinct behaviors and capped at
  eight; the live suite has five with zero public semantic clones.
- Every qualitative criterion is presented in mirrored A/B and B/A views. The
  kernel unblinds and aggregates the pair, requiring both views to confirm a
  severe regression.
- Strict deterministic dominance is explicit. A hard-gate-passing candidate
  that non-regressively improves executable public/private evidence cannot be
  rejected solely by a contradictory qualitative label.
- GPT-5.6 tool turns use a narrow Chat Completions compatibility adapter that
  sets `reasoning_effort=none`; non-tool compiler/private/judge calls retain the
  model default. Anthropic tool token counting is also fixed locally for
  ActiveGraph 1.10 cost caps.
- Candidate submission validates the manifest and entrypoint before ending the
  builder session. Recoverable exhaustion/schema failures advance to the next
  generation instead of terminating the campaign.

## Commands and observed results

Static and deterministic validation:

```bash
/Users/yoheinakajima/Documents/activegraph-bridge/.venv/bin/python -m py_compile ouroboros.py
/Users/yoheinakajima/Documents/activegraph-bridge/.venv/bin/ruff check ouroboros.py tests/test_ouroboros.py
/Users/yoheinakajima/Documents/activegraph-bridge/.venv/bin/python -m unittest -v tests.test_ouroboros
```

Observed: compilation passed, Ruff reported `All checks passed!`, and unittest
reported `Ran 25 tests ... OK`. Logged `llm.network_error`,
`tool.max_turns_exhausted`, and `budget.cost_exhausted` lines are deliberate
fault injections with asserted terminal/recovery behavior.

Final live command:

```bash
python ouroboros.py \
  "Build a robust multi-file argv todo CLI with persistent local JSON state, add/list/done/stats commands, helpful errors, and real automated tests." \
  --provider openai --model gpt-5.6-sol \
  --run-root artifacts/live-runs \
  --run-id upgrade-openai-evolution-20260716-v3 \
  --generations 1 --max-tool-turns 35 --max-tool-calls-per-turn 4 \
  --max-llm-calls 42 --max-cost-usd 5 \
  --command-timeout 45 --test-timeout 30 --memory-mb 1024 --json
```

Observed: completed in 4m23s; 12 builder calls, 28 tool calls, 15 total model
calls, estimated $1.413895, one accepted generation, and one terminal event.
The run-manifest engine hash equals the current `ouroboros.py` SHA-256:
`c477b44a78e3fbdce15baab855ac26e97b9d668c7fc3ec4cacaa46957469c818`.

Independent promoted-workspace verification:

```bash
cd artifacts/live-runs/upgrade-openai-evolution-20260716-v3/final_workspace
python -m unittest discover -v
python todo.py --data-file /tmp/audit.json add "Audit release"
python todo.py --data-file /tmp/audit.json list
python todo.py --data-file /tmp/audit.json done 1
python todo.py --data-file /tmp/audit.json stats
```

Observed: all six candidate tests passed. The real sequence added and listed one
pending item, completed it, and reported total 1 / pending 0 / completed 1.

## Immutable live debugging trail

| Bundle | Outcome | Defect exposed |
|---|---|---|
| `upgrade-openai-baseline-20260716` | baseline-only, complete | Validated GPT-5.6 contract/private path and accounting at $0.250165 |
| `upgrade-openai-evolution-20260716` | failed, seed preserved | GPT-5.6 Chat Completions rejects tools with reasoning enabled; added the scoped compatibility client |
| `upgrade-openai-evolution-20260716-v2` | completed, strong candidate rejected | 6/6 public, 5/5 private, 4/4 own tests; one judge row's prose and A/B score contradicted each other; added mirrored views and deterministic dominance |
| `upgrade-openai-evolution-20260716-v3` | completed, promoted | Current source: 8/8 public, 5/5 private, 6/6 own tests, judge 96.5 vs 10.0 |

The failed/rejected bundles were intentionally retained rather than rewritten.

## Integrity and leakage audit

- SQLite `PRAGMA integrity_check`: `ok`.
- Trace: 321 events, 15 `llm.requested`, 28 `tool.requested`, one candidate
  acceptance, zero runtime errors, and exactly one terminal event.
- Run-manifest source hash matches the current engine.
- Exact provider credential values from `.env` were compared against every
  bundle file, including SQLite: zero hits. Values were never printed.
- Exact private-suite bytes do not occur in public contract, suite, or receipt
  artifacts. Candidate-visible/public canary scan: zero hits.
- Final tree: 10 files, 12,752 bytes, no symlinks, content-addressed promotion.

## Remaining limitations

1. This remains constrained execution, not a universal hostile-code sandbox.
   macOS Seatbelt provides the strongest tested boundary; use a disposable VM
   or container for untrusted candidate code on other hosts.
2. Public and private tests are LLM-compiled. Executable evaluation, semantic
   de-duplication, manager separation, and mirrored judging reduce errors but do
   not prove specification completeness.
3. Private material is access-separated by bundle path and public redaction,
   not encrypted. Anyone with manager-run-directory access can read it.
4. Dollar totals are provider price-table estimates, not billing-system
   receipts. The runtime still enforces its estimate before subsequent calls.
5. The GPT-5.6 Chat Completions tool limitation means builder tool turns use
   reasoning effort `none`; moving ActiveGraph's builder transport to the
   Responses API would allow tool use with the model's reasoning mode.
6. Mirrored judge views are position-balanced but evaluated in one model call,
   so they are not statistically independent. Deterministic evidence remains
   the release authority when it strictly dominates.
7. Bundle immutability is logical: exclusive run IDs and content hashes detect
   mutation, but completed directories are not filesystem-locked or signed.
8. This release live-tested a standard-library Python argv application. Network,
   package-install, non-Python, and multi-generation live campaigns still need
   broader release evidence.
