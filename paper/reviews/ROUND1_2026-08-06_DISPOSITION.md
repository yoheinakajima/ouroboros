# Round 1 disposition

Paper: **When Self-Modification Becomes Memory**
Subtitle: **An Audited Comparison of Three Self-Improving Agent Substrates**
Frozen manuscript commit: `8bdff502cc08be968b21bbe5ebf177d49879a0fb`
Frozen source SHA-256: `ddbf7dd166716e4ccbf80ffd0db2b888e19db14c4c23cac8f7bad3b621a019b6`
Frozen PDF SHA-256: `ae49238e37140011e3c8656cdabdf3c1b4783133d3c54e69d7a5558c7b170df1`

This disposition covers the four isolated Round 1 reviews delivered together
to the writer. No reviewer saw another review. Raw review transcriptions are
bound by hashes in
[`ROUND1_2026-08-06_PROVENANCE.json`](ROUND1_2026-08-06_PROVENANCE.json).
Private session locators remain in the manager-held bundle and are not copied
into this public paper package.

## Manager packet-metadata correction

The manager-created packet header incorrectly expanded the title to **When
Self-Modification Becomes Memory: Governance, Legibility, and the Boundary of
Identity in Adaptive Agents**. The reviewed PDF itself displayed the canonical
title and subtitle above. Claude correctly detected the mismatch, but the
cause was manager packet metadata, not missing manuscript sections and not a
reviewer anomaly. The disposition preserves the discrepancy, rejects a
governance/identity scope expansion, and requires every Round 2 packet surface
to use the canonical title and empirical measurement/auditability frame.

Title- and venue-fit reactions from all four reviewers are treated as
contaminated by the incorrect header. No manuscript claim is revised merely
to satisfy that erroneous framing.

## Review summaries

| Reviewer | Verdict | Scores: novelty / significance / correctness / evidence / clarity / reproducibility / venue fit |
|---|---|---|
| ChatGPT Medium | minor revision | 4 / 4 / 4 / 4 / 4 / 4 / 4 |
| Claude Opus 5 High | major revision | 4 / 4 / 3 / 3 / 4 / 4 / 3 |
| Gemini Pro temporary chat | not ready | 5 / 5 / 4 / 4 / 5 / 5 / 5 |
| Grok Expert private chat | minor revision | 4 / 4 / 4 / 3 / 4 / 5 / 4 |

The pre-revision stop threshold is not met: two of four verdicts are ready or
minor, and Claude's critical control objection was unresolved at review time.

## Critical and release-blocker dispositions

| Finding | Source | Disposition | Evidence and revision |
|---|---|---|---|
| Cold and state-hidden ablation collapse at the actor-visible intervention boundary. | Claude C1 | **Accepted and resolved in the paper package.** | `StateAdapter.prepare` validates the ablation state and hash but emits an empty context and `exposed=false`; cold emits the same. `BrokeredRepoAgent.run` then receives the same task, model, seed field, tools, workspace, system instructions, null retained context, and tool protocol. The Harbor adapter has the same null-context behavior. The paper now says rung 2 is not separably implemented, preserves the frozen labeled-ablation rule, and adds deterministic pooled-six and leave-the-matched-ablation-out sensitivities. The null is unchanged. |
| Packet title promises governance, legibility, and identity material absent from the PDF. | Claude C2; contaminated venue-fit comments from all reviewers | **Reclassified as manager packet-metadata error.** | The PDF title was correct. Governance/identity expansion is rejected. The Round 2 packet is corrected instead. |
| Missing `hybrid-usage-gpt56-v4` result invalidates the reported Hybrid authoring cost and blocks the paper. | Gemini critical; Claude C3 distinguishes release from content | **Rejected as a paper-evidence inference; external repository CI remains outside this revision.** | `research/run_index.json` records `hybrid-usage-gpt56-v4` as an older `stateful_usage_tracker` pilot. The manuscript's $0.249 to $2.114 values come from `paper/data/generated/posthoc-metrics.json` at `development_process.hybrid_packs`, the paper's 28-generation authoring records. No false caveat was added and no unrelated research-index CI repair was attempted. Package-native checks remain required. |

## Major dispositions

