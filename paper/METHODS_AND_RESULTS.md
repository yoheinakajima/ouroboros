# Methods and preregistered results

Status: paper-facing draft. Sections labeled **preregistered** report the
frozen study outcome. Sections labeled **exploratory** were designed after
observing the completed probe and must not be presented as confirmatory.

## 1. Study question

We tested whether retained changes produced during a fixed development
curriculum improved later performance after a cold restart. We distinguish:

1. retention: persistent state changed;
2. expression: retained state reached the evaluation-time policy;
3. behavioral mediation: the policy's trajectory or resource use changed;
4. task improvement: externally graded held-out performance increased; and
5. recursive improvement: an earlier change improved the process that creates
   useful later descendants.

The experiment directly measures the first four at different strengths. It
does not causally identify the fifth.

## 2. Architectures

All three approaches used the same `gpt-5.6-sol` outer coding agent, task
environment, brokered tool protocol, task ceilings, and grader boundary. They
differed in the state retained during development:

- **Workspace v1.2** could rewrite and retain an arbitrary workspace tree.
- **Minimal v2** stored every scalar score receipt but promoted only
  externally successful experiences as procedures or deterministic
  capabilities.
- **Hybrid Packs** used a model-authored, tested, hash-pinned ActiveGraph Pack
  to store and retrieve retained lessons.

The native mutation units therefore differ in breadth. Scores are treated as a
causal comparison under the implemented common interface, not as a universal
ordering of the architectures' native ceilings.

## 3. Tasks and split

Each architecture traversed the same ordered 28-task development curriculum:
20 SWE-bench Verified issues, six Terminal-Bench 2 tasks, and two
Ouro-ActiveGraph-50 systems. The completed causal probe used 19 disjoint
held-out tasks:

| Family | Held-out tasks | Score |
|---|---:|---|
| SWE-bench Verified | 10 | Official resolved/unresolved binary outcome |
| Terminal-Bench 2 | 6 | Official Harbor verifier pass/fail |
| Ouro-ActiveGraph-50 | 3 | Fraction of 50 sealed checks |

SWE-bench and Terminal-Bench evaluate work in external task containers.
Ouro-ActiveGraph-50 begins from a deliberately incomplete 20/50 implementation
and includes sealed checks for typed state, relations, policy, adversarial
events, composition, idempotency, and cold-restart replay.

The frozen task selections, task order, replacement rules, model, and
evaluation contracts are bound to repository commit
`559843894578141dfbd39b7bae2246db76e57bde`.

## 4. Information boundary and persistence

After each development task, the lineage builder exposed only the public task,
the acting agent's trajectory-derived summary and submission, and one scalar
score receipt to a common reflection step. Hidden tests, expected outputs,
grader logs, private cases, and oracle artifacts were excluded from the
lineage schema.

Each accepted generation produced a new immutable state directory. Its
manifest bound the architecture, parent run identifiers, development
experience, artifact byte count, and artifact hash. Evaluation occurred after
cold reload. In-place mutation of a scored lineage was prohibited.

## 5. Arms and causal estimand

For every architecture-task pair, the probe included:

- **evolved:** retained development state enabled;
- **cold ablation:** the same lineage existed but learned state was hidden;
- **sham improvement:** an irrelevant opaque artifact approximately matched
  the evolved context in bytes;
- **cold:** no development state.

The preregistered primary estimand was the paired task score difference:

`evolved - cold ablation`.

The secondary causal contrast was `evolved - sham`. Cold measured the shared
model-and-harness floor. Because all cold and cold-ablation adapters entered
through the same no-context outer agent, their architecture labels had no
intended semantic difference.

The strong recursive-uplift rule required benefit over both ablation and sham,
a 95% interval strictly above zero in at least two task families including SWE
or Terminal, valid cold reload, and no material development regression.

## 6. Execution, failures, and adjudication

The probe produced 228 held-out rows: three architectures × four arms × 19
tasks. Failed model attempts remained in the denominator. Bounded agent,
grader, or task timeouts scored zero unless preserved receipts proved an
infrastructure contradiction.

The raw run had 215 immediately valid rows. The final analytical dataset
retained all 228:

- six SWE attempts reached the frozen 3,600-second official task limit and
  scored zero;
- six Terminal agents reached the frozen 1,800-second limit; completed
  verifiers returned zero;
