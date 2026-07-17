#!/usr/bin/env python3
"""Deterministic family-separated analysis for recorded Ouroboros scores."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

Arm = Literal["cold", "evolved", "cold_ablation", "sham_improvement_control"]
EXTERNAL_FAMILIES = {"ouro_swe_50", "ouro_terminal_12"}


class ResultRow(BaseModel):
    approach_id: str
    suite_id: str
    task_id: str
    arm: Arm
    seed: int
    replication: int = Field(ge=1)
    score: float
    maximum_score: float = Field(gt=0)
    cost_usd: float = Field(default=0, ge=0)
    wall_seconds: float = Field(default=0, ge=0)
    valid: bool = True
    invalid_reason: str | None = None

    @model_validator(mode="after")
    def score_within_bounds(self) -> "ResultRow":
        if not 0 <= self.score <= self.maximum_score:
            raise ValueError("score must be within [0, maximum_score]")
        if not self.valid and not self.invalid_reason:
            raise ValueError("invalid rows require invalid_reason")
        return self

    @property
    def normalized_score(self) -> float:
        return self.score / self.maximum_score

    @property
    def pair_key(self) -> tuple[str, int, int]:
        return (self.task_id, self.seed, self.replication)


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        raise ValueError("percentile requires data")
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(fraction * (len(ordered) - 1))))
    return ordered[index]


def _paired_delta(
    rows: list[ResultRow],
    *,
    left: Arm,
    right: Arm,
    bootstrap_samples: int,
    seed_label: str,
) -> dict[str, Any]:
    indexed: dict[Arm, dict[tuple[str, int, int], ResultRow]] = {left: {}, right: {}}
    for row in rows:
        if row.arm not in indexed:
            continue
        if row.pair_key in indexed[row.arm]:
            raise ValueError(f"duplicate result row for {row.arm}/{row.pair_key}")
        indexed[row.arm][row.pair_key] = row
    keys = sorted(set(indexed[left]) & set(indexed[right]))
    task_deltas: dict[str, list[float]] = defaultdict(list)
    cost_deltas: list[float] = []
    wall_deltas: list[float] = []
    for key in keys:
        left_row = indexed[left][key]
        right_row = indexed[right][key]
        task_deltas[key[0]].append(left_row.normalized_score - right_row.normalized_score)
        cost_deltas.append(left_row.cost_usd - right_row.cost_usd)
        wall_deltas.append(left_row.wall_seconds - right_row.wall_seconds)
    cluster_values = [statistics.fmean(values) for _, values in sorted(task_deltas.items())]
    if not cluster_values:
        return {
            "left": left,
            "right": right,
            "paired_rows": 0,
            "paired_tasks": 0,
            "status": "insufficient_pairs",
        }
    rng_seed = int(hashlib.sha256(seed_label.encode()).hexdigest()[:16], 16)
    rng = random.Random(rng_seed)
    draws = [statistics.fmean(rng.choice(cluster_values) for _ in cluster_values) for _ in range(bootstrap_samples)]
    mean_delta = statistics.fmean(cluster_values)
    lower = _percentile(draws, 0.025)
    upper = _percentile(draws, 0.975)
    status = "better" if lower > 0 else "worse" if upper < 0 else "no_detected_winner"
    return {
        "left": left,
        "right": right,
        "paired_rows": len(keys),
        "paired_tasks": len(cluster_values),
        "mean_normalized_delta": mean_delta,
        "median_task_delta": statistics.median(cluster_values),
        "bootstrap_95_interval": [lower, upper],
        "status": status,
        "mean_cost_delta_usd": statistics.fmean(cost_deltas),
        "mean_wall_delta_seconds": statistics.fmean(wall_deltas),
        "per_task_delta": {name: statistics.fmean(values) for name, values in sorted(task_deltas.items())},
    }


def compare(rows: list[ResultRow], *, bootstrap_samples: int = 10_000) -> dict[str, Any]:
    if bootstrap_samples < 100:
        raise ValueError("bootstrap_samples must be at least 100")
    invalid = [row for row in rows if not row.valid]
    valid = [row for row in rows if row.valid]
    grouped: dict[tuple[str, str], list[ResultRow]] = defaultdict(list)
    for row in valid:
        grouped[(row.suite_id, row.approach_id)].append(row)
    families: dict[str, dict[str, Any]] = defaultdict(dict)
    for (suite_id, approach_id), family_rows in sorted(grouped.items()):
        arm_scores: dict[str, dict[str, float | int]] = {}
        for arm in sorted({row.arm for row in family_rows}):
            selected = [row for row in family_rows if row.arm == arm]
            arm_scores[arm] = {
                "attempts": len(selected),
                "mean_normalized_score": statistics.fmean(row.normalized_score for row in selected),
                "mean_cost_usd": statistics.fmean(row.cost_usd for row in selected),
                "mean_wall_seconds": statistics.fmean(row.wall_seconds for row in selected),
            }
        uplift = _paired_delta(
            family_rows,
            left="evolved",
            right="cold_ablation",
            bootstrap_samples=bootstrap_samples,
            seed_label=f"{suite_id}/{approach_id}/ablation",
        )
        sham = _paired_delta(
            family_rows,
            left="evolved",
            right="sham_improvement_control",
            bootstrap_samples=bootstrap_samples,
            seed_label=f"{suite_id}/{approach_id}/sham",
        )
        families[suite_id][approach_id] = {
            "arm_scores": arm_scores,
            "evolved_minus_cold_ablation": uplift,
            "evolved_minus_sham": sham,
        }
    recursive_claims: dict[str, Any] = {}
    approaches = sorted({row.approach_id for row in valid})
    for approach_id in approaches:
        qualifying: list[str] = []
        for suite_id, by_approach in families.items():
            result = by_approach.get(approach_id)
            if not result:
                continue
            uplift = result["evolved_minus_cold_ablation"]
            sham = result["evolved_minus_sham"]
            if uplift.get("status") == "better" and sham.get("status") == "better":
                qualifying.append(suite_id)
        recursive_claims[approach_id] = {
            "qualifying_families": sorted(qualifying),
            "includes_external_family": bool(set(qualifying) & EXTERNAL_FAMILIES),
            "strong_evidence_threshold_met": len(qualifying) >= 2 and bool(set(qualifying) & EXTERNAL_FAMILIES),
            "remaining_non_score_gates": ["byte-identical restart", "no material development regression"],
        }
    return {
        "schema_version": 1,
        "family_scores_separate": True,
        "valid_rows": len(valid),
        "invalid_infrastructure_rows_retained": len(invalid),
        "families": dict(families),
        "recursive_claims": recursive_claims,
    }


def load_jsonl(path: Path) -> list[ResultRow]:
    rows: list[ResultRow] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(ResultRow.model_validate_json(line))
        except Exception as exc:
            raise ValueError(f"invalid row at {path}:{line_number}: {exc}") from exc
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path, help="JSONL rows matching ResultRow")
    parser.add_argument("--bootstrap-samples", type=int, default=10_000)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = compare(load_jsonl(args.results), bootstrap_samples=args.bootstrap_samples)
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