| Finding | Source | Disposition | Revision or reason |
|---|---|---|---|
| Novelty is not differentiated from mediation, memory utilization, and provenance/observability. | ChatGPT major 1; Claude novelty discussion | **Accepted.** | Added a bounded Related Work paragraph separating those precedents from the unified persistent-self-modification evidentiary chain, descendant-productivity endpoint, heterogeneous expression profile, and receipt-bound controls. No claim that every component is unprecedented. |
| Outcome claims oscillate between substrate/architecture and the implemented experimental object. | ChatGPT major 2; Grok major shared-interface finding | **Accepted.** | Defined the evaluated unit as a substrate-proposal-acceptance-interface configuration. Outcome tables and conclusions use configuration; substrate is reserved for retained-state properties. |
| “Independent” model coding hides that Sol generated the proposals it coded. | ChatGPT minor 6; Claude M1 | **Accepted.** | Removed “independent,” disclosed Sol self-coding in abstract, main text, appendix, and table caption, and reframed 84/84 agreement as a cross-model consistency check. Added primary-target coder marginals/confusion. No third coder was launched. |
| Vocabulary-adjusted regression is mediator adjustment, not attribution away from failure. | ChatGPT overstatement A; Claude M2; Grok overstatement | **Accepted.** | The raw failure-derived retrieval enrichment is now the total association. Vocabulary breadth is a plausible mediated selection path in the implemented overlap ranker. “Rather than failure status” was removed. |
| One of 57 outside-range cases lacks a chance benchmark and is overstated as harmful mediation. | Claude M3 | **Accepted and reanalyzed.** | Added a tie-aware conditional exchangeability calculation from committed compact data: expected 12/7 (1.71), observed 1. “Establishes” became “is consistent with” and the case is not described as a population or chance detection. |
| The six-label dispersion reference contains the three labeled ablations used as primary comparators. | Claude M4 | **Accepted.** | Overlap is stated at first use. Added leave-the-matched-ablation-out sensitivity for all nine cells. |
| The self-built ActiveGraph benchmark shares technology with the Hybrid substrate. | Claude M5 | **Accepted.** | Added an explicit structural-conflict disclosure. Sealed checks and the result unfavorable to Hybrid mitigate simple directional bias without removing the conflict. |
| “Preregistered” lacks a locator, timing, and independent freeze proof. | Claude M6 | **Accepted with evidence-limited wording.** | Added `research/local_study.json`, SHA-256 `8313d219...`, study commit `559843...`, and commit timestamp. The compact package does not preserve an independently witnessed first-call timestamp, so the paper now says “frozen study specification/decision rule,” not external preregistration. |
| Packet commit and in-paper commit appear inconsistent. | Claude M7 | **Accepted.** | Labeled `559843...` as the study-specification commit and `8bdff...` as the Round 1 manuscript package. |
| The five-construct framing suggests all five were instrumented. | Claude M8 | **Accepted.** | Abstract and framework now state that the study instruments the first four and defines descendant productivity as the stronger fifth endpoint. |
| Single lineage, one model, shared interface, and 10/6/3 tasks need more prominence. | Grok major 1 and 2; ChatGPT/Grok evidence limits | **Accepted.** | Foregrounded the configuration-level unit, common proposal generator/interface, one-lineage scope, and unstable three-task ActiveGraph planning diagnostic. No architecture or population ranking is claimed. |
| ActiveGraph ICC/MDE is hazardous with three targets. | Gemini major; ChatGPT minor 3 | **Accepted.** | Renamed it a continuous-approximation planning diagnostic, explicitly illustrative for ActiveGraph and not a decision threshold. |

## Overstatement and minor dispositions

