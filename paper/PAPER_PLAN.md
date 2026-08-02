# Paper plan

## Working title

**When Self-Modification Becomes Memory: An Audited Comparison of Three
Self-Improving Agent Substrates**

Alternative named-concept title:

**The Expression Bottleneck in Self-Improving Agent Evaluation**

Status: planning document based on one completed preregistered probe and
exploratory post-hoc analysis. It is not a paper draft and does not alter the
preregistered outcome.

## One-sentence paper claim

In a controlled comparison of three persistent self-modification substrates,
the common interface required for causal isolation expressed most retained
change as textual context; all systems accumulated state, but measured uplift
was no larger than important harness and control effects, and the resulting
memory channels exhibited truncation, retrieval skew, and capacity saturation.

## The claim we should not make

The study does not show that Ouroboros, or any of the three architectures,
reliably achieved recursive self-improvement. It also does not establish that
auditable evaluation must reduce expressivity in every design.

The present data establish that the **particular common audit interface used in
this study constrained expression**. The broader auditability–expressivity
tradeoff is a framework and hypothesis unless a follow-up experiment varies the
interface while holding the retained state fixed.

## Abstract v0

Language-model agents can edit prompts, memories, tools, and source code, but a
visible self-modification is not by itself evidence of improved future
capability. We conduct an audited comparison of three persistent agent
substrates: an arbitrary workspace, a success-gated procedure store, and a
governed executable ActiveGraph Pack. Each substrate experiences the same
28-task development curriculum and is evaluated after cold restart using a
shared outer agent, external graders, matched ablations, sham context, and
immutable receipts. Across 84 development attempts and 228 held-out attempts,
all three systems retained real changes, but none met the preregistered
recursive-uplift criterion. A post-hoc mechanism audit explains why the null is
informative. The shared evaluation interface converted retained structure
primarily into text: Workspace exposed 18 of 85 eligible files per task,
Minimal exposed all 41 exported items but no deterministic capabilities, and
Hybrid exposed three of 25 lessons through an automatically invoked retriever;
none gave the acting agent a retained callable capability. Six logically
equivalent no-context arms issued byte-identical first requests but differed on
7 of 19 tasks, producing family-level null spreads of 16.7–21.3 percentage
points. Hybrid further exhibited failure-memory stickiness: failure lessons
formed 40% of memory but 64.9% of retrievals, and its append-oriented Pack
eventually reached a 64 KB policy ceiling that blocked three consecutive
updates. These results motivate an expression profile for self-improving-agent
evaluations, equivalent-arm noise floors, token- and semantics-aware control
ladders, and separate measurement of self-modification, behavioral mediation,
task improvement, and descendant productivity.

## Research questions

1. What artifacts did each substrate create and persist?
2. How much retained state could the evaluation-time system express?
3. Did retained state change later behavior and resource use?
4. Did those behavioral changes improve externally graded held-out outcomes?
5. Did any system improve the process by which it generated later
   self-modifications?
6. How much apparent effect could be produced by equivalent-run stochasticity
   and control construction?
7. What mechanistic retention failures appeared in each substrate?

## Update-proposal taxonomy correction

The blinded packet contains the common generation-level reflection lessons,
not every native Workspace or Pack source mutation. The analysis must be named
an **architecture-masked update-proposal taxonomy**.

The single-coder pilot found that the shared reflection layer dominated form:
all 84 proposals were natural-language, append-only, nonexecutable operational
guidance. Architecture-specific semantic distributions were similar. The
larger difference appeared after gating: Minimal retained only 13
success-derived proposals, while Workspace and Hybrid each retained 25 and
included 12 and ten failure-derived proposals. Success-derived proposals were
mostly direct-validated (39/42); failure-derived proposals were mostly inferred
(30/42).

This strengthens the expression-bottleneck framing while narrowing the
taxonomy claim. Submission-grade taxonomy numbers require a second independent
coder and an agreement report.

## Conceptual decomposition

For architecture \(i\), let:

- \(R_i^t\) be retained state after development generation \(t\).
- \(A_i(R_i^t, x)\) be the evaluation adapter for task \(x\).
- \(O_i^t(x)\) be the observation and action surface emitted by that adapter.
- \(\pi(O_i^t(x), x)\) be the acting policy induced by the shared model and
  outer scaffold.
