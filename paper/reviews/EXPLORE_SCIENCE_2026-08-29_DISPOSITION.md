# Explore Science review disposition

- Review date: 2026-08-29
- Reviewed manuscript commit: `0c0893e0cc784f274148df3d48fb878645043a7f`
- Reviewed PDF SHA-256: `120e9ec1528e0ab42c0b29772cc7266efb907398873d26a1cfc8b601ccda3591`
- Explore Science report SHA-256: `b8945f974a9e2fd48eec05320ffaf74df924643397fed797e457746eb82e13d2`
Reported score: 100/100 (95% CI 99–100; Platinum tier; 13 minor issues)

The external report is review input, not manuscript authority. Its raw PDF is
retained in the private manager record and is not copied into this public
repository. This file preserves the issue-level disposition and the evidence
used to accept, narrow, or reject each recommendation.

| Issue | Disposition | Applied change or evidence |
|---|---|---|
| A1 shared ActiveGraph result as bias mitigation | Accepted | Replaced the directional-mitigation claim with a necessary-but-insufficient interpretation and made the unresolved shared-failure mode explicit in Methods and Limitations. |
| A2 study-specification SHA inconsistency | Rejected as factually false | `research/local_study.json` hashes to the single 64-character digest `8313d21971452704893200d2022718feca985142ae32fe7d16932d34a0e0d581`. The same digest appears in both the reviewed PDF and source. |
| A3 Round 1 commit inconsistency | Rejected as factually false | Both source locations and the reviewed PDF identify `8bdff502cc08be968b21bbe5ebf177d49879a0fb`; Git verifies that object as a commit. |
| A4 independent timestamp limitation | Accepted | Clarified that the frozen rule supports reproducibility and decision discipline but lacks the protection of independent registration. No retrospective preregistration or immutable-deposit claim was added. |
| B1 input-token divergence | Accepted | Excluded mechanically entailed input-token differences from the evidentiary statement. `behavior-mediation.csv` confirms at least one non-input resource difference in every configuration-family cell. |
| B2 gated trajectory evidence | Accepted as disclosure, not as an archive release | Added exact compact-package pointers and stated that the underlying execution logs remain unavailable, so the mechanism narratives are not independently verifiable from the compact release. No raw trace was disclosed. |
| B3 ICC on binary outcomes | Accepted | Added the violated-assumption caveat and made direct variable-task counts and family score ranges the primary repeatability evidence. No new statistic or post-hoc analysis was introduced. |
| C1 Figure 5 scales | Accepted | Added direct first/last Workspace cost labels and a 1/2/4-request bubble-size legend. |
| D1 complete-case pairing | Accepted | Identified `+7.3` as an unpaired 2-vs-3-task mean difference and separated it from the paired null determination. |
| D2 adjudication pre-specification | Accepted | Stated that the general infrastructure-fix permission was frozen but the specific category, criterion, and retry maximum were not; the grader-only regrade was a post-hoc adjudication of a hash-identical artifact. |
| Three online-only issues | Not assessable from the supplied report | The PDF names 13 issues but includes complete text for only the ten issues above. No unseen recommendation was inferred or applied. |
| Immutable external timestamp/deposit | Deferred | A retrospective archive could improve artifact access but cannot retroactively preregister the study. It remains a separate disclosure, DOI, and owner gate. |
| Release of trace excerpts | Deferred | The raw traces remain subject to the existing disclosure scan and archive gate. The present revision does not expand public evidence scope. |

No new experiment, reviewer round, provider call, statistical recomputation,
trace disclosure, DOI deposit, or publication action was performed for this
disposition.