| Finding | Source | Disposition |
|---|---|---|
| Abstract states sham below ablation as a uniform result. | Claude unsupported 1; ChatGPT minor 4 | **Fixed:** abstract reports five below, three above, one tie, and “possible” interference. |
| “Vocabulary-driven failure-memory stickiness” implies causal downstream harm. | ChatGPT overstatement A; Grok | **Fixed:** narrowed to selection association/mechanism in the implemented ranker; no score effect. |
| “Saturation” is broader than the policy cap. | ChatGPT overstatement B | **Fixed:** “policy-cap saturation under this append-oriented implementation.” |
| Shared reflector invites an unconstrained architecture comparison. | ChatGPT overstatement C | **Fixed:** the proposal bottleneck is stated before substrate descriptions. |
| “The instruments generalize” is categorical. | ChatGPT overstatement D | **Fixed:** “directly applicable in principle.” |
| Conclusion says the interface determines what self-modification can become. | ChatGPT overstatement E; Grok generality concern | **Fixed:** limited to admitted, expressed, and evaluated modifications in the studied system. |
| The five constructs may be read as one ordinal ladder. | ChatGPT minor 1 | **Fixed:** explicitly distinct evidentiary propositions with descriptive versus counterfactual requirements. |
| Byte-identical initial requests may be read as fully deterministic runs. | ChatGPT minor 2 | **Fixed:** listed frozen actor-visible inputs and uncontrolled post-request variation. |
| Compact release is called “fully receipted” although the complete trace DOI is pending. | ChatGPT minor 5; Claude unsupported 6 | **Fixed:** compact-package reproducibility and pending disclosure-gated trajectory archive are separated. No deposit date is invented. |
| Workspace 17 complete plus one partial file conflicts with 18/85. | Claude unsupported 8 | **Fixed:** stated frozen rule that a bounded prefix counts as one surfaced file, with completeness reported separately. |
| External-effects sentence is an insinuation. | Claude unsupported 9 | **Fixed:** removed and replaced with a direct independent-application proposal. |
| Related-work “re-audited” and NR cells are not independently verifiable. | Claude unsupported 10; Grok | **Partly accepted:** caption now calls them author classifications and says NR is not independently verified here. A per-cell primary-source worksheet remains a useful optional future artifact; no new literature work was authorized. |
| Degenerate [0,0] intervals look like zero population uncertainty and omit units. | Claude unsupported 11, m5 | **Fixed:** labeled degenerate observed contrasts and added point units. |
| “Variable” column is undefined; MDE and maximum gap are over-salient. | Claude m2; ChatGPT minor 3 | **Fixed:** column states tasks variable across six labels; diagnostics are descriptive/planning only. |
| Internal “Experiment B” and separate program jargon are undefined. | Claude m3 | **Fixed:** removed from manuscript limitations. |
| Primary-target kappa 0.000 at 90.5% agreement looks suspicious. | Claude m4 | **Fixed:** appendix gives Sol 76 procedure/8 validation-asset, Terra 84 procedure, and the resulting confusion. |
| Abstract “family-level mean gaps” misnames a maximum pair gap. | Claude m6 | **Fixed:** that compressed claim was removed from the abstract; exact descriptive quantities remain in Section 6. |
| SWE sham sentence names ablation while explaining evolved-minus-sham. | Claude m9 | **Fixed:** names evolved 8/10 directly. |
| Expression profile lacks absolute byte numerators and denominators. | Claude m10 | **Fixed:** added all storage and eligible-payload byte ratios in main text. |
| Related-work table layout and possible stray number/vertical whitespace. | Gemini minor; Claude m7 | **Accepted for visual QA:** regenerated PDF must be inspected before handoff. |
| Reference metadata and every related-work cell need primary-source verification. | Claude m8 and uncertainty; all novelty uncertainty | **Unresolved external-verification item, not silently accepted.** Existing link audit is rerun, but no fresh literature review or publication claim is made. |
| Add an example of a non-bottlenecked adapter. | Gemini optional | **Accepted narrowly:** the existing native-interface-ablation rung supplies the design; no speculative implementation was added. |
| Bold equivalent ranges, add a new schematic, third coder, or extensive per-cell worksheet. | Gemini/Grok/Claude optional | **Deferred:** not needed to resolve Round 1 correctness; would expand package or require new model/research work. |

## Validation and next-round gate

Round 2 may be prepared only after the revised Markdown, generated LaTeX, PDF,
analysis outputs, manifest, release scan, link audit, claim audit, style audit,
and visual PDF inspection are all complete. Round 2 reviewers must be fresh,
isolated sessions receiving only the corrected manuscript, rubric, and
paper-specific packet. They must not receive this disposition or the Round 1
reviews.

No Explore Science upload, publication, merge, provider call, new research
experiment, or repository-index CI repair is authorized by this disposition.