- \(Y_i^t(x)\) be the external task score.
- \(M_i^t\) be the productivity of the update process that creates useful
  descendants.

These induce five distinct claims:

1. **Self-modification:** \(R_i^{t+1} \ne R_i^t\).
2. **Expression:** \(O_i^{t+1}(x) \ne O_i^t(x)\).
3. **Behavioral mediation:** the induced policy trajectory changes.
4. **Task improvement:** expected external score increases.
5. **Recursive improvement:** descendant productivity \(M_i^t\) increases.

The completed study strongly demonstrates 1, implementation-level evidence
supports 2, resource and trace data support some forms of 3, preregistered data
do not establish 4, and the design does not causally identify 5.

## Contribution 1: an expression profile

### Why not one expression ratio

A single `exposed bytes / state bytes` number is not comparable across
heterogeneous substrates:

- Minimal's 1.84 MB state is mostly SQLite/provenance, while its complete
  semantic export is only 24.9 KB.
- Workspace's bytes are closer to payload but include code, tests,
  instructions, and development records.
- Hybrid's Pack is executed before the actor, so simple byte delivery misses
  runtime activation.

Use a profile with five measurements:

1. **Storage reach:** delivered context bytes / complete artifact bytes.
2. **Eligible-payload reach:** delivered bytes / bytes the adapter could
   legally serialize.
3. **Semantic-unit reach:** retained learned units surfaced for a task /
   retained learned units.
4. **Adaptivity:** the gap between per-task semantic reach and corpus reach
   across the probe, plus whether the same units are exposed for every task.
5. **Execution reach:**
   - whether retained code automatically executes in the evaluation path;
   - whether the acting agent can invoke a retained capability interactively.

### Measured profile

| Architecture | Storage reach | Eligible-payload reach | Semantic reach per task | Corpus reach across 19 tasks | Adaptivity gap | Runtime activation | Actor-callable retained capability |
|---|---:|---:|---:|---:|---:|---|---:|
| Workspace | 14.9% | 25.9% | 18/85 files = 21.2% | 21.2% | 0 pp, static | none | 0 |
| Minimal | 1.35% | 99.6% | 41/41 exported items = 100% | 100% | 0 pp, static | none | 0 |
| Hybrid | 4.0% mean | 17.1% mean | 3/25 lessons = 12% | 17/25 = 68% | 56 pp, task-adaptive | automatic pre-task Pack query | 0 |

Workspace exposed 17 files completely and truncated the eighteenth. All
post-priority files came from the alphabetically early `_development/`
directory. The acting agent could not invoke Workspace's retained tools.

Minimal exposed 13 procedures, zero deterministic capabilities, and 28
receipts. Its low storage reach therefore does not mean low semantic reach.
The three components are reported separately so that evidence receipts cannot
be mistaken for executable procedures or used to inflate a capability count.

Hybrid's Pack executed one retrieval operation before each task, but the acting
agent received its output as text and could not invoke the Pack during the task.
It was the only task-adaptive expression channel, and that adaptive channel was
also the channel exhibiting retrieval skew.

### Claims boundary

Supported:

> The common evaluation interface substantially narrowed and altered the
> expression of all three retained substrates.

Hypothesis only without an interface intervention:

> Increasing causal comparability generally decreases native expressivity.

## Contribution 2: equivalent-arm empirical noise floors

The six no-context labels are:

- Workspace cold;
- Workspace cold-ablation;
- Minimal cold;
- Minimal cold-ablation;
- Hybrid cold;
- Hybrid cold-ablation.

For every held-out task, their first model requests were byte-identical,
including seed. They nevertheless produced different outcomes on 7/19 tasks.
The other 12 were stable under all six equivalent requests: ten were fixed
passes and two were fixed failures.

| Family | Tasks | Variable tasks | ICC(1,1) | Maximum mean difference between equivalent labels | Approx. 80%-power MDE |
|---|---:|---:|---:|---:|---:|
| SWE | 10 | 3 | 0.717 | 20.0 pp | 30.7 pp |
| Terminal | 6 | 2 | 0.659 | 16.7 pp | 45.1 pp |
| ActiveGraph | 3 | 2 | 0.313 | 21.3 pp | 28.7 pp |

The MDE is an exploratory normal approximation using within-task variance
across the six equivalent arms. It is a design-sizing diagnostic, not a
confirmatory power calculation.

