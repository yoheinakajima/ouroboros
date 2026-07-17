# Curated evidence

This directory contains small, reviewable summaries suitable for Git. Raw run
trees, SQLite traces, exact model events, candidate workspaces, and
manager-private fixtures remain local under `artifacts/` and may be published
as redacted assets on tagged releases. They are intentionally not source files.

`pilot_summary.json` records the current mechanism evidence. It is not a hard
benchmark result and must not be presented as a reliability leaderboard.

`sandbox_smoke.json`, `calibration_smoke.json`, `benchmark_bootstrap.json`,
`activegraph_50_calibration.json`, `swe_verified_calibration.json`, and
`terminal_bench_2_calibration.json` are infrastructure receipts. They prove
local container, grading/audit, source, task-file, image-digest, official
gold/verifier, and deliberate 20/50-seed-to-50/50-oracle paths—not that an
agent solved any benchmark task. Every calibration receipt records zero model
calls.

`swe_harbor_materialization.json` proves that all 70 committed SWE tasks were
generated from the pinned parquet through the pinned Harbor adapter, rewritten
to exact official image digests, stripped of evaluator tests and network
installs, and checked as patch-only no-network environments. Its handoff sample
also proves that an exported gold patch resolves under the separately pinned
official SWE-bench evaluator. Gold patches, test patches, and generated task
trees remain manager-private in the ignored cache; only hashes are tracked.

The SWE and Terminal calibration summaries retain aggregate hashes for every
initial failure, infrastructure retry, deterministic replacement, and final
pass. Protected patches, tests, and exact verifier output stay in the ignored
manager-local cache.

`swe_canary_workspace_v1_2.json` is different: it records paid model calls on
one development SWE task. It retains an aborted pre-inference run, a valid
negative attempt that exposed missing test-environment parity, and the matched
protocol-0.5 retry that resolved under the official evaluator. It is explicitly
not a held-out score, reliability estimate, or architecture comparison.
