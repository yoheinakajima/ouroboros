#!/usr/bin/env python3
"""Ouroboros: a small, pack-free self-improving agent on ActiveGraph.

The visible organism is one program and one event-sourced graph.  A generic
model actor uses a handful of workspace tools, evaluated successes become
reusable procedures, and pure deterministic capabilities can be authored from
examples, tested in a hash-pinned ActiveGraph fork, and promoted.

``activegraph-packs`` is deliberately not a dependency.  ActiveGraph's native
``Pack`` value is used only as the hidden mutation ABI because it supplies the
manifest, isolated-trial, diff, disable, and promotion contracts.

This is an accident-containment demo, not a hostile-code sandbox.  Commands
and promoted mutations run with a scrubbed environment and strict static
gates, but OS-level syscall/network confinement remains the host's job.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Literal

from activegraph import Frame, Graph, Pack, Runtime, clear_registry, llm_behavior, tool
from activegraph.llm import AnthropicProvider, LLMResponse, OpenAIProvider
from activegraph.packs.manifest import (
    compute_bundle_hash,
    compute_content_hash,
    load_manifest,
    verify_bundle_hash,
    verify_surface,
)
from activegraph.sandbox import PackSource, TrialLimits, run_forked_trial
from activegraph.tools.decorators import clear_tool_registry
from pydantic import BaseModel, Field

ENGINE_VERSION = "2.0.0-minimal"
DEFAULT_STATE_DIR = Path(".ouroboros") / "organism"
DEFAULT_MODEL = "gpt-5.6-sol"
MAX_FILE_CHARS = 300_000
MAX_TOOL_OUTPUT_CHARS = 20_000
MAX_MUTATION_SOURCE_CHARS = 12_000
NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,48}$")
PRIVATE_FILE_NAMES = {".netrc", ".npmrc", ".pypirc", "credentials.json"}


# ---------------------------------------------------------------------------
# Typed model and tool boundaries
# ---------------------------------------------------------------------------


class ToolResult(BaseModel):
    ok: bool
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


class ListFilesInput(BaseModel):
    path: str = "."


class ReadFileInput(BaseModel):
    path: str


class WriteFileInput(BaseModel):
    path: str
    content: str


class ReplaceFileInput(BaseModel):
    path: str
    old: str
    new: str
    expected_occurrences: int = Field(default=1, ge=1, le=100)


class RunCommandInput(BaseModel):
    argv: list[str]
    timeout_seconds: int = Field(default=60, ge=1, le=180)


class InvokeCapabilityInput(BaseModel):
    capability: str
    payload: dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    status: Literal["completed", "blocked"]
    summary: str
    evidence: list[str] = Field(default_factory=list)
    procedure_name: str = ""
    procedure_trigger_terms: list[str] = Field(default_factory=list)
    procedure_steps: list[str] = Field(default_factory=list)


class MutationDraft(BaseModel):
    capability_name: str
    description: str
    implementation_source: str
    rationale: str


class ExampleCase(BaseModel):
    input: dict[str, Any]
    expected: dict[str, Any]


@dataclass
class Capability:
    name: str
    description: str
    pack_name: str
    root: Path
    bundle_hash: str
    implementation: Callable[[dict[str, Any]], dict[str, Any]]


@dataclass
class Config:
    workspace: Path
    state_dir: Path
    provider: str = "openai"
    model: str = DEFAULT_MODEL
    max_cost_usd: float | None = None
    max_tool_turns: int = 16
    command_timeout: int = 90
    use_procedures: bool = True


# ---------------------------------------------------------------------------
# Small utilities
# ---------------------------------------------------------------------------


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_env_file(path: Path) -> list[str]:
    """Load a tiny dotenv subset without adding a dependency.

    Existing process values win.  The return value contains names only so
    callers can report configuration without ever printing credentials.
    """

    loaded: list[str] = []
    if not path.is_file():
        return loaded
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        name, separator, value = line.partition("=")
        name = name.strip()
        if not separator or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if name not in os.environ:
            os.environ[name] = value
            loaded.append(name)
    return loaded


def graph_objects(runtime: Runtime, object_type: str) -> list[Any]:
    return [item for item in runtime.graph.all_objects() if item.type == object_type]


def latest_object(runtime: Runtime, object_type: str, *, after: int = 0) -> Any | None:
    items = graph_objects(runtime, object_type)
    return items[-1] if len(items) > after else None


def import_pack_root(root: Path, bundle_hash: str) -> tuple[Pack, Any]:
    """Verify exact bytes, import one generated pack, and verify its surface."""

    verify_bundle_hash(bundle_hash, root)
    manifest = load_manifest(root)
    module_name = f"_ouroboros_{manifest.name}_{bundle_hash[-12:]}"
    existing = sys.modules.get(module_name)
    if existing is not None:
        packs = [value for value in vars(existing).values() if isinstance(value, Pack)]
        if len(packs) != 1:
            raise RuntimeError(f"cached mutation {manifest.name!r} has an invalid Pack surface")
        verify_surface(manifest, packs[0])
        return packs[0], existing
    spec = importlib.util.spec_from_file_location(
        module_name,
        root / "__init__.py",
        submodule_search_locations=[str(root)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import mutation at {root}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    packs = [value for value in vars(module).values() if isinstance(value, Pack)]
    packs = [pack for pack in packs if pack.name == manifest.name]
    if len(packs) != 1:
        raise RuntimeError(f"mutation must expose exactly one Pack named {manifest.name!r}")
    verify_surface(manifest, packs[0])
    return packs[0], module


# ---------------------------------------------------------------------------
# Provider compatibility
# ---------------------------------------------------------------------------


class _OpenAICompletionsProxy:
    def __init__(self, target: Any) -> None:
        self._target = target

    def create(self, **kwargs: Any) -> Any:
        model = str(kwargs.get("model", ""))
        if kwargs.get("tools") and model.startswith("gpt-5.6"):
            kwargs.setdefault("reasoning_effort", "none")
        return self._target.create(**kwargs)


class _OpenAIChatProxy:
    def __init__(self, target: Any) -> None:
        self._target = target
        self.completions = _OpenAICompletionsProxy(target.completions)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._target, name)


class _OpenAIClientProxy:
    def __init__(self, client: Any) -> None:
        self._client = client
        self.chat = _OpenAIChatProxy(client.chat)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)


class SafeAnthropicProvider(AnthropicProvider):
    """Tool-aware count_tokens bridge for ActiveGraph 1.10 cost budgets."""

    def count_tokens(self, *, system: str, messages: list[Any], model: str) -> int:
        from activegraph.llm.wire import sanitize_tool_name

        converted: list[dict[str, Any]] = []
        for message in messages:
            if message.role == "tool":
                converted.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": message.tool_use_id or "",
                                "content": message.content,
                            }
                        ],
                    }
                )
            elif message.role == "assistant" and message.tool_calls:
                blocks: list[dict[str, Any]] = []
                if message.content:
                    blocks.append({"type": "text", "text": message.content})
                for call in message.tool_calls:
                    blocks.append(
                        {
                            "type": "tool_use",
                            "id": call.id,
                            "name": sanitize_tool_name(call.name),
                            "input": dict(call.args),
                        }
                    )
                converted.append({"role": "assistant", "content": blocks})
            else:
                converted.append({"role": message.role, "content": message.content})
        kwargs: dict[str, Any] = {"model": model, "messages": converted}
        if system:
            kwargs["system"] = system
        result = self._client().messages.count_tokens(**kwargs)
        return int(getattr(result, "input_tokens", 0) or 0)


def provider_for(name: str) -> Any:
    if name == "anthropic":
        return SafeAnthropicProvider()
    if name != "openai":
        raise ValueError(f"unknown provider {name!r}")
    from openai import OpenAI

    return OpenAIProvider(
        client=_OpenAIClientProxy(OpenAI()),
        pricing={
            "gpt-5.6-sol": {"input": "5", "output": "30"},
            "gpt-5.6-terra": {"input": "2.5", "output": "15"},
            "gpt-5.6-luna": {"input": "1", "output": "6"},
            "gpt-5.6": {"input": "5", "output": "30"},
            "gpt-4o-mini": {"input": "0.15", "output": "0.6"},
            "gpt-4o": {"input": "2.5", "output": "10"},
        },
    )


class OfflineProvider:
    """Registration-only provider used by read-only inspection."""

    default_model = "offline-inspection"

    def recognizes_model(self, model: str) -> bool:
        return True

    def supports_native_structured_output(self, model: str) -> bool:
        return True

    def complete(self, **kwargs: Any) -> LLMResponse:
        raise RuntimeError("offline inspection cannot make model calls")

    def estimate_cost(self, *, input_tokens: int, output_tokens: int, model: str) -> Decimal:
        return Decimal("0")

    def count_tokens(self, *, system: str, messages: list[Any], model: str) -> int:
        return 0


# ---------------------------------------------------------------------------
# Host-owned local capabilities
# ---------------------------------------------------------------------------


class Host:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.workspace = config.workspace.resolve()
        self.state_dir = config.state_dir.resolve()
        self.capabilities: dict[str, Capability] = {}
        self.current_goal = ""
        self.current_mode = "task"

    def safe_path(self, relative: str, *, allow_root: bool = False) -> Path:
        posix = PurePosixPath(relative or ".")
        if posix.is_absolute() or ".." in posix.parts:
            raise ValueError("path must be relative and may not contain '..'")
        if any(self.private_part(part) for part in posix.parts):
            raise ValueError("private credentials, internal state, and Git metadata are unavailable to tools")
        candidate = (self.workspace / Path(*posix.parts)).resolve(strict=False)
        try:
            candidate.relative_to(self.workspace)
        except ValueError as exc:
            raise ValueError("path escapes the workspace") from exc
        if candidate == self.workspace and not allow_root:
            raise ValueError("operation requires a file path")
        cursor = candidate
        while cursor != self.workspace:
            if cursor.exists() and cursor.is_symlink():
                raise ValueError("symlink paths are not allowed")
            cursor = cursor.parent
        return candidate

    @staticmethod
    def private_part(part: str) -> bool:
        lowered = part.lower()
        return (
            lowered in {".git", ".ouroboros", ".ouroboros_home", ".ouroboros_tmp"}
            or lowered in PRIVATE_FILE_NAMES
            or lowered == ".env"
            or lowered.startswith(".env.")
        )

    def list_files(self, relative: str = ".") -> ToolResult:
        root = self.safe_path(relative, allow_root=True)
        if not root.exists():
            return ToolResult(ok=False, message=f"not found: {relative}")
        if root.is_file():
            return ToolResult(ok=True, message="1 file", data={"files": [relative]})
        files: list[str] = []
        for path in sorted(root.rglob("*")):
            try:
                rel = path.relative_to(self.workspace)
            except ValueError:
                continue
            if any(
                self.private_part(part) or part in {"__pycache__", ".pytest_cache"}
                for part in rel.parts
            ):
                continue
            if path.is_file() and not path.is_symlink():
                files.append(rel.as_posix())
            if len(files) >= 500:
                break
        return ToolResult(ok=True, message=f"{len(files)} files", data={"files": files})

    def read_file(self, relative: str) -> ToolResult:
        path = self.safe_path(relative)
        if not path.is_file():
            return ToolResult(ok=False, message=f"not a file: {relative}")
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            return ToolResult(ok=False, message=f"cannot read {relative}: {exc}")
        truncated = len(content) > MAX_FILE_CHARS
        return ToolResult(
            ok=True,
            message="read" + (" (truncated)" if truncated else ""),
            data={"path": relative, "content": content[:MAX_FILE_CHARS], "truncated": truncated},
        )

    def write_file(self, relative: str, content: str) -> ToolResult:
        if len(content) > MAX_FILE_CHARS:
            return ToolResult(ok=False, message=f"content exceeds {MAX_FILE_CHARS} characters")
        path = self.safe_path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return ToolResult(
            ok=True,
            message=f"wrote {relative}",
            data={"path": relative, "characters": len(content), "sha256": sha256_json(content)},
        )

    def replace_file(self, args: ReplaceFileInput) -> ToolResult:
        if not args.old:
            return ToolResult(ok=False, message="old text must be non-empty")
        path = self.safe_path(args.path)
        if not path.is_file():
            return ToolResult(ok=False, message=f"not a file: {args.path}")
        content = path.read_text(encoding="utf-8")
        actual = content.count(args.old)
        if actual != args.expected_occurrences:
            return ToolResult(
                ok=False,
                message=f"expected {args.expected_occurrences} occurrences, found {actual}",
            )
        updated = content.replace(args.old, args.new)
        if len(updated) > MAX_FILE_CHARS:
            return ToolResult(ok=False, message="updated file is too large")
        path.write_text(updated, encoding="utf-8")
        return ToolResult(ok=True, message=f"updated {args.path}", data={"replacements": actual})

    def command_environment(self) -> dict[str, str]:
        home = self.workspace / ".ouroboros_home"
        temporary = self.workspace / ".ouroboros_tmp"
        home.mkdir(parents=True, exist_ok=True)
        temporary.mkdir(parents=True, exist_ok=True)
        return {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(home),
            "LANG": os.environ.get("LANG", "C.UTF-8"),
            "LC_ALL": os.environ.get("LC_ALL", "C.UTF-8"),
            "PYTHONIOENCODING": "utf-8",
            "PYTHONDONTWRITEBYTECODE": "1",
            "TMPDIR": str(temporary),
        }

    def sandboxed_argv(self, argv: list[str]) -> tuple[list[str], str]:
        """Use macOS Seatbelt when available; degrade honestly elsewhere."""

        sandbox = Path("/usr/bin/sandbox-exec")
        if not sandbox.exists():
            return argv, "portable-path-env-timeout-controls"
        workspace = str(self.workspace)
        state = str(self.state_dir)
        home = str(Path.home().resolve())
        prefix = str(Path(sys.prefix).resolve())
        rules = [
            "(version 1)",
            "(allow default)",
            f"(deny file-read* (subpath {json.dumps(home)}))",
            "(deny file-write*)",
            f"(allow file-read* (subpath {json.dumps(workspace)}))",
            f"(allow file-write* (subpath {json.dumps(workspace)}))",
        ]
        metadata: set[str] = set()
        for protected in (self.workspace, Path(prefix)):
            for parent in (protected, *protected.parents):
                metadata.add(str(parent))
        for path in sorted(metadata):
            rules.append(f"(allow file-read-metadata (literal {json.dumps(path)}))")
        if prefix.startswith(home + os.sep):
            rules.append(f"(allow file-read* (subpath {json.dumps(prefix)}))")
        rules.append('(allow file-write* (literal "/dev/null"))')
        # Specific denies remain explicit even when the workspace itself was
        # allowed above. This is the important `.env in cwd` case.
        rules.append(f"(deny file-read* (subpath {json.dumps(state)}))")
        for secret in sorted(self.workspace.glob(".env*")):
            rules.append(f"(deny file-read* (literal {json.dumps(str(secret.resolve()))}))")
        for name in sorted(PRIVATE_FILE_NAMES):
            secret = self.workspace / name
            rules.append(f"(deny file-read* (literal {json.dumps(str(secret))}))")
        rules.append("(deny network*)")
        return [str(sandbox), "-p", " ".join(rules), *argv], "macos-seatbelt"

    def run_command(self, args: RunCommandInput) -> ToolResult:
        if not args.argv or any(not isinstance(item, str) or not item or "\x00" in item for item in args.argv):
            return ToolResult(ok=False, message="argv must contain non-empty strings")
        argv = list(args.argv)
        if argv[0] in {"python", "python3"}:
            argv[0] = sys.executable
        executable = Path(argv[0]).name.lower()
        if executable in {"curl", "wget", "nc", "ncat", "ssh", "scp", "pip", "pip3"} or (
            executable.startswith("python") and len(argv) > 2 and argv[1:3] == ["-m", "pip"]
        ):
            return ToolResult(ok=False, message="network and package-install commands are disabled")
        timeout = min(args.timeout_seconds, self.config.command_timeout)
        actual_argv, isolation = self.sandboxed_argv(argv)
        try:
            result = subprocess.run(
                actual_argv,
                cwd=self.workspace,
                env=self.command_environment(),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
            stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
            return ToolResult(
                ok=False,
                message=f"timed out after {timeout}s",
                data={"stdout": stdout[-MAX_TOOL_OUTPUT_CHARS:], "stderr": stderr[-MAX_TOOL_OUTPUT_CHARS:]},
            )
        except OSError as exc:
            return ToolResult(ok=False, message=f"could not start command: {exc}")
        stdout = result.stdout[-MAX_TOOL_OUTPUT_CHARS:]
        stderr = result.stderr[-MAX_TOOL_OUTPUT_CHARS:]
        return ToolResult(
            ok=result.returncode == 0,
            message=f"exit {result.returncode}",
                data={
                    "argv": argv,
                    "exit_code": result.returncode,
                    "stdout": stdout,
                    "stderr": stderr,
                    "isolation": isolation,
                },
            )

    def invoke_capability(self, name: str, payload: dict[str, Any]) -> ToolResult:
        capability = self.capabilities.get(name)
        if capability is None:
            return ToolResult(
                ok=False,
                message=f"unknown capability {name!r}",
                data={"available": sorted(self.capabilities)},
            )
        try:
            result = capability.implementation(dict(payload))
            if not isinstance(result, dict):
                raise TypeError("capability must return a JSON object")
            json.dumps(result)
        except Exception as exc:  # candidate failure is data, not a host crash
            return ToolResult(ok=False, message=f"{type(exc).__name__}: {exc}")
        return ToolResult(ok=True, message=f"ran {name}", data={"result": result})


def build_tools(host: Host) -> list[Any]:
    clear_tool_registry()

    @tool(
        name="list_files",
        description="List regular files inside the current workspace.",
        input_schema=ListFilesInput,
        output_schema=ToolResult,
        deterministic=True,
    )
    def list_files(args: ListFilesInput, ctx: Any) -> ToolResult:
        try:
            return host.list_files(args.path)
        except ValueError as exc:
            return ToolResult(ok=False, message=str(exc))

    @tool(
        name="read_file",
        description="Read a UTF-8 file inside the current workspace.",
        input_schema=ReadFileInput,
        output_schema=ToolResult,
        deterministic=True,
    )
    def read_file(args: ReadFileInput, ctx: Any) -> ToolResult:
        try:
            return host.read_file(args.path)
        except ValueError as exc:
            return ToolResult(ok=False, message=str(exc))

    @tool(
        name="write_file",
        description="Create or replace a UTF-8 file inside the workspace.",
        input_schema=WriteFileInput,
        output_schema=ToolResult,
        deterministic=False,
    )
    def write_file(args: WriteFileInput, ctx: Any) -> ToolResult:
        try:
            return host.write_file(args.path, args.content)
        except ValueError as exc:
            return ToolResult(ok=False, message=str(exc))

    @tool(
        name="replace_file",
        description="Make an exact, occurrence-checked replacement in a workspace file.",
        input_schema=ReplaceFileInput,
        output_schema=ToolResult,
        deterministic=False,
    )
    def replace_file(args: ReplaceFileInput, ctx: Any) -> ToolResult:
        try:
            return host.replace_file(args)
        except ValueError as exc:
            return ToolResult(ok=False, message=str(exc))

    @tool(
        name="run_command",
        description="Run an argv command from the workspace without a shell or provider credentials.",
        input_schema=RunCommandInput,
        output_schema=ToolResult,
        deterministic=False,
    )
    def run_command(args: RunCommandInput, ctx: Any) -> ToolResult:
        return host.run_command(args)

    @tool(
        name="invoke_capability",
        description="Invoke a promoted deterministic capability by name with a JSON-object payload.",
        input_schema=InvokeCapabilityInput,
        output_schema=ToolResult,
        deterministic=True,
    )
    def invoke_capability(args: InvokeCapabilityInput, ctx: Any) -> ToolResult:
        return host.invoke_capability(args.capability, args.payload)

    return [list_files, read_file, write_file, replace_file, run_command, invoke_capability]


AGENT_ROLE = """
You are the one general actor inside Ouroboros. The trigger contains a USER
GOAL plus selected learned procedures, recent conversation, workspace path,
and promoted deterministic capabilities.