The empirical 95th-percentile bar is instead the nearest-rank quantile of all
15 absolute pairwise family-mean deltas among the six equivalent labels. With
only 15 values, the conservative 95th percentile equals the observed maximum:
20.0 pp for SWE, 16.7 pp for Terminal, and 21.3 pp for ActiveGraph.

Interpretation:

- Most observed evolved-control deltas are inside the empirical spread between
  equivalent labels.
- All observed baseline instability is concentrated in seven tasks.
- The 12 stable tasks are not information-free. Stable passes provide clean
  one-sided opportunities to observe regressions; stable failures provide
  clean one-sided opportunities to observe gains. Minimal/scikit-learn is the
  only evolved architecture-by-task result outside an exact task-specific
  equivalent-run range, and it is a regression from six passes to one failure.
- The probe could not reliably detect the modest 5–15 point effect sizes it was
  intended to find.
- Duplicate logically equivalent arms can be retained intentionally as a cheap
  empirical noise estimate.

The ActiveGraph ICC and MDE are especially unstable because there are only
three tasks.

## Contribution 3: failure-memory stickiness

### Observation

Hybrid retained 25 accepted lessons:

- 15 from passing development attempts;
- 10 from failed attempts.

Across 19 held-out tasks, the top-three retriever produced 57 slots:

- 37/57 = 64.9% came from failures;
- two Pylint failure lessons occupied 22/57 = 38.6%;
- 17/25 lessons were ever retrieved;
- only 5/57 slots shared a repository prefix with the held-out task.

Per lesson-task opportunity:

- a failure lesson was selected 19.5% of the time;
- a success lesson was selected 7.0% of the time;
- failures were selected 2.78 times as often.

### Mechanism

The Pack ranks raw set-overlap between task words and an index containing suite,
task id, title, scope, and trigger terms. Failure lessons had:

- 30.4% more serialized characters on average;
- 28.0% more words;
- about 21% larger indexed vocabularies.

Indexed-vocabulary size correlated with retrieval count:

- Pearson \(r \approx 0.62\);
- Spearman \(\rho \approx 0.75\).

The association survives the pass/fail split:

- passing lessons: Spearman \(\rho = 0.743\), \(n=15\);
- failure lessons: Spearman \(\rho = 0.763\), \(n=10\).

In the descriptive OLS model
`retrieval count ~ indexed vocabulary + failure flag`, indexed vocabulary has a
coefficient of 0.194 retrievals per additional term (standardized coefficient
0.627), while the adjusted failure coefficient is -0.093 retrievals
(standardized coefficient -0.015). A 50,000-draw permutation test that shuffles
vocabulary within pass/fail strata gives two-sided \(p=0.00454\) for the
vocabulary coefficient. The model \(R^2\) is 0.382.

This is strong evidence for a vocabulary-coverage mechanism within the
implemented retriever: broader summaries create more opportunities for
incidental word overlap, and failure status adds almost no linear predictive
signal after vocabulary breadth is included. The ranker uses a set, so repeated
terms add no weight. This does not establish that vocabulary breadth is the
only cause, that the selected content is irrelevant, or that the retrievals
changed downstream scores.

### Offline diagnostic

Re-ranking the same 19 prompts without making any new model calls gives:

| Retrieval rule | Failure slots | Unique lessons | Top-two share |
|---|---:|---:|---:|
| Raw overlap, used in study | 64.9% | 17 | 38.6% |
| Jaccard | 57.9% | 17 | 33.3% |
| Binary cosine | 47.4% | 19 | 24.6% |
| BM25 diagnostic | 49.1% | 22 | 17.5% |

This isolates the retrieval rule as a plausible source of skew. It does not
show that alternative ranking improves task performance.

### Claims boundary

Supported:

> Failure-derived memories were over-retrieved, and vocabulary breadth strongly
> tracked retrieval frequency under the implemented lexical rule.

Not supported without a rerun:

> Failure-memory stickiness caused Hybrid's held-out regressions.

## Contribution 4: rising marginal cost and saturation

### Hybrid

- Pack source grew from 7,053 bytes to 62,506 bytes.
- Mutations were accepted through generation 25.
- Generations 26–28 attempted to integrate new lessons and were rejected by the
  64,000-byte policy.
