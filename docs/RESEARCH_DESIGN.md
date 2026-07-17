# Comparative research design

Status: preregistration draft; execution is locked.

## Claim under test

The motivating hypothesis is that a minimal persistent agent can improve its
own future behavior by retaining evaluated changes. The benchmark must
distinguish three progressively stronger claims:

1. **Acquisition:** it can solve a difficult task and retain the result.
2. **Transfer:** the retained change works on new tasks after a cold restart.
3. **Recursive uplift:** retaining improvement A causes better acquisition of
   distinct improvement B than a matched organism without A.

Only the third supports “recursive self-improvement.” More code, more graph
objects, or a second successful task is not by itself evidence of recursion.

## Why the pilot suite is not the headline benchmark

The current fixtures are useful manager regressions: they proved hidden-case
handling, graph-state assertions, adoption, byte pinning, and restart. All
three valid hybrid tasks passed every check in one attempt, so they have a
ceiling effect and cannot discriminate architecture or reliability. The
manager also stores the private cases locally, which is appropriate for pilot
debugging but not for a public leaderboard.

The pilot suite remains versioned as mechanism evidence. It is excluded from
headline capability and recursive-improvement claims.

## Three studies

### Study 1 — common outcome

Question: with the same task container, task prompt, model, brokered tools, and
outer budget, which approach produces the best independently graded outcome?

Each approach gets the same general repo and terminal broker. The only intended
difference is the retained mutation unit:

- Workspace v1.2: arbitrary workspace tree.
- Minimal v2: evaluated procedure or pure deterministic capability.
- Hybrid: complete hash-pinned ActiveGraph Pack.

The operation schemas and authority invariants are versioned in
`research/broker_protocol.json`. Its implementation is still a readiness
blocker; the contract exists now so it cannot be quietly tailored per approach.

Report cold and evolved arms independently. The official grader, never the
agent, owns the score. A failed attempt, timeout, or budget exhaustion remains
in the denominator.

### Study 2 — recursive uplift

Question: does learning on development tasks improve performance on disjoint
evaluation tasks?

For every approach and task family, compare paired runs with the same seed:

- **Evolved:** retains the development-stage improvement.
- **Cold ablation:** has the same history and budget but retrieval/loading of
  the improvement is disabled.
- **Sham improvement:** performs a matched development stage and retains an
  irrelevant artifact of similar size/cost.

Primary measure: paired evaluation-score delta, evolved minus cold ablation.
Secondary measures: cost, model calls, latency, regression count, and retained
benefit after restart. The recursive claim requires a positive effect across
distinct B tasks, not merely reuse of A on more examples of A.

### Study 3 — native ceiling

Question: what can each architecture express when its natural strengths are
not forced into a lowest-common-denominator interface?

Native tasks are reported as capability profiles, not a cross-approach rank.
This is where pack composition, arbitrary workspace construction, and compact
procedure learning can each be shown at full power.

## Proposed hard suites

| Suite | Development / evaluation | What it measures | Grader |
|---|---:|---|---|
| Ouro-SWE-50 | 20 / 50 | Real unfamiliar-repository issue repair | Official SWE-bench Docker evaluator |
| Ouro-Terminal-12 | 6 / 12 | End-to-end builds, debugging, services, data, and system work | Harbor task tests |
| Ouro-MLE-6 | 3 / 6 | Continuous improvement of real ML scores over a supplied seed | Hidden MLE-bench grader |
| Ouro-REBench-2 | 1 / 2 | Long-horizon AI R&D optimization | METR task grader |
| Ouro-PaperBench-CodeDev-2 | 1 / 2 | Research understanding and substantial code reproduction | Official hierarchical rubric |
| Ouro-ActiveGraph-50 | 2 / 5 systems | Partial improvement from about 20/50 through typed state, relations, policy, replay, composition, and adversarial events | Sealed 50-check evaluator |

The external sources are the official [SWE-bench](https://github.com/SWE-bench/SWE-bench),
[Terminal-Bench/Harbor](https://github.com/harbor-framework/terminal-bench),
[MLE-bench](https://github.com/openai/mle-bench),
[RE-Bench](https://github.com/METR/RE-Bench), and
[PaperBench](https://github.com/openai/frontier-evals/tree/main/project/paperbench)
repositories. Upstream commits and exact task IDs are deliberately unpinned
until a no-score calibration checks runtime, license, data access, leakage,
broken tests, and cost. Selection is then frozen before any scored run.

## Task-selection rules

Selection happens without viewing model scores. A task is eligible only if:

- its grader runs reproducibly from a pinned image and revision;
- private grader material is not mounted into the agent filesystem;
- the task is not known broken, contaminated, or dependent on unavailable
  credentials;
- at least two independent humans agree the prompt and grader measure the same
  outcome;
- a seed solution or oracle establishes that the task is feasible;
- task runtime fits the declared resource envelope.

Calibration may remove an ineligible task but may not replace a hard task
because an approach scored poorly. Every removal and reason is published.
Recent analysis has shown that coding benchmark defects can materially distort
leaderboards, so selected SWE-style instances receive an explicit grader audit
before freezing.

## Controls and budgets

The primary model is `gpt-5.6-sol`. The initial common cap is $25, 80 model
calls, 200,000 output tokens, and two wall-clock hours per task attempt. These
are ceilings, not targets. Model, provider settings, broker, container digest,
CPU/GPU/RAM, source hashes, tool calls, token counts, and cost are recorded.

Use one run only for harness calibration, three independent replications for a
preliminary result, and at least five paired replications for a recursive
uplift claim. For stochastic ML tasks, use at least three seeds even during
preliminary evaluation. Increase replication when confidence intervals remain
too wide to distinguish practical effects.

## Scoring and reporting

Keep task-family scores separate; do not invent a weighted “general
intelligence” number. Publish:

- every task and attempt row, including zeroes and invalid infrastructure rows;
- mean, median, bootstrap interval, and paired deltas where applicable;
- pass rate for binary graders and normalized improvement for continuous ones;
- cost and wall time both unconditionally and conditional on success;
- regressions, requested authority, and restart retention;
- exact approach, prompt, docs, image, dependency, and grader hashes.

Infrastructure failures are labeled and rerun according to a rule frozen in
advance. Model-caused environment breakage, timeout, or budget exhaustion is a
scored failure, not infrastructure invalidation.

## Failure taxonomy

Every unsuccessful attempt receives one primary label:

1. specification misunderstanding;
2. planning or search failure;
3. implementation defect;
4. visible-test overfit / hidden generalization gap;
5. regression introduced;
6. authority or safety gate rejection;
7. mutation unit cannot express the solution;
8. persistence, reload, or composition failure;
9. budget or time exhaustion;
10. model/provider transient failure;
11. evaluator or infrastructure defect.

Labels 1–9 count against task performance. Label 10 follows the frozen retry
rule. Label 11 is retained publicly but excluded from model-success estimates.

## Leakage and evaluator isolation

The author sees development tasks and public task instructions only. Evaluation
IDs, cases, tests, rubrics, expected outputs, and grader logs are sealed. The
grader runs after the agent process exits and writes a separate `ScoreRecord`.
Aggregate failure feedback may be used only in a preregistered repair arm; it
never includes hidden inputs or expected outputs. Rejected attempts are never
discarded.

## Readiness rule

`python -m research.readiness` must return success from a clean checkout before
execution can be enabled. The benchmark runner also checks the gate. Changing a
source hash, task selection, grader revision, adapter, budget, or model relocks
the study and requires a new protocol version.