- one ActiveGraph grader reported a syntax error against a receipt-bound
  submission that independently parsed; one sealed grader-only retry of the
  hash-identical submission recovered 24/50.

No model attempt was rerun, no raw result was rewritten, and costs were
unchanged. A SHA-256 adjudication index binds the raw report, raw dataset,
analytical dataset, changed analytical row, and supporting evidence.

## 7. Preregistered analysis

Scores remain separate by task family. SWE and Terminal use pass rates;
ActiveGraph uses mean normalized score. Paired differences are clustered by
task. The reported 95% intervals use 10,000 deterministic task-clustered
bootstrap draws. With one completed development lineage and only 10, six, and
three held-out tasks, these intervals are descriptive uncertainty summaries;
the study is a one-replication probe, not the planned three-replication
preliminary study or five-replication recursive claim.

Cost, calls, tool use, tokens, and wall time are secondary outcomes. We do not
construct a weighted general-intelligence score.

## 8. Preregistered results

All 84 development attempts and all 228 held-out attempts completed. The
held-out model cost was $194.068625.

| Test | Agent | Evolved | Ablation | Evolved − ablation, 95% interval | Sham | Evolved − sham |
|---|---|---:|---:|---:|---:|---:|
| SWE (10) | Workspace | 80.0% | 80.0% | 0.0 pp [0.0, 0.0] | 60.0% | +20.0 pp |
| SWE (10) | Minimal | 70.0% | 60.0% | +10.0 pp [−20.0, +40.0] | 70.0% | 0.0 pp |
| SWE (10) | Hybrid | 80.0% | 70.0% | +10.0 pp [0.0, +30.0] | 80.0% | 0.0 pp |
| Terminal (6) | Workspace | 83.3% | 66.7% | +16.7 pp [0.0, +50.0] | 50.0% | +33.3 pp |
| Terminal (6) | Minimal | 50.0% | 83.3% | −33.3 pp [−66.7, 0.0] | 66.7% | −16.7 pp |
| Terminal (6) | Hybrid | 66.7% | 66.7% | 0.0 pp [0.0, 0.0] | 66.7% | 0.0 pp |
| ActiveGraph (3) | Workspace | 82.7% | 100.0% | −17.3 pp [−52.0, 0.0] | 96.0% | −13.3 pp |
| ActiveGraph (3) | Minimal | 96.7% | 88.0% | +8.7 pp [−10.0, +36.0] | 100.0% | −3.3 pp |
| ActiveGraph (3) | Hybrid | 82.7% | 92.7% | −10.0 pp [−40.0, +10.0] | 82.7% | 0.0 pp |

No architecture met the preregistered criterion. The completed probe therefore
does not demonstrate reliable recursive self-improvement.

## 9. Development and retention

All three architectures created cold-loadable state, but the retained products
differed:

| Architecture | Accepted updates | Accepted after passed task | Accepted after failed task | Final retained product |
|---|---:|---:|---:|---|
| Workspace | 25/28 | 13 | 12 | 429,731-byte arbitrary workspace |
| Minimal | 13/28 | 13 | 0 | 13 procedures, 0 capabilities, 28 receipts |
| Hybrid | 25/28 | 15 | 10 | 25 lessons in a 62,506-byte Pack source |

These facts establish persistent self-modification, not held-out benefit.

## 10. Exploratory mechanism analysis

### 10.1 Expression profile

A single byte ratio is misleading across heterogeneous stores, so we report
storage, eligible payload, semantic reach, adaptivity, and execution:

| Architecture | Storage reach | Eligible-payload reach | Per-task semantic reach | Probe corpus reach | Adaptivity | Runtime activation | Actor-callable capability |
|---|---:|---:|---:|---:|---|---|---:|
| Workspace | 14.9% | 25.9% | 18/85 files = 21.2% | 21.2% | static, 0 pp gap | none | 0 |
| Minimal | 1.35% | 99.6% | 41/41 = 100% | 100% | static, 0 pp gap | none | 0 |
| Hybrid | 4.0% mean | 17.1% mean | 3/25 lessons = 12% | 17/25 = 68% | task-adaptive, 56 pp gap | automatic pre-task query | 0 |

Minimal's 41 units comprise 13 procedures and 28 evidence receipts; the count
does not imply 41 executable capabilities. Hybrid alone changed its exposed
units by task, and did so through the retriever that exhibited the skew below.

This supports an **expression bottleneck in the implemented interface**. A
general auditability–expressivity tradeoff remains a hypothesis until an
experiment varies the interface while holding state fixed.