- Each performed four author/repair requests.
- The closest final candidate remained 1,928 bytes over.
- Mean authoring cost rose from $0.249 over the first five generations to
  $2.114 over the last five.
- Mean author requests rose from 1.0 to 3.2.

The policy rejection and retained-state plateau are direct evidence of
capacity saturation. The cost trend is descriptive because task order and task
difficulty are confounded with state size.

### Workspace

- Artifact size reached 429,731 bytes.
- 25/28 mutations were accepted.
- It accepted 12 lessons after failed tasks as well as 13 after successes.
- Mean native authoring cost rose from $1.741 over the first five generations
  to $2.954 over the last five.
- Mean native model calls rose from 16.4 to 20.6.

The cost trend is not causal evidence of deterioration, but it provides no
visible evidence of self-acceleration.

### Minimal

- It retained all 28 receipts and promoted exactly 13 passing procedures.
- It retained no lesson from a failed attempt as a procedure.
- It produced no deterministic capability.
- It made no additional native author-model calls.

Minimal avoided authoring-cost growth but did not exercise the architecture's
strongest claimed mutation unit.

## Contribution 5: a control ladder

The study's controls should be presented as successive rungs rather than one
binary choice:

1. **Cold model/harness floor:** no history and no retained state.
2. **Matched cold ablation:** same lineage exists, retained state hidden.
3. **Byte-matched opaque sham:** current study's sham.
4. **Token-matched neutral sham:** equal model-token load.
5. **Semantic sham:** plausible but unrelated lessons.
6. **Structure-preserving sham:** shuffled real lessons or permuted
   success/failure labels.
7. **Equivalent duplicates:** logically identical labels retained to estimate
   stochastic noise.
8. **Native-interface ablation:** same retained state, native execution enabled
   versus disabled.

Why this matters:

- Workspace SWE evolved-minus-sham was +20 points, but evolved-minus-ablation
  was zero and sham-minus-ablation was -20. The entire apparent sham advantage
  was sham harm.
- Workspace Terminal evolved-minus-sham was +33.3 points; half came from
  evolved-minus-ablation (+16.7) and half from sham-minus-ablation (-16.7).
- Opaque sham text used approximately 1.88–2.43 times as many incremental
  first-call tokens per byte as evolved context, depending on architecture.

The current sham remains informative as an interference control. It is not an
equal-compute semantic control.

## Contribution 6: behavioral mediation without reliable score uplift

Relative to the pooled six-run no-context baseline, evolved context changed
resource use even when it did not improve score.

Examples:

- Workspace SWE: +6.7 pp, +1.62 model calls, +243k input tokens, +$1.219/task.
- Hybrid SWE: +6.7 pp, +1.12 model calls, +39k input tokens, +$0.207/task.
- Minimal Terminal: -22.2 pp, +2.11 model calls, +70k input tokens,
  +$0.361/task.
- Hybrid Terminal: -5.6 pp, -1.22 model calls, -7k input tokens,
  -$0.037/task.

This supports the separation between behavioral change and capability
improvement. It does not prove that the agent used any particular lesson
correctly.

## Primary preregistered result

The paper must report this before post-hoc mechanisms:

- all 84 development attempts completed;
- all 228 held-out attempts are represented in the analytical dataset;
- no architecture met the preregistered strong recursive-uplift criterion;
- every family contains suggestive gains, nulls, or regressions, but no
  architecture is robustly better than both ablation and sham in two families
  including an external benchmark.

The full table in `../REPORT.md` is Table 1.

## Claim–evidence matrix

