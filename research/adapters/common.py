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
            context = self._render_context(self.retained_state)  # type: ignore[arg-type]
            exposed = True
        elif arm == "sham_improvement_control":
            if self.sham_context is None or not self.sham_context.is_file():
                raise ValueError("sham control requires a frozen unrelated-context file")
            context = self.sham_context.read_text(encoding="utf-8")
            exposed = True
        return PreparedAttempt(
            approach_id=self.approach_id,
            arm=arm,
            seed=seed,
            task=task,
            retained_state_hash=state_hash,
            retained_context=context,
            retained_state_present=state_present,
            retained_state_exposed=exposed,
        )

    def run(self, prepared: PreparedAttempt, broker: AuthorityBroker) -> AgentOutcome:
        if prepared.approach_id != self.approach_id:
            raise ValueError("prepared attempt belongs to a different architecture")
        return self.agent.run(prepared, broker)

    def _render_context(self, root: Path) -> str:
        raise NotImplementedError


class WorkspaceV12Adapter(StateAdapter):
    approach_id = "workspace_v1_2"
    mutation_unit = "arbitrary workspace tree"

    def _render_context(self, root: Path) -> str:
        sections: list[str] = []
        workspace = root / "final_workspace" if (root / "final_workspace").is_dir() else root
        for relative in ("SELF.md", "MEMORY.md"):
            path = workspace / relative
            if path.is_file():
                sections.append(f"## {relative}\n{path.read_text(encoding='utf-8')[:24_000]}")
        files = [path.relative_to(workspace).as_posix() for path in sorted(workspace.rglob("*")) if path.is_file()]
        sections.append("## Retained workspace files\n" + "\n".join(files[:500]))
        return "\n\n".join(sections)[:64_000]


class MinimalV2Adapter(StateAdapter):
    approach_id = "minimal_v2"
    mutation_unit = "evaluated procedure or pure deterministic capability"

    def _render_context(self, root: Path) -> str:
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

    def _render_context(self, root: Path) -> str:
        registry_path = root / "registry.json"
        if not registry_path.is_file():
            raise FileNotFoundError("Hybrid retained state requires registry.json")
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        rows = []
        for entry in registry.get("adopted", []):
            pack_root = (root / entry["path"]).resolve()
            if root != pack_root and root not in pack_root.parents:
                raise ValueError("Hybrid registry path escapes retained state")
            manifest = (pack_root / "manifest.toml").read_text(encoding="utf-8")
            rows.append(
                {
                    "name": entry["name"],
                    "version": entry["version"],
                    "bundle_hash": entry["bundle_hash"],
                    "manifest": manifest,
                }
            )
        return json.dumps({"adopted_pack_set": rows}, indent=2, sort_keys=True)[:64_000]
