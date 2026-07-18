"""Comparable architecture-state adapters over the one shared brokered agent."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from research.adapters.base import (
    AdapterDescriptor,
    AgentOutcome,
    ApproachAdapter,
    PreparedAttempt,
)
from research.agent import BrokeredRepoAgent
from research.broker import AuthorityBroker

ARMS = {"cold", "evolved", "cold_ablation", "sham_improvement_control", "native_evolved"}
CONTEXT_LIMIT = 64_000
CONTEXT_FILE_LIMIT = 16_000
DENIED_CONTEXT_PARTS = {
    ".git",
    ".env",
    "grader",
    "hidden",
    "manager",
    "private",
    "secret",
    "secrets",
    "__pycache__",
}


def _hash_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"retained state may not contain symlinks: {path}")
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            digest.update(relative.encode())
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def _safe_text_files(root: Path) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if relative.as_posix() == "evolution_manifest.json":
            continue
        if any(part.lower() in DENIED_CONTEXT_PARTS for part in relative.parts):
            continue
        raw = path.read_bytes()[: CONTEXT_FILE_LIMIT + 1]
        if b"\0" in raw:
            continue
        try:
            value = raw[:CONTEXT_FILE_LIMIT].decode("utf-8")
        except UnicodeDecodeError:
            continue
        if len(raw) > CONTEXT_FILE_LIMIT:
            value += "\n[truncated]"
        rows.append((relative.as_posix(), value))
    return rows


def _bounded_sections(sections: list[str]) -> str:
    output = ""
    for section in sections:
        remaining = CONTEXT_LIMIT - len(output)
        if remaining <= 0:
            break
        addition = ("\n\n" if output else "") + section
        output += addition[:remaining]
    return output


class StateAdapter(ApproachAdapter):
    approach_id = ""
    mutation_unit = ""

    def __init__(
        self,
        *,
        model: str,
        retained_state: str | Path | None = None,
        sham_context: str | Path | None = None,
    ) -> None:
        self.agent = BrokeredRepoAgent(model=model)
        self.retained_state = Path(retained_state).resolve() if retained_state else None
        self.sham_context = Path(sham_context).resolve() if sham_context else None

    @property
    def descriptor(self) -> AdapterDescriptor:
        return AdapterDescriptor(
            approach_id=self.approach_id,
            mutation_unit=self.mutation_unit,
            supports_cold_arm=True,
            supports_evolved_arm=True,
            supports_sham_control=True,
            broker_protocol_version="1.0",
        )

    def prepare(self, *, task: dict[str, Any], arm: str, seed: int) -> PreparedAttempt:
        if arm not in ARMS:
            raise ValueError(f"unsupported benchmark arm: {arm}")
        state_present = self.retained_state is not None and arm in {
            "evolved",
            "native_evolved",
            "cold_ablation",
        }
        state_hash = None
        context = ""
        exposed = False
        if state_present:
            assert self.retained_state is not None
            if not self.retained_state.is_dir():
                raise FileNotFoundError(self.retained_state)
            state_hash = _hash_tree(self.retained_state)
        if arm in {"evolved", "native_evolved"}:
            if not state_present:
                raise ValueError(f"{arm} requires a retained architecture state")
            context = self._render_context(self.retained_state, task)  # type: ignore[arg-type]
            exposed = True
        elif arm == "sham_improvement_control":
            if self.sham_context is None or not self.sham_context.is_file():
                raise ValueError("sham control requires a frozen unrelated-context file")
            if self.sham_context.is_symlink():
                raise ValueError("sham control may not be a symlink")
            context = self.sham_context.read_text(encoding="utf-8")[:CONTEXT_LIMIT]
            exposed = True
        context_bytes = context.encode("utf-8")
        return PreparedAttempt(
            approach_id=self.approach_id,
            arm=arm,
            seed=seed,
            task=task,
            retained_state_hash=state_hash,
            retained_context=context,
            retained_state_present=state_present,
            retained_state_exposed=exposed,
            exposed_context_sha256=("sha256:" + hashlib.sha256(context_bytes).hexdigest() if exposed else None),
            exposed_context_bytes=len(context_bytes),
        )

    def run(self, prepared: PreparedAttempt, broker: AuthorityBroker) -> AgentOutcome:
        if prepared.approach_id != self.approach_id:
            raise ValueError("prepared attempt belongs to a different architecture")
        return self.agent.run(prepared, broker)

    def _render_context(self, root: Path, task: dict[str, Any]) -> str:
        raise NotImplementedError


class WorkspaceV12Adapter(StateAdapter):
    approach_id = "workspace_v1_2"
    mutation_unit = "arbitrary workspace tree"

    def _render_context(self, root: Path, task: dict[str, Any]) -> str:
        sections: list[str] = []
        workspace = root / "final_workspace" if (root / "final_workspace").is_dir() else root
        rows = _safe_text_files(workspace)
        priority = {"SELF.md": 0, "MEMORY.md": 1}
        rows.sort(key=lambda row: (priority.get(row[0], 2), row[0]))
        sections.extend(f"## Retained workspace file: {relative}\n{text}" for relative, text in rows)
        return _bounded_sections(sections)


class MinimalV2Adapter(StateAdapter):
    approach_id = "minimal_v2"
    mutation_unit = "evaluated procedure or pure deterministic capability"

    def _render_context(self, root: Path, task: dict[str, Any]) -> str:
        export = root / "state_export.json"
        if not export.is_file():
            raise FileNotFoundError("minimal retained state requires state_export.json")
        value = json.loads(export.read_text(encoding="utf-8"))
        allowed = {
            "procedures": value.get("procedures", []),
            "capabilities": value.get("capabilities", []),
            "evidence_receipts": value.get("evidence_receipts", []),
        }
        return json.dumps(allowed, indent=2, sort_keys=True, ensure_ascii=False)[:64_000]


class HybridPacksAdapter(StateAdapter):
    approach_id = "hybrid_packs"
    mutation_unit = "atomic set of complete hash-pinned ActiveGraph Packs"

    def _render_context(self, root: Path, task: dict[str, Any]) -> str:
        registry_path = root / "registry.json"
        if not registry_path.is_file():
            raise FileNotFoundError("Hybrid retained state requires registry.json")
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        rows = []
        for entry in registry.get("adopted", []):
            pack_root = (root / entry["path"]).resolve()
            if root != pack_root and root not in pack_root.parents:
                raise ValueError("Hybrid registry path escapes retained state")
            rows.append(
                {
                    "name": entry["name"],
                    "version": entry["version"],
                    "bundle_hash": entry["bundle_hash"],
                    "files": [{"path": relative, "text": text} for relative, text in _safe_text_files(pack_root)],
                }
            )
        context: dict[str, Any] = {}
        interface = registry.get("research_context_interface")
        if interface:
            expected = {
                "schema_version": 1,
                "request_event": "hybrid.task.requested",
                "result_event": "hybrid.task.completed",
                "operation": "development_guidance",
                "query_field": "query",
            }
            if interface != expected:
                raise ValueError("Hybrid retained state has an unknown research context interface")
            from experiments.hybrid_ouroboros import invoke_pack_set_isolated

            invocation = invoke_pack_set_isolated(
                root,
                {
                    "operation": interface["operation"],
                    interface["query_field"]: str(task.get("prompt", "")),
                    "limit": 3,
                },
            )
            context["activegraph_query_output"] = invocation["output"]
            context["activegraph_query_receipt"] = {
                "loaded_packs": invocation["loaded_packs"],
                "credentials_forwarded": invocation["credentials_forwarded"],
                "behavior_failures": invocation["behavior_failures"],
            }
            context["adopted_pack_set"] = [
                {"name": row["name"], "version": row["version"], "bundle_hash": row["bundle_hash"]}
                for row in rows
            ]
        else:
            context["adopted_pack_set"] = rows
        return json.dumps(context, indent=2, sort_keys=True)[:CONTEXT_LIMIT]