| Claim | Status | Evidence | Main threat |
|---|---|---|---|
| All three substrates persistently self-modified | Strong | immutable state lineages and cold reloads | none material |
| The common adapter narrowed expression | Strong within this implementation | code audit and expression profile | metric units differ by substrate |
| Auditability generally trades off with expressivity | Hypothesis/framework | design rationale | auditability was not experimentally varied |
| Retained state changed cost and trajectories | Strong descriptively | trace and usage differences | stochastic trajectories |
| Retained state reliably improved held-out score | Unsupported | primary intervals include zero or fail criteria | one replication |
| Hybrid failure memories were sticky | Strong descriptively | corpus/retrieval distribution and ranker code | task relevance may also differ |
| Vocabulary breadth contributed to stickiness | Strong for this implemented retriever | ranker formula, within-status \(\rho\), adjusted regression, conditional permutation | observational corpus; relevance also varies |
| Failure stickiness caused score regressions | Unsupported | no outcome-causal evidence; quota result is inside its exact null range | no retrieval intervention |
| Hybrid reached a retention-capacity ceiling | Strong | three policy rejections and repair receipts | cap is system-specific |
| Update cost rose over time | Strong descriptively | metered author calls and cost | task-order confounding |
| The systems improved their ability to self-improve | Not identified | no descendant counterfactual | single sequential lineage |
| Exact request plus seed made the evaluation deterministic | Refuted | 7/19 task outcomes varied | provider/environment source unresolved |
| Byte-matched sham isolated semantic benefit | Refuted | token density and sham-ablation differences | entropy and token count co-vary |
| Probe results match public leaderboards | Unsupported | tiny selected subsets | incomparable task counts and protocols |

## Proposed figures

### Figure 1: Where self-modification is filtered

A system diagram:

`development experience → native retained state → evaluation adapter →
task-visible observation/action surface → shared outer agent → grader`

Show the three native states entering different adapters but all leaving as
text, with Hybrid's pre-task execution marked separately.

Purpose: define the expression bottleneck and avoid implying that state bytes
equal usable capability.

### Figure 2: Expression profile

Five aligned panels:

1. storage reach;
2. eligible-payload reach;
3. semantic-unit reach per task and across the probe;
4. adaptivity gap;
5. runtime activation and actor invocability.

Purpose: show why a single byte ratio is invalid.

### Figure 3: Failure-memory stickiness

Panel A: corpus composition, 40% failures.  
Panel B: retrieval composition, 64.9% failures.  
Panel C: retrieval count per lesson, highlighting two Pylint failures.  
Panel D: overlap versus length-normalized offline rankers.

Purpose: the most legible mechanistic result.

### Figure 4: Accumulation and saturation

Three small-multiple timelines:

- Workspace artifact bytes and authoring cost;
- Minimal procedures/receipts;
- Hybrid Pack source bytes, accepted/rejected mutations, and repair requests.

Mark the 64 KB Hybrid cap and generations 26–28.

Purpose: distinguish accumulation, selective promotion, and saturation.

### Figure 5: Task-level evolved outcomes inside the empirical clouds

Plot all 19 tasks on the x-axis. For each task, show the six equivalent
no-context scores as a cloud and overlay the three evolved architecture
outcomes with labeled shapes. Facet by family. Add the family-specific
nearest-rank 95th percentile of the 15 absolute pairwise equivalent-label mean
deltas as a descriptive dispersion reference, and report the normal-approximation MDE
separately as a design-sizing diagnostic.

Purpose: make visible that most evolved outcomes sit inside task-specific
equivalent-run ranges, while preserving the stable tasks that can expose
one-sided departures. Highlight Minimal/scikit-learn as the only such departure.

### Figure 6: Control ladder

Show the eight control rungs and mark which were present in the completed
study.

Purpose: convert a limitation into a reusable evaluation checklist.

## Proposed tables

1. Preregistered held-out results.
2. Architecture, retained state, and evaluation-time expression.
3. Equivalent-control noise, ICC, and MDE.
4. Cost/quality Pareto table.
5. Claim–evidence matrix.
6. Related-work comparison:
   - mutation unit;
   - native execution;
   - held-out evaluation;
   - ablation;
   - sham;
   - repeated trials;
   - cost reporting;
   - immutable trajectories/receipts;
   - descendant-productivity measurement.

## Paper outline

1. **Introduction**
   - Self-editing is observable; self-improvement is causal.
   - Explain the five constructs.
   - State the preregistered null and why the mechanism audit matters.
   - List contributions without claiming successful RSI.

2. **Related work**
   - Self-referential scaffold optimization: STOP, Gödel Agent, SICA.
   - Open-ended descendants: DGM and HGM.
   - Verbal memory and reflection: Reflexion and later memory systems.
   - Agent evaluation: AI Agents That Matter, stochastic-evaluation ICC, PACE.
   - Position the work as an audited cross-substrate measurement study.

3. **Architectures and protocol**
   - Workspace, Minimal, Hybrid.
   - Shared development curriculum.
   - External graders, cold reload, receipt boundary.
   - Four original arms.
   - Explicitly describe the common outer agent and adapter.

