# Round 2 disposition

Paper: **When Self-Modification Becomes Memory**

Reviewed candidate subtitle: **An Audited Comparison of Three Self-Improving
Agent Substrates**

Reviewed candidate commit: `16031c97f54fec106abc1dab2d075aaacbac4145`

Reviewed manuscript SHA-256:
`62a1111c39095ec9513c08ec79df308d3d55f301fa7a6fbd5deea4bc8b3acd35`

Reviewed PDF SHA-256:
`f7c9a78b87cd10ceeab944ddfd75153993dbd1453fe030d6f12831268303ce71`

Reviewed packet SHA-256:
`eb9ab03477a01e6ae515e97a9eecdd90aea2dd85f3cc4346f21e6be856489c6b`

This disposition covers the four fresh isolated Round 2 reviews delivered to
the writer as one simultaneous bundle. No reviewer saw another review, Round 1
review, prior disposition, or synthesis. Raw review transcriptions remain in
the manager-held bundle; their hashes and model labels are recorded in
[`ROUND2_2026-08-06_PROVENANCE.json`](ROUND2_2026-08-06_PROVENANCE.json).

## Review matrix

| Reviewer | Verdict | Novelty | Significance | Correctness | Evidence | Clarity | Reproducibility | Venue fit |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| ChatGPT Medium | minor revision | 4 | 4 | 4 | 3 | 4 | 4 | 4 |
| Claude Opus 5 High | major revision | 3 | 3 | 4 | 3 | 3 | 3 | 3 |
| Gemini Pro temporary chat | ready | 4 | 5 | 5 | 4 | 5 | 5 | 5 |
| Grok Expert private chat | minor revision | 4 | 4 | 4 | 3 | 4 | 4 | 4 |

The verdict count satisfies the numerical stop condition: three of four are
`ready` or `minor revision`. The reviewed candidate did not satisfy the full
condition because Claude's interval-sensitivity and behavioral-mediation
instrumentation objections were unresolved. This revision closes those two
objections from committed evidence. A later readiness determination still
requires green paper-native validation and owner review. No Explore Science
upload is authorized.

## Agreements and genuine conflicts

All reviewers treated the equivalent-duplicates protocol as a central or
high-value contribution. ChatGPT, Claude, and Grok described the residual
novelty as the integrated evidentiary chain, multidimensional expression
profile, receipt binding, and duplicate-execution reference rather than wholly
new component concepts. All reviewers bounded their review by unavailable raw
traces, unverified hashes, uninspected code/data, and unverified primary
literature.

The genuine conflicts are preserved rather than resolved by vote:

1. Claude treated the absence of sensitivity intervals as a critical
   correctness blocker; the other reviewers accepted or did not elevate the
   point-estimate sensitivity.
2. Claude treated “instruments the first four” as a critical evidence problem,
   while ChatGPT raised the same causal/status ambiguity as major and Gemini
   and Grok accepted the existing framing.
3. ChatGPT and Claude said the subtitle promised a substrate comparison the
   body disclaimed. Grok requested stronger configuration qualifiers; Gemini
   found no title blocker.
4. Claude treated the sham conjunct as unevaluable and the labeled ablation as
   a no-context draw. Grok considered the existing disclosure close to
   sufficient; Gemini accepted it.
5. Claude recommended major revision, Gemini said ready, and ChatGPT and Grok
   recommended minor revision.

## Critical objections

| Reviewer finding | Location | Disposition | Evidence and revision |
|---|---|---|---|
| C1: the frozen rule is interval-based while pooled-six and leave-one-out sensitivities reported point estimates only. | Section 4; Appendix F; Section 10 | **Accepted and resolved from committed data.** | `analysis/reanalyze_equivalent_controls.py` now applies the same deterministic 10,000-draw task-resampling percentile convention to all nine pooled-six and all nine leave-matched-out cells. No lower bound is above zero. The closest positive case, Workspace Terminal, is [0.0, +27.8] pooled and [0.0, +30.0] leave-out. All 18 intervals are reported in Section 4 and Appendix F and enforced by `audit_paper_claims.py`. The required positive pattern in two families is absent. |
| C2: “instruments the first four” overstates systematic behavioral-mediation evidence. | Abstract; Sections 1, 2, 6, 8; Limitations | **Accepted and resolved without new data.** | The paper now says retention, expression, and task improvement are systematic. Existing `behavior-mediation.csv` supplies descriptive resource divergence for all nine configuration-family cells. Three selected complete-chain traces remain mechanism audits whose complete traces are gated. The text explicitly separates descriptive divergence, causal behavioral mediation, and task-score mediation and makes no general causal mediation claim. |

No reviewer identified a critical novelty objection.

## Major, overstatement, and reproducibility dispositions

