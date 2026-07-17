# Current results

Date: 2026-07-17
Primary model: OpenAI `gpt-5.6-sol`
ActiveGraph: 1.10.0

These are pilot results and native evidence, not a completed comparative
benchmark. Task contracts differ across the three historical approaches.

## Hard-suite calibration (zero model calls)

The frozen local study now has valid evaluator ceilings before model scoring:

| Suite | Frozen tasks | Oracle result |
|---|---:|---:|
| SWE-bench Verified | 20 development + 50 evaluation | 70/70 resolved by official gold patches |
| Terminal-Bench 2 | 6 development + 12 evaluation | 18/18 pass official Harbor verifiers |
| Ouro-ActiveGraph-50 | 2 development + 3 evaluation systems | every seed 20/50; every oracle 50/50 |

Five defective initial SWE tasks and two defective initial Terminal tasks were
replaced by preregistered score-blind rules. All raw failures and retries remain
in the ignored calibration cache; curated zero-call receipts are in `../evidence/`.
These results validate tasks and infrastructure only. They do not measure any
of the three approaches.

## First paid hard-suite canary

One Workspace v1.2 cold attempt was run on the development issue
`matplotlib__matplotlib-25960` with `gpt-5.6-sol` and seed 101. This is harness
calibration, not a held-out or comparative score.

The first paid attempt produced a plausible patch for $0.460965 but could not
run NumPy/Matplotlib tests because Harbor exposed the base Conda interpreter.
The official evaluator rejected it: the fail-to-pass test failed and six
pass-to-pass subfigure tests regressed. Protocol 0.5 now places the official
image's `testbed` environment first on `PATH` for every architecture.

The matched retry then ran 10 visible subfigure tests successfully, used 13
model calls and 139,286 input / 2,494 output tokens, cost $0.771250, and passed
the official evaluator: 1/1 fail-to-pass and 137/137 pass-to-pass tests. The
patch was 2,456 bytes. The two paid attempts cost $1.232215 combined; an earlier
setup run was canceled before inference and cost $0.

This establishes that the protocol-0.5 SWE path can produce and independently
verify a real frontier-model fix. It also demonstrates why harness parity must
be calibrated before comparing architectures. It does **not** establish
Workspace v1.2 reliability: there is one resolved development task after a
harness-motivated retry. Exact public hashes are in
`../evidence/swe_canary_workspace_v1_2.json`; full traces and patches remain in
the ignored artifact tree.

## Docs-grounded Hybrid Packs

Three capability acquisitions have valid clean runs; two require materialized
graph state and one is the first portable pure-generalization task:

| Task | Public | Private | Transfer after restart | LLM calls | Input / output tokens | Cost | Author time |
|---|---:|---:|---:|---:|---:|---:|---:|
| Nested record normalizer | 4/4 | 4/4 | 3/3 | 1 | 23,428 / 1,237 | $0.154250 | 17.10s |
| Stateful usage tracker | 3/3 | 4/4 | 3/3 | 1 | 23,494 / 1,438 | $0.160610 | 21.32s |
| Dependency release planner | 5/5 | 5/5 | 4/4 | 1 | 24,107 / 2,225 | $0.187285 | 30.82s |
| Combined | 12/12 | 13/13 | 10/10 | 3 | 71,029 / 4,900 | $0.502145 | 69.23s |

Both candidates beat an empty incumbent, passed isolated manager-private
suites with zero behavior failures, were copied and reverified by exact bundle
hash, and loaded into the same persistent identity only after cold restart.

The usage task verifies one typed object per tenant and exact version changes
across cumulative updates. The dependency task verifies typed task objects,
three-edge hidden graphs, logical relation endpoints, and branching readiness.
The post-restart transfer rows also inspect materialized production graph state.

Evidence:

- `artifacts/research-runs/hybrid-nested-normalizer-gpt56-20260716-v2/`
- `artifacts/research-runs/hybrid-stateful-usage-gpt56-20260716-v4/`
- `artifacts/research-runs/hybrid-dependency-planner-gpt56-20260716-v1/`

An earlier retained failure in
`hybrid-stateful-usage-gpt56-20260716-v1` exposed a manager bug:
`EmptySettings` was emitted as a named manifest schema. The model's Pack was
reasonable; the manager rejected it while verifying the generated manifest.
The fix canonicalizes ActiveGraph's sentinel to an empty manifest field. That
run is invalid for model scoring but useful harness evidence.

