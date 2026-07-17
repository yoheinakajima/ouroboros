#!/usr/bin/env python3
"""Architecture-neutral, budgeted authority broker for benchmark attempts."""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Protocol, Sequence

from research.contracts import ResourceUsage
from research.sandbox import DockerSandbox, SandboxLimits, SandboxResult


class BrokerError(RuntimeError):
    """Base class for a denied or failed broker operation."""


class BudgetExhausted(BrokerError):
    """The operation would exceed the preregistered attempt budget."""


class AuthorityDenied(BrokerError):
    """The requested path, environment, or operation is outside the contract."""


@dataclass(frozen=True)
class BrokerBudget:
    max_cost_usd: float
    max_wall_seconds: float
    max_model_calls: int
    max_output_tokens: int
    max_tool_calls: int

    def validate(self) -> None:
        values = asdict(self)
        if any(value < 0 for value in values.values()):
            raise ValueError("broker budgets may not be negative")
        if self.max_wall_seconds <= 0:
            raise ValueError("max_wall_seconds must be positive")


@dataclass(frozen=True)
class CompletionRequest:
    messages: tuple[dict[str, Any], ...]
    model: str
    system: str = ""
    temperature: float = 0.0
    top_p: float = 1.0
    max_output_tokens: int = 4096
    timeout_seconds: float = 300.0
    seed: int | None = None
    response_schema: dict[str, Any] | None = None
    tools: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class CompletionResponse:
    text: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    provider_request_id: str | None = None
    finish_reason: str = "stop"
    tool_calls: tuple[dict[str, Any], ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


class InferenceProvider(Protocol):
    """Trusted host provider; implementations own credentials and price quotes."""

    def quote_max_cost(self, request: CompletionRequest) -> float:
        """Return a conservative upper-bound cost before a request is sent."""

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Perform one completion without exposing provider credentials."""


class ActiveGraphHostInference:
    """Use an ActiveGraph provider behind the host broker, never in a candidate."""

    def __init__(self, provider: Any) -> None:
        self.provider = provider

    @staticmethod
    def _messages(request: CompletionRequest) -> list[Any]:
        from activegraph.llm import LLMMessage, ToolCall

        messages: list[Any] = []
        for row in request.messages:
            tool_calls = row.get("tool_calls")
            messages.append(
                LLMMessage(
                    role=row["role"],
                    content=str(row.get("content", "")),
                    tool_use_id=row.get("tool_use_id"),
                    tool_name=row.get("tool_name"),
                    tool_calls=(
                        tuple(
                            ToolCall(id=str(item["id"]), name=str(item["name"]), args=dict(item.get("args", {})))
                            for item in tool_calls
                        )
                        if tool_calls
                        else None
                    ),
                )
            )
        return messages

    def quote_max_cost(self, request: CompletionRequest) -> float:
        messages = self._messages(request)
        input_tokens = int(
            self.provider.count_tokens(system=request.system, messages=messages, model=request.model)
        )
        quoted = self.provider.estimate_cost(
            input_tokens=input_tokens,
            output_tokens=request.max_output_tokens,
            model=request.model,
        )
        return float(quoted)

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        response = self.provider.complete(
            system=request.system,
            messages=self._messages(request),
            model=request.model,
            max_tokens=request.max_output_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            output_schema=None,
            timeout_seconds=request.timeout_seconds,
            tools=list(request.tools) or None,
            structured_output_mode="prompt",
        )
        return CompletionResponse(
            text=response.raw_text,
            input_tokens=int(response.input_tokens),
            output_tokens=int(response.output_tokens),
            cost_usd=float(response.cost_usd),
            finish_reason=response.finish_reason,
            tool_calls=tuple(call.to_dict() for call in (response.tool_calls or [])),
            metadata={"model": response.model, "provider_meta": response.provider_meta},
        )


@dataclass(frozen=True)
class BrokerConfig:
    workspace: Path
    trace_path: Path
    image: str
    budget: BrokerBudget
    sandbox_limits: SandboxLimits = field(default_factory=SandboxLimits)
    network: bool = False
    command_environment: Mapping[str, str] = field(default_factory=dict)


class AuthorityBroker:
    """The only file, command, and inference authority available to an approach."""

    _DENIED_PARTS = {".git", ".ouroboros", ".env", ".grader", ".evaluator", "__pycache__"}

    def __init__(
        self,
        config: BrokerConfig,
        *,
        sandbox: DockerSandbox | None = None,
        provider: InferenceProvider | None = None,
    ) -> None:
        config.budget.validate()
        DockerSandbox.validate_image(config.image)
        workspace = config.workspace.resolve(strict=True)
        if not workspace.is_dir() or workspace.is_symlink():
            raise ValueError("broker workspace must be a real directory")
        trace_path = config.trace_path.resolve()
        if trace_path == workspace or workspace in trace_path.parents:
            raise ValueError("broker trace must be outside the agent-visible workspace")
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        self.config = BrokerConfig(
            workspace=workspace,
            trace_path=trace_path,
            image=config.image,
            budget=config.budget,
            sandbox_limits=config.sandbox_limits,
            network=config.network,
            command_environment=dict(config.command_environment),
        )
        self.sandbox = sandbox or DockerSandbox()
        self.provider = provider
        self._started = time.monotonic()
        self._usage = ResourceUsage()
        self._sequence = 0
        self._previous_hash = "0" * 64

    @property
    def usage(self) -> ResourceUsage:
        usage = self._usage.model_copy(deep=True)
        usage.wall_seconds = self._elapsed()
        return usage

    def _elapsed(self) -> float:
        return time.monotonic() - self._started

    def _check_wall(self) -> None:
        if self._elapsed() >= self.config.budget.max_wall_seconds:
            self._record("budget_denied", {"kind": "wall_seconds"}, {"allowed": False})
            raise BudgetExhausted("wall-clock budget exhausted")

    def _reserve_tool(self, operation: str) -> None:
        self._check_wall()
        if self._usage.tool_calls >= self.config.budget.max_tool_calls:
            self._record("budget_denied", {"kind": "tool_calls", "operation": operation}, {"allowed": False})
            raise BudgetExhausted("tool-call budget exhausted")
        self._usage.tool_calls += 1

    def _path(self, raw: str, *, must_exist: bool = False) -> Path:
        relative = PurePosixPath(raw)
        if relative.is_absolute() or not relative.parts or ".." in relative.parts:
            raise AuthorityDenied(f"unsafe workspace path: {raw!r}")
        if any(part in self._DENIED_PARTS or part.startswith(".grader") for part in relative.parts):
            raise AuthorityDenied(f"manager-private workspace path denied: {raw!r}")
        path = self.config.workspace.joinpath(*relative.parts)
        parent = path if path.exists() and path.is_dir() else path.parent
        try:
            resolved_parent = parent.resolve(strict=must_exist)
        except FileNotFoundError as exc:
            raise AuthorityDenied(f"workspace path does not exist: {raw!r}") from exc
        if resolved_parent != self.config.workspace and self.config.workspace not in resolved_parent.parents:
            raise AuthorityDenied(f"workspace escape denied: {raw!r}")
        if any(candidate.is_symlink() for candidate in (path, *path.parents) if candidate != self.config.workspace):
            raise AuthorityDenied(f"symlink path denied: {raw!r}")
        return path

    def list_files(self) -> list[str]:
        self._reserve_tool("list_files")
        started = time.monotonic()
        files = []
        for path in self.config.workspace.rglob("*"):
            relative = path.relative_to(self.config.workspace)
            if any(part in self._DENIED_PARTS or part.startswith(".grader") for part in relative.parts):
                continue
            if path.is_file() and not path.is_symlink():
                files.append(relative.as_posix())
        result = sorted(files)
        self._record("list_files", {}, {"files": result}, started=started)
        return result

    def read_file(self, path: str, *, max_bytes: int = 1_000_000) -> str:
        self._reserve_tool("read_file")
        started = time.monotonic()
        target = self._path(path, must_exist=True)
        if not target.is_file() or target.is_symlink():
            raise AuthorityDenied(f"not a readable regular file: {path!r}")
        raw = target.read_bytes()
        if len(raw) > max_bytes:
            raise AuthorityDenied(f"file exceeds read limit: {len(raw)} > {max_bytes}")
        text = raw.decode("utf-8")
        self._record("read_file", {"path": path, "max_bytes": max_bytes}, {"text": text}, started=started)
        return text

    def write_file(self, path: str, text: str) -> None:
        self._reserve_tool("write_file")
        started = time.monotonic()
        target = self._path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + ".ouroboros-write")
        temporary.write_text(text, encoding="utf-8")
        temporary.replace(target)
        self._record("write_file", {"path": path, "text": text}, {"written": True}, started=started)

    def replace_file(self, path: str, old: str, new: str, *, expected_replacements: int = 1) -> None:
        self._reserve_tool("replace_file")
        started = time.monotonic()
        target = self._path(path, must_exist=True)
        if not target.is_file() or target.is_symlink():
            raise AuthorityDenied(f"not a writable regular file: {path!r}")
        original = target.read_text(encoding="utf-8")
        occurrences = original.count(old)
        if occurrences != expected_replacements:
            response = {"written": False, "occurrences": occurrences}
            self._record(
                "replace_file",
                {"path": path, "old": old, "new": new, "expected_replacements": expected_replacements},
                response,
                started=started,
            )
            raise BrokerError(f"expected {expected_replacements} replacements, found {occurrences}")
        temporary = target.with_name(target.name + ".ouroboros-replace")
        temporary.write_text(original.replace(old, new), encoding="utf-8")
        temporary.replace(target)
        self._record(
            "replace_file",
            {"path": path, "old": old, "new": new, "expected_replacements": expected_replacements},
            {"written": True, "occurrences": occurrences},
            started=started,
        )

    def run_command(self, command: Sequence[str]) -> SandboxResult:
        self._reserve_tool("run_command")
        started = time.monotonic()
        remaining_wall = self.config.budget.max_wall_seconds - self._elapsed()
        if remaining_wall <= 0:
            raise BudgetExhausted("wall-clock budget exhausted")
        limits = SandboxLimits(
            wall_seconds=min(self.config.sandbox_limits.wall_seconds, remaining_wall),
            memory_mb=self.config.sandbox_limits.memory_mb,
            cpus=self.config.sandbox_limits.cpus,
            pids=self.config.sandbox_limits.pids,
            tmpfs_mb=self.config.sandbox_limits.tmpfs_mb,
            output_bytes=self.config.sandbox_limits.output_bytes,
        )
        try:
            result = self.sandbox.run(
                image=self.config.image,
                workspace=self.config.workspace,
                command=command,
                limits=limits,
                environment=self.config.command_environment,
                network=self.config.network,
            )
        except Exception as exc:
            self._record(
                "run_command",
                {"command": list(command)},
                {"error": f"{type(exc).__name__}: {exc}"},
                started=started,
            )
            raise
        self._record("run_command", {"command": list(command)}, result.to_dict(), started=started)
        return result

    def model_complete(self, request: CompletionRequest) -> CompletionResponse:
        self._check_wall()
        if self.provider is None:
            raise AuthorityDenied("this broker has no configured inference provider")
        if self._usage.model_calls >= self.config.budget.max_model_calls:
            self._record("budget_denied", {"kind": "model_calls"}, {"allowed": False})
            raise BudgetExhausted("model-call budget exhausted")
        remaining_tokens = self.config.budget.max_output_tokens - self._usage.output_tokens
        if request.max_output_tokens > remaining_tokens:
            self._record(
                "budget_denied",
                {"kind": "output_tokens", "requested": request.max_output_tokens, "remaining": remaining_tokens},
                {"allowed": False},
            )
            raise BudgetExhausted("requested completion exceeds remaining output-token budget")
        quote = self.provider.quote_max_cost(request)
        remaining_cost = self.config.budget.max_cost_usd - self._usage.cost_usd
        if quote < 0 or quote > remaining_cost:
            self._record(
                "budget_denied",
                {"kind": "cost_usd", "quoted": quote, "remaining": remaining_cost},
                {"allowed": False},
            )
            raise BudgetExhausted("quoted completion exceeds remaining cost budget")
        self._usage.model_calls += 1
        started = time.monotonic()
        try:
            response = self.provider.complete(request)
        except Exception as exc:
            self._record(
                "model_complete",
                asdict(request),
                {"error": f"{type(exc).__name__}: {exc}", "quoted_max_cost_usd": quote},
                started=started,
            )
            raise
        if response.output_tokens < 0 or response.input_tokens < 0 or response.cost_usd < 0:
            self._record(
                "model_complete_invalid",
                asdict(request),
                {**asdict(response), "quoted_max_cost_usd": quote},
                started=started,
            )
            raise BrokerError("provider returned invalid negative usage")
        self._usage.input_tokens += response.input_tokens
        self._usage.output_tokens += response.output_tokens
        self._usage.cost_usd += response.cost_usd
        self._record(
            "model_complete",
            asdict(request),
            {**asdict(response), "quoted_max_cost_usd": quote},
            started=started,
        )
        if response.output_tokens > request.max_output_tokens or response.cost_usd > quote + 1e-9:
            raise BrokerError("provider exceeded its reserved token or cost quote; actual usage was retained")
        return response

    def _record(
        self,
        operation: str,
        request: dict[str, Any],
        response: dict[str, Any],
        *,
        started: float | None = None,
    ) -> None:
        self._sequence += 1
        payload = {
            "schema_version": 1,
            "sequence": self._sequence,
            "recorded_at": datetime.now(UTC).isoformat(),
            "operation": operation,
            "request": request,
            "response": response,
            "duration_seconds": 0.0 if started is None else time.monotonic() - started,
            "usage_after": self.usage.model_dump(mode="json"),
            "previous_hash": self._previous_hash,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        entry_hash = hashlib.sha256(canonical.encode()).hexdigest()
        payload["entry_hash"] = entry_hash
        line = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
        descriptor = os.open(self.config.trace_path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
        try:
            os.write(descriptor, line.encode())
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        self._previous_hash = entry_hash


def verify_journal(path: str | Path) -> dict[str, Any]:
    """Verify sequence numbers and the complete journal hash chain."""

    previous = "0" * 64
    count = 0
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        row = json.loads(line)
        entry_hash = row.pop("entry_hash", None)
        canonical = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        actual = hashlib.sha256(canonical.encode()).hexdigest()
        if row.get("sequence") != line_number:
            raise ValueError(f"journal sequence mismatch on line {line_number}")
        if row.get("previous_hash") != previous or entry_hash != actual:
            raise ValueError(f"journal hash-chain mismatch on line {line_number}")
        previous = actual
        count += 1
    return {"valid": True, "entries": count, "head_hash": previous}
