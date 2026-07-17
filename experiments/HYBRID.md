# Hybrid Ouroboros experiment

This is the pack-level hybrid, kept separate from `ouroboros.py` so Minimal v2
and recovered workspace v1.2 remain independent references.

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

Run the real documentation-grounded author with a recorded task:

```bash
python -m research.hybrid_author \
  --task research/tasks/dependency_release_planner.json \
  --run-dir artifacts/research-runs/dependency-planner \
  --docs-root /path/to/activegraph/docs \
  --model gpt-5.6-sol
```

The LLM proposes complete source from a hash-recorded ActiveGraph documentation
snapshot. It does not possess release authority or receive manager-private
cases. See `research/RESULTS.md` for the three successful live pilots and their
costs.

## What this proves

- A whole behavior pack can be the unit of recursive improvement.
- Public and manager-private execution can govern autonomous adoption.
- The trialed bytes and adopted bytes share the same external bundle hash.
- The changed capability set survives a genuinely fresh runtime.
- Requests for imports, tools, dependencies, or capabilities outside the
  configured envelope fail before candidate import.

## What this does not prove yet

The three one-shot pilots are too easy to establish reliability or comparative
advantage. No acquired Pack has yet improved later Pack authorship, and the
author has no general brokered repository/tool surface. The fresh process and
AST gate are accident-containment mechanisms, not a hostile-code sandbox;
production evaluation still needs container/syscall/network confinement. The
hard benchmark remains locked until those gaps are closed.
