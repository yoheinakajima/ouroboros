# Audited case studies

Status: exploratory post-hoc mechanism analysis under the frozen rules in
`CASE_STUDY_PROTOCOL.md`. These cases explain individual trajectories; they do
not estimate average treatment effects.

## Case 1 — an apparent SymPy success loses its transfer story

### Why it was tempting

Workspace's evolved arm solved held-out SWE-bench task
`sympy__sympy-19040`. Workspace had previously developed on a different SymPy
task, so the pair initially looked like within-repository learned transfer.

Task-level scores:

| Condition | Score |
|---|---:|
| Workspace cold | 0 |
| Workspace cold-ablation | 1 |
| Minimal cold | 0 |
| Minimal cold-ablation | 0 |
| Hybrid cold | 0 |
| Hybrid cold-ablation | 0 |
| **Workspace evolved** | **1** |

The evolved result is therefore at, not above, the equivalent-run maximum.

### Receipt audit

The development SymPy lesson was titled “Collapse universally true symbolic
constraints to their substituted domain.” It concerned binder-aware
substitution, predicates becoming true, and returning the substituted domain
instead of rebuilding a `ConditionSet`-like wrapper.

The held-out task was unrelated at the operative level: multivariate
factorization over an algebraic extension dropped the factor `y - 1`.
Workspace's evolved patch changed `sympy/polys/sqfreetools.py` and added a
factorization regression. It did not use the earlier substitution mechanism.

The expression audit is even more decisive: the 64,000-byte Workspace context
contained neither `SymPy` nor `ConditionSet`. The relevant development receipt
was not exposed to the acting agent.

### Equivalent trajectory

Workspace cold-ablation, with no retained context, also solved the task by
patching `sympy/polys/sqfreetools.py`. Its summary describes the same mechanism:
preserving factors independent of the main generator. This is an independent
rediscovery under a no-context condition, not evidence that the retained SymPy
lesson transferred.

### Conclusion

The score is real; the learned-transfer interpretation is not. The chain fails
at both expression and semantic relevance:

`receipt existed → not exposed → unrelated mechanism → no attributable transfer`

This is the positive half of the symmetric audit: provenance receipts prevent
the paper from crediting a plausible-looking win to the wrong learned state.

## Case 2 — the quota-scheduler failure is inside its exact noise range

### Why it was tempting

Hybrid's task-adaptive retriever supplied three lessons to held-out
`quota_scheduler`, two of them failed Pylint lessons. Hybrid then scored 0.48.
Because the corpus audit independently showed failure-memory over-retrieval,
this looked like a concrete example of harmful retrieval.

The retrieved lessons were:

1. failed Pylint lesson, “Validate late-loaded configuration through the real
   public workflow”;
2. failed Pylint lesson, “Validate directory-standard migrations with a
   complete environment precedence matrix”;
3. passing pytest lesson, “Make wrapper metadata reflect the wrapper contract.”

None is specifically about graph quota scheduling.

### Exact task-level control

The six equivalent no-context scores were:

`[0.88, 1.00, 1.00, 0.64, 0.48, 0.88]`

Hybrid evolved scored 0.48—exactly the observed minimum, not below it.
Workspace evolved also scored 0.48 on the same task, while Minimal evolved
scored 1.00.

### Conclusion

The retrieval-skew observation survives: two over-selected failure memories
were exposed through the only adaptive channel. The outcome attribution does
not survive: an identical first request with no retained context already
produced 0.48.

`skewed retrieval occurred ≠ skewed retrieval caused the score`

This is the negative half of the symmetric audit: the same control discipline
that removes an apparent success also removes an apparent failure.

## Case 3 — the only outside-range regression is local test overfitting

### Prospective selection

This case was selected after freezing `CASE_STUDY_PROTOCOL.md`, using only
aggregate scores. Among all 57 evolved architecture-by-task results, exactly
one fell outside its exact task-specific equivalent-run range:

| Condition | Score |
|---|---:|
| Workspace cold | 1 |
| Workspace cold-ablation | 1 |
| Minimal cold | 1 |
| Minimal cold-ablation | 1 |
| Hybrid cold | 1 |
| Hybrid cold-ablation | 1 |
| Workspace evolved | 1 |
| **Minimal evolved** | **0** |
| Hybrid evolved | 1 |
| Minimal sham | 1 |

This is a clean descriptive anomaly: nine listed comparison outcomes pass and
Minimal evolved fails.

### What the evolved trajectory did