4. **Preregistered results**
   - Report the null first.
   - Family-level scores and intervals.
   - Development retention and cost.

5. **Expression audit**
   - Formal expression profile.
   - Measured values.
   - Auditability/comparability versus native expression as a design tension,
     not a proven universal law.

6. **Harness and control audit**
   - Equivalent first-request duplicates.
   - ICC, empirical null spread, MDE.
   - Sham token/interference confound.
   - Control ladder.

7. **Retention mechanisms**
   - Failure-memory stickiness.
   - Offline re-ranking diagnostic.
   - Workspace truncation/order bias.
   - Minimal success-only promotion.
   - Hybrid saturation.

8. **Behavior, score, and meta-improvement**
   - Resource mediation.
   - No robust score uplift.
   - Why descendant productivity is unmeasured.

9. **Limitations**
   - one replication;
   - one model;
   - small score-blind task subsets;
   - only three internal ActiveGraph tasks and ceiling effect;
   - no native-interface intervention;
   - no causal retrieval intervention;
   - task order confounds update-cost trends;
   - post-hoc mechanism analyses;
   - public benchmark numbers are not leaderboard scores.

10. **Evaluation recommendations**
    - expression profiles;
    - equivalent duplicates;
    - token- and semantics-matched shams;
    - native-interface ablations;
    - consolidation and deletion;
    - descendant-productivity experiments.

11. **Conclusion**
    - A self-modifying state is an intermediate variable.
    - The evaluation interface and acceptance mechanism are part of the
      self-improving system.

## No-run analysis status

### Completed

1. **Architecture-masked update-proposal taxonomy**
   - Frozen codebook, 84-item masked packet, Sol pilot labels, frozen label
     hash, metadata join, and results memo complete.
   - A second independent coder remains a submission requirement.

2. **Preselected trajectory case studies**
   - Retrospective apparent positive: Workspace/SymPy; semantic audit rejects
     the transfer story.
   - Retrospective apparent negative: Hybrid/quota scheduler; exact
     equivalent-run range rejects outcome attribution.
   - Rule-selected negative candidate: Minimal/scikit-learn, the only evolved
     result below its task-specific equivalent-run range.
   - Saturation: Hybrid generations 25–28.
   - Complete under `CASE_STUDY_PROTOCOL.md`.

3. **Figures 1–5**
   - Generated from machine-readable tables and visually checked.

4. **Paper-facing methods and results**
   - Preregistered outcome is separated from exploratory mechanisms.
   - Related-work Table 6 and public-benchmark context are drafted.
   - Citation and local links resolve.

### Optional appendix work

5. **Behavioral mediation**
   - Classify shell actions into inspection, edit, test, environment repair,
     and validation.
   - Measure whether retrieved concepts appear in commands, patches, or tests.
   - Compare against equivalent-run trajectory variability.

6. **Workspace visibility audit**
   - Classify the 18 visible files and 67 invisible eligible files.
   - Quantify how much context came from the most recent task, generic process
     machinery, code tools, and instructions.

7. Robustness with and without the grader-only recovery.
8. Failure taxonomy for timeouts and bounded zeros.
9. Patch-size and test-execution distributions.
10. Wall-time and cost conditional on success.
11. Hash/provenance reproducibility appendix.

## Additional experiment decision

### A. No additional benchmark runs

Best if the paper is framed as an audited negative-result and measurement
paper.

Advantages:

- current dataset already supports the core descriptive mechanisms;
- avoids converting a clean post-hoc audit into an open-ended fishing
  expedition;
- leaves a preregistered second study as a separate contribution.

Risks:

- auditability–expressivity remains a conceptual tradeoff rather than a causal
  curve;
- failure-memory stickiness remains descriptive, not outcome-causal.

Gate decision: **closed for this paper**. The strongest reviewer threat is that
retrieval composition may not harm downstream outcomes. That blocks a causal
harm claim, which the paper has withdrawn, but not the descriptive mechanism
claim. Existing analysis supports the narrower claim without new runs. See
`EXPERIMENT_B_GATE.md`.

### B. Focused retrieval intervention

Question:

> Does length-normalized or failure-aware retrieval change task performance,
> holding Hybrid's retained memory fixed?

Design:

