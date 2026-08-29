# Minimal appendix

## A. Adjudication sensitivity

The raw run contained 215 immediately valid rows and 13 rows requiring
policy adjudication. The final dataset retained all 228 attempts. Categories
were six official SWE task timeouts, six Terminal agent-budget timeouts with
completed zero verifiers, and one ActiveGraph snapshot contradiction resolved
by a sealed grader-only retry of the hash-identical submission.

Eight of nine frozen `evolved - cold ablation` contrasts are identical
when raw invalid rows are scored zero and when the frozen adjudication
decisions are applied. The exception is Hybrid ActiveGraph: the contrast moves
from -26.0 points under raw-invalid-as-zero to -10.0 points after the
hash-identical quota-scheduler regrade. It remains negative and the
frozen conclusion is unchanged. A raw complete-case analysis gives
+7.3 points for this cell because it drops the evolved invalid row.
That value is an unpaired mean difference on two evolved tasks versus three draw
tasks, not a sensitivity of the frozen paired design. It must not be read as
corroborating the null determination, which for this cell rests on the
adjudicated paired contrast of -10.0 points. Complete-case contrasts are
reported only as sensitivity analyses because dropping bounded failures changes
the estimand and can favor arms with more invalid outcomes.

The study's single adjudication judgment moved a score in the evolved arm's
favor, and the frozen conclusion remained null. The frozen specification
permitted fixes to documented infrastructure defects but did not enumerate this
snapshot-contradiction category, define its distinguishing criterion, or specify
a retry maximum. The sealed grader-only regrade was therefore a post-hoc
adjudication: it was allowed because the original grader contradicted a
receipt-bound parsable submission, it reused the hash-identical artifact, and no
model action or raw row was rerun. One grader retry was performed; one was not a
pre-specified maximum.

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

The study specification is `research/local_study.json`, SHA-256
\texttt{8313d219\allowbreak{}71452704\allowbreak{}893200d2\allowbreak{}022718fe\allowbreak{}ca985142\allowbreak{}ae32fe7d\allowbreak{}16932d34\allowbreak{}a0e0d581},
with frozen status at study commit
\texttt{55984389\allowbreak{}4578141d\allowbreak{}fbd39b7b\allowbreak{}ae2246db\allowbreak{}76e57bde} dated
2026-07-17T18:30:38-07:00. The compact release does not retain an independently
witnessed timestamp for the first development call. The Round 1 manuscript
package was commit
\texttt{8bdff502\allowbreak{}cc08be96\allowbreak{}8b21bbe5\allowbreak{}ebf177d4\allowbreak{}9879a0fb}.

The provenance manifest records byte counts and SHA-256 hashes for the paper
package's frozen analytical datasets and reports, adjudication ledger,
post-hoc metrics, masked coding packet, both original coder label files,
agreement report, and manuscript:
[`provenance-manifest.json`](provenance-manifest.json).

The adjudication ledger separately hashes each changed row and its supporting
evidence. Both original taxonomy-label files were frozen before adjudication.

## E. Cross-model coding agreement

The table reports exact agreement, Cohen's kappa, and Gwet's AC1 for two
separately executed, outcome-blind model-coding passes using the recorded
identifiers `gpt-5.6-sol` and `gpt-5.6-terra`. Sol generated the 84 proposals
it later coded; Terra supplied the other pass. The package does not establish
provider or pretraining independence between these identifiers. The analysis
is therefore a cross-model consistency check rather than independent human
reliability. Kappa is undefined when both coders use one
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

For primary update target, Sol assigned 76 procedure and eight
validation-asset labels, while Terra assigned all 84 to procedure. The
resulting confusion is 76 procedure/procedure and eight
validation-asset/procedure cases, which explains 90.5% exact agreement with
kappa 0.000. Complete coder marginals and disagreements are retained in
[`data/taxonomy/coder-agreement.json`](data/taxonomy/coder-agreement.json).

No coefficient interval is reported because these are two fixed model-coding
passes used as a prompt and model-sensitivity check rather than sampled human
raters. Interpretive fields remain exploratory.

## F. Actor-visible control-collapse sensitivity

Source inspection confirms that cold and cold ablation use the same task,
model, seed field, tools, workspace, system instructions, empty
retained-context field, and later actor-visible tool protocol. Cold ablation
validates the lineage state hash before suppressing its contents; that
provenance difference never reaches the actor. The frozen
`evolved - cold ablation` contrast is therefore retained as a decision record,
not described as a separable lineage intervention.

The pooled-six and leave-the-matched-ablation-out calculations use only the
committed compact score table. Across Workspace, Minimal, and Hybrid, the
pooled-six deltas are +6.7, -3.3, and +6.7 points for SWE; +11.1, -22.2, and
-5.6 for Terminal; and -9.9, +4.1, and -9.9 for ActiveGraph. The corresponding
leave-one-out deltas are +8.0, -6.0, +6.0; +10.0, -20.0, -6.7; and -8.4,
+3.2, -9.9 points.

The nominal 95% deterministic task-resampling intervals use 10,000 draws and
the same percentile convention as the frozen comparison. For Workspace,
Minimal, and Hybrid respectively, pooled-six intervals are SWE [-8.3, +26.7],
[-30.0, +18.3], [-3.3, +21.7]; Terminal [0.0, +27.8], [-50.0, 0.0],
[-25.0, +8.3]; and ActiveGraph [-33.3, +3.7], [-6.3, +18.7], [-33.3, +3.7].
Leave-one-out intervals are SWE [-10.0, +32.0], [-32.0, +16.0], [-4.0,
+20.0]; Terminal [0.0, +30.0], [-46.7, 0.0], [-30.0, +10.0]; and ActiveGraph
[-29.6, +4.4], [-5.6, +15.2], [-32.0, +2.4]. No lower bound is above zero, so
the sensitivity analyses do not produce the required positive pattern in two
families. The written no-uplift decision is unchanged.

A tie-aware conditional exchangeability calculation pools each evolved score
with its six actor-visible-equivalent controls and uniformly relabels the focal
score. Only a unique minimum or maximum is strictly outside the other six. Each
case therefore contributes 0, 1/7, or 2/7 according to the number of unique
extrema among its seven observed values. In these data, exactly 12 cases
contribute 1/7 and the other 45 contribute zero. The contributors are:
Workspace, Minimal, and Hybrid on SWE `pydata__xarray-3305`; Minimal and Hybrid
on SWE `sympy__sympy-19040`; Minimal on SWE
`scikit-learn__scikit-learn-13124`; Workspace and Hybrid on Terminal
`bn-fit-modify`; Workspace, Minimal, and Hybrid on ActiveGraph
`delegated_access_control`; and Minimal on ActiveGraph `quota_scheduler`.

Across 57 configuration-task cases, the expected outside-range count is 12/7
(1.71) and the observed count is one. The expected counts are 1/7 among 36
cases on stable control tasks and 11/7 among 21 cases on variable control
tasks. Under independent conditional relabelings across cases, the count
variance is 72/49 (1.469). Cases share tasks and control observations, so that
variance is a descriptive reference rather than a sampling-design claim.
Machine-readable outputs are
[`data/generated/equivalent-control-sensitivity.csv`](data/generated/equivalent-control-sensitivity.csv)
and
[`data/generated/outside-range-exchangeability.json`](data/generated/outside-range-exchangeability.json).
