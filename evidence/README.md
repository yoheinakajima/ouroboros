# Curated evidence

This directory contains small, reviewable summaries suitable for Git. Raw run
trees, SQLite traces, exact model events, candidate workspaces, and
manager-private fixtures remain local under `artifacts/` and may be published
as redacted assets on tagged releases. They are intentionally not source files.

`pilot_summary.json` records the current mechanism evidence. It is not a hard
benchmark result and must not be presented as a reliability leaderboard.

`sandbox_smoke.json`, `calibration_smoke.json`, and
`benchmark_bootstrap.json` are infrastructure receipts. They prove local
container, grading/audit, source, task-file, and image-digest paths—not that an
agent solved any upstream benchmark task. `upstream_tasks_executed` is false in
the calibration summaries for this reason.