### 10.2 Equivalent-input outcome spread

For each task, six no-context labels produced byte-identical first requests:
Workspace cold and ablation, Minimal cold and ablation, and Hybrid cold and
ablation. Outcomes differed on seven of 19 tasks. Twelve tasks were stable:
ten fixed passes and two fixed failures.

| Family | Tasks | Variable | ICC(1,1) | Largest equivalent-label mean gap | Approximate 80%-power MDE |
|---|---:|---:|---:|---:|---:|
| SWE | 10 | 3 | 0.717 | 20.0 pp | 30.7 pp |
| Terminal | 6 | 2 | 0.659 | 16.7 pp | 45.1 pp |
| ActiveGraph | 3 | 2 | 0.313 | 21.3 pp | 28.7 pp |

Figure 5 reports the six outcomes at task level and overlays evolved results.
The nearest-rank 95th percentile of the 15 absolute pairwise label-mean gaps
equals the observed maximum in every family. Those 15 values are dependent
functions of six labels and the labels were not randomized replicate draws.
The bar is therefore a descriptive empirical dispersion reference—not an
assumption-free null distribution or formal significance threshold.

The normal-approximation MDE is also exploratory and is used only for
follow-up design sizing.

Stable tasks are not information-free: fixed passes offer one-sided tests for
regression and fixed failures offer one-sided tests for improvement. Minimal's
evolved failure on `scikit-learn__scikit-learn-13124`, against six equivalent
passes, is the only one of 57 evolved architecture-task outcomes outside the
exact task-specific equivalent range.

### 10.3 Hybrid retrieval mechanism

Hybrid's 25-lesson corpus contained 15 success and ten failure lessons. Across
57 top-three slots, failures occupied 37 (64.9%). Two failed Pylint lessons
occupied 22 slots (38.6%).

Failure lessons were longer, but failure status does not explain the skew once
indexed vocabulary is modeled. Indexed vocabulary correlated with retrievals
within successful lessons (Spearman ρ=0.743, n=15) and failed lessons
(ρ=0.763, n=10). In
`retrievals ~ indexed vocabulary + failure flag`, vocabulary had a coefficient
of 0.194 retrievals per term (standardized 0.627); the adjusted failure
coefficient was −0.093 (standardized −0.015), with R²=0.382. A 50,000-draw
within-status permutation test gave two-sided p=0.00454 for vocabulary.

This is evidence that broad vocabularies increased incidental matching under
the implemented set-overlap retriever. It does not show that retrieved
failures caused downstream regressions.

Offline re-ranking reduced concentration:

| Rule | Failure slots | Unique lessons | Top-two share |
|---|---:|---:|---:|
| Raw overlap, used | 64.9% | 17 | 38.6% |
| Jaccard | 57.9% | 17 | 33.3% |
| Binary cosine | 47.4% | 19 | 24.6% |
| BM25 diagnostic | 49.1% | 22 | 17.5% |

No downstream outcomes were generated under these counterfactual rankers.

### 10.4 Capacity saturation

Hybrid Pack source grew from 7,053 to 62,506 bytes. Generation 25 first
exceeded the 64,000-byte limit but succeeded after one repair. Every candidate
in generations 26–28 remained over the cap; the closest was 65,928 bytes.
Authoring requests rose from a mean of 1.0 in the first five generations to
3.2 in the last five, and mean authoring cost rose from $0.249 to $2.114.

This directly establishes saturation of the append-oriented Pack under this
policy. Task order and difficulty confound the cost trend, and the result is
not a general limitation of ActiveGraph.

### 10.5 Architecture-masked update-proposal taxonomy

A frozen codebook was applied to all 84 generation-level reflection lessons.
The coder saw opaque shuffled excerpts but not architecture, task, sequence,
score, acceptance, cost, or later retrieval metadata. The label file was
hashed before unblinding.

The scope of the update-proposal taxonomy required correction. These excerpts
represent the common reflection and proposal layer. They do not represent
every native Workspace edit or Hybrid Pack code change. Within that layer, all 84
proposals were natural-language, append-only, nonexecutable, operational
guidance with no specified activation. Seventy-six targeted procedures and
eight targeted validation assets. Architecture distributions were otherwise
similar.

