# Migration to the minimal ActiveGraph organism

Ouroboros has explored three mutable units:

| Generation | Mutable unit | Main limitation |
|---|---|---|
| Text-policy prototype | One marked Python function | Could not grow into general software |
| Workspace evolution manager | Arbitrary generated project tree | Large evaluator dominated the idea; outputs imitated agents without retaining live model intelligence |
| Minimal ActiveGraph organism | Procedures plus promoted deterministic capabilities | Pure local capabilities only; production governance intentionally deferred |

The canonical `ouroboros.py` now uses ActiveGraph directly and has no
`activegraph-packs` dependency. The organism is the persistent event graph,
model actor, evaluated procedures, promoted capability source, and host tool
boundary—not a generated workspace.

## What remains from the workspace engine

- Strong model/tool loops for real coding work
- Provider credentials owned only by the host
- Execution-grounded checks
- Content-addressed artifacts
- Cost and trace evidence
- Exact source retention for rejected and promoted candidates

## What ActiveGraph now owns

- Event persistence and restart
- Model and tool trace pairs
- Budgets and behavior failures
- Forked subprocess trials
- Manifest and bundle hashes
- Structural dry-run and promotion

## Compatibility

Prior raw run bundles remain local under ignored `artifacts/` and are not
consumed by the new organism. Curated evidence lives under `evidence/`. The
exact recovered workspace v1.2 source is under `recovered/v1.2/`; the
historical text mutator remains under `experiments/baselines/`. New Minimal-v2
state lives by default in:

```text
.ouroboros/organism/
  organism.json
  trace.sqlite
  mutations/
```

There is no automatic migration of earlier workspace histories because their
ontology and promotion unit are different. Importing selected successful
procedures later should be an explicit, auditable graph operation.