| Finding | Reviewer | Location | Disposition and revision |
|---|---|---|---|
| The paper's object is a substrate-interface configuration, while the subtitle promises a native substrate ranking; the main title lacks a threshold definition. | ChatGPT M4; Claude J1 | Title; Abstract; Sections 2-3 | **Accepted.** Subtitle changed to “An Audited Comparison of Three Retention-Interface Configurations Under a Shared Reflection Layer.” Section 2 defines “becomes memory” as surviving restart and being eligible for later actor-visible expression; it does not imply mediation or improvement. |
| Empirical, exercised, proposed, and external-pending contributions blur together. | ChatGPT M2; Claude C2 | Abstract; Sections 1-2 | **Accepted.** Added a contribution-status table covering all five propositions and their evidence boundaries. |
| The cold-ablation label remains too easy to read as a separable intervention. | Grok major 1; ChatGPT; Claude J9 | Abstract; Sections 3-4; Table 1; Discussion | **Accepted.** Abstract foregrounds actor-visible equivalence. Table 1 now says “Labeled no-context draw,” and the caption and discussion state that the written contrast is one no-context draw retained as a decision record. |
| Benefit over sham is not evaluable because token load is unmatched and Hybrid also has a byte mismatch. | Claude 5.6/J7 | Frozen rule; Table 1; Sections 4, 6, 10 | **Accepted.** The paper calls the sham columns descriptive and the frozen sham conjunct unevaluable. Token and byte mismatches appear at point of use. This limitation cannot convert the failed written rule into uplift evidence. |
| A Table 5 numbering gap suggests a dropped artifact. | Claude J2 | Related work and generated LaTeX | **Accepted.** Related work is Table 5. Appendix tables follow as Tables 6 and 7. |
| The second coder is identified only as Terra, so the cross-model check is not reproducible and its independence can be over-read. | Claude J3; ChatGPT coding concern | Sections 1, 7.3; Appendix E | **Accepted within recorded evidence.** Both identifiers are now explicit: `gpt-5.6-sol` and `gpt-5.6-terra`. The package does not establish provider or pretraining independence, so none is claimed. |
| The `12/7` expectation lacks derivation, contributing cases, tie handling, and variance. | Claude J4 | Section 6; Appendix F | **Accepted.** Appendix F states the 0/7, 1/7, or 2/7 unique-extrema rule, names all 12 nonzero 1/7 cases, gives the 45 zero-contribution cases by complement, and reports conditional variance 72/49 under independent relabelings with a dependence caveat. The generated JSON preserves the case list and variance. |
| Three-task ActiveGraph bootstrap intervals imply unsupported precision. | Claude J5; ChatGPT/Gemini ICC cautions | Table 1; Sections 3, 6 | **Accepted.** Headline ActiveGraph intervals are suppressed as `n=3, interval not displayed`; its ICC and planning diagnostics remain explicitly anecdotal/descriptive. The underlying values remain in the analytical package. |
| Minimal produced zero deterministic capabilities, so its capability path was never exercised. | Claude J6 | Sections 3, 5, 11; Tables 2-3 | **Accepted.** The zero-capability fact is prominent and conclusions are limited to the recorded procedure-and-receipt instance. |
| The abstract compares 12%-100% item coverage despite the non-comparability rule. | Claude 5.4; ChatGPT | Abstract; Section 5 | **Accepted.** Abstract reports Workspace 21.2%, Minimal 100%, and Hybrid 12% separately and states that they are within-configuration measures, not comparable useful-information quantities. |
| Append-only accumulation is blamed without varying the 64,000-byte cap. | Claude 5.5; ChatGPT | Sections 7.2 and 8 | **Accepted.** Claims are limited to the implemented source-size policy and append-oriented design. No inherent append-only limitation is claimed. |
| Behavioral divergence language can be read as causal mediation. | ChatGPT M1; Claude C2 | Sections 1-2, 6, 8, 11 | **Accepted.** Systematic resource deltas are descriptive. The three trace cases are selected audits; the manuscript does not claim a general causal retained-state effect. |
| Artifact reproducibility is compact and gated at different boundaries. | ChatGPT M3; Claude Explore prerequisites | README; Artifact statement; Limitations | **Accepted.** The package now distinguishes regenerable manuscript/tables/figures/audits, inspectable adjudication/coding artifacts, gated trajectories and trace-dependent reproduction, proposed methods, and pending external deposit. |
| Table 6/5 author classifications and introduction literature claims are not independently verified. | All reviewer uncertainty; Claude J10; Grok must-do | Section 9; Table 5; Limitations | **Accepted as an unresolved external-verification gate.** The table is permanently labeled author-classified against specific versions read on 2026-07-23, and exact per-cell pointers remain pending before external circulation. No new literature research was conducted or fabricated in this revision. |
| “Failure-memory stickiness” is causal/anthropomorphic. | ChatGPT optional/overstatement | Section 7.1; Figure 4 | **Accepted.** Renamed “vocabulary-mediated retrieval concentration.” The regression remains a descriptive slope on a fixed, competing-slot corpus. |
| “Substantially determine,” “reusable,” and broad interface claims overstate magnitude or generality. | ChatGPT; Grok | Abstract; Sections 1, 10, 12 | **Accepted.** Replaced with recorded constraints and “specified for reuse”; no magnitude or universal interface law is claimed. |
| Minimal and Hybrid eligible-byte denominators appear unexplained. | Claude m7 | Section 5 | **Accepted.** Minimal's 98-byte difference is identified as full export versus canonical admitted-array serialization; Hybrid's eligible denominator sums lesson payloads and excludes the Pack wrapper. |
| The outer model seed looks like a determinism guarantee, and sampling/endpoint settings are absent. | Claude m8-m9 | Section 3; Limitations | **Accepted with evidence boundary.** The seed is a best-effort request parameter. Missing provider guarantee, endpoint immutability, temperature, top-p, and context-window settings are disclosed rather than invented. |