For software work, inspect the workspace before changing it, make the smallest
coherent edits, and run relevant tests. Never claim a command passed unless a
tool result proves it. For conversational requests, answer directly in
`summary` and do not manufacture file work. You may call `invoke_capability`
when a promoted capability exactly fits the task.

Return `completed` only when the requested result is actually delivered;
otherwise return `blocked` and say what is missing. Populate procedure fields
only for a reusable method supported by evidence from this attempt. A
procedure is not a transcript and not an unverified guess.
""".strip()


MUTATION_ROLE = """
Author one small, pure, deterministic Python capability from the training
examples in the mutation_request. Additional held-out examples exist and are
not visible to you. Generalize; do not enumerate or special-case the shown
examples.

`implementation_source` must contain optional imports followed by exactly one
top-level function:

    def implementation(payload):
        ...
        return {"some": "JSON-compatible result"}

The input and output are JSON objects. Allowed modules are collections,
decimal, fractions, functools, itertools, json, math, re, statistics, string,
typing, and unicodedata. No filesystem, network, process, environment, clock,
randomness, dynamic execution, classes, decorators, or global mutation.
""".strip()


def build_behaviors(host: Host, tools: list[Any], model: str, max_tool_turns: int) -> list[Any]:
    clear_registry()

    @llm_behavior(
        name="ouro.agent",
        on=["goal.created"],
        description=AGENT_ROLE,
        view={"include_types": ["goal"], "recent_events": 1},
        output_schema=AgentResult,
        model=model,
        temperature=0.1,
        max_tokens=8_000,
        timeout_seconds=300,
        tools=tools,
        max_tool_turns=max_tool_turns,
        creates=["attempt"],
    )
    def agent(event: Any, graph: Any, ctx: Any, llm_output: AgentResult) -> None:
        data = llm_output.model_dump(mode="json")
        data.update({"goal": host.current_goal, "mode": host.current_mode, "created_at": utc_now()})
        graph.add_object("attempt", data)

    @llm_behavior(
        name="ouro.mutation_author",
        on=["object.created"],
        where={"object.type": "mutation_request"},
        description=MUTATION_ROLE,
        view={"include_types": ["mutation_request"], "recent_events": 1},
        output_schema=MutationDraft,
        model=model,
        temperature=0.0,
        max_tokens=8_000,
        timeout_seconds=300,
        creates=["mutation_draft"],
    )
    def mutation_author(event: Any, graph: Any, ctx: Any, llm_output: MutationDraft) -> None:
        request = event.payload["object"]
        data = llm_output.model_dump(mode="json")
        data.update(
            {
                "request_id": request["id"],
                "goal": request["data"].get("goal", ""),
                "created_at": utc_now(),
                "authored_by": "agent",
            }
        )
        graph.add_object("mutation_draft", data)

    return [agent, mutation_author]


# ---------------------------------------------------------------------------
# Mutation gate and bundle materialization
# ---------------------------------------------------------------------------


ALLOWED_IMPORTS = {
    "collections",
    "decimal",
    "fractions",
    "functools",
    "itertools",
    "json",
    "math",
    "re",
    "statistics",
    "string",
    "typing",
    "unicodedata",
}
BAN_NAMES = {
    "__import__",
    "breakpoint",
    "compile",
    "eval",
    "exec",
    "getattr",
    "globals",
    "help",
    "input",
    "locals",
    "open",
    "setattr",
    "vars",
}


def validate_mutation(draft: MutationDraft) -> list[str]:
    failures: list[str] = []
    if not NAME_RE.fullmatch(draft.capability_name):
        failures.append("capability_name must match [a-z][a-z0-9_]{1,48}")
    source = draft.implementation_source
    if not source.strip() or len(source) > MAX_MUTATION_SOURCE_CHARS:
        failures.append(f"implementation_source must be 1..{MAX_MUTATION_SOURCE_CHARS} characters")
        return failures
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [f"syntax error: {exc}"]
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    if len(functions) != 1 or functions[0].name != "implementation":
        failures.append("source must define exactly one top-level function named implementation")
    if functions:
        fn = functions[0]
        if fn.decorator_list:
            failures.append("implementation may not have decorators")
        args = fn.args
        if (
            len(args.args) != 1
            or args.args[0].arg != "payload"
            or args.posonlyargs
            or args.kwonlyargs
            or args.vararg is not None
            or args.kwarg is not None
        ):
            failures.append("implementation signature must be exactly implementation(payload)")
    for node in tree.body:
        if not isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef)):
            failures.append(f"top-level {type(node).__name__} is not allowed")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] not in ALLOWED_IMPORTS:
                    failures.append(f"import {alias.name!r} is not allowed")
        elif isinstance(node, ast.ImportFrom):
            module = (node.module or "").split(".")[0]
            if node.level or module not in ALLOWED_IMPORTS:
                failures.append(f"import from {node.module!r} is not allowed")
        elif isinstance(node, (ast.AsyncFunctionDef, ast.ClassDef, ast.Global, ast.Nonlocal)):
            failures.append(f"{type(node).__name__} is not allowed")
        elif isinstance(node, ast.Name) and node.id in BAN_NAMES:
            failures.append(f"name {node.id!r} is not allowed")
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            failures.append("dunder attribute access is not allowed")
    return sorted(set(failures))


TRIAL_SOURCE = '''import json
from pathlib import Path


def main(runtime):
    cases = json.loads((Path(__file__).resolve().parent / "cases.json").read_text(encoding="utf-8"))
    loaded = [pack for pack in runtime.loaded_packs() if pack.name == PACK_NAME]
    if len(loaded) != 1:
        raise AssertionError(f"expected one loaded pack {PACK_NAME!r}, found {len(loaded)}")
    candidate_tool = loaded[0].tools[0]
    counts = {"training": 0, "heldout": 0}
    for index, case in enumerate(cases):
        args = candidate_tool.input_schema.model_validate({"payload": case["input"]})
        output = candidate_tool.fn(args, None)
        actual = output.model_dump(mode="json")["result"]
        if actual != case["expected"]:
            raise AssertionError(
                f"{case['split']} case {index} failed: expected {case['expected']!r}, got {actual!r}"
            )
        counts[case["split"]] += 1
    runtime.graph.add_object(
        "mutation_trial_result",
        {"pack_name": PACK_NAME, "passed": True, "counts": counts},
        actor="trial",
    )
'''


def materialize_mutation(
    state_dir: Path,
    draft: MutationDraft,
    cases: list[dict[str, Any]],
) -> tuple[Path, str, str]:
    source_digest = hashlib.sha256(draft.implementation_source.encode("utf-8")).hexdigest()[:10]
    pack_name = f"agent_{draft.capability_name[:35]}_{source_digest}"
    root = state_dir / "mutations" / pack_name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    description_literal = repr(draft.description.strip() or draft.capability_name)
    module_source = f'''from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from activegraph import EmptySettings, Pack
from activegraph.packs import tool

{draft.implementation_source.rstrip()}


class CapabilityInput(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)


class CapabilityOutput(BaseModel):
    result: dict[str, Any]


@tool(
    name="run",
    description={description_literal},
    input_schema=CapabilityInput,
    output_schema=CapabilityOutput,
    deterministic=True,
)
def run(args, ctx):
    result = implementation(dict(args.payload))
    if not isinstance(result, dict):
        raise TypeError("implementation must return a dict")
    return CapabilityOutput(result=result)


pack = Pack(
    name={pack_name!r},
    version="0.1.0",
    description={description_literal},
    tools=(run,),
    settings_schema=EmptySettings,
)
'''
    (root / "__init__.py").write_text(module_source, encoding="utf-8")
    trial_source = f"PACK_NAME = {pack_name!r}\n\n" + TRIAL_SOURCE
    (root / "trial.py").write_text(trial_source, encoding="utf-8")
    (root / "cases.json").write_text(json.dumps(cases, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    content_hash = compute_content_hash(root)
    manifest = f'''[pack]
name = {json.dumps(pack_name)}
version = "0.1.0"
description = {json.dumps(draft.description.strip() or draft.capability_name)}
license = "MIT"

[pack.provenance]
authors = ["Ouroboros"]
authored_by = "agent"
generator = "ouroboros/{ENGINE_VERSION}"
source_url = ""
created_at = {json.dumps(utc_now())}

[pack.integrity]
content_hash = {json.dumps(content_hash)}

[dependencies]
activegraph = ">=1.10,<2"
python = ">=3.11"
python-deps = []

[surface]
object_types = []
relation_types = []
behaviors = []
tools = ["run"]
settings_schema = ""

[fixtures]
entrypoint = "trial.py"
deterministic = true
'''
    (root / "manifest.toml").write_text(manifest, encoding="utf-8")
    return root, compute_bundle_hash(root), pack_name


# ---------------------------------------------------------------------------
# The organism
# ---------------------------------------------------------------------------


class Ouroboros:
    def __init__(
        self,
        config: Config,
        *,
        llm_provider: Any | None = None,
        load_promotions: bool = True,
    ) -> None:
        self.config = config
        self.config.workspace = config.workspace.resolve()
        self.config.state_dir = config.state_dir.resolve()
        self.config.workspace.mkdir(parents=True, exist_ok=True)
        self.config.state_dir.mkdir(parents=True, exist_ok=True)
        self.load_promotions = load_promotions
        self.host = Host(self.config)
        self.tools = build_tools(self.host)
        self.behaviors = build_behaviors(
            self.host,
            self.tools,
            self.config.model,
            self.config.max_tool_turns,
        )
        self.provider = llm_provider or provider_for(self.config.provider)
        budget: dict[str, Any] = {
            "max_events": 4_000,
            "max_behavior_calls": 300,
            "max_tool_calls": 200,
            "max_llm_calls": 80,
            "max_seconds": 1_800,
        }
        if self.config.max_cost_usd is not None:
            budget["max_cost_usd"] = self.config.max_cost_usd
        self.trace_path = self.config.state_dir / "trace.sqlite"
        self.identity_path = self.config.state_dir / "organism.json"
        frame = Frame(
            goal="Improve through evaluated experience",
            constraints=[
                "Every model and tool action is recorded",
                "Only evaluated procedures are retained",
                "Structural mutations must pass model-hidden held-out examples",
            ],
        )
        if self.trace_path.exists() and self.identity_path.exists():
            identity = json.loads(self.identity_path.read_text(encoding="utf-8"))
            self.runtime = Runtime.load(
                str(self.trace_path),
                run_id=identity["run_id"],
                behaviors=self.behaviors,
                tools=self.tools,
                frame=frame,
                llm_provider=self.provider,
                budget=budget,
                native_structured_output=True,
                trace_context_reads=True,
            )
        else:
            graph = Graph(run_id=f"ouro_{uuid.uuid4().hex[:16]}")
            self.runtime = Runtime(
                graph,
                behaviors=self.behaviors,
                tools=self.tools,
                frame=frame,
                llm_provider=self.provider,
                budget=budget,
                persist_to=str(self.trace_path),
                native_structured_output=True,
                trace_context_reads=True,
            )
            write_json(
                self.identity_path,
                {"schema_version": 1, "run_id": self.runtime.run_id, "engine_version": ENGINE_VERSION},
            )
        if load_promotions:
            self._reload_promotions()

    def _reload_promotions(self) -> None:
        for item in graph_objects(self.runtime, "promotion"):
            data = item.data
            if data.get("status") != "active":
                continue
            name = str(data.get("capability_name", ""))
            if not name or name in self.host.capabilities:
                continue
            try:
                root = Path(str(data["root"]))
                bundle_hash = str(data["bundle_hash"])
                pack, module = import_pack_root(root, bundle_hash)
                self.runtime.load_pack(pack)
                implementation = getattr(module, "implementation")
                self.host.capabilities[name] = Capability(
                    name=name,
                    description=str(data.get("description", name)),
                    pack_name=pack.name,
                    root=root,
                    bundle_hash=bundle_hash,
                    implementation=implementation,
                )
            except Exception as exc:
                self.runtime.graph.add_object(
                    "capability_gap",
                    {
                        "kind": "promotion_reload_failed",
                        "capability_name": name,
                        "promotion_id": item.id,
                        "error": f"{type(exc).__name__}: {exc}",
                    },
                    actor="ouroboros",
                )
        if self.host.capabilities:
            self.runtime.run_until_idle()

    def relevant_procedures(self, goal: str, limit: int = 5) -> list[dict[str, Any]]:
        if not self.config.use_procedures:
            return []
        terms = set(re.findall(r"[a-z0-9_]+", goal.lower()))
        ranked: list[tuple[int, int, dict[str, Any]]] = []
        for index, item in enumerate(graph_objects(self.runtime, "procedure")):
            data = dict(item.data)
            triggers = {str(term).lower() for term in data.get("trigger_terms", [])}
            name_terms = set(re.findall(r"[a-z0-9_]+", str(data.get("name", "")).lower()))
            score = len(terms & (triggers | name_terms))
            if score:
                ranked.append((score, index, data))
        ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
        return [data for _, _, data in ranked[:limit]]

    def context_goal(self, goal: str, mode: str) -> str:
        procedures = self.relevant_procedures(goal)
        history = [
            {"goal": item.data.get("goal", ""), "summary": item.data.get("summary", "")}
            for item in graph_objects(self.runtime, "attempt")[-6:]
            if item.data.get("mode") == "chat"
        ]
        capabilities = [
            {"name": cap.name, "description": cap.description}
            for cap in sorted(self.host.capabilities.values(), key=lambda item: item.name)
        ]
        envelope = {
            "user_goal": goal,
            "mode": mode,
            "workspace": str(self.config.workspace),
            "learned_procedures": procedures,
            "recent_conversation": history,
            "promoted_capabilities": capabilities,
        }
        return "OUROBOROS CONTEXT\n" + json.dumps(envelope, indent=2, ensure_ascii=False)

    def run_goal(
        self,
        goal: str,
        *,
        check_command: list[str] | None = None,
        mode: Literal["task", "chat"] = "task",
    ) -> dict[str, Any]:
        goal = goal.strip()
        if not goal:
            raise ValueError("goal must be non-empty")
        self.host.current_goal = goal
        self.host.current_mode = mode
        attempt_count = len(graph_objects(self.runtime, "attempt"))
        goal_object = self.runtime.graph.add_object(
            "goal",
            {"text": goal, "mode": mode, "created_at": utc_now()},
            actor="user",
        )
        before_failure_ids = {failure.failed_event_id for failure in self.runtime.errors}
        self.runtime.frame.goal = goal
        self.runtime.run_goal(self.context_goal(goal, mode))
        attempt = latest_object(self.runtime, "attempt", after=attempt_count)
        new_failures = [
            failure for failure in self.runtime.errors if failure.failed_event_id not in before_failure_ids
        ]
        check: ToolResult | None = None
        if check_command:
            check = self.host.run_command(
                RunCommandInput(argv=check_command, timeout_seconds=self.config.command_timeout)
            )
            passed = bool(attempt is not None and check.ok and not new_failures)
            basis = "check_command"
        else:
            passed = bool(
                attempt is not None
                and attempt.data.get("status") == "completed"
                and not new_failures
            )
            basis = "agent_completion"
        evaluation = self.runtime.graph.add_object(
            "evaluation",
            {
                "goal_id": goal_object.id,
                "attempt_id": attempt.id if attempt else "",
                "passed": passed,
                "basis": basis,
                "check": check.model_dump(mode="json") if check else None,
                "failure_ids": [failure.failed_event_id for failure in new_failures],
                "created_at": utc_now(),
            },
            actor="evaluator",
        )
        procedure_id = ""
        if passed and mode == "task" and attempt is not None:
            steps = [str(step).strip() for step in attempt.data.get("procedure_steps", []) if str(step).strip()]
            if steps:
                name = str(attempt.data.get("procedure_name") or "learned procedure").strip()
                fingerprint = sha256_json({"name": name, "steps": steps})
                existing = {
                    item.data.get("fingerprint") for item in graph_objects(self.runtime, "procedure")
                }
                if fingerprint not in existing:
                    procedure = self.runtime.graph.add_object(
                        "procedure",
                        {
                            "name": name,
                            "trigger_terms": attempt.data.get("procedure_trigger_terms", []),
                            "steps": steps,
                            "fingerprint": fingerprint,
                            "evidence_evaluation_id": evaluation.id,
                            "created_at": utc_now(),
                        },
                        actor="ouroboros",
                    )
                    procedure_id = procedure.id
        self.runtime.run_until_idle()
        return {
            "passed": passed,
            "goal_id": goal_object.id,
            "attempt_id": attempt.id if attempt else "",
            "evaluation_id": evaluation.id,
            "procedure_id": procedure_id,
            "response": attempt.data.get("summary", "") if attempt else "",
            "evidence": attempt.data.get("evidence", []) if attempt else [],
            "failures": [failure._asdict() for failure in new_failures],
            "check": check.model_dump(mode="json") if check else None,
        }

    @staticmethod
    def split_examples(examples: list[ExampleCase]) -> tuple[list[ExampleCase], list[ExampleCase]]:
        if len(examples) < 4:
            raise ValueError("at least four examples are required for a model-hidden held-out split")
        ordered = sorted(examples, key=lambda case: sha256_json(case.input))
        training = [case for index, case in enumerate(ordered) if index % 2 == 0]
        heldout = [case for index, case in enumerate(ordered) if index % 2 == 1]
        return training, heldout

    def teach(self, goal: str, examples: list[ExampleCase]) -> dict[str, Any]:
        training, heldout = self.split_examples(examples)
        self.host.current_goal = goal
        self.host.current_mode = "mutation"
        draft_count = len(graph_objects(self.runtime, "mutation_draft"))
        full_receipt = sha256_json([case.model_dump(mode="json") for case in examples])
        request = self.runtime.graph.add_object(
            "mutation_request",
            {
                "goal": goal,
                "training_examples": [case.model_dump(mode="json") for case in training],
                "heldout_count": len(heldout),
                "evaluation_receipt": full_receipt,
                "created_at": utc_now(),
            },
            actor="user",
        )
        self.runtime.run_until_idle()
        draft_object = latest_object(self.runtime, "mutation_draft", after=draft_count)
        if draft_object is None or draft_object.data.get("request_id") != request.id:
            failures = [failure._asdict() for failure in self.runtime.errors[-3:]]
            return {"promoted": False, "stage": "author", "failures": failures}
        draft = MutationDraft.model_validate(draft_object.data)
        gate_failures = validate_mutation(draft)
        gate = self.runtime.graph.add_object(
            "mutation_gate",
            {
                "request_id": request.id,
                "draft_id": draft_object.id,
                "passed": not gate_failures,
                "failures": gate_failures,
                "created_at": utc_now(),
            },
            actor="gate",
        )
        if gate_failures:
            self.runtime.run_until_idle()
            return {
                "promoted": False,
                "stage": "static_gate",
                "draft_id": draft_object.id,
                "gate_id": gate.id,
                "failures": gate_failures,
            }
        cases = [
            {**case.model_dump(mode="json"), "split": "training"} for case in training
        ] + [
            {**case.model_dump(mode="json"), "split": "heldout"} for case in heldout
        ]
        root, bundle_hash, pack_name = materialize_mutation(self.config.state_dir, draft, cases)
        candidate = self.runtime.graph.add_object(
            "mutation_candidate",
            {
                "request_id": request.id,
                "draft_id": draft_object.id,
                "capability_name": draft.capability_name,
                "description": draft.description,
                "pack_name": pack_name,
                "root": str(root),
                "bundle_hash": bundle_hash,
                "evaluation_receipt": full_receipt,
                "training_count": len(training),
                "heldout_count": len(heldout),
            },
            actor="ouroboros",
        )
        self.runtime.run_until_idle()
        at_event = self.runtime.graph.events[-1].id
        report = run_forked_trial(
            str(self.trace_path),
            parent_run_id=self.runtime.run_id,
            at_event=at_event,
            pack_source=PackSource(
                root_dir=str(root),
                expected_bundle_hash=bundle_hash,
                manifest_required=True,
            ),
            scenario="trial.py::main",
            limits=TrialLimits(
                wall_clock_seconds=30,
                max_rss_bytes=512 * 2**20,
                max_events=300,
                max_llm_calls=0,
            ),
            label=f"mutation:{draft.capability_name}",
        )
        trial_data = {
            "candidate_id": candidate.id,
            "outcome": report.outcome,
            "fork_run_id": report.fork_run_id,
            "events_appended": report.events_appended,
            "behavior_failures": report.behavior_failures,
            "detail": report.detail,
            "warnings": list(report.warnings),
            "passed": report.outcome == "completed" and report.behavior_failures == 0,
            "evaluation_receipt": full_receipt,
        }
        if report.outcome != "completed" or report.behavior_failures:
            trial = self.runtime.graph.add_object(
                "mutation_trial", trial_data, actor="trial"
            )
            self.runtime.run_until_idle()
            return {
                "promoted": False,
                "stage": "heldout_trial",
                "draft_id": draft_object.id,
                "candidate_id": candidate.id,
                "trial_id": trial.id,
                "outcome": report.outcome,
                "detail": report.detail,
                "fork_run_id": report.fork_run_id,
            }
        fork = Runtime.load(str(self.trace_path), run_id=report.fork_run_id, behaviors=[])
        self.runtime.promote(fork, dry_run=True)
        pack, module = import_pack_root(root, bundle_hash)
        self.runtime.load_pack(pack)
        promote_result = self.runtime.promote(fork)
        # Record parent-side trial metadata only after applying the fork.  A
        # parent object created before promote would reuse the fork's next
        # deterministic object id and correctly trigger a both-created
        # conflict.
        trial = self.runtime.graph.add_object(
            "mutation_trial", trial_data, actor="trial"
        )
        promotion = self.runtime.graph.add_object(
            "promotion",
            {
                "candidate_id": candidate.id,
                "trial_id": trial.id,
                "capability_name": draft.capability_name,
                "description": draft.description,
                "pack_name": pack.name,
                "root": str(root),
                "bundle_hash": bundle_hash,
                "from_run_id": report.fork_run_id,
                "promote_event_id": promote_result.marker_event_id,
                "status": "active",
                "created_at": utc_now(),
            },
            actor="ouroboros",
        )
        self.host.capabilities[draft.capability_name] = Capability(
            name=draft.capability_name,
            description=draft.description,
            pack_name=pack.name,
            root=root,
            bundle_hash=bundle_hash,
            implementation=getattr(module, "implementation"),
        )
        self.runtime.run_until_idle()
        return {
            "promoted": True,
            "stage": "promoted",
            "capability_name": draft.capability_name,
            "pack_name": pack.name,
            "promotion_id": promotion.id,
            "trial_id": trial.id,
            "fork_run_id": report.fork_run_id,
            "bundle_hash": bundle_hash,
            "root": str(root),
            "training_count": len(training),
            "heldout_count": len(heldout),
        }

    def summary(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for item in self.runtime.graph.all_objects():
            counts[item.type] = counts.get(item.type, 0) + 1
        cost = Decimal("0")
        for event in self.runtime.graph.events:
            if event.type == "llm.responded":
                try:
                    cost += Decimal(str(event.payload.get("cost_usd", "0")))
                except Exception:
                    pass
        promoted_names = {
            str(item.data.get("capability_name", ""))
            for item in graph_objects(self.runtime, "promotion")
            if item.data.get("status") == "active"
        }
        return {
            "engine_version": ENGINE_VERSION,
            "run_id": self.runtime.run_id,
            "workspace": str(self.config.workspace),
            "state_dir": str(self.config.state_dir),
            "trace": str(self.trace_path),
            "events": len(self.runtime.graph.events),
            "objects": dict(sorted(counts.items())),
            "procedures": [item.data.get("name", "") for item in graph_objects(self.runtime, "procedure")],
            "capabilities": sorted(set(self.host.capabilities) | promoted_names),
            "loaded_packs": [pack.name for pack in self.runtime.loaded_packs()],
            "estimated_model_cost_usd": str(cost),
            "procedure_retrieval_enabled": self.config.use_procedures,
            "promotion_loading_enabled": self.load_promotions,
        }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


DESCRIPTION = """Ouroboros has one generic model actor over an ActiveGraph
event log. Evaluated successes become retrieved procedures. `--teach` asks the
model to author a pure deterministic capability from half of an examples file;
the other half remains hidden until a hash-pinned subprocess fork trial. No
package from activegraph-packs is installed or imported."""


def parse_examples(path: Path) -> list[ExampleCase]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("examples file must contain a JSON array")
    return [ExampleCase.model_validate(item) for item in raw]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="A minimal self-improving agent on ActiveGraph")
    parser.add_argument("objective", nargs="?", help="task, chat prompt, or capability teaching goal")
    parser.add_argument("--workspace", default=".", help="workspace visible to model tools")
    parser.add_argument("--state-dir", default=str(DEFAULT_STATE_DIR), help="persistent organism directory")
    parser.add_argument("--provider", choices=["openai", "anthropic"], default="openai")
    parser.add_argument("--model", default=os.environ.get("OUROBOROS_MODEL", DEFAULT_MODEL))
    parser.add_argument("--max-cost-usd", type=float)
    parser.add_argument("--max-tool-turns", type=int, default=16)
    parser.add_argument("--check", help="deterministic success command, parsed as argv without a shell")
    parser.add_argument(
        "--teach",
        metavar="EXAMPLES.json",
        help="author, trial, and promote a deterministic capability",
    )
    parser.add_argument("--chat", action="store_true", help="persistent terminal chat loop")
    parser.add_argument("--inspect", action="store_true", help="print graph-derived organism summary")
    parser.add_argument("--describe", action="store_true", help="describe the minimal architecture")
    parser.add_argument("--fresh", action="store_true", help="delete only --state-dir before starting")
    parser.add_argument(
        "--no-procedures",
        action="store_true",
        help="cold ablation: retain the graph but do not retrieve learned procedures",
    )
    parser.add_argument(
        "--no-promotions",
        action="store_true",
        help="cold ablation: do not load promoted capability code",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.describe:
        print(DESCRIPTION)
        return 0
    workspace = Path(args.workspace).resolve()
    state_dir = Path(args.state_dir)
    if not state_dir.is_absolute():
        state_dir = (workspace / state_dir).resolve()
    if args.fresh and state_dir.exists():
        shutil.rmtree(state_dir)
    load_env_file(Path.cwd() / ".env")
    if workspace != Path.cwd().resolve():
        load_env_file(workspace / ".env")
    required_key = "OPENAI_API_KEY" if args.provider == "openai" else "ANTHROPIC_API_KEY"
    if not args.inspect and not os.environ.get(required_key):
        parser.error(f"{required_key} is not set (a local .env file is supported)")
    config = Config(
        workspace=workspace,
        state_dir=state_dir,
        provider=args.provider,
        model=args.model,
        max_cost_usd=args.max_cost_usd,
        max_tool_turns=max(1, args.max_tool_turns),
        use_procedures=not args.no_procedures,
    )
    organism = Ouroboros(
        config,
        llm_provider=OfflineProvider() if args.inspect else None,
        load_promotions=not args.inspect and not args.no_promotions,
    )
    if args.inspect:
        print(json.dumps(organism.summary(), indent=2, sort_keys=True))
        return 0
    if args.chat:
        if args.objective:
            first = organism.run_goal(args.objective, mode="chat")
            print(first["response"])
        while True:
            try:
                message = input("you> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not message:
                continue
            if message.lower() in {"/quit", "/exit"}:
                break
            result = organism.run_goal(message, mode="chat")
            print(f"ouroboros> {result['response']}")
        return 0
    if not args.objective:
        parser.error("objective is required unless --chat, --inspect, or --describe is used")
    if args.teach:
        result = organism.teach(args.objective, parse_examples(Path(args.teach)))
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result.get("promoted") else 1
    check = shlex.split(args.check) if args.check else None
    result = organism.run_goal(args.objective, check_command=check)
    result["organism"] = organism.summary()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
