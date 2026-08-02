# When Self-Modification Becomes Memory

> Frozen readable companion. The canonical arXiv source is
> [`main.tex`](main.tex); changes to this file require regenerating and
> re-reviewing the LaTeX/PDF.

## An Audited Comparison of Three Self-Improving Agent Substrates

### Abstract

Language-model agents can edit their own prompts, memories, tools, and code,
but self-improvement bundles five separable claims: retention, expression,
behavioral mediation, task improvement, and recursive improvement. We audit
three persistent self-modification substrates: an arbitrary workspace, a
success-gated procedure store, and a governed executable Pack. They share one
outer agent, a 28-task development curriculum, cold-restart evaluation on 19
held-out tasks, matched ablation, sham, and cold controls, and immutable
receipts. None of the three recorded development lineages met the
preregistered uplift criterion. The shared interface expressed retained
structure almost entirely as text. Within-substrate per-task item coverage
ranged from 12% to 100%, and the actor-visible action schema exposed no
retained invocation handle. Six no-context arms issued byte-identical initial
requests per task yet differed on 7 of 19 tasks. Descriptive family-level mean
gaps were 2/10 tasks (20.0 points) on SWE, 1/6 task (16.7 points) on Terminal,
and 21.3 points on continuous-score ActiveGraph. An approximately
byte-size-matched sham scored below matched ablation, so evolved-minus-sham
contrasts could not distinguish sham interference from ordinary outcome
spread. Mechanism audits identified vocabulary-driven failure-memory
stickiness, append-only capacity saturation, and common-template
reflection-proposal homogenization. Two independent outcome-blind model-coding
passes agreed that all 84 proposals shared one nonexecutable textual genre;
interpretive labels showed lower agreement and remain exploratory. We
contribute an expression profile, an equivalent duplicates protocol, and a
control ladder. The interface and acceptance mechanism are part of the
self-improving system and must be measured.

## 1. Introduction

