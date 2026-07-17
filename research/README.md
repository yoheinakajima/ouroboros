# Ouroboros research program

Ouroboros is being treated as a family of testable recursive-improvement
architectures, not as a single demo whose success is inferred from vibes.

The motivating hypothesis is deliberately ambitious:

> A very small persistent agent, given a sufficiently expressive mutation
> unit and a trustworthy evaluation loop, may be able to grow into much more
> capable systems.

The current evidence supports **governed capability acquisition**. It does not
yet support the stronger claim of recursive self-improvement, where one
acquired improvement measurably helps the organism acquire the next one.

## Current status

- The hybrid author is a real ActiveGraph `@llm_behavior` using `gpt-5.6-sol`.
- It receives an exact, hash-recorded 90,406-character snapshot of the relevant
  ActiveGraph documentation.
- It proposes an atomic set of one to six complete Pack sources but has no release authority.
- Candidate source is checked before import, run in fresh subprocess trials,
  compared with the incumbent on public and manager-private cases, copied by
  exact bundle hash, then loaded only after restart.
- The test harness now verifies emitted outputs **and** materialized graph
  objects, object versions, relation endpoints, type counts, behavior failures,
  and post-restart transfer behavior.
- Two different graph-audited live pilots pass: a multi-tenant usage tracker and
  a dependency-aware release planner. A third portable task has matched passing
  Minimal-v2 and Hybrid runs on identical visible, hidden, and transfer cases.

See [RESULTS.md](RESULTS.md) for observed evidence, [PROTOCOL.md](PROTOCOL.md)
for the experimental rules, and [APPROACHES.md](APPROACHES.md) for the
architecture comparison.

The next phase is specified in [the hard research design](../docs/RESEARCH_DESIGN.md):
SWE-bench, Terminal-Bench, MLE-bench, selected long-horizon R&D tasks, and a
sealed 20/50-to-50/50 ActiveGraph construction benchmark. The suites in
`hard_benchmark.json` are calibration-locked research inputs, not executed results.
SWE-bench Verified and Terminal-Bench 2 can be oracle-calibrated locally without
a hosted sandbox account. The MLE, RE-Bench, and PaperBench tracks keep their
real data, accelerator, and trusted-grader prerequisites explicit.

## Run a recorded hybrid experiment

From the repository root, using the Python environment that contains
ActiveGraph 1.10:

```bash
python -m research.hybrid_author \
  --task research/tasks/dependency_release_planner.json \
  --run-dir artifacts/research-runs/my-dependency-run \
  --docs-root ../activegraph/docs \
  --model gpt-5.6-sol \
  --max-cost-usd 10 \
  --max-llm-calls 6 \
  --max-output-tokens 20000 \
  --author-timeout 900 \
  --trial-timeout 90
```

The local `.env` is read without printing secret values. Private and transfer
cases are not placed in the author prompt or author event trace.

## What a full run records

Every hybrid run directory contains:

- `run.manifest.json`: approach, task, timestamp, and ceilings;
- `request.public.json`: exactly what the author was allowed to see;
- `docs/index.json` and `docs/corpus.md`: exact documentation and hashes;
- `author.trace.sqlite` and `author.events.jsonl`: full ActiveGraph author run;
- `author.summary.json`: calls, tokens, model, cost, time, and failures;
- `proposal.json`: complete structured model output and source files;
- sealed private/transfer receipts plus manager-only exact suites;
- candidate source, generated manifest, subprocess stdout/stderr, case-level
  actual and expected values, graph assertion evidence, and behavior failures;
- the persistent organism database, adoption registry, and exact adopted pack;
- `result.json`: adoption, restart identity, and transfer results.

`research/run_index.json` separates valid experiments, valid negative evidence,
and invalid runs caused by harness defects. Failed experiments are retained.

## Research layout

```text
research/
  README.md                 this overview
  PROTOCOL.md               preregistered comparison rules
  APPROACHES.md             architectural analysis
  RESULTS.md                evidence-backed current findings
  benchmark.json            category-balanced task catalog
  hard_benchmark.json       external and sealed hard-suite design (locked)
  approaches.json           exact source hashes and hardening status
  contracts.py              architecture-neutral attempt/score records
  broker_protocol.json      equal outer tools, inference, and authority contract
  adapters/                 common outer-interface contract
  attempt_runner.py         one adapter → broker → grader → audit execution path
  selections/               score-blind task IDs, revisions, and image hashes
  readiness.py              no-spend execution and release preflight
  run_index.json            provenance and validity of recorded runs
  hybrid_author.py          docs-grounded LLM Pack author and recorder
  tasks/                    executable public/private/transfer contracts
```

The original benchmark catalog is now explicitly a pilot mechanism suite. A
task marked `designed` is a research commitment, not a claimed result. Raw run
trees are ignored; `../evidence/pilot_summary.json` is the public summary.
