# Hybrid Ouroboros experiment

This is the first pack-level hybrid, kept separate from `ouroboros.py` so the
v1.2 evaluator remains an independent reference.

The mutation unit is a complete ActiveGraph `Pack`. The organism's durable
identity is:

1. an ActiveGraph event log (`identity.db`), and
2. a registry of hash-pinned adopted packs (`registry.json`).

The evolution loop is:

```text
objective -> proposed pack -> static authority gate
          -> fresh-process public/private trials
          -> deterministic release decision
          -> hash-pinned adoption -> restart -> transfer task
```

The implementation imports only `activegraph`; the separate
`activegraph-packs` repository is neither imported nor installed. Candidate
behaviors use the pack-scoped decorators in `activegraph.packs`, and every
load/adoption/task is visible in the ActiveGraph trace.

Run the deterministic demo with any environment containing the requirement in
the repository's `requirements.txt`:

```bash
python experiments/hybrid_ouroboros.py demo --store /tmp/ouroboros-hybrid-demo
```

The expected result is a 4/4 strict win, adoption of
`slugify_capability@1.0.0`, reconstruction from the event log, and an unseen
transfer result of `evolve-forever`.

Run its tests:

```bash
python -m unittest -v tests.test_hybrid_ouroboros
```

## What this proves

- A whole behavior pack can be the unit of recursive improvement.
- Public and manager-private execution can govern autonomous adoption.
- The trialed bytes and adopted bytes share the same external bundle hash.
- The changed capability set survives a genuinely fresh runtime.
- Requests for imports, tools, dependencies, or capabilities outside the
  configured envelope fail before candidate import.

## What this does not prove yet

The demo author is scripted, not an LLM. The `PackDraft` boundary is the seam
for an LLM author, while deterministic code remains release authority. The
fresh process and AST gate are accident-containment mechanisms, not a hostile
code sandbox; production execution still needs container/syscall/network
confinement. Qualitative independent judging and the richer v1.2 evaluator
matrix are also not wired into this experiment yet.
