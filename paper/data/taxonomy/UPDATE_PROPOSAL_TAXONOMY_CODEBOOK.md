# Mutation taxonomy codebook

Version: 1.0  
Frozen: 2026-07-23, before extracting or reading mutation excerpts for this
taxonomy.

## Research purpose

Characterize what the three self-modifying substrates actually produced during
the 28-task development curriculum. This analysis asks about the form,
specificity, grounding, validation, consolidation, and executable status of
proposed updates. It does not test whether an update improved held-out scores.

## Unit of analysis

The primary unit is one development-generation update proposal. The intended
sample is all 84 generations: 28 per architecture, including accepted,
rejected, no-op, and mechanically generated updates.

Where one generation changes multiple artifacts, code the proposal as one unit
and use the `secondary_target` field for the next most important target. Do not
split a single generation into an arbitrary number of file-level observations.

Acceptance, development-task score, architecture, task id, suite id,
chronological sequence, authoring cost, and later retrieval count are hidden
from the primary coder. They are joined only after labels are frozen.

## Blinding and packet construction

Each packet item receives a deterministic random identifier unrelated to
architecture or sequence. Packet order is shuffled with a frozen seed.

Redact:

- architecture and arm names;
- suite, repository, and task identifiers;
- development score and pass/fail language when it is metadata rather than
  part of the proposed update;
- filesystem roots and framework-specific wrapper names;
- generation and chronology;
- acceptance/rejection status;
- author cost, request count, and downstream retrieval frequency.

Preserve:

- the substantive proposed change;
- enough surrounding text or code to determine its function;
- validation steps stated inside the proposal;
- explicit symptoms, causes, and safeguards;
- executable syntax when execution status is being coded.

Do not paraphrase before coding. Truncate only at natural boundaries and record
whether truncation occurred. If redaction makes a field unknowable, code
`unclear`; never infer from stylistic fingerprints.

Perfect architecture blinding may be impossible because mutation forms differ
by design. The paper must call this **architecture-masked coding**, not
double-blind coding. The current session's coding, if performed, is a pilot:
the analyst already knows aggregate study results. A submission-grade analysis
requires a second independent coder who has not read the outcome report.

## Coding procedure

1. Read the complete masked excerpt once.
2. Assign every field without consulting outcome data or neighboring items.
3. Write a one-sentence rationale using only visible evidence.
4. Mark confidence as high, medium, or low.
5. Freeze labels and rationales.
6. Join hidden metadata.
7. Compute architecture-level distributions and exploratory associations.

Do not revise labels after seeing architecture, score, acceptance, retrieval, or
held-out outcomes. Corrections for transcription errors must be logged.

## Fields

### 1. Primary update target

Choose one.

- `task_solution`: patch or instruction aimed at solving the current task
  instance.
- `procedure`: reusable steps, strategy, heuristic, or playbook.
- `episodic_memory`: retained description of an experience, outcome, or lesson.
- `deterministic_capability`: callable routine, tool, transformation, or
  executable operation intended for later direct use.
- `scaffold_policy`: source code or prompt logic that changes how the agent
  reasons, plans, retrieves, selects tools, or updates itself.
- `retrieval_memory_policy`: indexing, ranking, selection, consolidation, or
  deletion logic for retained knowledge.
- `validation_asset`: test, checker, assertion, or evaluation procedure.
- `configuration`: policy limit, schema, dependency, or execution setting.
- `documentation_provenance`: explanation, receipt, manifest, or audit record
  without a substantive strategy or capability change.
- `none_noop`: no proposed substantive update.
- `unclear`.

`task_solution` differs from `procedure` by intended reuse. A patch to the
training repository is task-specific even if it contains elegant code. A
reusable checklist is a procedure even if derived from one task.

### 2. Secondary update target

Use the same vocabulary, or `none`. Select at most one.

### 3. Representational form

Choose one primary form.

- `natural_language`
- `executable_code`
- `structured_data`
- `test_code`
- `mixed`
- `none`
- `unclear`

Executable syntax embedded only as an illustration in prose remains
`natural_language`. `mixed` requires two forms that materially contribute to
the update.

### 4. Transfer scope

Choose the broadest scope explicitly supported by the proposal.

- `instance`: exact current task or symptom.
- `repository_family`: same codebase, tool, or tightly related task family.
- `cross_task`: reusable across unrelated tasks sharing a method.
- `self_improvement_process`: changes how future updates are generated,
  accepted, retrieved, consolidated, or validated.
- `unclear`.

Do not code aspirational words such as "general" as cross-task unless the
content provides a cross-task trigger or method.

### 5. Abstraction level

Choose one.

- `observation`: records what happened.
- `prescription`: tells a future actor what to do.
- `mechanism`: states a causal or operational explanation linking symptom to
  action.
- `policy`: specifies conditional selection among actions or changes the update
  process.
- `unclear`.

### 6. Evidence grounding

Choose one.

- `direct_validated`: cites an executed test, external grader, or observable
  artifact that directly supports the update.
- `direct_unvalidated`: cites trace or artifact evidence but no validating test.
- `inferred`: proposes a cause or lesson beyond directly observed evidence.
- `unsupported`: no visible connection between evidence and change.
- `not_applicable`
- `unclear`