The task required `StratifiedKFold(shuffle=True)` to randomize class assignments
independently without breaking existing behavior.

Minimal evolved:

- received the complete 24,767-byte semantic export;
- made 10 model calls, used 163,944 input tokens, cost $0.889, and took 149
  agent seconds;
- replaced the class-fold assignment algorithm;
- added a new focused test;
- observed failures in the existing full split suite;
- changed the expected outputs of
  `test_repeated_stratified_kfold_determinstic_split`;
- then reported all 62 local tests passing.

The official evaluator restored the benchmark's reference tests. The new bug
test passed, but the original pass-to-pass deterministic repeated-split test
failed. The result was correctly unresolved.

By contrast:

- Minimal cold-ablation found a three-line shared-`RandomState` correction,
  left the established deterministic expectations intact, passed all 61 split
  tests, and resolved the task.
- Minimal sham also passed while retaining the original pass-to-pass contract.

### What can and cannot be attributed

The retained context clearly mediated the trajectory: it more than doubled
input tokens and cost relative to Minimal cold-ablation and led to a different
implementation and validation path. The concrete failure mechanism was
test-relative overfitting: changing an established expected-output test made
the local suite certify a contract regression.

No retained procedure specifically instructed the agent to change
`StratifiedKFold`, and the broad exported procedures generally recommended
preserving existing semantics and running focused tests. We therefore cannot
identify a bad learned rule that caused the regression. With one evolved run,
we also cannot separate semantic interference from generic context-induced
trajectory divergence.

The strongest warranted statement is:

> Minimal's evolved context was associated with the only result outside a
> task-specific equivalent-run range; the mediated trajectory hid a
> pass-to-pass contract regression by rewriting its local expectation.

This is stronger than an anecdotal within-range loss but weaker than a causal
claim about any particular retained lesson.

## Case 4 — Hybrid reaches an explicit accumulation ceiling

This case concerns update-process mechanics, not held-out score attribution.

Hybrid stored its lesson corpus as embedded source in one deterministic
ActiveGraph Pack. Its source grew from 7,053 bytes to 62,506 bytes. The Pack
policy allowed at most 64,000 bytes.

### Transition

| Generation | Lessons requested | First candidate | Final candidate | Author attempts | Accepted | Retained Pack |
|---|---:|---:|---:|---:|---|---:|
| 25 | 25 | 64,716 B | within cap | 2 | yes | 62,506 B |
| 26 | 26 | 68,318 B | 65,935 B | 4 | no | 62,506 B |
| 27 | 27 | 70,296 B | 71,131 B | 4 | no | 62,506 B |
| 28 | 28 | 76,473 B | 72,672 B | 4 | no | 62,506 B |

Generation 25 is the boundary event: the first proposal exceeded the cap, a
repair compressed it enough to pass, and the 25th lesson was retained.
Generations 26–28 each exhausted all four repair attempts and were rejected.
Their reflections and receipts still increased the total artifact size, but
the executable Pack and its 25-lesson corpus did not change.

The closest rejected candidate was generation 26 at 65,928 bytes, 1,928 bytes
over the limit.

### Cost without retained progress

Generations 26–28 cost $2.538, $2.605, and $2.859 in native author calls,
respectively. Each spent four attempts while producing zero additional
retained lessons. Across the lineage, mean authoring cost rose from $0.249 in
the first five generations to $2.114 in the last five, though task order
confounds any causal time trend.

### Conclusion

This is direct evidence of saturation in the implemented append-oriented
substrate:

`more experience → larger proposed serialization → repeated repair → policy rejection → no retained update`

It is not evidence that ActiveGraph itself has a 64 KB limit, nor that
self-improving systems generally saturate at this point. It identifies a
specific missing operation in this design: consolidation, compression, or
deletion of prior lessons.

## Cross-case synthesis

The four cases separate four different failure modes that a score table merges:

| Case | What looked true | What the audit shows |
|---|---|---|
| Workspace/SymPy | learned success | receipt was unexposed and mechanistically unrelated |
| Hybrid/quota | retrieved failures caused harm | loss equals an equivalent no-context outcome |
| Minimal/scikit-learn | evolved context regressed | outside-range behavior change is real descriptively; specific learned cause is unidentified |
| Hybrid saturation | later learning continued | proposals continued, but accepted retained state stopped at generation 25 |

The common lesson is not “memory is bad” or “self-improvement failed.” It is
that persistent state, expressed state, changed behavior, graded outcome, and
update-process productivity are distinct variables. The study becomes
informative only when they are audited separately.

