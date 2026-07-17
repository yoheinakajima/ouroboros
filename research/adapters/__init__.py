"""Comparable outer adapters for the three mutation architectures.

The public contracts exist now; execution remains locked until every adapter
passes the readiness requirements recorded in ``research/approaches.json``.
"""

from research.adapters.base import AdapterDescriptor, ApproachAdapter

__all__ = ["ApproachAdapter", "AdapterDescriptor"]
