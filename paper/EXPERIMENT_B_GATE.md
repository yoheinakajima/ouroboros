# Experiment B gate decision

Decision date: 2026-07-23  
Decision: **closed — no retrieval benchmark rerun for this paper**

## Specific reviewer threat

The strongest threat is:

> Hybrid's raw-overlap retriever over-selected broad-vocabulary and
> failure-derived lessons, but that composition may reflect legitimate task
> relevance and may have no harmful effect on downstream behavior or score.

The current data cannot causally answer the second half. Offline re-ranking
changes which lessons would be selected but generates no new task outcomes.
Quota scheduler cannot serve as outcome evidence because evolved Hybrid's 0.48
equals the minimum of six byte-identical no-context runs.

## Applying the frozen gate

1. **Would this threat block a central claim?**  
   It blocks “retrieval skew caused score regression.” That claim has already
   been withdrawn. It does not block the supported claim that vocabulary
   breadth drove selection frequency under the implemented set-overlap rule.

2. **Can existing analysis answer the retained claim?**  
   Yes. The ranker code, within-status correlations, adjusted regression,
   stratified permutation test, retrieval receipts, and offline counterfactual
   rankings identify the implemented selection mechanism.

3. **Would narrowing remove a central contribution?**  
   No. The paper remains about expression, causal identification, equivalent
   controls, sham construction, and the difference between self-modification,
   behavioral mediation, score improvement, and descendant productivity.

4. **Can a focused intervention be cleanly isolated?**  
   Probably, but it would require a new preregistration and enough replication
   to exceed the measured task-level noise. It is not needed for the present
   descriptive mechanism claim.

## Consequence for the paper

Use:

> Vocabulary breadth strongly predicted retrieval frequency under Hybrid's
> implemented lexical ranker, and alternative offline rankers reduced
> concentration.

Do not use:

> Failure-memory retrieval harmed held-out performance.

The causal retrieval intervention remains a well-specified follow-up. It
should be run only if a future paper makes downstream retrieval efficacy a
primary claim.

