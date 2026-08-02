# Public benchmark context

Snapshot date: 2026-07-23.

## The short answer

The study's absolute task scores are credible sanity checks, but they are not
leaderboard-comparable numbers. The meaningful paper result is the
within-task, within-harness comparison among evolved, ablated, sham, cold, and
equivalent conditions.

## SWE-bench Verified

The official benchmark contains 500 human-validated tasks and distinguishes
full agent-system results from a standardized bash-only model comparison
([official benchmark description](https://www.swebench.com/verified.html)).
The current official bash-only table includes, for example, 56.2% for GPT-5
Mini, 70.0% for DeepSeek V3.2 high reasoning, 69.6% for Gemini 3 Pro, and 66.6%
for Claude 4.5 Haiku high reasoning under the listed mini-SWE-agent release
([official leaderboard](https://www.swebench.com/)).

Our evolved arms scored 70%, 80%, and 80% on a frozen **ten-task subset** using
`gpt-5.6-sol`, a different agent scaffold, different budgets, and one attempt
per architecture-task. Those percentages cannot be ranked against 500-task
leaderboard submissions. With ten binary tasks, one task is ten percentage
points, and the six equivalent no-context labels already spanned 60–80% on
this same subset.

The defensible context sentence is:

> Absolute SWE resolution was within the broad range of contemporary coding
> agents, confirming that the harness was nontrivial but capable; the subset
> was too small and the protocol too different for leaderboard comparison.

## Terminal-Bench 2

The official Terminal-Bench 2.0 leaderboard reports, among many systems, 82.2%
for Codex CLI with GPT-5.5, 75.1% for Simple Codex with GPT-5.3-Codex, 69.4%
for Ante with Gemini 3 Pro, and 64.7% for Terminus 2 with GPT-5.3-Codex
([official 2.0 leaderboard](https://www.tbench.ai/leaderboard/terminal-bench/2.0?verified=true)).

Our evolved arms scored 50.0%, 66.7%, and 83.3% on a frozen **six-task subset**.
Again, these are not leaderboard estimates: one task moves the rate by 16.7
points, task selection differs, and the agent/model configuration is not an
official submission.

Version drift strengthens the warning. Terminal-Bench 2.1 was released after
2.0 with fixes to 28 tasks and continuous validation
([official release note](https://www.tbench.ai/news)). A future public
submission should use the current benchmark and remain separate from this
frozen causal study.

## Ouro-ActiveGraph-50

Ouro-ActiveGraph-50 is a local benchmark with sealed checks and no public
leaderboard. It supplies a controlled partial-credit family, not an external
state-of-the-art comparison. Its three held-out tasks are especially
underpowered: one task can dominate the family mean, and its equivalent-arm
ICC and MDE estimates are unstable.

## What may be compared

Safe:

- evolved versus matched ablation on the exact same task and study seed;
- evolved versus sham under the same harness;
- exact task-specific position relative to the six equivalent no-context
  outcomes;
- cost and wall time within this recorded run;
- mechanisms supported by immutable traces and artifacts.

Unsafe:

- calling 80% on ten SWE tasks better than a lower 500-task public score;
- ranking a six-task Terminal result against the official leaderboard;
- combining SWE, Terminal, and ActiveGraph into one intelligence number;
- treating public systems' different models, prompts, tools, rollouts, and
  budgets as architecture controls.