- freeze a new protocol;
- use the exact final Hybrid state;
- compare original overlap, binary cosine/BM25, and a failure-aware ranker;
- include no-memory and token-matched semantic-sham controls;
- repeat enough times to exceed the measured noise floor;
- use newly frozen tasks or state clearly that the experiment is a mechanistic
  replay on the original held-out set.

Value:

- causally tests the most interesting memory finding.

Cost:

- meaningful replication is much larger than one 19-task pass.

### C. Interface-expression intervention

Question:

> Does enabling a substrate's native execution surface improve behavior or
> score relative to the common text projection?

Design:

- hold retained state fixed;
- text-projection arm;
- native-execution arm;
- native-execution ablation;
- matched task, model, budget, and repeated seeds.

Problem:

- the final Minimal state contains no deterministic capabilities;
- Workspace tools were not authored against a stable callable interface;
- Hybrid's only native behavior is lesson retrieval.

The current final states are therefore poor material for a fair native-power
comparison. A credible version probably requires a new development lineage
whose mutation units expose explicit callable contracts.

Value:

- necessary if the paper wants to empirically claim a general
  auditability–expressivity tradeoff.

### D. Consolidation intervention

Question:

> Can an autonomous consolidation/deletion step prevent Hybrid's capacity
> saturation while retaining retrieval utility?

Design:

- freeze the generation-25 Pack;
- compare append-only continuation with a consolidation-enabled continuation;
- attempt lessons 26–28 plus new tasks;
- measure retained coverage, source bytes, author cost, repair count, retrieval
  composition, and held-out score.

Value:

- directly tests the observed saturation mechanism.

This is likely the best follow-up if the project wants to advance the agent
rather than only strengthen the current paper. It is the Ouroboros development
track and is out of scope for this paper.

### E. Full RSI confirmation

A serious RSI efficacy claim still needs:

- larger held-out families;
- at least three preliminary and five recursive paired replications;
- executable retained improvements;
- token/semantic shams;
- distinct capability A that changes acquisition of B;
- descendant-productivity measurement or branching lineages.

This is a new study, not an extension of the current probe.

## Recommended sequencing from here

1. Obtain the second independent taxonomy coder and report agreement.
2. Turn the methods/results draft into manuscript prose.
3. Complete only appendix analyses that materially answer a named reviewer
   threat.
4. Keep Experiment B closed unless the intended claim changes.
5. Keep consolidation (Experiment D) in the separate Ouroboros development
   track; do not use it to expand this paper.

## Reproducible analysis artifacts

- `../analysis/posthoc_quantitative.py`
- `../analysis/generated/posthoc-metrics.json`
- `../analysis/generated/expression-profile.csv`
- `../analysis/generated/equivalent-control-tasks.csv`
- `../analysis/generated/task-level-noise-and-evolved.csv`
- `../analysis/generated/empirical-null-pairwise-deltas.csv`
- `../analysis/generated/sham-control.csv`
- `../analysis/generated/behavior-mediation.csv`
- `../analysis/generated/hybrid-lesson-corpus.csv`
- `../analysis/generated/hybrid-retrieval-slots.csv`
- `../analysis/generated/development-process.csv`
- `../analysis/generated/state-growth.csv`

## Core related work

- STOP: https://openreview.net/pdf?id=46Zgqo4QIU
- SICA: https://openreview.net/pdf?id=rShJCyLsOr
- Darwin Gödel Machine: https://openreview.net/forum?id=pUpzQZTvGY
- Gödel Agent: https://arxiv.org/abs/2410.04444
- Huxley-Gödel Machine:
  https://openreview.net/pdf/3acf0849444035b86d5c18ebc10e654a5951c9de.pdf
- Reflexion: https://openreview.net/pdf?id=vAElhFcKW6
- AI Agents That Matter: https://arxiv.org/abs/2407.01502
- Stochasticity in Agentic Evaluations:
  https://arxiv.org/abs/2512.06710
- PACE acceptance testing: https://arxiv.org/abs/2606.08106
- Useful Memories Become Faulty:
  https://arxiv.org/abs/2605.12978
- DeltaMem: https://arxiv.org/abs/2606.03083
- SWE-bench Verified: https://www.swebench.com/verified.html
- Terminal-Bench 2:
  https://www.tbench.ai/leaderboard/terminal-bench/2.0
