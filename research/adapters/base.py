"""Interface that prevents an architecture from receiving a richer outer agent."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from research.broker import AuthorityBroker


class AdapterDescriptor(BaseModel):
    approach_id: str
    mutation_unit: str
    supports_cold_arm: bool
    supports_evolved_arm: bool
    supports_sham_control: bool
    broker_protocol_version: str


class PreparedAttempt(BaseModel):
    approach_id: str
    arm: str
    seed: int
    task: dict[str, Any]
    retained_state_hash: str | None = None
    retained_context: str = ""
    retained_state_present: bool = False
    retained_state_exposed: bool = False
    exposed_context_sha256: str | None = None
    exposed_context_bytes: int = 0


class AgentOutcome(BaseModel):
    status: str
    summary: str
    evidence: list[str] = Field(default_factory=list)
    turns: int
    tool_calls: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class ApproachAdapter(ABC):
    """All benchmark arms must enter through this deliberately small surface."""

    @property
    @abstractmethod
    def descriptor(self) -> AdapterDescriptor:
        raise NotImplementedError

    @abstractmethod
    def prepare(self, *, task: dict[str, Any], arm: str, seed: int) -> PreparedAttempt:
        """Prepare isolated state without seeing evaluator-private material."""
        raise NotImplementedError

    @abstractmethod
    def run(self, prepared: PreparedAttempt, broker: AuthorityBroker) -> AgentOutcome:
        """Execute one budgeted attempt through the common broker."""
        raise NotImplementedError
