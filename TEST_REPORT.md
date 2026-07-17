# Ouroboros minimal ActiveGraph prototype — test report

Date: 2026-07-16

Host: macOS, Python 3.11

Runtime: ActiveGraph 1.10.0

Live provider/model: OpenAI / `gpt-5.6-sol`

External pack library: not installed or imported

## Result

The pack-free prototype works across all three target demonstrations:

1. A real coding-agent task repaired a workspace and passed an independent
   four-test check.
2. A model-backed chatbot remembered two facts across a process restart.
3. A live model authored a deterministic capability from three visible
   examples; a key-free subprocess fork tested three hidden examples, promoted
   the passing delta, and a fresh process reused the exact hash-verified code.

The current Minimal-v2 regression suite passes 13/13 tests. Python compilation and
`git diff --check` also pass.

## Architecture under test

The public dependency is only:

```text
activegraph[llm]>=1.10,<2
```

The running organism is:

```text
persistent ActiveGraph event log
  + one generic model actor
  + evaluated procedures
  + promoted deterministic capabilities
  + six host-owned tools
```

Generated structural mutations use ActiveGraph's native `Pack` and manifest
types internally as a trial/promotion ABI. No code is discovered or installed
from `activegraph-packs`.

## Deterministic suite

Command:

```bash
python -m unittest discover -v -s tests -p 'test_ouroboros.py'
```

Observed:

```text
Ran 13 tests
OK
```

Covered boundaries:

- Native model/tool turn loop edits a workspace.
- A failing external check overrides an agent's success claim.
- Procedures are stored only after passing evaluation.
- Procedures survive restart and enter related future context.
- A procedure cold ablation retains its audit history but excludes it from the
  model's scoped graph view.
- A promotion cold ablation retains its graph record but does not import the
  promoted code.
- `.env` and common credential files are hidden from file tools.
- macOS command children cannot read workspace `.env`.
- Command environments contain no provider credentials.
- Offline inspection performs no model call or mutation-code import.
- Unsafe generated imports fail the static mutation gate.
- A memorized candidate passes visible cases but fails hidden cases and is not
  promoted.
- A general candidate passes a real subprocess fork, promotes, survives
  restart, and is invoked by the generic agent.

ActiveGraph reports its documented macOS limitation during mutation tests:
Darwin cannot enforce `RLIMIT_AS`, so the child announces that the memory net
is off. The subprocess boundary, parent wall-clock kill, and event budget
remain active.

## Live test 1: coding agent

Prompt:

```text
Become a coding agent. Inspect this workspace, repair the implementation so
every test passes, and verify the result.
```

The seed `factorial(0)` incorrectly returned `0`. The agent:

- listed and read the workspace;
- ran tests and observed three failures;
- changed the base case to return `1`;
- ran pytest and unittest;
- passed the kernel's independent `python -m unittest -q` check.

Observed external result:

```text
Ran 4 tests
OK
```

The first run recorded 34 events and retained an evidence-linked procedure.
A later hardened restart reverified all four tests under macOS Seatbelt. The
coding trace now contains 62 events, 9 model responses, and 12 tool calls.
Recorded model cost across both coding turns: `$0.140770`.

Evidence:

- `artifacts/minimal-demo-20260716/coding-workspace/`
- `artifacts/minimal-demo-20260716/coding-state/trace.sqlite`

## Live test 2: persistent chatbot

First prompt:

```text
Turn into a chatbot. My name is Ada and my favorite number is 17. Reply
naturally and remember these facts.
```

Response:

```text
Hi Ada! Nice to meet you. I’ll remember that your favorite number is 17.
```

After exiting and starting a fresh Python process:

```text
User: What is my name and favorite number?
Ouroboros: Your name is Ada, and your favorite number is 17.
```

The trace contains 22 events and two model responses. There were no tool calls,
rules, or chatbot packs. Recorded model cost: `$0.021730`.

Evidence: `artifacts/minimal-demo-20260716/chat-state/trace.sqlite`

## Live test 3: structural self-improvement

Prompt:

```text
Learn a reusable slugify capability that converts arbitrary text into
lowercase hyphen-separated slugs.
```

Six examples were hash-sorted and split 3/3. Only the training half entered the
author's graph event and model prompt. GPT-5.6 produced a general Unicode-aware
implementation using `unicodedata`; it did not enumerate the examples.

The generated bundle passed:

- source-size and AST gates;
- import allow-list and dynamic-execution bans;
- manifest content-hash validation;
- external bundle-hash validation including the manifest;
- three training examples;
- three model-hidden held-out examples;
- subprocess wall/event limits;
- zero behavior failures.

ActiveGraph then dry-ran promotion, loaded the exact candidate surface, and
promoted the fork's `mutation_trial_result`. Promotion ID: `promotion#7`.

After process restart, Ouroboros reverified bundle
`sha256:d24502796213a440fab746630cd74d5a3b186f86fa769df1eee7dac66e048478`
and exposed `slugify_text`. The generic agent called it through the recorded
`invoke_capability` tool and returned:

```text
recursive-improvement-works
```

The parent trace contains 34 events, three model responses, one
`tool.requested`, and one `promote.applied`. Recorded model cost for authorship
plus reuse: `$0.055335`.

Evidence:

- `artifacts/minimal-demo-20260716/mutation-state/trace.sqlite`
- `artifacts/minimal-demo-20260716/mutation-state/mutations/agent_slugify_text_09a3959294/`

## Security regression found and fixed during live testing

The first implementation scrubbed provider keys from child environments but
did not hide a `.env` physically located in the workspace. That would allow a
command to read it directly.

The final implementation now:

- removes `.env*`, `.netrc`, `.npmrc`, `.pypirc`, and `credentials.json` from
  file-tool visibility;
- denies direct tool paths to those files;
- uses a provider-key-free child environment;
- denies package-install and common network commands;
- applies macOS Seatbelt with home/state read denial, workspace-only writes,
  explicit credential-file denial, and network denial;
- permits `/dev/null` and workspace-local temp/home directories so pytest and
  normal developer tools continue to work.

Post-fix sandbox smoke:

```text
python -m pytest -q
4 passed in 0.00s
isolation: macos-seatbelt
```

## Remaining limitations

1. Without `--check`, task success is based on the actor's structured
   `completed` status. This is appropriate for chat but weak evidence for
   open-ended work; serious tasks should supply an executable check.
2. Procedure synthesis is model-proposed and lexical retrieval is deliberately
   simple. Evaluation gates whether a procedure is retained, but does not yet
   measure whether it improves later outcomes.
3. Structural mutations currently implement pure JSON-object-to-JSON-object
   capabilities. They cannot create new external credentials, network access,
   or host authorities.
4. Static Python gates and subprocess limits contain common accidents, not a
   determined malicious model. Non-macOS hostile runs still require a
   container or VM.
5. Low-risk pure mutations auto-promote after held-out success. There is no
   owner review UI, signature system, concurrent writer protocol, or automatic
   rollback yet.
6. The implementation is 1,400+ lines because it includes the CLI, two model
   providers, workspace safety, mutation materialization, and tests' public
   contracts. The conceptual kernel is much smaller, but further reduction
   should wait until the demo surface is chosen.

## Assessment

This is a materially cleaner initial demonstration than the previous workspace
evolution manager. “Coding agent” and “chatbot” are behaviors of one persistent
model actor rather than separately generated imitations. Actual structural
improvement remains visible: a model-authored capability is tested against
unseen evidence, promoted through ActiveGraph, survives restart, and becomes a
new callable action.
