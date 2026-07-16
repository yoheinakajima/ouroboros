# Migration note: from function mutation to workspace evolution

This documents the pivot of Ouroboros from a **constrained text-policy mutator**
(v0) to an **open-ended software-workspace evolution** engine (v1, the canonical
root `ouroboros.py`).

## What v0 was

v0 (`experiments/baselines/text_policy_v0.py`, preserved verbatim) evolved a
single deterministic, import-free **text policy**: one mutable region containing
six required functions (`act`, `analyze_task`, `generate_options`,
`select_strategy`, `compose_response`, `improvement_advice`). Each candidate
replaced **exactly one** existing function with a new body. Candidates were
scored by an output-blind pairwise LLM judge over visible development probes and
hidden holdout probes, and accepted by a deterministic rule. The organism was a
string of Python source; the substrate could not create files, run commands,
access the network, or restructure itself. Its capability profile explicitly
declared `does_not_support: multi-file workspaces, external tools, filesystem
writes, network`.

v0 was a good instrument for a narrow question — *can single-function mutation
under blinded evaluation produce measurable, generalizing improvement?* — but its
ceiling was the ceiling of a single pure function.

## Why the pivot

The interesting target is not a better paragraph generator; it is an agent that
can **build software**. That requires the evolving organism to be an arbitrary
multi-file workspace that executes, is tested, and can change its own
architecture — not a fixed six-function template. The three constraints that most
limited v0 were:

1. **One function, one file.** Real capability needs modules, packages, tests,
   data files, and the freedom to restructure.
2. **No execution surface.** v0 evaluated text; it could not run a CLI, start a
   server, persist state, or call a library API. "Distinguish execution from
   claims" was impossible because there was nothing to execute.
3. **No tool use.** The proposer returned a whole function in one model response.
   Substantial coding needs many inspect/edit/test turns.

## What v1 changes

| Concern | v0 (text policy) | v1 (workspace evolution) |
|---|---|---|
| Organism | one mutable function region | arbitrary multi-file workspace tree |
| Unit of change | replace exactly one function | any file create/rewrite/move/delete |
| How the model works | one structured response | many `@llm_behavior` tool turns |
| Manifest | implicit (`REQUIRED_FUNCTIONS`) | workspace-owned `ouroboros.json`, candidate-editable |
| Objective | consumed as a probe prompt | compiled into an executable `ObjectiveContract` |
| Evaluation | pairwise LLM over text probes | hard gates + public/private behavioral tests in clean processes + blinded judge |
| Execution grounding | none (text only) | entrypoint runs, servers start, state persists, APIs import |
| Content identity | `code-sha256-<hash of source>` | `workspace-sha256-<hash of sorted tree>` |
| Capabilities | none | opt-in `--allow-network`, `--allow-pip` with isolation |
| Self-state | `improvement_advice()` return value | mutable `SELF.md` / `MEMORY.md`, promoted only via full evaluation |
| Meta-evolution | not supported | workspace may propose `next_ouroboros.py` (release candidate) |

## What was deliberately preserved

The pivot kept v0's strongest infrastructure and its manager/release discipline —
this is a redesign of the organism and evaluation, not a rewrite of the audit and
governance model:

- **Content-addressed versions** — now `workspace-sha256-<tree hash>` over sorted
  relative paths plus file content hashes.
- **Unique run IDs and immutable bundles** — one directory per invocation, never
  overwritten.
- **`promotion.json` / `result.json` / `lineage.jsonl`** — same handoff and
  audit files, extended for workspaces and release candidates.
- **Hidden validation** — private tests generated separately, sealed by receipt,
  never placed in builder events, prompts, or graph views.
- **Blinded judging** — anonymized artifacts, balanced A/B per case, plus
  absolute rubric anchors; hard-gate failures cannot be overridden by a score.
- **Namespaced events** — the `ouro.v0.*` prefix is retained. Application events
  never reuse framework-reserved names (`patch.proposed/applied/rejected`).
- **Manager-controlled release handoff** — the engine never hot-swaps itself; the
  manager remains the sole release authority, now including engine
  meta-candidates.
- **Deterministic acceptance** — an explicit rule owns promotion; the LLM never
  decides acceptance.

## Backwards compatibility

None is claimed at the CLI or bundle level: v1 is `PROTOCOL_VERSION = 2`,
`BUNDLE_SCHEMA_VERSION = 2`, and the bundle layout changed (`seed_workspace/` and
`final_workspace/` trees instead of `seed.py`/`final.py`). v0 remains runnable
standalone from `experiments/baselines/text_policy_v0.py` for anyone reproducing
the baseline. No v0 run bundles, manager_lab reports, or traces were modified or
deleted — this repository contained none at the time of the pivot (only
`README.md` and `LICENSE`); v0's bundles were always written under the invoking
manager's run root, outside this repository.
