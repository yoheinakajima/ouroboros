# Ouroboros vague-capability test report

Date: 2026-07-16  
Engine: `1.1.0-workspace`  
Provider/model: OpenAI / `gpt-5.6-sol`

## Question

What happens when the upgraded Ouroboros kernel receives only these objectives?

1. `Become a coding agent.`
2. `Turn into a chatbot.`

Both were run from the default seed as fresh one-generation campaigns with the
same 35-turn, 42-model-call, and $5 estimated-cost caps. No extra specification
was added to either objective.

## Summary

| Result | Coding agent | Chatbot |
|---|---:|---:|
| Status | completed; candidate rejected | completed; candidate promoted |
| Public executable tests | 5/5 | 6/6 |
| Manager-private tests | 2/5 | 5/5 |
| Candidate's declared tests | 0 discovered | 3/3 |
| Model calls | 20 | 11 |
| Tool calls | 28 | 16 |
| Estimated cost | $1.529720 | $0.663070 |
| Duration | 3m58s | 1m54s |

Both traces have SQLite integrity `ok`, zero runtime errors, exactly one terminal
event, zero public/private semantic test clones, and zero exact `.env` secret
value hits.

## `Become a coding agent.`

### What the compiler decided it meant

The objective compiler chose a dependency-free Python JSONL source-transformer:

- Input: `{"task": string, "files": {path: source_text}}`.
- Output: a complete transformed `files` mapping.
- Required artifact: `solution.py` with an importable `handle_request`.
- Behavioral expectations: create or repair small Python modules, preserve
  unrelated files, emit valid Python, and reject malformed requests.

This is a reasonable locally executable interpretation of the vague phrase, but
it excludes model inference, direct filesystem operation, repository discovery,
and open-ended planning.

### What the builder produced

The candidate implemented an AST-assisted deterministic pattern rewriter. It
recognized a short library of task phrases including mean, even/odd,
normalization, greeting, factorial, and palindrome. It preserved unrelated
files and returned a complete in-memory workspace.

It passed all five public tasks but only two of five manager-private tasks. The
private suite exposed failures on unseen rotation, counter-repair, and chunking
requirements. Independent out-of-suite probes confirmed the same boundary:

| Probe | Result |
|---|---|
| Generate supported factorial function | pass |
| Generate novel `double(x)` function | fail |
| Repair novel `add(a,b)` implementation | fail |
| Preserve an unrelated README | pass |

The candidate therefore did not generalize as a coding agent; it overfit a
small family of transformations.

### Why it was rejected

The hard-gate reason was `entrypoint start/protocol gate failed`: the kernel's
generic JSON smoke request is `{"input":"protocol-smoke"}`, while this valid
contract requires `task` and `files`. The candidate correctly returned an error
and exit code 2. This is a protocol-gate false negative.

That false negative did not hide a releasable candidate: private execution was
only 2/5. The declared command `python -m unittest -q` also exited successfully
while discovering zero tests, exposing another hard-gate weakness.

The rejected implementation remains available for audit at
[`generations/g001/candidate/`](artifacts/capability-runs/capability-coding-agent-20260716/generations/g001/candidate/).
The run correctly kept the seed as `final_workspace`.

## `Turn into a chatbot.`

### What the compiler decided it meant

The compiler chose a local, dependency-free NDJSON chatbot with process-lifetime
session state. It specified exact behaviors for greeting, identity, learning a
name, recalling it per session, session isolation, deterministic fallback, and
malformed-input recovery.

### What the builder produced

The candidate is a concise rule-based state machine. It passed 6/6 public tests,
5/5 manager-private tests, and its three subprocess test groups. The kernel
promoted it by `execution-grounded deterministic dominance`.

Independent probes verified:

- Name recall works within one process.
- A second session cannot read the first session's name.
- Malformed JSON emits a structured error and later messages still work.
- Restarting the process loses memory, as specified.
- An open-domain question such as `What is 2+2?` receives
  `You said: What is 2+2?`.

It is therefore a correct chatbot protocol and conversation-state demo, not an
LLM-backed conversational intelligence.

- [Final result](artifacts/capability-runs/capability-chatbot-20260716/result.json)
- [Evaluation](artifacts/capability-runs/capability-chatbot-20260716/generations/g001/evaluation.json)
- [Promoted workspace](artifacts/capability-runs/capability-chatbot-20260716/final_workspace/)

## Judge observation

The chatbot run supplied new evidence about the mirrored judge. For two rubric
criteria, the judge correctly described the six-test artifact as superior in
both position-swapped rationales, but its cross-case numeric identity assignment
still credited the seed. This produced a reported score of 56.6 versus 43.8 and
a spurious worst delta of -98.

The deterministic-dominance rule worked as intended: a 6/6 public and 5/5
private candidate could not be vetoed by those contradictory qualitative
labels. Mirrored views in one shared call reduce simple position bias but are
not independent and do not prevent cross-case identity inference.

## Conclusion

With vague objectives, Ouroboros currently becomes the smallest deterministic
program that its compiler can specify and execute—not the broad colloquial
meaning of “coding agent” or “chatbot.” This is desirable for auditability, but
it reveals the missing primitive needed for genuinely open-ended agents:
budgeted, runtime-brokered model inference.

A candidate cannot safely receive the manager's provider key, and network is
disabled by default. Without an audited inference capability, the builder can
only bake finite heuristics into the resulting workspace. Closed behaviors such
as the chatbot can pass; open-ended semantic work such as arbitrary coding does
not generalize.

## Recommended next changes

1. Add an `llm_inference` capability implemented by a kernel-owned broker with
   explicit model, token, call, cost, and trace controls. Candidates receive a
   tool/protocol, never credentials.
2. Have the objective contract provide a schema-valid protocol-smoke input, or
   make the startup gate check clean EOF/startup separately from input validity.
3. Require declared test commands to discover and execute at least one test
   when the contract requires automated tests.
4. Evaluate mirrored judge views in isolated calls or require artifact-specific
   evidence fingerprints so one case cannot contaminate another.
5. Retain the separate private-suite generalization gate; it was the decisive
   signal that prevented the pattern-rewriter from being mistaken for a coding
   agent.