Language-model agents now edit their own prompts, memories, tools, and source
code, and the reported results are striking. [STOP](https://arxiv.org/abs/2310.02304)
recursively improves its own improver. [SICA](https://arxiv.org/abs/2504.15228)
raises its score on a SWE-bench Verified subset from 17% to 53%. The
[Darwin Gödel Machine](https://arxiv.org/abs/2505.22954) more than doubles
SWE-bench performance across a branching archive of self-modified descendants,
and the [Huxley-Gödel Machine](https://arxiv.org/abs/2510.21614) scores
lineages by the productivity of their descendants. These systems make
self-modification easy to observe. Self-improvement is a different empirical
claim. A visible edit establishes that the system changed itself. It does not
establish that the change was expressed at evaluation time, altered behavior,
caused better externally graded outcomes, or improved the system's capacity to
produce useful future changes.

We separate the statement that an agent improved itself into five constructs:
(1) **retention**, meaning persistent state changed; (2) **expression**,
meaning retained state reached the evaluation-time policy; (3) **behavioral
mediation**, meaning the policy's trajectory or resource use changed; (4)
**task improvement**, meaning externally graded held-out performance rose
beyond matched controls and stochastic spread; and (5) **recursive
improvement**. Each construct requires different evidence. A score delta
addresses task improvement. The other links require state, exposure,
trajectory, and lineage evidence.

We study those links in a heavily instrumented comparison of three persistent
self-modification substrates chosen for the breadth of their native update
surfaces: an arbitrary rewritable workspace, a success-gated procedure store,
and a governed, hash-pinned executable ActiveGraph Pack. Each traversed the
same ordered 28-task development curriculum and then faced 19 disjoint
held-out tasks across three families after a cold restart. The design used
external graders, four arms, immutable receipts, hash-bound adjudication, and a
preregistered success criterion. It also had one development lineage per
architecture, one model, and small task families. The orchestration and local
ActiveGraph family were self-built; SWE and Terminal used external official
graders, and every claim is scoped to the recorded harness. The preregistered
result is null: none of the three recorded lineages met the criterion. This
paper explains why that null is informative and why several favorable and
unfavorable results inside our data dissolve under audit.

The audit measures mechanisms that recur across agent systems. First, budgeted
context is a common route from memory to later action. Under that route, our
three substrate-interface configurations delivered between 12% and 100% of
their declared retained items per task, exposed no retained invocation handle
in the actor-visible action schema, and expressed native structural change to
the acting policy almost entirely as text. These percentages are
within-substrate coverage measures rather than comparable quantities of useful
information. Second,
single-run task estimates can conceal substantial outcome variability. Our six
no-context labels issued byte-identical first requests per task, seed included,
and still differed on 7 of 19 tasks. Their family-level means spanned 2/10
tasks (20.0 points) on SWE and 1/6 task (16.7 points) on Terminal; the
continuous-score ActiveGraph span was 21.3 points. Third,
placebo context can change the computation it is meant to control. On SWE, the
Workspace sham solved 6/10 tasks and the matched ablation solved 8/10, creating
a 20-point evolved-minus-sham contrast; the six equivalent no-context labels
on the same ten tasks already ranged from 6/10 to 8/10. Fourth, lexical
retrieval and append-only retention created observable selection and capacity
effects. A top-three retriever over-selected broad-vocabulary failure lessons,
and the Pack eventually blocked three consecutive updates at its policy limit.

The shared reflection layer created a proposal-form bottleneck before
architecture-specific acceptance and native mutation. Two
independent outcome-blind model-coding passes over all 84 update proposals
assigned every proposal to the same representational genre:
natural-language, append-only, nonexecutable, operational guidance with no
specified activation. Interpretive fields were less stable across coders and
remain exploratory pending independent human coding. The replicated form
finding concerns the proposal layer. Native Workspace edits and Pack source
changes remained structurally real and heterogeneous.

The receipts cut in both directions. An apparent transfer success involved an
evolved SymPy pass matched by a no-context run that produced essentially the
same fix, while the retained SymPy lesson concerned a different mechanism. An
apparent retrieval failure scored exactly at the minimum of six equivalent
no-context runs. The one evolved result outside its task's exact equivalent
range was a regression in which retained context mediated a larger invalid
intervention and the ablation produced the smaller correct fix. A case audit
that can reject favorable and unfavorable causal stories symmetrically is a
minimum requirement for interpreting individual trajectories.

Prior systems provide strong evidence for the forms of optimization they
measure. Table 6 records which studies report held-out transfer, mechanism
ablations, sham retained state, independent evolution runs, byte-identical
initial-request duplicates, immutable receipts, and descendant productivity. We do not
reinterpret their reported gains through our experiment. Under our controls,
our apparent gains dissolved. It is currently unknown how many published
self-improvement effects would survive them.

This paper contributes six reusable instruments and observations:

1. a five-construct decomposition separating retention, expression,
   behavioral mediation, task improvement, and recursive improvement;
2. an **expression profile** measuring storage reach, eligible-payload reach,
   semantic-unit reach, selection adaptivity, and execution reach;
3. an **equivalent duplicates** protocol that creates task-level empirical
   dispersion references from executions with byte-identical initial requests;
4. a **control ladder** organizing eight control designs by the nuisance they
   address and the claims they license;
5. mechanism checks for **failure-memory stickiness**, capacity saturation,
   and common-template reflection-proposal homogenization; and
6. a fully receipted null with traces, graders, requests, artifacts, and an
   adjudication ledger.

The scope is a within-study diagnostic demonstration. It does not supply a
population estimate, a universal architecture ranking, or a universal
auditability-expressivity law. The expression bottleneck was created by the
implemented common interface, and that fact is central to the result. The
reflection template determined what could be proposed, the acceptance gate
determined what survived, the retriever and adapter determined what was
expressed, and the execution stack determined what a score could mean. The
interface and the acceptance mechanism are part of the self-improving system.

![Figure 1. The expression bottleneck.](figures/figure-1-expression-bottleneck.svg)

**Figure 1: The expression bottleneck.** The study separates retention,
expression, behavioral mediation, task improvement, and recursive improvement.
Retention is necessary but does not identify later score improvement or
recursive self-improvement. The bold bottleneck is the implemented adapter
boundary. It does not imply that all auditable interfaces reduce expressivity.

## 2. Measurement framework

Let \(R_i^t\) denote retained state for architecture \(i\) after development
generation \(t\). Let \(A_i(R_i^t, x)\) be the evaluation adapter for task
\(x\), \(O_i^t(x)\) the observation and action surface emitted by the adapter,
\(\pi(O_i^t(x), x)\) the induced acting policy, \(Y_i^t(x)\) the external task
score, and \(M_i^t\) the productivity of the process that creates useful
descendants. The five constructs correspond to different comparisons:

1. Retention: \(R_i^{t+1} \ne R_i^t\).
2. Expression: \(O_i^{t+1}(x) \ne O_i^t(x)\).
3. Behavioral mediation: the induced policy trajectory changes.
4. Task improvement: expected external score increases beyond matched controls
   and relevant outcome spread.
5. Recursive improvement: the productivity \(M_i^t\) of generating useful
   descendants increases.

This decomposition prevents evidence from moving silently between levels. A
new file establishes retention. A serialized lesson establishes possible
expression. A changed trace establishes behavioral mediation. An external
score contrast supports task improvement. Recursive improvement is the
construct; descendant productivity is its operationalization. It requires
evidence that earlier changes improved later update production.

### 2.1 Expression profile

A single byte ratio cannot compare heterogeneous stores. Minimal's complete
SQLite state is mostly provenance, while its semantic export is small.
Workspace bytes mix source, tests, instructions, and records. Hybrid executes
a Pack query before the actor, so direct byte delivery omits runtime
activation. We therefore report five structured axes:

1. **storage reach**: unique bytes copied into the initial actor-visible
   context divided by bytes in a declared canonical serialization of the
   complete frozen retained-state snapshot;
2. **eligible-payload reach**: those copied bytes divided by the canonical
   retained byte spans admitted by the adapter's frozen eligibility rule;
3. **semantic-unit reach**: declared substrate-native retained items surfaced
   per task, plus their union across the probe, divided by the frozen item
   inventory;
4. **selection adaptivity**: whether selection is explicitly conditioned on
   task input, accompanied by the per-task-to-probe-union coverage expansion;
   and
5. **execution reach**: whether retained code runs automatically and how many
   retained invocation handles appear in the actor-visible action schema.

Semantic units are files for Workspace, typed procedures, capabilities, or
receipts for Minimal, and lessons for Hybrid. The unitization rule and item
types are frozen before evaluation. These ratios measure coverage within one
substrate and must not be used to compare quantities of useful information
across substrates. The coverage-expansion gap measures selection turnover; it
does not by itself show that selection is relevant or beneficial. Interfaces
without byte-copy semantics should report the byte axes as not applicable and
declare a proxy rather than force a ratio.

The expression profile is diagnostic rather than ordinal. Greater reach can
increase useful transfer, interference, cost, or all three.

### 2.2 Control ladder

The control ladder organizes controls by the nuisance they address and the
inference they license. Rungs 3 through 6 are alternative payload controls,
not a monotonic sequence in which every higher number dominates every lower
number.

| Rung | Intervention and held-fixed variables | Licensed inference |
|---|---|---|
| 1. Cold floor | Same model, task, harness, and budget; no development lineage | Model-and-harness floor |
| 2. Matched state-hidden ablation | Same developed lineage and evaluation stack; retained learned state hidden | Effect of enabling the implemented retained-state channel |
| 3. Opaque byte-size sham | Replace retained payload with seeded opaque text; report observed byte ratio and token load | Sensitivity to adding an opaque payload of the recorded size |
| 4. Token-matched neutral sham | Match tokenizer, position, and token count using a preregistered candidate corpus and blinded relevance screen | Payload effect after equalizing first-call token load |
| 5. Semantic sham | Insert plausible units selected from disjoint task families under a blinded relevance screen | Sensitivity to plausible but screened-unrelated guidance |
| 6. Structure-preserving sham | Seed and record the shuffle unit; preserve real-unit count, schema, and token budget while permuting content or metadata | Sensitivity to the retained structure apart from its original mapping |
| 7. Equivalent duplicates | Repeat executions with byte-identical initial model requests, model, seed field, task image, harness, and budgets; later trajectories may diverge | Observed within-task execution dispersion under identical initial requests |
| 8. Native-interface ablation | Hold retained state, task, model, and budgets fixed while enabling or disabling native execution; record resulting latency and observation differences | Effect of the native execution path under the stated downstream changes |

The present study implements rungs 1, 2, 3, and 7. The other rows are
operational specifications for follow-up designs rather than empirical
controls claimed here.

## 3. Study design

All three approaches used the same `gpt-5.6-sol` outer coding agent, brokered
tool protocol, task ceilings, grader boundary, and common reflection step.
They differed in retained state:

- **Workspace v1.2** could rewrite and retain an arbitrary workspace tree.
- **Minimal v2** stored every scalar receipt and promoted only successful
  experiences as procedures or deterministic capabilities.
- **Hybrid Packs** used a model-authored, tested, hash-pinned ActiveGraph Pack
  to store and retrieve lessons.

The native mutation units differ in breadth. The score comparison concerns
their implemented common interface and does not order their native ceilings.

Each architecture traversed the same 28-task development curriculum: 20
SWE-bench Verified issues, six Terminal-Bench 2 tasks, and two local
Ouro-ActiveGraph-50 systems. Evaluation used 19 disjoint held-out tasks: ten
SWE-bench Verified issues, six Terminal-Bench 2 tasks, and three
Ouro-ActiveGraph-50 systems. SWE and Terminal used official binary verifiers.
The ActiveGraph family used normalized scores from 50 sealed checks.

For each architecture and held-out task, the study ran four arms:

- **evolved**, with retained development state enabled;
- **cold ablation**, with the same lineage present and learned state hidden;
- **sham**, with a seeded opaque artifact intended to approximate the evolved
  context size;
  and
- **cold**, with no development state.

The preregistered primary estimand was paired `evolved - cold ablation`.
Strong recursive uplift required benefit over ablation and sham, a nominal
95% task-resampling interval above zero in at least two families including SWE
or Terminal, valid cold reload, and no material development regression. This
was an operational decision rule for the recorded probe rather than a claim of
population-level interval coverage.

The information boundary excluded hidden tests, expected outputs, private
cases, grader logs, and oracle artifacts from lineage state. Each accepted
generation produced an immutable directory whose manifest bound architecture,
parent run, development experience, artifact size, and hash. Evaluation
occurred after cold reload. The frozen repository commit was
`559843894578141dfbd39b7bae2246db76e57bde`.

The study completed 84 development attempts and 228 held-out attempts. Failed
attempts remained in the denominator. Six SWE runs reached the frozen
3,600-second task limit. Six Terminal agents reached the 1,800-second limit,
and completed verifiers returned zero. One ActiveGraph grader contradicted a
receipt-bound parsable submission; one sealed grader-only retry of the
hash-identical artifact recovered 24/50. No model attempt was rerun and no raw
row was rewritten. The adjudication index binds the raw report, datasets,
changed analytical row, and evidence by SHA-256.

Scores remain separate by family. Nominal 95% descriptive task-resampling
intervals use 10,000 deterministic percentile-bootstrap draws. Each draw
resamples the paired per-task arm differences jointly with replacement. With
one lineage and ten, six, and three held-out tasks, no frequentist coverage is
asserted. The three-task ActiveGraph interval is especially discrete and
unstable.

## 4. Preregistered outcome

None of the three recorded lineages met the preregistered uplift criterion.
Table 1 reports the binary families as fractions and percentages. For context,
the six equivalent no-context labels ranged from 6/10 to 8/10 on SWE and from
4/6 to 5/6 on Terminal despite byte-identical initial requests within each
task.

| Family | Architecture | Evolved | Ablation | Evolved minus ablation; nominal 95% descriptive task-resampling interval | Sham | Evolved minus sham |
|---|---|---:|---:|---:|---:|---:|
| SWE, 10 tasks | Workspace | 8/10 (80.0%) | 8/10 (80.0%) | 0/10 (0.0 pp) [0.0, 0.0] | 6/10 (60.0%) | +2/10 (+20.0 pp) |
| SWE, 10 tasks | Minimal | 7/10 (70.0%) | 6/10 (60.0%) | +1/10 (+10.0 pp) [-20.0, +40.0] | 7/10 (70.0%) | 0/10 (0.0 pp) |
| SWE, 10 tasks | Hybrid | 8/10 (80.0%) | 7/10 (70.0%) | +1/10 (+10.0 pp) [0.0, +30.0] | 8/10 (80.0%) | 0/10 (0.0 pp) |
| Terminal, 6 tasks | Workspace | 5/6 (83.3%) | 4/6 (66.7%) | +1/6 (+16.7 pp) [0.0, +50.0] | 3/6 (50.0%) | +2/6 (+33.3 pp) |
| Terminal, 6 tasks | Minimal | 3/6 (50.0%) | 5/6 (83.3%) | -2/6 (-33.3 pp) [-66.7, 0.0] | 4/6 (66.7%) | -1/6 (-16.7 pp) |
| Terminal, 6 tasks | Hybrid | 4/6 (66.7%) | 4/6 (66.7%) | 0/6 (0.0 pp) [0.0, 0.0] | 4/6 (66.7%) | 0/6 (0.0 pp) |
| ActiveGraph, 3 continuous-score tasks | Workspace | 82.7% | 100.0% | -17.3 pp [-52.0, 0.0] | 96.0% | -13.3 pp |
| ActiveGraph, 3 continuous-score tasks | Minimal | 96.7% | 88.0% | +8.7 pp [-10.0, +36.0] | 100.0% | -3.3 pp |
| ActiveGraph, 3 continuous-score tasks | Hybrid | 82.7% | 92.7% | -10.0 pp [-40.0, +10.0] | 82.7% | 0.0 pp |

The table establishes persistent evaluation after development and the absence
of preregistered uplift. It does not explain whether retained state was
available, whether it changed behavior, or whether visible contrasts exceeded
outcome variability. Sections 5 through 7 audit those links.

## 5. Expression bottleneck

All three architectures created cold-loadable state:

| Architecture | Accepted updates | Accepted after passed task | Accepted after failed task | Final retained product |
|---|---:|---:|---:|---|
| Workspace | 25/28 | 13 | 12 | 429,731-byte workspace |
| Minimal | 13/28 | 13 | 0 | 13 procedures, 0 capabilities, 28 receipts |
| Hybrid | 25/28 | 15 | 10 | 25 lessons in a 62,506-byte Pack source |

These receipts establish retention. The expression profile shows what could
reach later behavior:

| Architecture | Storage reach | Eligible-payload reach | Semantic coverage: per task; probe union | Selection adaptivity and coverage expansion | Execution reach: automatic; actor-visible retained handles |
|---|---:|---:|---:|---|---|
| Workspace | 14.9% | 25.9% | 18/85 files (21.2%); 18/85 (21.2%) | static; 0 pp | none; 0 handles, with retained tools hidden |
| Minimal | 1.35% | 99.6% | 41/41 typed items (100%); 41/41 (100%) | static; 0 pp | none; N/A because 0 retained executable units |
| Hybrid | 4.0% mean | 17.1% mean | 3/25 lessons (12%); 17/25 (68%) | task-conditioned top-three query; 56 pp turnover | automatic pre-task Pack query; 0 actor-visible handles |

Minimal supplies the decisive counterexample to storage reach as a sufficient
metric. Its database and provenance artifacts were large, giving 1.35%
storage reach, while the adapter exported all declared semantic units. Those 41 units
comprised 13 procedures and 28 receipts. None was a deterministic capability.

Workspace exposed 17 complete files and part of an eighteenth. All
post-priority files came from the alphabetically early `_development/`
directory, and the actor could not invoke retained tools. Minimal delivered the
same complete export to every task. Hybrid alone selected different learned
units by task: three of 25 per task and 17 of 25 across the probe. Its Pack
executed a retrieval before each task, while the actor received only the
returned text and could not call the Pack interactively.

The common adapter therefore narrowed each native substrate in a different
way. Workspace was truncated and static. Minimal was semantically complete and
static. Hybrid used task-conditioned selection with 56 points of probe-union
coverage expansion. No actor-visible action schema contained a retained
invocation handle. Minimal had no retained executable unit, while Workspace
and Hybrid retained executable material that the actor could not invoke on
demand. This supports an expression bottleneck in the implemented interface. A
general auditability-expressivity tradeoff remains a hypothesis for a future
interface intervention.

![Figure 2. Expression profile.](figures/figure-2-expression-profile.svg)

**Figure 2: Expression is a profile.** Five axes are reported: storage reach,
eligible-payload reach, semantic coverage with per-task and probe-union
submeasures, selection adaptivity, and execution reach with automatic and
actor-visible submeasures. Percentages are within-substrate coverage measures
and do not compare quantities of useful information. Minimal's 41 declared
units are 13 procedures and 28 receipts; none is executable. Hybrid conditions
top-three selection on task text, exposing three of 25 lessons per task and 17
across the probe. Its Pack runs automatically in the adapter and supplies no
on-demand actor-visible invocation handle.

## 6. Equivalent duplicates and control interference

The six no-context labels were Workspace cold, Workspace ablation, Minimal
cold, Minimal ablation, Hybrid cold, and Hybrid ablation. For each task, their
first model requests were byte-identical, including seed. Their outcomes varied
on 7 of 19 tasks. The remaining 12 tasks were stable: ten fixed passes and two
fixed failures.

| Family | Tasks | Variable tasks | Descriptive ICC(1,1) | Maximum of 15 dependent pairwise label-mean gaps | Normal-approximation design-sizing diagnostic, nominal 80% power |
|---|---:|---:|---:|---:|---:|
| SWE | 10 | 3 | 0.72 | 2/10 tasks (20.0 pp) | 30.7 pp |
| Terminal | 6 | 2 | 0.66 | 1/6 task (16.7 pp) | 45.1 pp |
| ActiveGraph | 3 | 2 | 0.31, highly unstable | 21.3 pp | 28.7 pp |

The one-way random-effects ICC treats tasks as targets and the six named
no-context labels as exchangeable single replicate executions on the observed
score scale. It is a descriptive repeatability coefficient, and the
three-target ActiveGraph value is especially unstable. The design-sizing
diagnostic is \((1.96 + 0.842)\widehat{SE}\), using a two-sided nominal
\(\alpha=0.05\), 80% power, and the within-task variance across the six
equivalent labels. It is a continuous normal approximation for a paired mean
contrast. On the binary families it does not represent an attainable observed
score increment.

All discriminative variation in the no-context probe was concentrated in seven
tasks that changed outcome under equivalent requests. Stable tasks still
provide one-sided opportunities: fixed passes can expose regressions and fixed
failures can expose gains. Minimal's evolved failure on
`scikit-learn__scikit-learn-13124`, against six equivalent passes, was the
only one of 57 evolved architecture-task results outside an exact
task-specific equivalent range.

The maximum of the 15 absolute pairwise label-mean gaps is reported for each
family. The 15 values are dependent functions of six labels, and the labels
are not randomized evolution replications. The maximum is a descriptive
dispersion reference rather than a significance threshold.

The sham comparison exposes a second control problem. Workspace SWE evolved
minus sham was +2/10 tasks (+20.0 points) because the evolved and ablation arms
each solved 8/10 tasks while the opaque sham solved 6/10; equivalent
no-context labels on the same tasks also ranged from 6/10 to 8/10. On
Terminal, Workspace evolved minus sham was +2/6 tasks (+33.3 points) because
evolved solved 5/6, ablation solved 4/6, and sham solved 3/6; equivalent labels
on those tasks ranged from 4/6 to 5/6.
The SWE sham family score fell within the equivalent-label range, at 6/10
against 6/10 to 8/10. The Terminal sham fell below all six equivalent family
means, at 3/6 against 4/6 to 5/6. With six dependent draws, a seventh
observation below the observed minimum is consistent with interference and
does not establish it.
The sham consumed approximately 1.88 to 2.43 times as many incremental
first-call tokens per byte as evolved context, depending on architecture.
Its context bytes exactly matched evolved context for Workspace and Minimal.
For Hybrid, the 6,093-byte sham was 56% to 58% of the mean evolved context
across families.
Byte matching therefore controlled artifact size while leaving tokenization,
semantic load, and interference uncontrolled for Workspace and Minimal; Hybrid
also retained a substantial byte-size mismatch.

![Figure 3. Task-level initial-request duplicate spread.](figures/figure-3-task-level-noise.svg)

**Figure 3: Task-level initial-request duplicate spread.** For each of 19
tasks, gray points show six no-context outcomes generated from byte-identical
initial model requests; colored marks show the three evolved outcomes. Later
trajectory inputs may diverge. Seven tasks varied under the duplicate
executions and 12 were stable.
Minimal/scikit-learn is the only evolved architecture-task outcome outside the
observed duplicate-execution range. The bar is the maximum of 15 dependent
absolute pairwise label-mean gaps and is descriptive rather than a formal
significance threshold.

## 7. Mechanism audits

### 7.1 Failure-memory stickiness

Hybrid retained 25 lessons, including 15 from passing development attempts and
ten from failed attempts. Across 19 held-out tasks, the top-three retriever
filled 57 slots. Failure-derived lessons occupied 37/57 slots (64.9%) despite
forming 10/25 of the corpus (40%). Two failed Pylint lessons occupied 22/57
slots (38.6%). Only 17/25 lessons were ever retrieved, and 5/57 slots shared a
repository prefix with the held-out task.

The implemented ranker counted set overlap between task words and an index
containing suite, task identifier, title, scope, and trigger terms.
Failure-derived lessons had broader indexed vocabularies. Indexed vocabulary
correlated with retrieval count within passing lessons
(\(\rho=0.743, n=15\)) and failed lessons (\(\rho=0.763, n=10\)). In the
descriptive regression `retrievals ~ indexed vocabulary + failure flag`,
vocabulary had a coefficient of 0.194 retrievals per additional term and the
adjusted failure coefficient was -0.093 retrievals. A 50,000-draw
descriptive within-status label-permutation diagnostic shuffled vocabulary
values within pass/fail strata, refit the vocabulary coefficient, and counted
absolute coefficients at least as large as observed with a plus-one Monte
Carlo correction. It gave \(p_{\mathrm{MC}}\approx0.0045\). This conditional
reference requires exchangeability of vocabulary labels within status; the 25
lessons form one fixed corpus and compete for 57 retrieval slots, so the value
is neither causal nor population inference.

Offline re-ranking the same prompts changed the selection pattern without new
model calls. Failure slots fell from 37/57 under raw overlap to 33/57 under
Jaccard, 27/57 under binary cosine, and 28/57 under BM25. BM25 surfaced 22/25
lessons and reduced the top-two share from 22/57 to 10/57. These diagnostics
identify vocabulary coverage as a mechanism in the implemented ranker. They do
not show that alternative retrieval improves downstream task scores.

![Figure 4. Failure-memory stickiness.](figures/figure-4-failure-memory-stickiness.svg)

**Figure 4: Failure-memory stickiness and lexical coverage.** Hybrid's
retained corpus was 40% failure-derived, while failures occupied 37/57
retrieval slots (64.9%). Retrieval count increased with indexed vocabulary
within both success and failure groups. The adjusted regression assigns nearly
all linear signal to vocabulary breadth rather than failure status. This
identifies a mechanism in the implemented ranker and does not establish an
effect on held-out score.

### 7.2 Capacity saturation

Hybrid Pack source grew from 7,053 to 62,506 bytes. Generation 25 first
exceeded the 64,000-byte policy and succeeded after one repair. Every candidate
in generations 26 through 28 remained over the cap after four author or repair
requests; the closest final candidate was 65,928 bytes. Mean authoring requests
rose from 1.0 over the first five generations to 3.2 over the last five, and
mean authoring cost rose from $0.249 to $2.114.

The policy rejection and retained-state plateau directly establish saturation
under this append-oriented design. Task identity and difficulty are confounded
with generation order, so the cost trend is descriptive. The result does not
establish a general limitation of ActiveGraph or executable memory.

![Figure 5. Accumulation and saturation.](figures/figure-5-accumulation-saturation.svg)

**Figure 5: Accumulation, rising effort, and saturation.** Panel A shows
Workspace artifact growth and authoring cost; panel B shows Minimal's
universal receipts and success-gated procedures; panel C shows Hybrid Pack
growth and rejected updates at the 64,000-byte source policy. Hybrid
generation 25 succeeded after repair and generations 26 through 28 produced
no within-cap candidate. The cost trend is descriptive because generation
order is confounded with task identity and difficulty.

### 7.3 Update-proposal taxonomy

A frozen codebook was applied to all 84 generation-level reflection proposals.
Each coder saw opaque shuffled excerpts without architecture, task, sequence,
score, acceptance, cost, or later retrieval metadata. Sol and Terra completed
independent high-reasoning coding passes. Original labels were hashed before
comparison and no disagreement was adjudicated.

Both coders labeled 84/84 proposals as natural-language, append-only,
nonexecutable, operational guidance with no specified activation. They agreed
on failure specificity for 83/84 proposals and validation strategy for 82/84.
These replicated labels support a stable description of proposal form.

Interpretive fields were less stable: agreement was 59/84 for abstraction,
59/84 for evidence grounding, 63/84 for transfer scope, and 47/84 for
secondary target. Both coders assigned the same grounding totals to
success-derived proposals, 39/42 direct-validated and 3/42 inferred. For
failure-derived proposals, Sol assigned 7/42 direct-validated, 5/42
direct-unvalidated, and 30/42 inferred; Terra assigned 21/42, 6/42, and 15/42.
The direction of the success-failure contrast replicated and its magnitude
did not.

The shared reflector therefore produced a homogeneous representational genre.
Architecture-specific gates selected different retained mixtures: Minimal
accepted 13 success-derived proposals and no failure-derived proposals;
Workspace accepted 25 proposals including 12 after failures; Hybrid accepted
25 including ten after failures. Human inter-rater reliability remains
pending, and interpretive distributions remain exploratory. The analysis
describes common update proposals rather than every native Workspace edit or
Pack source change.

## 8. Audited cases

Case selection followed a frozen rule that required a complete chain:

> retained update -> expression -> plausible mechanism -> later behavior

The rule also required comparison with the exact task-specific range among
equivalent duplicates.

**Apparent success.** Workspace passed a held-out SymPy task. Its retained
SymPy lesson concerned a different mechanism, and a no-context run generated
essentially the same fix. Equivalent outcomes on the task ranged from failure
to pass. The receipts establish a pass and reject the learned-transfer story.

**Apparent failure.** Hybrid scored 0.48 on quota scheduler after retrieving
mechanistically skewed lessons. Six equivalent no-context runs on the same
task ranged from 0.48 to 1.00. The evolved score equaled the observed minimum.
The receipts establish retrieval skew and reject attribution of this outcome
to that skew.

**Outside-range regression.** Minimal failed a scikit-learn task that all six
equivalent no-context runs passed. The retained-context trajectory changed an
algorithm and rewrote an established expected-output test. The ablation made a
smaller fix and passed the restored official test. This establishes harmful
behavioral mediation. The trace does not identify one retained sentence as the
cause.

**Capacity ceiling.** Hybrid generation 25 succeeded after a repair near the
policy cap. Generations 26 through 28 produced four over-cap candidates each.
This case establishes a direct mechanism from append-only accumulation to
failed retention.

Together, the cases show why receipts must be permitted to invalidate stories
in both directions. They also show why score, mechanism, and attribution
should be reported separately.

## 9. Related work

Self-improving agent systems measure different portions of the five-construct
chain. STOP reports repeated recursive improver optimization and held-out task
utilities. [Gödel Agent](https://arxiv.org/abs/2410.04444) evaluates runtime
self-referential modification with tool and policy ablations. SICA optimizes a
coding-agent source tree through a reported primary lineage. Darwin Gödel
Machine uses a branching archive and reports transfer across benchmarks,
models, and languages. Huxley-Gödel Machine explicitly measures descendant
productivity through
clade-metaproductivity.

Our study complements these capability results by instrumenting retained-state
attribution. Table 6 separates unevolved baselines, mechanism interventions,
independent complete evolution runs, versioned provenance, immutable exposure
receipts, and recursive-improvement operationalization. No design reports
every listed feature. This study lacks independent evolution-lineage
replication and does not identify descendant productivity. It adds sham state,
initial-request duplicates, and immutable exposure receipts to a persistent
post-curriculum comparison.

[Reflexion](https://arxiv.org/abs/2303.11366) shows that episodic linguistic
feedback can alter later trials; [AI Agents That
Matter](https://arxiv.org/abs/2407.01502) motivates cost, holdout, and
attribution controls. [Stochasticity in Agentic
Evaluations](https://arxiv.org/abs/2512.06710) motivates consistency analysis;
[PACE](https://arxiv.org/abs/2606.08106) studies noisy acceptance. [Useful
Memories Become Faulty When Continuously Updated by
LLMs](https://arxiv.org/abs/2605.12978) contrasts episodes with consolidation;
[DeltaMem](https://arxiv.org/abs/2606.03083) studies residual-tree memory.
Together they motivate measurement of retained-state mechanisms.

**Table 6: Related-work evidence features.** “Yes” means that the cited primary
paper reports the feature. “Partial” identifies a nearby but weaker design.
“NR” means not reported and does not imply that the authors could not
implement it. Cells were re-audited against the linked primary paper versions
on 2026-07-23. The strict receipt column requires immutable binding among
retained state, evaluation exposure, trajectory, and outcome.

| System | Retained mutation surface | Held-out transfer after evolution | Unevolved or initial baseline | Mechanism intervention | Sham retained-state control | Independent complete evolution runs | Byte-identical initial-request duplicates | Versioned lineage or provenance | Immutable exposure and trajectory receipts | Descendant productivity |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| [STOP](https://arxiv.org/abs/2310.02304) | Python improver or scaffold | Yes: independent LPN instances and five new task utilities | Yes: seed improver | Yes: nonrecursive and alternative improver baselines | NR | Yes: five GPT-4 and 25 smaller-model runs in key experiments | NR | NR | NR | NR |
| [Gödel Agent](https://arxiv.org/abs/2410.04444) | Self-referential runtime logic and actions | Partial: held-out task splits rather than a persistent post-curriculum substrate test | Yes: initial policy and hand-designed baselines | Yes: initial-tool ablations | NR | Yes: six independent self-improvement cycles per task | NR | NR | NR | NR |
| [SICA](https://arxiv.org/abs/2504.15228) | General coding-agent source tree | NR: benchmark utility reused throughout the primary 15-iteration run | Yes: initial agent | NR | NR | NR: one reported primary lineage | NR | Yes: archive of prior agents and benchmark results | NR | NR |
| [Darwin Gödel Machine](https://arxiv.org/abs/2505.22954) | Coding-agent codebase in a branching archive | Yes: cross-benchmark, cross-model, and cross-language transfer | Yes: initial agent and handcrafted baselines | Yes: without self-improving agents and without open-ended exploration | NR | Yes: three complete DGM runs in the reported stability analysis | NR | Yes: traceable archive tree and modification lineage | NR | NR |
| [Huxley-Gödel Machine](https://arxiv.org/abs/2510.21614) | Coding-agent codebase in a search tree | Yes: SWE-Verified to SWE-Lite and model transfer | Yes: shared initial agent | Yes: matched SICA and DGM selection policies | NR | NR for repeated complete searches | NR | Yes: retained search tree of modified agents | NR | Yes: clade-metaproductivity explicitly aggregates descendant performance |
| This study | Workspace tree; procedures and receipts; ActiveGraph Pack | Yes: 19 disjoint tasks after cold restart | Yes: cold floor and initial model-harness baseline | Yes: matched state-hidden ablation | Yes: opaque sham with reported byte and token mismatch | No: one development lineage per substrate | Yes: six labels with byte-identical initial requests per task | Yes: immutable state generations and hashes | Yes: state, exposure, request, trajectory, grader, and adjudication bindings | No: not causally identified |

## 10. Discussion

The preregistered null does not establish that persistent
self-modification cannot improve agents. It establishes that three retained
substrates, under one common interface and one lineage each, did not meet the
specified uplift criterion. The mechanism audit explains why a score-only
summary would discard the most informative evidence.

First, native update breadth and evaluation-time expression are separate
design dimensions. Workspace retained arbitrary files, Minimal retained
procedures and receipts, and Hybrid retained executable Pack source. The actor
received truncated static text, complete static text, or task-conditioned
text. It received no callable retained capability. Evaluation therefore
compared native substrates after a consequential common transformation.

Second, proposal, acceptance, retrieval, and expression form a pipeline. The
common reflector produced one representational genre across all 84 proposals.
Acceptance gates created different epistemic mixtures. Workspace and Hybrid
retained failure-derived proposals that Minimal excluded. Hybrid's lexical
retriever then concentrated exposure on broad-vocabulary failure lessons.
Each mechanism belongs inside the system boundary because each changes what a
later actor can use.

Third, controls can confound contrasts. The opaque sham matched evolved bytes
for Workspace and Minimal but not Hybrid, and it differed in tokenization and
semantic load. Equivalent duplicates varied despite identical first requests.
A positive evolved-minus-sham contrast can therefore combine useful
expression, possible sham interference, and ordinary outcome spread. The
control ladder makes these alternatives explicit and suggests the next
diagnostic comparison.

Fourth, append-only retention carries a measurable maintenance burden. Hybrid
reached a hard cap; Workspace and Minimal accumulated without consolidation.
This observation motivates consolidation, pruning, and replacement as
first-class update operations. It does not establish which operation would
improve held-out performance.

The instruments generalize to persistent agents whose retained-state
inventory, eligibility rule, adapter emissions, and actor-visible actions can
be frozen and inspected. Systems without byte-copy semantics should declare a
computable proxy or mark the byte axes not applicable. Equivalent duplicates
can be retained whenever multiple labels issue byte-identical initial
requests under a common execution contract. The control ladder can be
selected according to the intended causal claim. The update-proposal taxonomy
can be applied to shared reflectors while native state changes are analyzed
separately. Receipts can bind retained artifacts, exposures, trajectories,
graders, and adjudication.

## 11. Limitations

The study completed one development lineage per architecture. The six
equivalent labels expose outcome variability and do not replace independent
evolution replications. All approaches shared one model and outer agent, which
may dominate architecture differences. The held-out families contained ten,
six, and three tasks. ActiveGraph uncertainty estimates are especially
unstable.

The common interface constrained native expression and exposed no retained
interactive capability. This limits architecture ranking and creates the
expression bottleneck examined in the paper. A general
auditability-expressivity relationship requires an intervention that varies
the interface while holding retained state fixed.

The sham targeted byte matching rather than token or semantic matching, and
Hybrid retained a substantial byte-size mismatch. It remains useful as an
interference control and cannot identify equal-compute semantic effects.
Duplicate-label pairwise gaps are dependent and post-hoc. The task-level
ranges are descriptive.

The update-proposal taxonomy used two language-model coders. Exact agreement
on representational form does not substitute for independent human coding.
Interpretive labels showed lower exact agreement and remain exploratory.
Architecture masking may be incomplete because proposal form can reveal
substrate.

The retrieval analysis identifies lexical selection mechanics and does not
establish causal harm to score. Offline re-ranking produced no new behavioral
outcomes. Experiment B remains closed because the paper does not require a
causal retrieval-harm claim. Consolidation at generation 25 is a separate
Ouroboros development experiment.

## 12. Conclusion

All three systems retained persistent changes. Their evaluation interface
expressed those changes mainly as text, their controls exhibited substantial
outcome spread and left interference uncontrolled, and none met the
preregistered uplift criterion. The resulting null separates five claims that
are often compressed into one: retention, expression, behavioral mediation,
task improvement, and recursive improvement.

The central lesson is operational. Treat reflection templates, acceptance
gates, retrievers, adapters, execution paths, and controls as components of the
self-improving system. Measure each link with receipts and matched
interventions. The interface and acceptance mechanism determine what
self-modification can become.

## Artifact and appendix pointers

- Full methods and preregistered results:
  [`METHODS_AND_RESULTS.md`](METHODS_AND_RESULTS.md)
- Expression and equivalent-duplicate analyses:
  [`PAPER_PLAN.md`](PAPER_PLAN.md)
- Update-proposal reliability:
  [`UPDATE_PROPOSAL_TAXONOMY_RELIABILITY.md`](UPDATE_PROPOSAL_TAXONOMY_RELIABILITY.md)
- Case-study protocol and traces:
  [`CASE_STUDY_PROTOCOL.md`](CASE_STUDY_PROTOCOL.md) and
  [`CASE_STUDIES.md`](CASE_STUDIES.md)
- Related-work comparison grid:
  [`RELATED_WORK_TABLE.md`](RELATED_WORK_TABLE.md)
- Public benchmark context:
  [`PUBLIC_BENCHMARK_CONTEXT.md`](PUBLIC_BENCHMARK_CONTEXT.md)
- Hash-bound adjudication:
  [`data/probe-adjudication.json`](data/probe-adjudication.json)
- Complete immutable run archive:
  Zenodo DOI pending; release plan and disclosure gate in
  [`ARTIFACT_ARCHIVE.md`](ARTIFACT_ARCHIVE.md)
