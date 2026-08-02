# Update-proposal taxonomy reliability

Status: exploratory cross-model architecture-masked reliability check

This check compares two independent model-coding passes over the same
84-item architecture-masked packet. It measures cross-model and prompt
sensitivity. It does not replace independent human coding.

| Field | Agreement | Cohen's kappa | Gwet's AC1 | Disagreements |
|---|---:|---:|---:|---:|
| primary update target | 76/84 (90.5%) | 0.000 | 0.904 | 8 |
| secondary update target | 47/84 (56.0%) | -0.081 | 0.543 | 37 |
| representational form | 84/84 (100.0%) | undefined | 1.000 | 0 |
| transfer scope | 63/84 (75.0%) | 0.470 | 0.717 | 21 |
| abstraction level | 59/84 (70.2%) | 0.529 | 0.647 | 25 |
| evidence grounding | 59/84 (70.2%) | 0.428 | 0.669 | 25 |
| failure specificity | 83/84 (98.8%) | 0.661 | 0.988 | 1 |
| validation strategy | 82/84 (97.6%) | 0.592 | 0.976 | 2 |
| consolidation operation | 84/84 (100.0%) | undefined | 1.000 | 0 |
| executable status | 84/84 (100.0%) | undefined | 1.000 | 0 |
| anticipated activation | 84/84 (100.0%) | undefined | 1.000 | 0 |
| counterfactual actionability | 84/84 (100.0%) | undefined | 1.000 | 0 |
| novelty relative to prior state | 84/84 (100.0%) | undefined | 1.000 | 0 |
| confidence | 63/84 (75.0%) | 0.393 | 0.687 | 21 |

## Interpretation rule

Raw agreement is primary. Cohen's kappa is retained for familiarity
and may be undefined when both coders use a single category. Gwet's
AC1 is included as a prevalence-robust companion using each field's
full pre-specified vocabulary.

No taxonomy claim is upgraded to human-validated evidence on the basis
of this comparison. Fields with substantive disagreement must remain
qualified or undergo independent human adjudication.

## What replicated

Both coders assigned all 84 proposals to the same representational
genre: natural-language, append-only, nonexecutable, operational
guidance with no specified activation. They also agreed on failure
specificity for 83/84 proposals and validation strategy for 82/84.
These results support a robust descriptive claim about proposal form.

Interpretive labels were less stable. Agreement was 59/84 for
abstraction and evidence grounding, 63/84 for transfer scope, and
47/84 for secondary target. The two coders assigned the same
success-derived grounding totals, 39/42 direct-validated and 3/42
inferred. For failure-derived proposals, Sol assigned 7/42
direct-validated, 5/42 direct-unvalidated, and 30/42 inferred;
Terra assigned 21/42, 6/42, and 15/42. The direction of the
success-failure contrast replicated, while its magnitude did not.

## Frozen inputs

- Coder A labels SHA-256: `9290e7358b1b2d384805e75be7cc612d1dce6a0d8699ed27ac4f7193e433a667`
- Coder B labels SHA-256: `61a5a859f63f58df313fbde0fd77a8e6ae69e38a37f6c232754d561cf1e21d80`

The machine-readable report preserves category distributions and every
item-level disagreement in
[`data/taxonomy/coder-agreement.json`](data/taxonomy/coder-agreement.json).
