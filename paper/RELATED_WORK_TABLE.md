# Table 6 — related work and the control ladder

Snapshot date: 2026-07-23.

This table separates a system's ability to produce a stronger descendant from
the controls needed to attribute that improvement to retained self-change.
`Yes` means the cited primary paper reports the feature. `Partial` means the
paper contains a nearby but weaker design. `NR` means not reported; it does not
mean the authors could not implement it.

| System | Retained mutation surface | Held-out transfer after evolution | No-improvement or mechanism ablation | Sham retained-state control | Independent repeated evolution runs | Exact equivalent-input noise control | Immutable mechanistic receipts | Descendant productivity |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| [STOP](https://arxiv.org/abs/2310.02304) | Python improver/scaffold | Yes: independent LPN instances and five new task utilities | Yes: seed and nonrecursive improvers | NR | Yes: 5 GPT-4 and 25 smaller-model runs in key experiments | NR | NR | Partial: recursive rounds, but no matched intervention on later authorship |
| [Gödel Agent](https://arxiv.org/abs/2410.04444) | Self-referential logic/actions modified at runtime | Partial: held-out task splits, not a persistent post-curriculum substrate test | Yes: tool and policy ablations | NR | Partial: repeated task evaluation; evolution-lineage replication is unclear | NR | NR | NR |
| [SICA](https://arxiv.org/abs/2504.15228) | General coding-agent source tree | NR: the benchmark utility is reused throughout the 15-iteration run | Yes: initial agent and iteration history | NR | NR: one reported primary 15-iteration lineage | NR | Partial: archive and observability, not a hash-bound causal ledger | NR |
| [Darwin Gödel Machine](https://arxiv.org/abs/2505.22954) | Coding-agent codebase in a branching archive | Yes: cross-benchmark, cross-model, and cross-language transfer | Yes: without self-improving agents and without open-ended exploration | NR | NR for independent full searches | NR | Partial: versioned archive, not an immutable exposure/trajectory ledger | Partial: descendant trees exist, but parent selection uses current benchmark performance |
| [Huxley–Gödel Machine](https://arxiv.org/abs/2510.21614) | Coding-agent codebase in a search tree | Yes: SWE-Verified to SWE-Lite and model transfer | Yes: matched SICA/DGM search policies | NR | Partial: repeated agent-task evaluations, not repeated complete searches | NR | Partial: archive/tree, not an immutable exposure/trajectory ledger | Yes: clade-metaproductivity explicitly scores descendants |
| This study | Workspace tree; procedures/receipts; ActiveGraph Pack | Yes: 19 disjoint tasks after cold restart | Yes: matched cold ablation | Yes: byte-size-matched opaque sham | No: one development lineage per architecture | Yes: six labels with byte-identical first requests per task | Yes: hashes, manifests, raw rows, requests, traces, graders, and adjudication ledger | No: not causally identified |

## What the grid establishes

The novelty is not “the first agent that changes itself.” STOP, Gödel Agent,
SICA, DGM, and HGM all provide stronger evidence for successful optimization
in at least one setting. The differentiator is **causal and mechanistic
auditing of retained state**:

- a matched state-hidden ablation;
- an explicit sham state;
- exact request-equivalence checks;
- immutable exposure and grader receipts;
- task-level empirical noise ranges;
- case-study rules that can invalidate apparent wins and apparent losses.

No system in the comparison occupies every rung. In particular, this study
does not supply independent evolution-lineage replication or descendant
productivity, while HGM directly targets the latter.

## Adjacent evidence that shapes the interpretation

- [Reflexion](https://arxiv.org/abs/2303.11366) established that linguistic
  feedback in episodic memory can alter subsequent trials and included
  component ablations. It did not study the three persistent mutation
  substrates or the matched retained-state controls used here.
- [AI Agents That Matter](https://arxiv.org/abs/2407.01502) argues that agent
  evaluation should jointly report accuracy and cost, use adequate holdouts,
  and avoid attributing gains without appropriate controls. Those principles
  motivate the separate family scores and complete cost ledger here.
- [Stochasticity in Agentic Evaluations](https://arxiv.org/abs/2512.06710)
  shows why single-run accuracy hides within-query inconsistency and motivates
  our task-level equivalent-run analysis. Our six labels are not six
  randomized replications, so their pairwise deltas remain a descriptive noise
  reference rather than a formal null distribution.
- [PACE](https://arxiv.org/abs/2606.08106) treats self-evolution acceptance as
  paired sequential testing and demonstrates false commits under noisy reused
  development sets. Our acceptance rules differ, but the paper reinforces the
  need to distinguish proposal quality from acceptance reliability.
- [Useful Memories Become Faulty When Continuously Updated by
  LLMs](https://arxiv.org/abs/2605.12978) separates raw episodes from
  consolidated abstractions and shows consolidation-induced degradation.
  This supports preserving receipts and treating consolidation as a gated
  operation, but it does not retroactively establish that consolidation caused
  any outcome in our study.
- [DeltaMem](https://arxiv.org/abs/2606.03083) addresses redundancy and
  retrieval conflict with residual trees and failure-penalized retrieval. It
  provides a concrete alternative to Hybrid's flat lexical top-three channel,
  not evidence that such an alternative would improve our held-out scores.

## Positioning sentence

> Prior work primarily demonstrates that self-editing or memory-bearing agents
> can produce stronger descendants. We study a complementary identification
> problem: whether a retained change was expressed, changed later behavior,
> improved externally graded outcomes beyond matched controls and stochastic
> spread, and improved the production of future descendants.