Outcome status sharply separated epistemic grounding. Of 42 success-derived
proposals, 39 were coded direct-validated and three inferred. Of 42
failure-derived proposals, seven were direct-validated, five
direct-unvalidated, and 30 inferred. The architecture-specific gates then
changed the retained mixture: Minimal accepted 13 successes and no failures;
Workspace accepted 25 proposals including 12 failures; Hybrid accepted 25
including ten failures.

This suggests that the shared reflector determined semantic form while the
architectures differed more through acceptance and later expression. It does
not establish equivalence of their native mutation spaces. Because this is one
model coder with no inter-rater estimate, the numeric taxonomy remains an
exploratory pilot.

## 11. Audited cases

The case-study rules were frozen before selecting the replacement negative
case. Two retrospective anecdotes show why receipts must be allowed to destroy
either story:

- Workspace's evolved SymPy pass fell within an exact equivalent range of
  0–1, and the retained SymPy lesson concerned a different mechanism from the
  held-out patch. The apparent win is not evidence of learned transfer.
- Hybrid's quota-scheduler score of 0.48 exactly equaled the minimum of six
  equivalent no-context runs. The retrieved lessons were mechanistically
  skewed, but the apparent loss cannot be attributed to retrieval.

The predeclared replacement rule selected Minimal/scikit-learn because it was
the only evolved outcome outside its task's exact equivalent range. Trace
inspection showed a retained-context-mediated but invalid trajectory: the
agent changed an algorithm and rewrote an established expected-output test,
whereas the ablation produced the smaller fix and passed the restored official
test. This demonstrates harmful behavioral mediation, but no specific retained
sentence can be identified as the cause.

Hybrid generations 25–28 provide the fourth case: one repaired near-cap update
followed by three generations with four over-cap candidates each.

## 12. Limitations

- Only one development lineage per architecture completed. The six equivalent
  labels expose outcome variability but are not independent evolution
  replications.
- The common outer agent may dominate architecture differences.
- The adapters expressed retained state primarily as context; none exposed a
  retained capability as an interactive actor tool.
- Mutation units differ substantially, making native breadth a Pareto
  dimension rather than a scalar rank.
- Equivalent-label pairwise gaps are dependent and post-hoc.
- The ActiveGraph family contains only three held-out tasks.
- Update-proposal taxonomy coding is exploratory and architecture-masked. It
  codes common reflection proposals rather than all native code mutations.
- The experiment tests self-modification and possible task-level
  self-improvement. It does not isolate improved self-improvement productivity.

## 13. Frozen gate for Experiment B

After drafting the discussion, we will name the strongest specific reviewer
threat to the retrieval mechanism claim. We run a preregistered retrieval
intervention only if:

1. that threat materially blocks a claim needed for the paper;
2. the existing stickiness analysis and offline re-ranking cannot answer it;
3. narrowing the claim would remove a central contribution rather than merely
   make it more cautious; and
4. the intervention can hold retained state, tasks, model, and evaluation
   interface fixed while varying only retrieval.

Cost, curiosity, a desire for a positive result, or momentum are not sufficient
reasons. Otherwise retrieval intervention remains future work. Generation-25
consolidation is a separate Ouroboros development track and is outside this
paper.

## Artifact pointers

- Primary report: [`STUDY_REPORT.md`](STUDY_REPORT.md)
- Hash-bound adjudication: [`data/probe-adjudication.json`](data/probe-adjudication.json)
- Analysis plan: [`PAPER_PLAN.md`](PAPER_PLAN.md)
- Case protocol: [`CASE_STUDY_PROTOCOL.md`](CASE_STUDY_PROTOCOL.md)
- Four cases: [`CASE_STUDIES.md`](CASE_STUDIES.md)
- Taxonomy analysis: [`UPDATE_PROPOSAL_TAXONOMY_RESULTS.md`](UPDATE_PROPOSAL_TAXONOMY_RESULTS.md)
- Related-work grid: [`RELATED_WORK_TABLE.md`](RELATED_WORK_TABLE.md)
- Public benchmark context: [`PUBLIC_BENCHMARK_CONTEXT.md`](PUBLIC_BENCHMARK_CONTEXT.md)
- Experiment B gate: [`EXPERIMENT_B_GATE.md`](EXPERIMENT_B_GATE.md)
- Readiness decision: [`PAPER_READINESS.md`](PAPER_READINESS.md)
- Quantitative outputs: [`data/generated/posthoc-metrics.json`](data/generated/posthoc-metrics.json)
