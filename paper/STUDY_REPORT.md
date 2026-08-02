# Can three minimal self-improving agents improve themselves?

Status: primary experiment complete. All 84 development tasks and all 228
held-out attempts finished. Results below use the hash-bound adjudicated
dataset generated on 2026-07-23.

## Abstract

We compared three recursive self-improvement architectures using the same
`gpt-5.6-sol` outer agent, frozen tasks, tools, ceilings, and grader boundary.
Each architecture learned from an ordered development curriculum and was then
cold-restarted on held-out tasks. The causal comparison paired its evolved
state against the same lineage with retained improvement hidden, plus a
size-matched sham artifact and a cold baseline.

## The three agents

1. **Workspace v1.2** can rewrite and retain an arbitrary software workspace.
2. **Minimal v2** retains only externally evaluated procedures or deterministic
   capabilities; failed attempts remain receipts but are not promoted.
3. **Hybrid Packs** authors, tests, hash-pins, cold-loads, and executes complete
   ActiveGraph Packs as its retained behavior.

## The three tests

1. **SWE-bench Verified:** repair unfamiliar real repositories; binary score
   from the official container evaluator.
2. **Terminal-Bench 2:** complete difficult end-to-end terminal tasks; binary
   score from the official Harbor verifier.
3. **Ouro-ActiveGraph-50:** improve deliberately incomplete systems from 20/50
   against sealed typed-state, relation, policy, composition, adversarial, and
   restart checks; score from 0 to 50.

## Experimental design

- Primary model: `gpt-5.6-sol` for every model-mediated arm.
- Development per agent: 20 SWE + 6 Terminal + 2 ActiveGraph tasks, in frozen
  order.
- Held-out probe: 10 SWE + 6 Terminal + 3 ActiveGraph tasks.
- Causal arms: evolved, cold ablation, sham improvement, and cold baseline.
- Primary measure: paired held-out score of evolved minus cold ablation,
  reported separately for every test family.
- Secondary measures: evolved minus sham, absolute score, cost, calls, tokens,
  tools, wall time, regressions, and byte-identical restart validity.
- Failed model attempts remain in the denominator. Bounded task and agent
  timeouts are scored zero. A grader may be retried only when preserved
  receipts prove a contradictory infrastructure snapshot and the retry uses
  the exact hash-identical submission.

## Results

The raw run recorded 228 attempts, of which 215 were immediately valid. The
final analytical dataset contains all 228:

- Six SWE attempts exhausted the frozen 3,600-second official task limit and
  score zero.
- Six Terminal attempts exhausted the frozen 1,800-second agent limit; their
  completed verifiers returned zero, so they score zero.
- One ActiveGraph grader reported a syntax error against a receipt-bound
  submission that independently parsed. One sealed grader-only retry against
  the exact same submission recovered 24/50.

No agent/model attempt was rerun, no raw result was rewritten, and costs were
unchanged. The 228 held-out attempts recorded $194.068625 in model cost.

### Held-out causal comparison

Scores are mean normalized scores. SWE and Terminal are pass rates;
ActiveGraph is the mean fraction of 50 points. `Δ abl.` is evolved minus the
same lineage with learned state hidden. `Δ sham` is evolved minus a
size-matched fake improvement artifact. Intervals are task-clustered bootstrap
95% intervals.

| Test | Agent | Evolved | Ablation | Δ abl. (95% interval) | Sham | Δ sham |
|---|---|---:|---:|---:|---:|---:|
| SWE (10) | Workspace v1.2 | 80.0% | 80.0% | 0.0 pp [0.0, 0.0] | 60.0% | +20.0 pp |
| SWE (10) | Minimal v2 | 70.0% | 60.0% | +10.0 pp [-20.0, +40.0] | 70.0% | 0.0 pp |
| SWE (10) | Hybrid Packs | 80.0% | 70.0% | +10.0 pp [0.0, +30.0] | 80.0% | 0.0 pp |
| Terminal (6) | Workspace v1.2 | 83.3% | 66.7% | +16.7 pp [0.0, +50.0] | 50.0% | +33.3 pp |
| Terminal (6) | Minimal v2 | 50.0% | 83.3% | -33.3 pp [-66.7, 0.0] | 66.7% | -16.7 pp |
| Terminal (6) | Hybrid Packs | 66.7% | 66.7% | 0.0 pp [0.0, 0.0] | 66.7% | 0.0 pp |
| ActiveGraph (3) | Workspace v1.2 | 82.7% | 100.0% | -17.3 pp [-52.0, 0.0] | 96.0% | -13.3 pp |
| ActiveGraph (3) | Minimal v2 | 96.7% | 88.0% | +8.7 pp [-10.0, +36.0] | 100.0% | -3.3 pp |
| ActiveGraph (3) | Hybrid Packs | 82.7% | 92.7% | -10.0 pp [-40.0, +10.0] | 82.7% | 0.0 pp |

No architecture met the preregistered strong-evidence threshold. No agent was
better than both ablation and sham with an interval strictly above zero in two
families, including an external family.

The most encouraging pattern was Workspace on Terminal: evolved passed 5/6,
versus 4/6 for ablation and 3/6 for sham. That signal did not generalize to
ActiveGraph, where evolved underperformed both controls. Minimal showed modest
SWE and ActiveGraph uplift over ablation but regressed sharply on Terminal and
did not beat sham. Hybrid showed modest SWE uplift over ablation but tied sham,
tied both controls on Terminal, and regressed against ablation on ActiveGraph.

These are family-specific findings; the protocol intentionally does not
combine them into one intelligence score.

### Development and retained evolution

All three systems completed the ordered 28-task development curriculum and
produced cold-loadable retained state. The run also exposed real limitations:
invalid structured model outputs, failed proposed mutations, retained-state
capacity pressure, and orchestration retries. Those events remain in the
lineages and recovery ledger. Development performance demonstrates that each
mechanism can alter and persist behavior, but it is not causal evidence of
held-out improvement.

### Reliability and failure analysis

The final adjudication contains 12 bounded scored failures and one
hash-identical grader recovery. Raw artifacts remain untouched. The
adjudication index binds the raw report, raw dataset, final dataset, every
changed analytical row, and its supporting evidence by SHA-256. The full
recovery ledger separately records native-evolution failures, bytecode drift,
Docker races, capacity-limit rejections, and orchestration retries.

## Interpretation rule

This one-replication probe shows that all three mechanisms can evolve and
cold-reload behavior, and it provides suggestive task-level gains and
regressions. It does **not** demonstrate reliable recursive self-improvement.
A stronger claim still requires fixed repeated replications, positive held-out
uplift in at least two families including SWE or Terminal, benefit over sham,
valid cold reload, and no material development regression.

## Limitations

- One primary model tests architectures around that model, not model-independent
  intelligence.
- Mutation units differ in breadth, so scores and efficiency form a Pareto
  profile rather than a universal ranking.
- Development experience may help through retrieval, caution, tooling, or
  behavior changes; artifact inspection is required to explain any uplift.
- One replication has high stochastic uncertainty and is explicitly exploratory.

## Reproducibility appendix

- Frozen repository commit: `559843894578141dfbd39b7bae2246db76e57bde`
- Raw rows and report: `results-probe.jsonl`, `report-probe.json`
- Final analytical rows and report: `results-probe-adjudicated.jsonl`,
  `report-probe-adjudicated.json`
- Hash-bound decision ledger: `probe-adjudication.json`
- Execution and recovery ledger: `recovery-notes.md`
- Complete attempts, traces, receipts, graders, lineages, and retained states
  remain under this run directory.
