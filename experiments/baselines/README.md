# Historical baselines

## text_policy_v0.py

The version-0 Ouroboros engine, preserved verbatim as a historical baseline
(sha256 `6cb2790dfb8aeda193694ce43e22e4796d986f832323c987520c70fd035213e0`).

v0 evolved a deterministic, import-free *text policy*: one mutable region of
six required functions, one function replaced per candidate, judged by an
output-blind pairwise LLM over visible development probes and hidden holdout
probes, with a deterministic acceptance rule.

It was retired as the canonical architecture on 2026-07-16 in favor of the
workspace-evolution engine at the repository root (see `docs/MIGRATION.md`).
Its strongest infrastructure — content-addressed versions, unique run IDs,
immutable bundles, `promotion.json` / `result.json` / `lineage.jsonl`, hidden
validation, blinded judging, `ouro.v0.*` namespaced events, and
manager-controlled release handoff — was carried forward into the new engine.

This snapshot still runs standalone:

    pip install "activegraph[anthropic]"
    export ANTHROPIC_API_KEY="..."
    python experiments/baselines/text_policy_v0.py "objective" --generations 3

Note on manager_lab evidence: this repository contains no manager_lab
reports, traces, or run bundles (it held only `README.md` and `LICENSE`
before the pivot). Runs of v0 recorded their bundles under the invoking
manager's run root (default `.ouroboros/runs/`), outside this repository;
nothing here was deleted or rewritten.
