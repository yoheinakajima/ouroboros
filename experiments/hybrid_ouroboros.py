#!/usr/bin/env python3
"""A small, governed, pack-level self-improvement experiment.

The organism is an ActiveGraph event log plus a hash-pinned set of adopted
packs.  An author may propose arbitrary pack source, but deterministic policy
and manager-private behavioral trials are the only release authority.

This file deliberately depends on ``activegraph`` only.  It does not import or
install the separate ``activegraph-packs`` repository.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from activegraph import Event, Graph, Runtime
from activegraph.packs import Pack
from activegraph.packs.manifest import (
    compute_bundle_hash,
    compute_content_hash,
    load_manifest,
    verify_bundle_hash,
    verify_content_hash,
    verify_surface,
)


REQUEST_EVENT = "hybrid.task.requested"
RESULT_EVENT = "hybrid.task.completed"
EVENT_PREFIX = "ouroboros.hybrid"
_NAME = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_VERSION = re.compile(r"^[0-9]+(?:\.[0-9]+)*(?:(?:a|b|rc)[0-9]+)?$")
_SAFE_SUFFIXES = {".py", ".md", ".json", ".txt"}
_DENIED_CALLS = {
    "breakpoint",
    "compile",
    "delattr",
    "eval",
    "exec",
    "getattr",
    "globals",
    "input",
    "locals",
    "open",
    "setattr",
    "vars",
    "__import__",
}
_DENIED_ROOTS = {
    "asyncio",
    "builtins",
    "ctypes",
    "http",
    "importlib",
    "multiprocessing",
    "os",
    "pathlib",
    "requests",
    "shutil",
    "signal",
    "socket",
    "subprocess",
    "sys",
    "urllib",
}


@dataclass(frozen=True)
class Case:
    """One execution-grounded check against the pack event protocol."""

    id: str
    payload: dict[str, Any]
    expected: Any


@dataclass(frozen=True)
class PackDraft:
    """The complete mutation unit returned by an author, including an LLM."""

    name: str
    version: str
    description: str
    files: dict[str, str]
    behaviors: tuple[str, ...]
    object_types: tuple[str, ...] = ()
    relation_types: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()
    settings_schema: str = ""
    capabilities: tuple[dict[str, str], ...] = ()


@dataclass(frozen=True)
class ReleasePolicy:
    """The capability envelope inside which adoption may be autonomous."""

    allowed_imports: frozenset[str] = frozenset(
        {"__future__", "activegraph.packs", "collections", "dataclasses", "json", "math", "re", "statistics", "typing", "unicodedata"}
    )
    allowed_tools: frozenset[str] = frozenset()
    allowed_capabilities: frozenset[str] = frozenset()
    max_files: int = 12
    max_bytes: int = 64_000
    trial_timeout_seconds: float = 10.0


@dataclass(frozen=True)
class EvolutionReport:
    accepted: bool
    reason: str
    name: str
    version: str
    bundle_hash: str
    public_candidate: str
    public_incumbent: str
    private_candidate: str
    private_incumbent: str
    restart_required: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value).encode()).hexdigest()


def _toml_string(value: str) -> str:
    # JSON string escaping is valid TOML basic-string escaping for this data.
    return json.dumps(value, ensure_ascii=False)


def _toml_list(values: Iterable[str]) -> str:
    return "[" + ", ".join(_toml_string(value) for value in values) + "]"


def _manifest_text(draft: PackDraft, content_hash: str) -> str:
    capability_rows = "".join(
        "\n[[surface.capabilities]]\n"
        + "\n".join(f"{key} = {_toml_string(str(value))}" for key, value in cap.items())
        + "\n"
        for cap in draft.capabilities
    )
    return f'''[pack]
name = {_toml_string(draft.name)}
version = {_toml_string(draft.version)}
description = {_toml_string(draft.description)}
license = "Apache-2.0"

[pack.provenance]
authors = ["ouroboros"]
authored_by = "agent"
generator = "hybrid_ouroboros"

[pack.integrity]
content_hash = {_toml_string(content_hash)}

[dependencies]
activegraph = ">=1.10,<2"
python = ">=3.11"
python-deps = []

[dependencies.packs]

[dependencies.optional-packs]

[surface]
object_types = {_toml_list(draft.object_types)}
relation_types = {_toml_list(draft.relation_types)}
behaviors = {_toml_list(draft.behaviors)}
tools = {_toml_list(draft.tools)}
settings_schema = {_toml_string(draft.settings_schema)}
consumes = []
{capability_rows}
[fixtures]
entrypoint = "__init__.py"
deterministic = true
'''


def _safe_relative_path(raw: str) -> PurePosixPath:
    path = PurePosixPath(raw)
    if path.is_absolute() or not path.parts or ".." in path.parts or "manifest.toml" in path.parts:
        raise ValueError(f"unsafe or manager-owned pack path: {raw!r}")
    if any(part.startswith(".") or part == "__pycache__" for part in path.parts):
        raise ValueError(f"hidden/cache pack path rejected: {raw!r}")
    if path.suffix not in _SAFE_SUFFIXES:
        raise ValueError(f"unsupported pack file type: {raw!r}")
    return path


def _materialize_draft(draft: PackDraft, destination: Path) -> str:
    if not _NAME.fullmatch(draft.name):
        raise ValueError(f"invalid pack name: {draft.name!r}")
    if not _VERSION.fullmatch(draft.version):
        raise ValueError(f"invalid pack version: {draft.version!r}")
    if not draft.description.strip():
        raise ValueError("pack description must be nonempty")
    if "__init__.py" not in draft.files:
        raise ValueError("pack draft must contain __init__.py")
    if destination.exists():
        raise FileExistsError(destination)
    destination.mkdir(parents=True)
    for raw_path, text in draft.files.items():
        relative = _safe_relative_path(raw_path)
        target = destination.joinpath(*relative.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    content_hash = compute_content_hash(destination)
    (destination / "manifest.toml").write_text(_manifest_text(draft, content_hash), encoding="utf-8")
    return compute_bundle_hash(destination)


def _static_gate(root: Path, policy: ReleasePolicy) -> list[str]:
    """Reject obvious authority expansion before candidate code is imported."""

    errors: list[str] = []
    files = [path for path in root.rglob("*") if path.is_file()]
    if len(files) > policy.max_files:
        errors.append(f"file budget exceeded: {len(files)} > {policy.max_files}")
    total = sum(path.stat().st_size for path in files)
    if total > policy.max_bytes:
        errors.append(f"byte budget exceeded: {total} > {policy.max_bytes}")
    if any(path.is_symlink() for path in root.rglob("*")):
        errors.append("symlinks are not allowed")

    try:
        manifest = load_manifest(root)
        verify_content_hash(manifest, root)
        if manifest.python_deps or manifest.pack_deps or manifest.optional_pack_deps:
            errors.append("candidate may not introduce package dependencies autonomously")
        undeclared_tools = set(manifest.tools) - set(policy.allowed_tools)
        if undeclared_tools:
            errors.append(f"tools outside capability envelope: {sorted(undeclared_tools)}")
        requested = {f"{item.provider}.{item.capability}" for item in manifest.capabilities}
        outside = requested - set(policy.allowed_capabilities)
        if outside:
            errors.append(f"capabilities outside capability envelope: {sorted(outside)}")
    except Exception as exc:  # Manifest errors are gate evidence, not crashes.
        errors.append(f"manifest rejected: {type(exc).__name__}: {exc}")

    for path in sorted(root.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, UnicodeError, SyntaxError) as exc:
            errors.append(f"{path.name}: cannot parse: {exc}")
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name not in policy.allowed_imports:
                        errors.append(f"{path.name}:{node.lineno}: import {alias.name!r} denied")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if node.level == 0 and module not in policy.allowed_imports:
                    errors.append(f"{path.name}:{node.lineno}: import from {module!r} denied")
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _DENIED_CALLS:
                errors.append(f"{path.name}:{node.lineno}: call {node.func.id!r} denied")
            elif isinstance(node, ast.Name) and node.id in _DENIED_ROOTS:
                errors.append(f"{path.name}:{node.lineno}: name {node.id!r} denied")
            elif isinstance(node, ast.Attribute) and (
                node.attr.startswith("__")
                or (isinstance(node.value, ast.Name) and node.value.id in _DENIED_ROOTS)
            ):
                errors.append(f"{path.name}:{node.lineno}: attribute {node.attr!r} denied")
    return sorted(set(errors))


def _load_pack_bundle(root: Path, bundle_hash: str) -> Pack:
    """Pin, validate, import, and verify exactly one ActiveGraph Pack."""

    verify_bundle_hash(bundle_hash, root)
    manifest = load_manifest(root)
    verify_content_hash(manifest, root)
    module_name = f"_ouroboros_pack_{manifest.name}_{bundle_hash[-12:]}"
    spec = importlib.util.spec_from_file_location(
        module_name,
        root / "__init__.py",
        submodule_search_locations=[str(root)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import pack at {root}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    packs = [value for value in vars(module).values() if isinstance(value, Pack)]
    packs = [pack for pack in packs if pack.name == manifest.name]
    if len(packs) != 1:
        raise RuntimeError(f"expected exactly one Pack named {manifest.name!r}; found {len(packs)}")
    verify_surface(manifest, packs[0])
    return packs[0]


def _emit(graph: Graph, event_type: str, payload: dict[str, Any], *, actor: str) -> Event:
    return graph.emit(
        Event(
            id=graph.ids.event(),
            type=event_type,
            payload=payload,
            actor=actor,
            timestamp=graph.clock.now(),
        )
    )


def _trial_worker(payload: dict[str, Any]) -> dict[str, Any]:
    """Fresh-process trial. Exact cases enter over stdin and are never stored."""

    graph = Graph(run_id="trial_" + uuid.uuid4().hex)
    runtime = Runtime(graph, behaviors=[], budget={"max_events": 2_000, "max_behavior_calls": 500})
    for item in payload["packs"]:
        runtime.load_pack(_load_pack_bundle(Path(item["root"]), item["bundle_hash"]))

    rows: list[dict[str, Any]] = []
    for raw in payload["cases"]:
        request_id = uuid.uuid4().hex
        start = len(graph.events)
        _emit(graph, REQUEST_EVENT, {**raw["payload"], "request_id": request_id}, actor="trial_manager")
        runtime.run_until_idle()
        outputs = [
            event.payload.get("output")
            for event in graph.events[start:]
            if event.type == RESULT_EVENT and event.payload.get("request_id") == request_id
        ]
        passed = len(outputs) == 1 and outputs[0] == raw["expected"]
        rows.append({"id": raw["id"], "passed": passed, "result_count": len(outputs)})
    failures = len(runtime.trace.failures())
    passed = sum(1 for row in rows if row["passed"])
    return {
        "worker_ok": True,
        "passed": passed,
        "total": len(rows),
        "all_passed": passed == len(rows) and failures == 0,
        "behavior_failures": failures,
        "case_results": rows,
        "loaded_packs": [f"{pack.name}@{pack.version}" for pack in runtime.loaded_packs()],
        "event_count": len(graph.events),
    }


def _worker_entry() -> int:
    try:
        result = _trial_worker(json.loads(sys.stdin.read()))
    except Exception as exc:  # The parent treats this as failed evidence.
        result = {"worker_ok": False, "error": f"{type(exc).__name__}: {exc}"}
    print(_canonical({"hybrid_trial": result}), flush=True)
    return 0 if result.get("worker_ok") else 2


def _case_payload(cases: Iterable[Case]) -> list[dict[str, Any]]:
    return [{"id": case.id, "payload": case.payload, "expected": case.expected} for case in cases]


def _run_suite(
    packs: list[dict[str, str]],
    cases: tuple[Case, ...],
    *,
    timeout: float,
    home: Path,
) -> dict[str, Any]:
    env = {key: os.environ[key] for key in ("PATH", "LANG") if key in os.environ}
    env["HOME"] = str(home)
    payload = {"packs": packs, "cases": _case_payload(cases)}
    try:
        process = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "worker"],
            input=_canonical(payload),
            text=True,
            capture_output=True,
            timeout=timeout,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"worker_ok": False, "error": "trial timed out", "passed": 0, "total": len(cases)}
    for line in reversed(process.stdout.splitlines()):
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and "hybrid_trial" in parsed:
            return parsed["hybrid_trial"]
    return {
        "worker_ok": False,
        "error": f"trial exited {process.returncode} without a report",
        "passed": 0,
        "total": len(cases),
    }


def _score(result: dict[str, Any]) -> str:
    return f"{int(result.get('passed', 0))}/{int(result.get('total', 0))}"


class HybridOuroboros:
    """Governed pack adoption around a durable ActiveGraph identity."""

    def __init__(self, root: str | Path, *, policy: ReleasePolicy | None = None) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.policy = policy or ReleasePolicy()
        self.registry_path = self.root / "registry.json"
        self.store_path = self.root / "identity.db"
        self.home = self.root / ".trial_home"
        self.home.mkdir(exist_ok=True)
        self.registry = self._read_registry()
        if self.store_path.exists():
            self.runtime = Runtime.load(str(self.store_path), run_id=self.registry["run_id"], behaviors=[])
        else:
            self.runtime = Runtime(
                Graph(run_id=self.registry["run_id"]),
                behaviors=[],
                persist_to=str(self.store_path),
            )
        self._record(f"{EVENT_PREFIX}.booted", {"adopted_count": len(self.registry["adopted"])})
        for entry in self.registry["adopted"]:
            pack = _load_pack_bundle(self.root / entry["path"], entry["bundle_hash"])
            self.runtime.load_pack(pack)

    def _read_registry(self) -> dict[str, Any]:
        if self.registry_path.exists():
            data = json.loads(self.registry_path.read_text(encoding="utf-8"))
            if not isinstance(data.get("adopted"), list) or not data.get("run_id"):
                raise ValueError("invalid hybrid registry")
            return data
        data = {"schema": 1, "run_id": "ouroboros_" + uuid.uuid4().hex, "adopted": []}
        self._write_registry(data)
        return data

    def _write_registry(self, data: dict[str, Any]) -> None:
        temporary = self.root / (".registry-" + uuid.uuid4().hex + ".json")
        temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(self.registry_path)

    def _record(self, event_type: str, payload: dict[str, Any]) -> None:
        _emit(self.runtime.graph, event_type, payload, actor="ouroboros")

    def _pack_specs(self, entries: list[dict[str, Any]]) -> list[dict[str, str]]:
        return [
            {"root": str((self.root / item["path"]).resolve()), "bundle_hash": item["bundle_hash"]}
            for item in entries
        ]

    def evolve(
        self,
        *,
        objective: str,
        draft: PackDraft,
        public_cases: Iterable[Case],
        private_cases: Iterable[Case],
    ) -> EvolutionReport:
        """Trial one whole-pack proposal and adopt it only on a strict win."""

        public = tuple(public_cases)
        private = tuple(private_cases)
        if not objective.strip() or not public or not private:
            raise ValueError("objective and nonempty public/private suites are required")
        if len({case.id for case in public + private}) != len(public) + len(private):
            raise ValueError("test case ids must be unique")

        proposal_id = uuid.uuid4().hex
        candidate_root = self.root / "candidates" / proposal_id
        self._record(f"{EVENT_PREFIX}.gap_observed", {"objective": objective, "proposal_id": proposal_id})
        try:
            bundle_hash = _materialize_draft(draft, candidate_root)
        except Exception as exc:
            return self._reject(draft, "materialization rejected", "", [f"{type(exc).__name__}: {exc}"])
        self._record(
            f"{EVENT_PREFIX}.pack_proposed",
            {"proposal_id": proposal_id, "name": draft.name, "version": draft.version, "bundle_hash": bundle_hash},
        )

        gate_errors = _static_gate(candidate_root, self.policy)
        self._record(
            f"{EVENT_PREFIX}.gate_checked",
            {"proposal_id": proposal_id, "accepted": not gate_errors, "error_count": len(gate_errors)},
        )
        if gate_errors:
            return self._reject(draft, "static policy rejected proposal", bundle_hash, gate_errors)

        incumbent_entries = list(self.registry["adopted"])
        candidate_entries = [entry for entry in incumbent_entries if entry["name"] != draft.name]
        candidate_specs = self._pack_specs(candidate_entries) + [
            {"root": str(candidate_root.resolve()), "bundle_hash": bundle_hash}
        ]
        incumbent_specs = self._pack_specs(incumbent_entries)

        incumbent_public = _run_suite(
            incumbent_specs, public, timeout=self.policy.trial_timeout_seconds, home=self.home
        )
        candidate_public = _run_suite(
            candidate_specs, public, timeout=self.policy.trial_timeout_seconds, home=self.home
        )
        incumbent_private = _run_suite(
            incumbent_specs, private, timeout=self.policy.trial_timeout_seconds, home=self.home
        )
        candidate_private = _run_suite(
            candidate_specs, private, timeout=self.policy.trial_timeout_seconds, home=self.home
        )

        self._record_trial("public", public, candidate_public, incumbent_public, proposal_id)
        self._record_trial("private", private, candidate_private, incumbent_private, proposal_id)
        reports = (incumbent_public, candidate_public, incumbent_private, candidate_private)
        workers_ok = all(report.get("worker_ok") for report in reports)
        candidate_clean = bool(candidate_public.get("all_passed")) and bool(candidate_private.get("all_passed"))
        no_regression = (
            candidate_public.get("passed", 0) >= incumbent_public.get("passed", 0)
            and candidate_private.get("passed", 0) >= incumbent_private.get("passed", 0)
        )
        improvement = (
            candidate_public.get("passed", 0) + candidate_private.get("passed", 0)
            > incumbent_public.get("passed", 0) + incumbent_private.get("passed", 0)
        )
        if not workers_ok:
            return self._reject(
                draft,
                "isolated trial failed",
                bundle_hash,
                [],
                scores=(candidate_public, incumbent_public, candidate_private, incumbent_private),
            )
        if not candidate_clean:
            return self._reject(
                draft,
                "candidate did not pass every public and private case",
                bundle_hash,
                [],
                scores=(candidate_public, incumbent_public, candidate_private, incumbent_private),
            )
        if not no_regression:
            return self._reject(
                draft,
                "candidate regressed against the adopted pack set",
                bundle_hash,
                [],
                scores=(candidate_public, incumbent_public, candidate_private, incumbent_private),
            )
        if not improvement:
            return self._reject(
                draft,
                "behavioral no-op: candidate did not improve on the incumbent",
                bundle_hash,
                [],
                scores=(candidate_public, incumbent_public, candidate_private, incumbent_private),
            )

        adopted_rel = Path("adopted") / draft.name / f"{draft.version}-{bundle_hash[-12:]}"
        adopted_root = self.root / adopted_rel
        adopted_root.parent.mkdir(parents=True, exist_ok=True)
        if adopted_root.exists():
            verify_bundle_hash(bundle_hash, adopted_root)
        else:
            shutil.copytree(candidate_root, adopted_root)
        verify_bundle_hash(bundle_hash, adopted_root)
        entry = {
            "name": draft.name,
            "version": draft.version,
            "bundle_hash": bundle_hash,
            "path": adopted_rel.as_posix(),
        }
        self.registry["adopted"] = [item for item in incumbent_entries if item["name"] != draft.name] + [entry]
        self._write_registry(self.registry)
        self._record(
            f"{EVENT_PREFIX}.pack_adopted",
            {
                **entry,
                "proposal_id": proposal_id,
                "public_suite": _digest(_case_payload(public)),
                "private_suite": _digest(_case_payload(private)),
            },
        )
        return EvolutionReport(
            accepted=True,
            reason="strict execution-grounded improvement adopted",
            name=draft.name,
            version=draft.version,
            bundle_hash=bundle_hash,
            public_candidate=_score(candidate_public),
            public_incumbent=_score(incumbent_public),
            private_candidate=_score(candidate_private),
            private_incumbent=_score(incumbent_private),
            restart_required=True,
        )

    def _record_trial(
        self,
        split: str,
        cases: tuple[Case, ...],
        candidate: dict[str, Any],
        incumbent: dict[str, Any],
        proposal_id: str,
    ) -> None:
        self._record(
            f"{EVENT_PREFIX}.trial_completed",
            {
                "proposal_id": proposal_id,
                "split": split,
                "suite_hash": _digest(_case_payload(cases)),
                "case_count": len(cases),
                "candidate_score": _score(candidate),
                "incumbent_score": _score(incumbent),
                "candidate_worker_ok": bool(candidate.get("worker_ok")),
                "incumbent_worker_ok": bool(incumbent.get("worker_ok")),
            },
        )

    def _reject(
        self,
        draft: PackDraft,
        reason: str,
        bundle_hash: str,
        errors: list[str],
        *,
        scores: tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]] | None = None,
    ) -> EvolutionReport:
        self._record(
            f"{EVENT_PREFIX}.pack_rejected",
            {
                "name": draft.name,
                "version": draft.version,
                "bundle_hash": bundle_hash,
                "reason": reason,
                "gate_errors": errors[:20],
            },
        )
        candidate_public, incumbent_public, candidate_private, incumbent_private = scores or ({}, {}, {}, {})
        return EvolutionReport(
            accepted=False,
            reason=reason,
            name=draft.name,
            version=draft.version,
            bundle_hash=bundle_hash,
            public_candidate=_score(candidate_public),
            public_incumbent=_score(incumbent_public),
            private_candidate=_score(candidate_private),
            private_incumbent=_score(incumbent_private),
            restart_required=False,
        )

    def restart(self) -> "HybridOuroboros":
        """Rebuild the same identity from its event log and adopted packs."""

        return type(self)(self.root, policy=self.policy)

    def invoke(self, payload: dict[str, Any], *, actor: str = "user") -> Any:
        """Exercise the currently loaded capability set through ActiveGraph."""

        request_id = uuid.uuid4().hex
        start = len(self.runtime.graph.events)
        _emit(self.runtime.graph, REQUEST_EVENT, {**payload, "request_id": request_id}, actor=actor)
        self.runtime.run_until_idle()
        outputs = [
            event.payload.get("output")
            for event in self.runtime.graph.events[start:]
            if event.type == RESULT_EVENT and event.payload.get("request_id") == request_id
        ]
        if len(outputs) != 1:
            raise RuntimeError(f"expected one capability result, received {len(outputs)}")
        return outputs[0]

    def identity(self) -> dict[str, Any]:
        return {
            "run_id": self.runtime.run_id,
            "event_count": len(self.runtime.graph.events),
            "adopted": [f"{item['name']}@{item['version']}" for item in self.registry["adopted"]],
            "loaded": [f"{pack.name}@{pack.version}" for pack in self.runtime.loaded_packs()],
        }


def demo_draft() -> PackDraft:
    source = '''from __future__ import annotations

import re

from activegraph.packs import Pack, behavior


@behavior(name="slugify", on=["hybrid.task.requested"])
def slugify(event, graph, ctx):
    if event.payload.get("operation") != "slugify":
        return
    value = str(event.payload.get("input", "")).strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    graph.emit(
        "hybrid.task.completed",
        {"request_id": event.payload["request_id"], "output": value},
    )


PACK = Pack(
    name="slugify_capability",
    version="1.0.0",
    description="Adds a reusable slugification behavior.",
    behaviors=(slugify,),
)
'''
    return PackDraft(
        name="slugify_capability",
        version="1.0.0",
        description="Adds a reusable slugification behavior.",
        files={"__init__.py": source},
        behaviors=("slugify",),
    )


def _demo(store: Path) -> int:
    organism = HybridOuroboros(store)
    report = organism.evolve(
        objective="Learn to turn arbitrary labels into stable URL slugs",
        draft=demo_draft(),
        public_cases=(
            Case("public-basic", {"operation": "slugify", "input": "Hello World"}, "hello-world"),
            Case("public-punctuation", {"operation": "slugify", "input": "Agents, Evolve!"}, "agents-evolve"),
        ),
        private_cases=(
            Case("private-spacing", {"operation": "slugify", "input": "  Recursive   Systems  "}, "recursive-systems"),
            Case("private-symbols", {"operation": "slugify", "input": "Powerful / Simple"}, "powerful-simple"),
        ),
    )
    result: dict[str, Any] = {"evolution": report.to_dict()}
    if report.accepted:
        restarted = organism.restart()
        result["after_restart"] = restarted.identity()
        result["transfer_output"] = restarted.invoke(
            {"operation": "slugify", "input": "Evolve / Forever"}, actor="demo"
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if report.accepted else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("demo", "worker"))
    parser.add_argument("--store", type=Path)
    args = parser.parse_args(argv)
    if args.command == "worker":
        return _worker_entry()
    if args.store is None:
        parser.error("demo requires --store PATH")
    return _demo(args.store)


if __name__ == "__main__":
    raise SystemExit(main())