The first normalizer attempt is also retained. A valid `collections.abc`
import was rejected even though `collections` was allowlisted, and the model
misread an ambiguous `capabilities` output field as an event-interface summary.
The candidate was never imported. The manager now permits only exact allowed
module roots and their submodules, while the schema explicitly reserves
`capabilities` for external authority. The corrected v2 run above passed.

### What this establishes

- A real strongest-model author can use recorded ActiveGraph documentation to
  create more than one kind of nontrivial graph-native behavior.
- Hidden execution and graph assertions can distinguish real durable state and
  relation topology from output imitation.
- Exact source survives governed adoption and becomes usable after restart.

### What this does not establish

- Reliability: each graph-audited task currently has only one valid run.
- Breadth across the nine benchmark categories.
- Security against deliberately malicious generated Python.
- Recursive improvement: neither acquired Pack helped author the next Pack.

## Workspace-evolution lineage

The strongest recorded native success is a GPT-5.6 run that built and promoted
a multi-file persistent todo CLI. It passed 5/5 manager-private executable
tests plus six declared tests, used 15 LLM calls, 206,561 input and 12,703
output tokens, cost $1.413895, and took about 4m23s. The artifact run reports
engine `1.1.0-workspace`; the recovered current workspace kernel identifies as
`1.2.0-workspace`, so this is lineage evidence rather than a fresh v1.2 result.

Vague-objective experiments are especially informative:

- `Turn into a chatbot.` produced a promoted deterministic state machine:
  6/6 public, 5/5 private, 11 calls, $0.663070.
- `Become a coding agent.` produced a pattern rewriter that passed 5/5 public
  but only 2/5 private and was rejected: 20 calls, $1.529720.

The negative coding result is a strength of the evaluator: the artifact looked
plausible and passed everything visible, but hidden generalization failed.

## Minimal v2

The current minimal prototype passes 13 deterministic tests and has three live
GPT-5.6 demonstrations:

- repaired a real calculator workspace and passed four independent tests;
- remembered a name and number across a fresh-process restart;
- authored a Unicode-aware slugification capability from three visible
  examples, passed three held-out examples in a key-free subprocess, promoted
  the exact hash, cold-reloaded it, and invoked it through the generic agent.

Recorded cost was $0.140770 for the coding turns, $0.021730 for chat memory, and
$0.055335 for capability authorship plus reuse: $0.217835 combined. These are
different tasks from the hybrid pilots and cannot support a cost ranking.

### First matched portable task

Minimal v2 and Hybrid Packs both attempted the exact nested-record-normalizer
contract. The four examples hidden from Minimal's author were byte-for-byte
the Hybrid manager-private cases; both then received the same three new
post-restart transfer cases.

| Approach | Public | Private | Transfer | Calls | Input / output | Cost | Author time |
|---|---:|---:|---:|---:|---:|---:|---:|
| Minimal v2 pure capability | 4/4 | 4/4 | 3/3 | 1 | 1,584 / 1,286 | $0.046500 | 26.73s |
| Hybrid docs-grounded Pack | 4/4 | 4/4 | 3/3 | 1 | 23,428 / 1,237 | $0.154250 | 17.10s |

Correctness is tied in this single pilot. Minimal is cheaper because its
specialized pure-function prompt is small; Hybrid sends the complete 90k
ActiveGraph documentation corpus and returns a full event-driven Pack. Hybrid
was faster in this sample. The task structurally favors Minimal's mutation
unit, so none of these differences should be generalized beyond pure local
transformations without repetitions and harder portable tasks.

Evidence: `artifacts/research-runs/minimal-nested-normalizer-gpt56-20260716-v1/`

## Comparative interpretation

| Finding | Evidence level |
|---|---|
| Workspace mutation has the broadest artifact ceiling | Architecture + several native live runs |
| Minimal v2 is the simplest coherent persistent-agent demo | Architecture + three live demonstrations |
| Hybrid can acquire pure, typed-state, and relational behavior in one call | Three valid pilots, two graph-audited |
| Minimal and Hybrid can both acquire the same pure recursive transform | One matched valid pilot each |
| Hybrid is more reliable than the other approaches | **Not established**; no matched repeated tasks |
| Any approach recursively improves its improvement process | **Not established** |

The next publishable milestone is not another attractive one-off demo. It is
five independent runs on the first three portable tasks, followed by the
paired recursive-bootstrap experiment described in [PROTOCOL.md](PROTOCOL.md).
