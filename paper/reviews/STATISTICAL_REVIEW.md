# Isolated statistical referee review

Input supplied to the reviewer: `MANUSCRIPT.md` and `APPENDIX.md` only.

## Ranked objections

1. **Blocking. Permutation result sounds like confirmatory inference.**
   Quoted sentence: “It gave \(p=0.00454\).”
   Minimal fix: name the statistic and shuffle scheme, use a plus-one Monte
   Carlo correction, state the within-status exchangeability condition, and
   call the result descriptive rather than causal or population inference.

2. **Should-fix. Bootstrap interval is underspecified and too confidence-like
   for one lineage and tiny task counts.**
   Quoted sentence: “Strong recursive uplift required ... a 95% interval above
   zero.”
   Minimal fix: specify joint paired task resampling, percentile construction,
   and deterministic draws; call it a nominal descriptive task-resampling
   interval and disclaim coverage, especially for three ActiveGraph tasks.

3. **Should-fix. ICC(1,1) lacks a target and model definition.**
   Quoted sentence: “Descriptive ICC(1,1).”
   Minimal fix: define tasks as targets, the six labels as exchangeable single
   replicate executions, and the coefficient as observed-scale repeatability;
   emphasize instability at three targets.

4. **Should-fix. The normal-approximation MDE is not fully specified.**
   Quoted sentence: “Normal-approximation design MDE.”
   Minimal fix: give the formula, alpha, power, variance source, and explain
   that the continuous approximation is not an attainable binary increment.

5. **Should-fix. A nearest-rank 95th percentile of 15 observations is the
   observed maximum.**
   Quoted sentence: “The empirical 95th-percentile bar is based on 15
   dependent label-pair deltas.”
   Minimal fix: report the maximum directly and retain the dependence and
   descriptive-only qualifications.

6. **Should-fix. Small-family percentages need fractions.**
   Quoted sentence: “The family-level mean gaps were 20.0 points on SWE and
   16.7 points on Terminal.”
   Minimal fix: add 2/10 and 1/6 wherever those binary-family quantities are
   presented.

7. **Should-fix. Kappa and AC1 are absent or easy to misinterpret for invariant
   fields.**
   Quoted sentence: “Interpretive fields were less stable across coders.”
   Minimal fix: report field-level exact agreement, kappa, and AC1; explain
   undefined kappa under zero marginal variance and mechanical AC1 of one for
   invariant fields.

8. **Nitpick. “Empirical null” sounds more formal than the design warrants.**
   Quoted sentence: “The empirical null is reported for each family.”
   Minimal fix: call the values dependent pairwise duplicate-execution gaps or
   a descriptive dispersion reference.

Wilson intervals are not used in the manuscript, so no Wilson-specific change
is required.

## Cannot be fixed by language alone

- Population-level uncertainty requires more held-out tasks and independent
  development lineages.
- Calibrated power requires a larger design and a defensible variance model.
- Causal vocabulary effects require a randomized retrieval intervention.
- Human inter-rater reliability requires independent human coders; two model
  passes establish only cross-model coding sensitivity.

