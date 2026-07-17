"""Deterministic, score-blind helpers for benchmark oracle calibration."""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

SWE_REPLACEMENT_SEED = "ouroboros-hard-v1-swe-calibration-replacement-v1"
TERMINAL_REPLACEMENT_SEED = "ouroboros-hard-v1-terminal2-calibration-replacement-v1"


def stable_rank(seed: str, scope: str, value: str) -> str:
    """Return a domain-separated deterministic rank for a selection value."""

    return hashlib.sha256(f"{seed}\0{scope}\0{value}".encode()).hexdigest()


def balanced_replacements(
    records: Iterable[Mapping[str, Any]],
    *,
    selected_ids: Sequence[str],
    excluded_ids: Sequence[str],
    count: int,
    seed: str = SWE_REPLACEMENT_SEED,
) -> list[str]:
    """Choose unused replacements while keeping repository counts balanced.

    Candidate outcomes are deliberately absent from this interface. Repositories
    with the fewest retained selections are filled first; SHA-256 ranks break
    repository and instance ties. Previously selected IDs, including exclusions,
    are never eligible again.
    """

    if count < 0:
        raise ValueError("count must be non-negative")
    selected = set(selected_ids)
    excluded = set(excluded_ids)
    if not excluded <= selected:
        raise ValueError("every excluded ID must be present in selected_ids")

    repositories: dict[str, str] = {}
    candidates: dict[str, list[str]] = defaultdict(list)
    for record in records:
        instance_id = str(record["instance_id"])
        repository = str(record["repo"])
        previous = repositories.setdefault(instance_id, repository)
        if previous != repository:
            raise ValueError(f"instance appears in multiple repositories: {instance_id}")
        if instance_id not in selected:
            candidates[repository].append(instance_id)

    missing = selected - repositories.keys()
    if missing:
        raise ValueError(f"selected IDs missing from records: {sorted(missing)}")
    retained_counts = Counter(repositories[item] for item in selected - excluded)
    for repository, ids in candidates.items():
        ids.sort(key=lambda item: stable_rank(seed, "instance", item))

    replacements: list[str] = []
    for _ in range(count):
        available = [repository for repository, ids in candidates.items() if ids]
        if not available:
            raise ValueError("not enough unused candidates")
        repository = min(
            available,
            key=lambda item: (
                retained_counts[item],
                stable_rank(seed, "repository", item),
            ),
        )
        replacement = candidates[repository].pop(0)
        replacements.append(replacement)
        retained_counts[repository] += 1
    return replacements


def stratum_replacements(
    records: Iterable[Mapping[str, Any]],
    *,
    selected_ids: Sequence[str],
    excluded_ids: Sequence[str],
    strata: Sequence[str],
    seed: str = TERMINAL_REPLACEMENT_SEED,
) -> list[str]:
    """Replace failed tasks from the same preregistered metadata stratum.

    Each excluded task is processed in the supplied manifest order. Its
    replacement must match every named stratum (for Terminal-Bench, difficulty
    and category) and is the lowest domain-separated SHA-256-ranked unused ID.
    """

    if not strata:
        raise ValueError("at least one stratum is required")
    rows = {str(record["id"]): dict(record) for record in records}
    selected = set(selected_ids)
    excluded = set(excluded_ids)
    if not excluded <= selected:
        raise ValueError("every excluded ID must be present in selected_ids")
    missing = selected - rows.keys()
    if missing:
        raise ValueError(f"selected IDs missing from records: {sorted(missing)}")

    unused = set(rows) - selected
    replacements: list[str] = []
    for excluded_id in excluded_ids:
        target = rows[excluded_id]
        matches = [
            candidate
            for candidate in unused
            if all(rows[candidate].get(field) == target.get(field) for field in strata)
        ]
        if not matches:
            values = {field: target.get(field) for field in strata}
            raise ValueError(f"no unused replacement for {excluded_id} in stratum {values}")
        replacement = min(matches, key=lambda item: stable_rank(seed, "task", item))
        replacements.append(replacement)
        unused.remove(replacement)
    return replacements
