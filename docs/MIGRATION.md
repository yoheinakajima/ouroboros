# Migration: text-policy mutation to workspace evolution

The historical v0 engine evolved one existing Python function inside a marked
text-policy region. It provided useful manager-facing infrastructure—unique
runs, content identity, hidden probes, blinded judging, immutable evidence, and
`promotion.json`—but its organism could not grow beyond a single constrained
text transformer.

The canonical root `ouroboros.py` now treats an arbitrary workspace tree as the
organism. This is a redesign, not an incremental extension of the mutable
function region.

## What changed

| Area | Historical v0 | Workspace engine |
|---|---|---|
| Mutable unit | One existing function | Any files and directories |
| Seed | Mutable region in the engine | Embedded `agent.py`, manifest, self, memory |
| Builder output | One replacement function | Multi-turn runtime-owned tool session |
| Architecture | Fixed text policy | Candidate-controlled manifest and entrypoint |
| Evaluation | Text probes | Startup/protocol gates, commands, imports, HTTP, files, sealed tests, blinded judge |
| Identity | Source SHA-256 | Canonical sorted tree/content SHA-256 |
| Self-improvement | Advice inside policy | Promoted `SELF.md`/`MEMORY.md`; manager-only `next_ouroboros.py` |

## What was retained

- ActiveGraph as the authoritative event log;
- unique run IDs and one `trace.sqlite` per invocation;
- exact lineage plus content-addressed versions;
- public development evidence and sealed validation;
- blinded qualitative comparison and deterministic acceptance;
- complete finalization on success and failure;
- `promotion.json` as a handoff, never an automatic source rewrite.

Application events remain under `ouro.v0.*` so the historical and new runs can
coexist without using framework-reserved lifecycle names. The graph projection
now models `objective_contract`, `workspace_version`, `file_blob`,
`build_session`, `file_change`, `command_run`, test suites/results,
`evaluation`, `history_summary`, `release_candidate`, and `run_summary`.

## Compatibility and release handling

Existing manager code should consume `result.json` and `promotion.json` as
before, but must expect `final_workspace/` rather than `final.py`. Cross-run
identity is now `final_content_id` with the
`workspace-sha256-<canonical-tree-digest>` form. The old implementation remains
unchanged at `experiments/baselines/text_policy_v0.py` (SHA-256
`6cb2790dfb8aeda193694ce43e22e4796d986f832323c987520c70fd035213e0`) so old
manager reports and traces retain a reproducible engine snapshot.

A produced `next_ouroboros.py` is only a release candidate. A manager should run
the full deterministic and live suite, inspect its bundle, and promote it in a
later version-control commit. The currently executing kernel is never replaced
in place.
