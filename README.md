# Ouroboros

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Ouroboros is an experiment in the smallest useful recursively self-improving
agent: a model, an ActiveGraph event history, an evaluation boundary, and a
way to retain what worked. The long-term hypothesis is that a minimal organism
with an expressive mutation unit can grow into much more capable systems.

The honest status is **governed capability acquisition**, not yet demonstrated
recursive self-improvement. Current pilots show evaluated changes surviving a
restart. The new research program will test whether one acquired improvement
causally improves acquisition of a different one under paired ablations.

Three architectures are retained for comparison:

| Approach | What it is allowed to change | Character |
|---|---|---|
| Workspace v1.2 | An arbitrary project tree | Broadest and most dangerous; can build real software |
| Minimal v2 | Retrieved procedures and small pure capabilities | Smallest coherent organism and clearest teaching artifact |
| Hybrid Packs | Complete governed ActiveGraph Packs | Rich graph-native behavior with a deterministic release membrane |

The canonical `ouroboros.py` is Minimal v2. Exact workspace v1.2 is preserved
under `recovered/v1.2/`; the Hybrid is under `experiments/` with its real
documentation-grounded author under `research/`. None depends on the separate
`activegraph-packs` repository.

See [the research design](docs/RESEARCH_DESIGN.md), [benchmark feasibility
audit](docs/BENCHMARK_AUDIT.md), [current pilot results](research/RESULTS.md),
and [the readiness gate](research/readiness.py). Paid hard-benchmark execution
is locked until oracle calibration promotes the pinned selections to frozen.

The no-account study has three locally runnable families: 50 held-out
SWE-bench Verified issues, 12 held-out Terminal-Bench 2 tasks, and three
held-out ActiveGraph systems that begin at exactly 20/50. See [the local test
plan](docs/LOCAL_TEST_PLAN.md) for the precise better/worse rules and
[`research/local_study.json`](research/local_study.json) for the frozen matrix.

## Minimal v2

There is one generic model actor, six graph concepts (`goal`, `attempt`,
`evaluation`, `procedure`, `mutation`, and `promotion`), and six host-owned
tools. ActiveGraph supplies the persistent event log, model/tool traces,
budgets, replay, hash-pinned subprocess trials, structural diffs, and
promotion.

## Install

Python 3.11 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Put `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in the environment or a local
`.env` file. Values are used only by the host model provider and are never
forwarded to workspace commands or mutation trials.

## Run a goal

```bash
python ouroboros.py "Inspect this project and fix its failing tests" \
  --check "python -m pytest -q"
```

The model can list, read, write, and exactly replace workspace files; run
argv commands without a shell; and invoke previously promoted deterministic
capabilities. A model claim cannot override a failing `--check` command.

By default the strongest configured OpenAI model is `gpt-5.6-sol`. Override it
explicitly when needed:

```bash
python ouroboros.py "Explain this repository" \
  --provider anthropic --model claude-opus-4-8
```

## Chat

```bash
python ouroboros.py --chat
```

Chat uses the same model actor and graph. Recent turns survive restart. No
chatbot pack or rule-based response layer is involved.

## Teach a structural capability

An examples file contains JSON-object inputs and expected JSON-object outputs:

```json
[
  {"input": {"text": "Hello World"}, "expected": {"value": "hello-world"}},
  {"input": {"text": "Trim Me"}, "expected": {"value": "trim-me"}},
  {"input": {"text": "More   Space"}, "expected": {"value": "more-space"}},
  {"input": {"text": "Symbols & More!"}, "expected": {"value": "symbols-more"}}
]
```

Then run:

```bash
python ouroboros.py "Learn a reusable slugify capability" \
  --teach examples/slugify_cases.json
```

Ouroboros deterministically splits the examples in half. The author model sees
only the training half. Its generated pure function must pass static gates and
all examples in a fresh, key-free, hash-pinned ActiveGraph fork. Only then is
the structural delta promoted into the parent graph. After restart, the exact
promoted bytes are hash-verified and exposed through `invoke_capability`.

Generated mutations use ActiveGraph's native `Pack` value internally as a
mutation ABI, but nothing is discovered or installed from `activegraph-packs`.
Users do not manage bundles or pack dependencies.

## Inspect the organism

```bash
python ouroboros.py --inspect
```

The summary is projected from the event log and reports object counts,
procedures, promoted capabilities, loaded mutation modules, total events, and
estimated model cost. The full trace is stored at:

```text
.ouroboros/organism/trace.sqlite
```

## What improvement means

There are two paths:

1. **Procedural improvement.** A successful, externally evaluated attempt may
   return reusable steps. Ouroboros stores them with their evaluation evidence
   and retrieves them for related future goals.
2. **Structural improvement.** `--teach` authors deterministic code from
   incomplete evidence, holds back test cases, trials the exact source in a
   fork, and promotes only a passing delta.

The model remains the general intelligence. Ouroboros does not try to turn it
into generated keyword rules or a standalone imitation of a model.

## Safety boundary

Workspace paths reject escapes, symlinks, `.git`, and `.ouroboros`. Commands
use argv with `shell=False`, a workspace cwd, a timeout, bounded output, and a
scrubbed environment without provider credentials. Generated mutations have a
small import allow-list and reject filesystem, process, network, environment,
dynamic-execution, and dunder-reflection surfaces before trial.

ActiveGraph's subprocess trial boundary contains crashes, event explosions,
wall-clock overruns, and (on supported platforms) memory overruns. It is not a
security sandbox: use a disposable container or VM for adversarial objectives
or candidate code.

## Tests

```bash
python -m unittest discover -s tests -p 'test_*.py'
python -m research.validate_research
python -m research.smoke --output evidence/calibration_smoke.json
python -m research.readiness --development
```

The deterministic Minimal suite covers model tool use, external evaluation authority,
procedure persistence and retrieval, static mutation gates, hidden-test
rejection, fork promotion, capability reuse, restart recovery, trace integrity,
dotenv handling, and the absence of an `activegraph-packs` dependency.

Raw experiment trees live locally under ignored `artifacts/`. Small public
summaries are under `evidence/`; selected redacted bundles can be attached to
tagged releases without turning model traces into source code.

## Prepare the hard local benchmark inputs

The anonymous local profile is SWE-bench Verified plus Terminal-Bench 2. Fetch
and verify their exact revisions, selected task files, dataset hash, and remote
image digests without making model calls:

```bash
python -m research.bootstrap_benchmarks --fetch --verify-images
python -m research.readiness
```

This prepares oracle calibration; it does not unlock scored execution.
