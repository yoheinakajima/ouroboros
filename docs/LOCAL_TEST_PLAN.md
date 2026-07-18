# Locally runnable comparison

This is the exact study we can run without Kaggle data, H100s, a hosted
sandbox account, or an external LLM judge. The machine-readable preregistration
is `research/local_study.json`.

## The three test families

| Family | Development | Held out | What success means |
|---|---:|---:|---|
| SWE-bench Verified | 20 issues | 50 issues | The official evaluator says the real GitHub issue is resolved without breaking required tests. |
| Terminal-Bench 2 | 6 tasks | 12 tasks | The official Harbor verifier passes the end-to-end terminal task. |
| Ouro-ActiveGraph-50 | 2 systems | 3 systems | A deliberately incomplete 20/50 Pack gains sealed output-and-graph checks, up to 50/50. |

The ActiveGraph development systems are an incident coordinator and an
approval workflow. The held-out systems are a quota scheduler, a provenance
pipeline, and nested delegated access control. Every system has 20 visible
checks and 30 sealed checks spanning typed state, relation topology, policy,
composition, adversarial inputs, idempotency, and cold-restart replay.

MLE-bench, RE-Bench, and PaperBench are explicitly outside this local study:
they respectively require accepted private data terms, H100-class compute, or
a trusted model judge. Their selections remain documented as future tracks but
cannot enter the local headline comparison.

## What is actually compared

The cold arm uses the same outer coding agent for all three adapters. It is a
model-and-harness floor, not evidence that one architecture is better. The
architecture comparison begins after each system receives the same development
curriculum and retains improvements in its native mutation unit:

- Workspace v1.2 retains a workspace tree.
- Minimal v2 retains evaluated procedures and deterministic capabilities.
- Hybrid retains an atomic set of hash-pinned ActiveGraph Packs.

Every evolved-state directory requires `evolution_manifest.json`, which binds
the approach, development suites/tasks, parent run ids, feedback policy,
artifact byte count, and artifact hash. Private/grader paths are rejected and
any mutation after manifest creation invalidates the state before evaluation.

The development boundary is also explicit. `research/lineage.py` creates a
strict allowlisted record containing only the public instruction, the agent's
own summary/evidence/submission, and a scalar grader receipt. Exact hidden
tests, expected values, grader logs, oracle patches, and manager cases cannot
be represented by that schema. A recorded ActiveGraph reflection distills one
transfer lesson, after which each approach uses a genuinely different native
path:

- Workspace v1.2 receives the evidence as seed material and may rewrite the
  entire retained workspace under its own public/private evaluator.
- Minimal v2 records every external receipt but promotes a procedure only
  after a passing score.
- Hybrid authors a complete documentation-grounded ActiveGraph Pack, passes
  public and manager-private event/typed-state trials, adopts it by exact hash,
  cold-restarts it, and answers future context queries by executing the Pack
  in a fresh credential-free subprocess.

This is the first point at which the approach labels have distinct causal
meaning. Repeating cold labels does not compare architectures because they all
use the same outer agent by design. Likewise, sharing one development receipt
across approaches is permitted only with the explicit unscored calibration
flag. Scored lineages reject cross-approach evidence and use independently
generated parent runs.

The decisive number is paired held-out uplift:

`score(evolved with retained improvement) - score(same history, improvement hidden)`

A sham artifact matched for development effort and approximate exposed context
size is the second control. Exposed context hashes and byte counts are recorded
for audit. Merely scoring well, retaining more code, or reusing a solution on
the same task does not establish recursive self-improvement.

## Better and worse

Scores are never blended into one “intelligence” number. SWE resolution rate,
Terminal pass rate, and ActiveGraph check score remain separate. Within each
family, tasks and random seeds are paired. A result is called better only when
the paired score difference is positive and uncertainty no longer includes
zero; otherwise it is reported as no detected winner.

Cost, model calls, tool calls, and wall time are secondary Pareto measures. If
two systems have indistinguishable task scores, the cheaper/faster one is more
efficient—not more capable. A strong recursive claim additionally requires
positive uplift in at least two families, including SWE-bench or
Terminal-Bench, benefit over the sham control, byte-identical cold reload, and
no material regression on development checks.

The confirmatory recursive stage stops after its fixed five replications. If
uncertainty still spans zero, the result is inconclusive; adding runs requires
a newly frozen follow-up study rather than a post-hoc extension.

## Spend gate

First run the no-model oracle calibration. Next, each approach traverses the
same committed development curriculum and writes a hash-pinned state lineage.
Then run one replication on the fixed 19-task recursive probe. Only after that
bundle audits cleanly do we run the three-replication full comparison or
five-replication recursive claim.

## Resumable Sol execution

The complete local preliminary study is driven by `research/study_runner.py`.
It fixes the model to `gpt-5.6-sol`, verifies the freeze root and exact local
ActiveGraph image before every stage, and checkpoints each task attempt,
official grade, sanitized evidence record, reflection, native state generation,
and held-out result row independently.

For three independent replications, the frozen plan contains 252 development
attempts (28 ordered generations for each of three approaches and three
replications), a 228-attempt one-replication causal probe, and 1,170 preliminary
held-out attempts across all 65 evaluation tasks. The probe must be complete and
free of infrastructure-invalid rows before the preliminary stage begins.

```bash
python -m research.study_runner plan --replications 3
python -m research.study_runner run \
  --run-root artifacts/sol-full-study-v1 \
  --replications 3 \
  --concurrency 3 \
  --through preliminary
```

Re-running the same command resumes from completed receipts. It never treats a
model failure as an infrastructure retry; partial task directories stop the
runner for inspection so paid attempts are not silently overwritten.