## Reviewer-specific remaining and optional findings

| Finding | Reviewer | Disposition |
|---|---|---|
| Add an inferential hierarchy, move or visually separate planning diagnostics, and reduce repeated collapse caveats. | ChatGPT optional; Grok optional; Claude m2/m6 | **Partly accepted.** Contribution-status and explicit descriptive/causal boundaries supply the hierarchy. Planning diagnostics remain labeled and visually separate in Table 4. Further shortening is editorial and optional. |
| Audit Workspace alphabetical truncation and Minimal acceptance symmetrically with Hybrid. | Claude J8 | **Deferred.** High-value follow-up from existing data, but unnecessary to close C1/C2 and outside this bounded revision. |
| Recompute Section 8 duplicate ranges using only four non-comparator labels. | Claude J12 | **Deferred.** The overlap remains disclosed. This robustness addition is optional and does not affect the interval-based C1 result. |
| Replace constrained-total OLS with a slot-allocation model and add ICC intervals. | Claude J11; ChatGPT optional | **Deferred with explicit boundary.** Current coefficients remain labeled descriptive on one fixed, competing-slot corpus; ActiveGraph ICC is anecdotal. No new statistical model was introduced. |
| Surface raw-invalid-as-zero ActiveGraph scores in the main table. | Claude optional | **Deferred.** Appendix A already reports both scoring policies and records that adjudication favored evolved while preserving the null. |
| Add total cost/token accounting. | Claude m10 | **Deferred.** Existing recorded resource summaries remain available. A new total-accounting artifact is not required for C1/C2 and was not reconstructed. |
| Use a third human coder. | Claude/ChatGPT uncertainty | **Deferred.** Would require a new review/research process. The paper preserves exploratory status. |
| Clarify Table 2 pass/fail headers and expression denominators. | Gemini minor | **Accepted.** Generated Table 2 says “Passed task” and “Failed task”; denominator prose is explicit. |
| Add Sol definition to Figure 1 and expand Figure 3 task acronyms. | Gemini optional | **Deferred.** Sol is defined at first textual use; Figure 1 does not depend on the coder. The task identifiers remain traceable in the data. |
| Keep Figure 1's auditability caveat and visually separate Table 4 diagnostics. | Grok optional | **Accepted as already satisfied.** Figure 1 limits the bottleneck to the implemented adapter; Table 4 states neither planning quantity is a threshold. |
| Reframe control collapse as a contribution. | Claude optional | **Accepted in substance.** The equivalent-duplicates and control-ladder discussion makes the discovered collapse a methodological finding while preserving it as a design limitation. |
| Complete disclosure scan/deposit of trajectories. | Gemini Explore prerequisite; all uncertainty | **Unresolved external gate.** The archive remains gated, DOI pending, and no upload or publication occurred. |

## Validation boundary and next gate

Revised readable manuscript SHA-256:
`aa18529a8a07e9f26f317b636d4a1d97573ff88e8de65c2fa9efd5028f2cce52`

Revised canonical LaTeX SHA-256:
`cc860d2c003be1f06268a1637ac989133546621c27e80d721ae97d2453b0b6ba`

Revised 18-page PDF SHA-256:
`7fa244555082958b43043a93facc24a30814abfc132b30a1fc071d410fc05ca8`

The package-native build must regenerate the Markdown companion, LaTeX, PDF,
figures, analyses, audits, scan report, and provenance manifest, followed by a
visual inspection of every PDF page. The repository-wide
`hybrid-usage-gpt56-v4` missing historical run-index failure is unrelated to
this paper package. It remains untouched and must be reported separately from
paper-native validation.

Round 3 is not launched by this disposition. Explore Science remains an
owner-gated external pre-submission review, not a publication venue. No merge,
undraft, publication, deployment, provider call, spend, new literature review,
new experiment, or unrelated repository repair is authorized here.
