# Curated evidence

This directory contains small, reviewable summaries suitable for Git. Raw run
trees, SQLite traces, exact model events, candidate workspaces, and
manager-private fixtures remain local under `artifacts/` and may be published
as redacted assets on tagged releases. They are intentionally not source files.

`pilot_summary.json` records the current mechanism evidence. It is not a hard
benchmark result and must not be presented as a reliability leaderboard.

`sandbox_smoke.json`, `calibration_smoke.json`, `benchmark_bootstrap.json`, and
`activegraph_50_calibration.json` are infrastructure receipts. They prove local
container, grading/audit, source, task-file, image-digest, and deliberate
20/50-seed-to-50/50-oracle paths—not that an agent solved any benchmark task.
`upstream_tasks_executed` is false in the external calibration summaries for
this reason.
