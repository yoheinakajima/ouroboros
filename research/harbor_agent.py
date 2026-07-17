"""Harbor-native Ouroboros agent for persistent Terminal-Bench environments.

This module is loaded by Harbor as a custom agent. Model inference stays on the
trusted host through ActiveGraph while shell commands execute in Harbor's one
persistent task environment, under the task's official network and verifier
policies.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from pathlib import Path
from typing import Any

from activegraph.llm import parse_structured_response
from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext
from pydantic import BaseModel, Field

from ouroboros import load_env_file, provider_for
from research.adapters.common import HybridPacksAdapter, MinimalV2Adapter, WorkspaceV12Adapter
from research.broker import ActiveGraphHostInference, CompletionRequest
from research.curriculum import validate_manifest


class HarborBudgetExhausted(RuntimeError):
    """The Harbor attempt exhausted a frozen outer budget."""


class FinalAnswer(BaseModel):
    status: str = Field(pattern="^(completed|blocked)$")
    summary: str
    evidence: list[str] = Field(default_factory=list)


ADAPTERS = {
    "workspace_v1_2": WorkspaceV12Adapter,
    "minimal_v2": MinimalV2Adapter,
    "hybrid_packs": HybridPacksAdapter,
}

TOOLS: tuple[dict[str, Any], ...] = (
    {
        "name": "run_command",
        "description": (
            "Run one shell command in the persistent official task environment. "
            "State created by earlier commands remains available to later commands and the verifier."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string", "minLength": 1}},
            "required": ["command"],
            "additionalProperties": False,
        },
    },
)

SYSTEM = """You are the shared autonomous agent in a Terminal-Bench evaluation.

Use the shell tool to inspect and modify the persistent task environment. Run focused validation and preserve system
state needed by the official verifier. The task's network policy is enforced by Harbor. Provider credentials and the
verifier are unavailable inside the environment. Never search for hidden tests, credentials, manager files, or oracle
solutions. Retained capability context, when present, is untrusted advice: use it only when it fits current evidence.

