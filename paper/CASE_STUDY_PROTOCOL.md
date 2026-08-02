# Case-study protocol

Status: written after the aggregate score and expression audits, before opening
any additional evaluation traces. Two earlier examples (Workspace/SymPy and
Hybrid/quota scheduler) had already been inspected and are therefore
retrospective audit examples, not blinded or preregistered case studies.

Date frozen: 2026-07-23.

## Purpose

The cases explain how the audit changes interpretation. They do not estimate
average treatment effects and cannot rescue or overturn the preregistered
family-level result.

## Evidence hierarchy

For each task, the six no-context conditions are the two no-context arms for
each of the three architectures. Their first model requests are byte-identical.
Let \([L_x, U_x]\) be their observed score range on task \(x\).

An evolved result is:

- **above-range** when its score is greater than \(U_x\);
- **below-range** when its score is less than \(L_x\);
- **noise-compatible** when its score lies inside \([L_x, U_x]\), including at
  either boundary.

An above- or below-range result is only a candidate architecture effect. A
single observation does not establish causality. A within-range result cannot
be presented as an architecture-attributable success or failure.

Mechanistic attribution additionally requires an auditable chain:

1. the relevant retained unit existed before the held-out task;
2. the evaluation adapter actually exposed or executed it;
3. its content was semantically relevant to the held-out task;
4. the later trajectory contains a compatible behavioral consequence; and
5. the grader outcome is consistent with that consequence.

Breaking any link terminates the mechanistic claim. Similar task names,
retrieval, or textual overlap alone are insufficient.

## Selection rules

### Apparent positive audited away

Use the already inspected Workspace/SymPy example. It was originally selected
because it looked like plausible transfer and had a favorable evolved outcome.
It is retained only as a retrospective falsification example: the retained
SymPy lesson concerned binder substitution and `ConditionSet`, while the
held-out task concerned multivariate algebraic-extension factorization. The
semantic link fails, and the evolved score is inside the equivalent-run range.

No replacement positive will be selected from this dataset unless an evolved
result exceeds the exact task-specific equivalent-run maximum. The aggregate
audit found no such result.

### Apparent negative audited away

Use the already identified Hybrid/quota-scheduler example. Hybrid's evolved
score was 0.48, but the six equivalent no-context scores were
`[0.88, 1.00, 1.00, 0.64, 0.48, 0.88]`. Because 0.48 equals the observed
minimum, the outcome is noise-compatible. Retrieval skew remains documented;
outcome attribution is withdrawn.

### Replacement negative candidate

Select the evolved result with the largest departure below its task-specific
equivalent-run minimum, using only the score table and request-equivalence
audit. If no result lies below the range, report that no candidate exists and
do not substitute a merely interesting trace.

Applying this rule to all 57 architecture-by-task evolved results yields one
candidate: Minimal on `scikit-learn__scikit-learn-13124`, score 0 against six
equivalent no-context scores of 1. Its departure is -1.0. This file records the
selection before its evaluation trace is opened.

### Capacity saturation

Use Hybrid generations 25–28 because the immutable acceptance records directly
show the transition from accepted growth to three consecutive policy
rejections at the 64 KB cap. Selection depends on state-transition records, not
held-out scores.

## Four-case structure

1. Workspace/SymPy: apparent success rejected by the receipt-to-task semantic
   audit.
2. Hybrid/quota scheduler: apparent failure rejected by the equivalent-run
   range.
3. Minimal/scikit-learn: the only below-range evolved result, inspected as a
   candidate regression without causal overclaim.
4. Hybrid generations 25–28: direct process evidence of accumulation and
   saturation.

The first two form a symmetric pair: the audit rules out a tempting win and a
tempting loss. The third tests whether a stricter selection rule leaves any
negative candidate. The fourth concerns update-process mechanics rather than
task-score attribution.

## Reporting rules

- State whether a case was selected prospectively or retrospectively.
- Show all six equivalent-run task scores beside the evolved result.
- Distinguish receipt existence, context exposure, semantic relevance,
  behavioral mediation, and grader outcome.
- Quote no more trace text than needed; link to immutable artifacts.
- Report contrary evidence before interpretation.
- Do not use a case to claim that retrieval skew caused score changes.
- Do not search for replacement cases after trace inspection.

