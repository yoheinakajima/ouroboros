# Minimal appendix

## A. Adjudication sensitivity

The raw run contained 215 immediately valid rows and 13 rows requiring
policy adjudication. The final dataset retained all 228 attempts. Categories
were six official SWE task timeouts, six Terminal agent-budget timeouts with
completed zero verifiers, and one ActiveGraph snapshot contradiction resolved
by a sealed grader-only retry of the hash-identical submission.

Eight of nine preregistered `evolved - cold ablation` contrasts are identical
when raw invalid rows are scored zero and when the frozen adjudication
decisions are applied. The exception is Hybrid ActiveGraph: the contrast moves
from -26.0 points under raw-invalid-as-zero to -10.0 points after the
hash-identical quota-scheduler regrade. It remains negative and the
preregistered conclusion is unchanged. A raw complete-case analysis gives
+7.3 points for this cell because it drops the evolved invalid row.
Complete-case contrasts are reported only as sensitivity analyses because
dropping bounded failures changes the estimand and can favor arms with more
invalid outcomes.

The study's single adjudication judgment moved a score in the evolved arm's
favor, and the preregistered conclusion remained null.

Machine-readable table:
[`data/generated/adjudication-sensitivity.csv`](data/generated/adjudication-sensitivity.csv)

## B. Timeout taxonomy

| Category | Count | Treatment | Interpretation |
|---|---:|---|---|
| Official SWE task timeout | 6 | Scored zero | The patch-bound official evaluation exceeded the frozen 3,600-second task limit. |
| Terminal agent-budget timeout with verifier zero | 6 | Scored zero | The agent exhausted the frozen 1,800-second budget and the completed verifier returned zero. |
| ActiveGraph snapshot regrade | 1 | Hash-identical grader-only retry | The original grader contradicted a receipt-bound parsable submission; no model action was rerun. |

Timeouts remain outcomes under the bounded-agent estimand. The taxonomy
separates agent budget exhaustion, official evaluator limits, and
infrastructure contradiction.

## C. Success-conditional efficiency

For the binary SWE and Terminal families, the companion table reports mean
cost and wall time among successful attempts for every architecture and arm:
[`data/generated/success-conditional-efficiency.csv`](data/generated/success-conditional-efficiency.csv).

These quantities describe the resource profile of observed successes. They do
not estimate causal efficiency because conditioning on success selects
different tasks and trajectories across arms. Unconditional costs remain the
primary resource comparison.

## D. Provenance

The provenance manifest records byte counts and SHA-256 hashes for the frozen
study specification, raw and adjudicated datasets and reports, adjudication
ledger, post-hoc metrics, masked coding packet, both original coder label
files, agreement report, and manuscript:
[`provenance-manifest.json`](provenance-manifest.json).

The adjudication ledger separately hashes each changed row and its supporting
evidence. Both original taxonomy-label files were frozen before adjudication.

## E. Cross-model coding agreement

The table reports exact agreement, Cohen's kappa, and Gwet's AC1 for the two
outcome-blind model-coding passes. Kappa is undefined when both coders use one
category for every item because the marginals have zero variance. AC1 is a
supplemental prevalence-robust coefficient computed with the full
pre-specified category vocabulary. Its value of 1.000 for invariant fields is
mechanical and supplies no evidence beyond 84/84 exact agreement.

| Field | Exact agreement | Cohen's kappa | Gwet's AC1 |
|---|---:|---:|---:|
| Primary update target | 76/84 (90.5%) | 0.000 | 0.904 |
| Secondary update target | 47/84 (56.0%) | -0.081 | 0.543 |
| Representational form | 84/84 (100%) | undefined: zero marginal variance | 1.000 |
| Transfer scope | 63/84 (75.0%) | 0.470 | 0.717 |
| Abstraction level | 59/84 (70.2%) | 0.529 | 0.647 |
| Evidence grounding | 59/84 (70.2%) | 0.428 | 0.669 |
| Failure specificity | 83/84 (98.8%) | 0.661 | 0.988 |
| Validation strategy | 82/84 (97.6%) | 0.592 | 0.976 |
| Consolidation operation | 84/84 (100%) | undefined: zero marginal variance | 1.000 |
| Executable status | 84/84 (100%) | undefined: zero marginal variance | 1.000 |
| Anticipated activation | 84/84 (100%) | undefined: zero marginal variance | 1.000 |
| Counterfactual actionability | 84/84 (100%) | undefined: zero marginal variance | 1.000 |
| Novelty relative to prior state | 84/84 (100%) | undefined: zero marginal variance | 1.000 |
| Confidence | 63/84 (75.0%) | 0.393 | 0.687 |

No coefficient interval is reported because these are two fixed model-coding
passes used as a prompt and model-sensitivity check rather than sampled human
raters. Interpretive fields remain exploratory.
