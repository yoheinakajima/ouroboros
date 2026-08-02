# Architecture-masked update-proposal taxonomy

Status: exploratory, dual-model reliability analysis. This is not independent
human inter-rater evidence.

## Freeze and blinding record

The codebook was written before extracting or reading taxonomy excerpts. The
84 development-generation lessons were assigned opaque identifiers and
shuffled. Architecture, suite, task, sequence, score, pass/fail status,
acceptance, cost, and later retrieval frequency were removed from the coder's
packet. Independent Sol and Terra coders read only the frozen codebook and
masked packet.

- Items: 84, 28 per architecture
- Truncated items: 0
- Redactions: 39
- Masked packet SHA-256:
  `7b13a1ab2ffccaf5dc9917962f828720690f74856ff20a272b163858065105af`
- Frozen Sol label-file SHA-256 before unblinding:
  `9290e7358b1b2d384805e75be7cc612d1dce6a0d8699ed27ac4f7193e433a667`
- Frozen Terra label-file SHA-256 before unblinding:
  `61a5a859f63f58df313fbde0fd77a8e6ae69e38a37f6c232754d561cf1e21d80`
- Coders: `gpt-5.6-sol` and `gpt-5.6-terra`, high reasoning

The coding is architecture-masked. It is not double-blind because
substrate-specific form can reveal an architecture even when names are absent.
Independent human coding is required before treating interpretive fields as
submission-grade quantitative evidence.

## The most important correction

The unit we successfully blinded is the **common reflection/update proposal**.
Workspace's arbitrary source changes and Hybrid's generated Pack source are
not represented directly in these 84 lesson excerpts. Calling this a general
taxonomy of native mutation would overstate what was coded.

The analysis instead answers a narrower and useful question:

> After three independent development runs pass through the same reflection
> schema, what semantic kind of update does that shared layer propose, and how
> do the architectures gate those proposals?

## Result 1: the shared reflection layer dominated semantic form

Both coders independently assigned the following labels:

| Field | Result |
|---|---|
| Representational form | 84/84 natural language |
| Consolidation | 84/84 append |
| Executable status | 84/84 nonexecutable |
| Intended activation | 84/84 not specified |
| Counterfactual actionability | 84/84 operational |
| Validation strategy | Agreement on 82/84 |
| Failure specificity | Agreement on 83/84 |

Every architecture therefore produced 28 proposals in the same replicated
representational genre. Interpretive agreement was lower: 76/84 for primary
target, 63/84 for transfer scope, 59/84 for abstraction, 59/84 for evidence
grounding, and 47/84 for secondary target.

This near-invariance is not evidence that the native architectures are the
same. It is evidence that the common reflection template compressed their
development experiences into the same semantic genre before architecture-
specific acceptance and evaluation-time expression.

## Result 2: outcome quality changed epistemic grounding

After both label files were frozen, the 84 proposals were unblinded and split
evenly between 42 successful and 42 failed development attempts.

| Grounding | Success, Sol | Success, Terra | Failure, Sol | Failure, Terra |
|---|---:|---:|---:|---:|
| Direct validated | 39 | 39 | 7 | 21 |
| Direct unvalidated | 0 | 0 | 5 | 6 |
| Inferred | 3 | 3 | 30 | 15 |

The success-derived totals replicated exactly. Both coders found more inferred
grounding and less direct validation after failures, while the magnitude of
that contrast differed substantially. These are exploratory descriptive
associations and not prespecified hypothesis tests. The direction is robust to
model choice; exact failure-derived counts are not.

The coders did not see scalar outcome metadata or pass/fail labels. They did
see substantive validation statements inside each proposal because the
codebook intentionally preserved them. The result characterizes proposal
content and does not independently reconstruct hidden success.

## Result 3: the strongest architecture difference was gating

The common reflection layer proposed a lesson after every generation. The
architectures retained different subsets:

| Architecture | Accepted | Accepted after successes | Accepted after failures |
|---|---:|---:|---:|
| Workspace | 25 | 13 | 12 |
| Minimal | 13 | 13 | 0 |
| Hybrid | 25 | 15 | 10 |

Minimal's success gate excluded every failure-derived proposal. Workspace and
Hybrid retained both success-derived and failure-derived proposals. The
present held-out probe cannot determine which mixture is better.

This is a sharper description than “three systems learned different kinds of
lessons.” In this implementation:

1. a common reflector generated mostly homogeneous procedural memory;
2. the retention gate selected which epistemic mixture survived;
3. the adapter determined which retained units were expressed later; and
4. the outer agent determined whether expressed text changed behavior.

## Paper claim

Supported:

> The shared reflection interface produced a replicated natural-language,
> append-only, nonexecutable proposal genre across architectures, while
> architecture-specific gates changed the success and failure history retained
> in state.

Not supported:

> The native mutation spaces of Workspace, Minimal, and Hybrid are
> semantically equivalent.

## Submission path

Before treating interpretive taxonomy fields as submission-grade:

1. recruit independent human coders who have not read the outcome report;
2. adjudicate disagreements without changing either frozen model-coder file;
3. report human agreement separately from the cross-model sensitivity check;
4. keep “update-proposal taxonomy” in the title and methods;
5. separately sample native code/state diffs if the paper wants to compare
   actual mutation forms; and
6. treat outcome-grounding associations as exploratory unless preregistered in
   a new dataset.