The existence of a score in hidden metadata cannot support this label.

### 7. Failure specificity

Choose one.

- `none`: no failure content.
- `symptom_only`: names an error, timeout, mismatch, or failed outcome.
- `localized_cause`: identifies a concrete likely source.
- `root_cause_chain`: connects symptom, cause, and relevant system mechanism.
- `recovery_procedure`: gives steps to diagnose or recover.
- `preventive_safeguard`: encodes a check or policy intended to prevent
  recurrence.
- `unclear`.

For items containing multiple levels, choose the highest level actually
supported. `preventive_safeguard` outranks `recovery_procedure`, which outranks
`root_cause_chain`, `localized_cause`, and `symptom_only`.

### 8. Validation strategy

Choose the strongest validation proposed or reported inside the item.

- `none`
- `static_check`: syntax, schema, type, lint, or compilation check.
- `focused_test`: targeted unit or reproduction test.
- `integration_test`: multi-component or end-to-end test.
- `external_evaluation`: held-out grader or independent benchmark.
- `multiple_levels`: at least two substantively different validation levels.
- `unclear`

Merely recommending "test it" without specifying what to run is `none`.

### 9. Consolidation operation

Choose one.

- `append`: adds a new unit without revising prior units.
- `revise`: edits or replaces an existing unit.
- `merge_deduplicate`: combines overlapping prior units.
- `delete_prune`: removes retained material.
- `compress_summarize`: reduces representation size while aiming to preserve
  meaning.
- `none`
- `unclear`

If a source file is rewritten only to append a new registry entry or branch,
code `append`.

### 10. Executable status

Judge the proposed retained update, not the evaluation adapter.

- `nonexecutable`: prose, receipt, or passive data only.
- `executable_unvalidated`: executable implementation without visible
  validation.
- `executable_validated`: executable implementation with at least a focused
  test or direct execution evidence.
- `execution_metadata_only`: records a capability or command but does not
  retain its implementation.
- `none`
- `unclear`

### 11. Anticipated activation

Choose one based only on the proposal.

- `always_in_context`: intended to be serialized for every later task.
- `conditional_retrieval`: intended to surface by task-dependent selection.
- `automatic_execution`: intended to run automatically in a later task path.
- `actor_callable`: intended for the acting agent to invoke interactively.
- `development_only`: changes only update generation or governance.
- `not_specified`
- `unclear`

This field records intended activation. Actual evaluation-time activation is
measured separately by the expression audit.

### 12. Counterfactual actionability

Choose one.

- `none`: description only.
- `weak`: generic advice unlikely to determine a distinct action.
- `specific`: contains a trigger and a concrete action.
- `operational`: contains a trigger, action, and verification or fallback.
- `unclear`.

### 13. Novelty relative to prior retained state

This field requires a separately masked summary of prior retained units. If
that summary is not supplied, code `not_coded`.

- `duplicate`
- `incremental`
- `new`
- `contradictory`
- `not_coded`
- `unclear`

### 14. Confidence

- `high`: label follows explicit evidence.
- `medium`: one reasonable ambiguity.
- `low`: substantial redaction, truncation, or architectural ambiguity.

### 15. Rationale

One sentence, no outcome information, quoting or pointing to the visible
feature that determined the labels.

## Derived variables specified before unblinding

- **Executable-update rate:** executable statuses divided by all substantive
  proposals.
- **Operational-actionability rate:** `operational` divided by substantive
  proposals.
- **Cross-task-or-meta scope:** `cross_task` or
  `self_improvement_process`.
- **Validation-bearing rate:** any validation other than `none` or `unclear`.
- **Consolidation rate:** revise, merge/deduplicate, delete/prune, or
  compress/summarize rather than append.
- **Mechanistic failure rate:** root-cause chain, recovery procedure, or
  preventive safeguard among failure-relevant items.

Architecture comparisons are descriptive counts and proportions with exact
binomial intervals. Because architecture determines the allowable mutation
surface, these are design outcomes, not estimates of an architecture-independent
causal effect.

Exploratory outcome joins may compare labels with:

- acceptance;
- current development pass/fail;
- later retrieval;
- authoring cost;
- sequence and retained-state size.

No held-out-score association will be treated as confirmatory, and no
per-task-level join will be used to claim transfer without the full
receipt-to-expression-to-behavior audit.

## Reliability

For submission:

- two independent coders label at least all 84 primary units;
- report raw agreement and Cohen's kappa for mutually exclusive fields;
- report prevalence-adjusted agreement or Gwet's AC1 when kappa is distorted
  by rare categories;
- adjudicate only after independent labels are frozen;
- publish the masked packet, both original label files, adjudication log, and
  extraction script.

If only one coder is available, label the results a single-rater exploratory
taxonomy and do not report pseudo-reliability.

## Exclusions

Exclude only:

- corrupted records with no recoverable proposal;
- exact duplicated records caused by infrastructure replay, retaining the
  canonical receipt;
- pure grader-only recovery artifacts that did not alter retained state.

Report every exclusion by masked id and reason. Rejected or no-op proposals are
not exclusions.

