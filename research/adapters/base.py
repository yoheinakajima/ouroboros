"""Interface that prevents an architecture from receiving a richer outer agent."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from research.contracts import AttemptRecord


class AdapterDescriptor(BaseModel):
    approach_id: str
    mutation_unit: str
    supports_cold_arm: bool
    supports_evolved_arm: bool
    supports_sham_control: bool
    broker_protocol_version: str


class ApproachAdapter(ABC):
    """All benchmark arms must enter through this deliberately small surface."""

    @property
    @abstractmethod
    def descriptor(self) -> AdapterDescriptor:
        raise NotImplementedError

    @abstractmethod
    def prepare(self, *, task: dict[str, Any], arm: str, seed: int) -> dict[str, Any]:
        """Prepare isolated state without seeing evaluator-private material."""
        raise NotImplementedError

    @abstractmethod
    def run(self, prepared: dict[str, Any]) -> AttemptRecord:
        """Execute one budgeted attempt through the common broker."""
        raise NotImplementedError