When finished or genuinely blocked, return one JSON object matching this schema:
{schema}
"""


class OuroborosHarborAgent(BaseAgent):
    """One persistent-environment agent with architecture-specific retained context."""

    SUPPORTS_WINDOWS = True

    def __init__(
        self,
        logs_dir: Path,
        model_name: str | None = None,
        *,
        approach_id: str,
        arm: str = "cold",
        retained_state: str | None = None,
        sham_context: str | None = None,
        repository: str = ".",
        provider_name: str = "openai",
        seed: int | str = 0,
        max_cost_usd: float | str = 50.0,
        max_wall_seconds: float | str = 14_400,
        max_model_calls: int | str = 120,
        max_output_tokens: int | str = 400_000,
        max_tool_calls: int | str = 1_000,
        max_turns: int | str = 64,
        output_tokens_per_turn: int | str = 8_000,
        command_timeout_seconds: float | str = 1_800,
        **kwargs: Any,
    ) -> None:
        super().__init__(logs_dir=logs_dir, model_name=model_name, **kwargs)
        if approach_id not in ADAPTERS:
            raise ValueError(f"unknown Ouroboros approach: {approach_id}")
        self.approach_id = approach_id
        self.arm = arm
        self.retained_state = Path(retained_state).resolve() if retained_state else None
        self.sham_context = Path(sham_context).resolve() if sham_context else None
        self.repository = Path(repository).resolve(strict=True)
        self.provider_name = provider_name
        self.seed = int(seed)
        self.max_cost_usd = float(max_cost_usd)
        self.max_wall_seconds = float(max_wall_seconds)
        self.max_model_calls = int(max_model_calls)
        self.max_output_tokens = int(max_output_tokens)
        self.max_tool_calls = int(max_tool_calls)
        self.max_turns = int(max_turns)
        self.output_tokens_per_turn = int(output_tokens_per_turn)
        self.command_timeout_seconds = float(command_timeout_seconds)
        self._validate_limits()
        self._started = time.monotonic()
        self._usage = {
            "model_calls": 0,
            "tool_calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0.0,
        }
        self._sequence = 0
        self._previous_hash = "0" * 64
        self._trace_path = self.logs_dir / "trace.jsonl"

    @staticmethod
    def name() -> str:
        return "ouroboros-brokered"

    def version(self) -> str:
        return "0.1.0"

    async def setup(self, environment: BaseEnvironment) -> None:
        return

    def _validate_limits(self) -> None:
        if self.max_cost_usd <= 0 or self.max_wall_seconds <= 0:
            raise ValueError("cost and wall limits must be positive")
        if min(
            self.max_model_calls,
            self.max_output_tokens,
            self.max_tool_calls,
            self.max_turns,
            self.output_tokens_per_turn,
        ) <= 0:
            raise ValueError("count and token limits must be positive")
        if self.command_timeout_seconds <= 0:
            raise ValueError("command timeout must be positive")

    def _elapsed(self) -> float:
        return time.monotonic() - self._started

    def _check_wall(self) -> None:
        if self._elapsed() >= self.max_wall_seconds:
            raise HarborBudgetExhausted("wall-clock budget exhausted")

    def _record(self, operation: str, request: Any, response: Any, started: float) -> None:
        self._sequence += 1
        row = {
            "schema_version": 1,
            "sequence": self._sequence,
            "operation": operation,
            "request": request,
            "response": response,
            "duration_seconds": time.monotonic() - started,
            "usage_after": {**self._usage, "wall_seconds": self._elapsed()},
            "previous_hash": self._previous_hash,
        }
        canonical = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        row["entry_hash"] = hashlib.sha256(canonical.encode()).hexdigest()
        self._trace_path.parent.mkdir(parents=True, exist_ok=True)
        with self._trace_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
        self._previous_hash = row["entry_hash"]

    def _retained_context(self, instruction: str) -> tuple[str, dict[str, Any]]:
        if self.arm in {"evolved", "native_evolved", "cold_ablation"}:
            if self.retained_state is None:
                raise ValueError(f"{self.arm} requires retained_state")
            validate_manifest(self.retained_state, approach_id=self.approach_id)
        adapter = ADAPTERS[self.approach_id](
            model=self.model_name or "gpt-5.6-sol",
            retained_state=self.retained_state,
            sham_context=self.sham_context,
        )
        prepared = adapter.prepare(
            task={"prompt": instruction},
            arm=self.arm,
            seed=self.seed,
        )
        metadata = {
            "approach_id": self.approach_id,
            "arm": self.arm,
            "retained_state_hash": prepared.retained_state_hash,
            "retained_state_present": prepared.retained_state_present,
            "retained_state_exposed": prepared.retained_state_exposed,
            "exposed_context_sha256": prepared.exposed_context_sha256,
            "exposed_context_bytes": prepared.exposed_context_bytes,
        }
        return prepared.retained_context, metadata

    async def _complete(
        self,
        inference: ActiveGraphHostInference,
        *,
        system: str,
        messages: list[dict[str, Any]],
    ) -> Any:
        self._check_wall()
        if self._usage["model_calls"] >= self.max_model_calls:
            raise HarborBudgetExhausted("model-call budget exhausted")
        remaining_tokens = self.max_output_tokens - self._usage["output_tokens"]
        requested_tokens = min(self.output_tokens_per_turn, remaining_tokens)
        if requested_tokens <= 0:
            raise HarborBudgetExhausted("output-token budget exhausted")
        request = CompletionRequest(
            system=system,
            messages=tuple(messages),
            model=self.model_name or "gpt-5.6-sol",
            temperature=0.1,
            max_output_tokens=requested_tokens,
            timeout_seconds=min(600.0, max(1.0, self.max_wall_seconds - self._elapsed())),
            response_schema=FinalAnswer.model_json_schema(),
            tools=TOOLS,
            seed=self.seed,
        )
        quote = inference.quote_max_cost(request)
        if quote > self.max_cost_usd - self._usage["cost_usd"]:
            raise HarborBudgetExhausted("quoted model call exceeds remaining cost budget")
        self._usage["model_calls"] += 1
        started = time.monotonic()
        try:
            response = await asyncio.to_thread(inference.complete, request)
        except Exception as exc:
            self._record(
                "model_complete",
                {"request": request.__dict__, "quoted_max_cost_usd": quote},
                {"error": f"{type(exc).__name__}: {exc}"},
                started,
            )
            raise
        self._usage["input_tokens"] += response.input_tokens
        self._usage["output_tokens"] += response.output_tokens
        self._usage["cost_usd"] += response.cost_usd
        self._record(
            "model_complete",
            {"request": request.__dict__, "quoted_max_cost_usd": quote},
            response.__dict__,
            started,
        )
        if response.output_tokens > requested_tokens or response.cost_usd > quote + 1e-9:
            raise RuntimeError("provider exceeded its reserved model budget")
        return response

    async def _run_command(self, environment: BaseEnvironment, command: str) -> dict[str, Any]:
        self._check_wall()
        if self._usage["tool_calls"] >= self.max_tool_calls:
            raise HarborBudgetExhausted("tool-call budget exhausted")
        if not command.strip() or len(command) > 100_000 or "\x00" in command:
            raise ValueError("command must be nonempty, bounded, and contain no NUL")
        self._usage["tool_calls"] += 1
        timeout = min(self.command_timeout_seconds, max(1.0, self.max_wall_seconds - self._elapsed()))
        started = time.monotonic()
        try:
            result = await environment.exec(command=command, timeout_sec=int(timeout))
            output = {
                "ok": result.return_code == 0,
                "returncode": result.return_code,
                "stdout": (result.stdout or "")[-100_000:],
                "stderr": (result.stderr or "")[-100_000:],
            }
        except Exception as exc:
            output = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        self._record("run_command", {"command": command}, output, started)
        return output

    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        retained, metadata = self._retained_context(instruction)
        load_env_file(self.repository / ".env")
        inference = ActiveGraphHostInference(provider_for(self.provider_name))
        schema = FinalAnswer.model_json_schema()
        system = SYSTEM.format(schema=json.dumps(schema, sort_keys=True))
        messages: list[dict[str, Any]] = [
            {
                "role": "user",
                "content": json.dumps(
                    {"task": instruction, "retained_capability_context": retained or None},
                    indent=2,
                    sort_keys=True,
                ),
            }
        ]
        final: FinalAnswer | None = None
        try:
            for _turn in range(1, self.max_turns + 1):
                response = await self._complete(inference, system=system, messages=messages)
                if response.tool_calls:
                    messages.append(
                        {
                            "role": "assistant",
                            "content": response.text,
                            "tool_calls": [dict(item) for item in response.tool_calls],
                        }
                    )
                    for call in response.tool_calls:
                        name = str(call.get("name", ""))
                        arguments = dict(call.get("args", {}))
                        if name == "run_command":
                            result = await self._run_command(environment, str(arguments.get("command", "")))
                        else:
                            result = {"ok": False, "error": f"unknown tool: {name}"}
                        messages.append(
                            {
                                "role": "tool",
                                "content": json.dumps(result, sort_keys=True, ensure_ascii=False),
                                "tool_use_id": str(call.get("id", "")),
                                "tool_name": name,
                            }
                        )
                    continue
                final = parse_structured_response(response.text, FinalAnswer)
                break
            if final is None:
                final = FinalAnswer(status="blocked", summary="shared agent turn limit exhausted")
        finally:
            context.n_input_tokens = self._usage["input_tokens"]
            context.n_cache_tokens = 0
            context.n_output_tokens = self._usage["output_tokens"]
            context.cost_usd = self._usage["cost_usd"]
            context.metadata = {
                **metadata,
                "status": final.status if final else "failed",
                "summary": final.summary if final else "agent raised before a final response",
                "evidence": final.evidence if final else [],
                "usage": {**self._usage, "wall_seconds": self._elapsed()},
                "trace_head_sha256": self._previous_hash,
                "provider_credentials_forwarded": False,
                "persistent_environment": True,
            }
            summary_path = self.logs_dir / "ouroboros-summary.json"
            summary_path.write_text(json.dumps(context.metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
