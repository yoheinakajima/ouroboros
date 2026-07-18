# Experimental protocol

## Research questions

The program asks four different questions that should not be conflated:

1. **Task competence:** did the candidate solve public, hidden, and transfer
   cases?
2. **Capability acquisition:** did the same persistent identity adopt a new
   reusable behavior that survives restart?
3. **Mutation power:** what can the architecture change—one expression, a pure
   capability, an ActiveGraph Pack, or an arbitrary workspace?
4. **Recursive improvement:** did acquired improvement A measurably improve the
   later acquisition of B?

A system may score well on the first three while providing no evidence for the
fourth.

## Two comparison layers

### Portable tasks

Pilot portable tasks use a normalized input/output contract and can be attempted by
all approaches. Examples are recursive data normalization, stateful usage
tracking, incident workflows, authority traps, and the recursive bootstrap.

The implementation representation may differ, but the public, manager-private,
and post-restart transfer semantics must remain the same. Results are reported
with the approach's mutation unit attached; a 100-line pure function and a
multi-file service are not described as equivalent products merely because
they return the same fixture outputs.

### Native-strength tasks

Some tasks intentionally exercise an approach's natural domain:

- workspace evolution: unfamiliar multi-file repository repair;
- hybrid packs: typed objects, relations, patterns, and pack composition;
- minimal agent: open-ended tool use, learned procedures, and small pure
  capabilities.

Native tasks establish breadth but do not enter a cross-approach leaderboard.
The hard common-outcome and recursive-uplift studies are preregistered in
`../docs/RESEARCH_DESIGN.md` and `hard_benchmark.json`. The exact locally
runnable matrix, recursive probe, and better/worse rules are frozen in
`local_study.json`.

## Evidence splits

Every capability-acquisition attempt has four possible evidence stages:

1. **Public:** specification and examples visible to the author.
2. **Manager-private:** unseen cases in a fresh runtime. Exact cases remain
   manager evidence; only a receipt exists before authorship completes.
3. **Post-restart transfer:** new cases executed by the adopted artifact in the
   persistent organism, not inside the trial sandbox.
4. **Recursive transfer:** a later authorship/evaluation task that may use a
   previously adopted improvement.

Adoption requires a strict improvement over the incumbent, every public and
private case, no behavior failures, and no release-policy violation. Research
success additionally requires every transfer case after restart.

## Development-lineage boundary

Hard-suite work happens in two phases. First, the shared outer agent acts in
the official task environment and the external grader writes its result after
the agent exits. Second, the lineage builder may expose only the public task,
the agent's own trajectory-derived summary and submission, and one scalar
score receipt to a recorded reflection model. Exact grader tests, expected
outputs, logs, component diagnostics, manager cases, and oracle artifacts are
not valid lineage inputs.

The common reflection controls the information surface; it does not erase the
architectural difference. Workspace v1.2 may evolve an arbitrary seed tree,
Minimal v2 may import only a passing evaluated procedure, and Hybrid must
author and adopt an executable hash-pinned Pack that retrieves retained
guidance through ActiveGraph. Failed development attempts remain provenance;
Minimal does not promote them as procedures, while broader mutation units may
encode them as cautions. Every step produces a new immutable state directory
whose manifest includes all parent run ids. In-place lineage mutation is not
allowed. Scored lineages may inherit only their own approach's development
runs. Reusing one approach's evidence to exercise another architecture is
rejected by default and requires an explicit cross-approach calibration flag;
such a run is unscored and must be labeled as builder calibration.

## What is measured

No weighted “intelligence score” is reported. Each run produces a vector:

| Dimension | Measure |
|---|---|
| Acquisition | public/private exact pass counts; adoption decision |
| Transfer | post-restart pass count on new entities and sequences |
| State integrity | typed objects, versions, relation topology, event failures |
| Generalization | hidden-minus-public gap and failure taxonomy |
| Regression | candidate versus incumbent on both visible and hidden suites |
| Authority | requested surface, static rejection, side effects, secret exposure |
| Persistence | same run identity, exact bundle hash, successful cold reload |
| Efficiency | calls, input/output tokens, estimated cost, latency, tool calls |
| Breadth | mutation unit and types of behavior expressible |
| Reproducibility | exact prompt/docs/source/suites/runtime artifacts available |
| Recursion | paired B performance with A versus an ablated no-A control |

Results should be discussed as Pareto tradeoffs. For example, broad workspace
mutation may justify more calls than pure capability synthesis.

## Budget and model controls

The primary model is `gpt-5.6-sol`. Hybrid pilot defaults were intentionally raised
to a $30 per-run ceiling, 12 LLM calls, 40,000 output tokens, 15 minutes for
authorship, 90 seconds per isolated suite, 10,000 events, and 2,000 behavior
calls. A typical one-shot hybrid author currently uses one call and less than
$0.20, but the ceiling permits repair loops and harder tasks later.

Hard cross-approach comparisons use the same model, a $50 cost ceiling, a
120-call ceiling, 400,000 output tokens, 1,000 broker tools, and a four-hour wall ceiling. Calls and tool turns are reported rather than forced to
be identical, because the architectures allocate work differently. Model,
provider, documentation commit, engine hash, platform, and dependencies must be
recorded.

## Replication

- Calibration: one no-score run, used only to debug the task and harness.
- Preliminary result: three independent scored attempts per approach/task.
- Recursive claim: at least five paired evolved/cold/sham attempts; increase
  replication if uncertainty remains large.
- Stochastic ML tasks: at least three seeds.

Harness failures are retained but excluded from model success rates. An invalid
run must identify the manager defect and the correction; it must never silently
be relabeled a model failure. Post-hoc task changes create a new task version.

## The recursive-bootstrap test

The decisive experiment is paired:

1. Measure baseline success/cost for acquiring difficult capability B.
2. Acquire A, a capability intended to improve future evolution—for example a
   schema compiler, test synthesizer, documentation retriever, or Pack critic.
3. Adopt A and cold-restart the same organism.
4. Attempt B with A available through an explicit, recorded interface.
5. Repeat the same B attempt with an otherwise matched ablated organism that
   does not contain A.
6. Compare pass rate first, then cost, calls, repair count, and latency.

“The organism contains more code after two adoptions” is cumulative extension,
not recursive self-improvement. The recursive claim requires A to improve the
process that produces or evaluates B, and the ablation is mandatory.

## Threats to validity

- Hidden suites can still be too narrow or accidentally resemble public cases.
- A single model can exploit benchmark conventions without learning a general
  authoring skill.
- LLM variance makes one-shot successes anecdotal.
- Static source membranes reduce common accidents but do not securely contain
  deliberately hostile Python; hostile-code claims require a container or VM.
- Different mutation scopes make a single ordinal ranking scientifically weak.
- The manager, documentation, and task wording are part of the system and must
  be versioned alongside candidate code.
