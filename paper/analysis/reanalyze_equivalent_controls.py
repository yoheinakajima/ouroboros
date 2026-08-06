#!/usr/bin/env python3
"""Reanalyze the collapsed cold/ablation controls from compact paper data.

The study's three cold and three cold-ablation labels had the same
actor-visible inputs. This script keeps the frozen matched-ablation
contrast visible while adding pooled and leave-the-matched-ablation-out
descriptive sensitivity analyses. It also computes a tie-aware conditional
exchangeability expectation for evolved results outside the six-control range.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from fractions import Fraction
from pathlib import Path
from statistics import fmean

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "generated" / "task-level-noise-and-evolved.csv"
SUMMARY_OUTPUT = ROOT / "data" / "generated" / "equivalent-control-sensitivity.csv"
EXCHANGEABILITY_OUTPUT = (
    ROOT / "data" / "generated" / "outside-range-exchangeability.json"
)

APPROACH_ORDER = ("workspace_v1_2", "minimal_v2", "hybrid_packs")
SUITE_ORDER = ("ouro_swe_50", "ouro_terminal_12", "ouro_activegraph_50")


def load_rows() -> list[dict[str, str]]:
    with INPUT.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def strict_outside(value: float, references: list[float]) -> bool:
    return value < min(references) or value > max(references)


def exchangeability_probability(values: list[float]) -> Fraction:
    """Probability a uniformly relabeled focal value is outside the other six.

    Only a unique minimum or unique maximum is strictly outside the range of
    the other observations. Ties therefore receive zero tail probability.
    """

    minimum = min(values)
    maximum = max(values)
    unique_extremes = int(values.count(minimum) == 1)
    if maximum != minimum:
        unique_extremes += int(values.count(maximum) == 1)
    return Fraction(unique_extremes, len(values))


def main() -> None:
    rows = load_rows()
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row["suite_id"], row["task_id"])].append(row)

    summaries: list[dict[str, object]] = []
    exchangeability_cases: list[dict[str, object]] = []

    for suite_id in SUITE_ORDER:
        tasks = sorted(task for suite, task in grouped if suite == suite_id)
        for approach_id in APPROACH_ORDER:
            task_rows: list[dict[str, float | str | bool]] = []
            for task_id in tasks:
                current = grouped[(suite_id, task_id)]
                controls = [
                    row for row in current if row["condition_type"] == "equivalent_no_context"
                ]
                if len(controls) != 6:
                    raise SystemExit(
                        f"expected six no-context controls for {suite_id}/{task_id}, "
                        f"found {len(controls)}"
                    )
                evolved_matches = [
                    row
                    for row in current
                    if row["condition_type"] == "evolved"
                    and row["approach_id"] == approach_id
                ]
                if len(evolved_matches) != 1:
                    raise SystemExit(
                        f"expected one evolved row for {suite_id}/{task_id}/{approach_id}"
                    )
                ablation_matches = [
                    row
                    for row in controls
                    if row["approach_id"] == approach_id
                    and row["arm"] == "cold_ablation"
                ]
                if len(ablation_matches) != 1:
                    raise SystemExit(
                        f"expected one matched ablation for {suite_id}/{task_id}/{approach_id}"
                    )

                evolved = float(evolved_matches[0]["score"])
                control_scores = [float(row["score"]) for row in controls]
                matched_ablation = float(ablation_matches[0]["score"])
                leave_matched_out = [
                    float(row["score"])
                    for row in controls
                    if row is not ablation_matches[0]
                ]
                variable_controls = len(set(control_scores)) > 1
                observed_outside = strict_outside(evolved, control_scores)
                probability = exchangeability_probability(control_scores + [evolved])

                task_rows.append(
                    {
                        "evolved": evolved,
                        "matched_ablation": matched_ablation,
                        "pooled_controls": fmean(control_scores),
                        "leave_matched_out": fmean(leave_matched_out),
                        "control_minimum": min(control_scores),
                        "control_maximum": max(control_scores),
                        "observed_outside": observed_outside,
                    }
                )
                exchangeability_cases.append(
                    {
                        "suite_id": suite_id,
                        "task_id": task_id,
                        "approach_id": approach_id,
                        "control_task_class": "variable" if variable_controls else "stable",
                        "observed_outside": observed_outside,
                        "conditional_expected_outside": probability,
                    }
                )

            evolved_mean = fmean(float(row["evolved"]) for row in task_rows)
            matched_mean = fmean(float(row["matched_ablation"]) for row in task_rows)
            pooled_mean = fmean(float(row["pooled_controls"]) for row in task_rows)
            leave_out_mean = fmean(float(row["leave_matched_out"]) for row in task_rows)
            summaries.append(
                {
                    "suite_id": suite_id,
                    "approach_id": approach_id,
                    "tasks": len(tasks),
                    "evolved_mean": evolved_mean,
                    "matched_ablation_mean": matched_mean,
                    "frozen_delta_vs_matched_ablation": evolved_mean - matched_mean,
                    "pooled_six_no_context_mean": pooled_mean,
                    "delta_vs_pooled_six_no_context": evolved_mean - pooled_mean,
                    "leave_matched_ablation_out_mean": leave_out_mean,
                    "delta_vs_leave_matched_ablation_out": evolved_mean - leave_out_mean,
                    "evolved_results_outside_six_control_range": sum(
                        bool(row["observed_outside"]) for row in task_rows
                    ),
                }
            )

    fieldnames = list(summaries[0])
    with SUMMARY_OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(summaries)

    def aggregate(cases: list[dict[str, object]]) -> dict[str, object]:
        expected = sum(
            (case["conditional_expected_outside"] for case in cases), Fraction()
        )
        return {
            "cases": len(cases),
            "observed_outside": sum(bool(case["observed_outside"]) for case in cases),
            "conditional_expected_outside_fraction": f"{expected.numerator}/{expected.denominator}",
            "conditional_expected_outside": float(expected),
        }

    by_family = {
        suite_id: aggregate(
            [case for case in exchangeability_cases if case["suite_id"] == suite_id]
        )
        for suite_id in SUITE_ORDER
    }
    by_control_task_class = {
        task_class: aggregate(
            [
                case
                for case in exchangeability_cases
                if case["control_task_class"] == task_class
            ]
        )
        for task_class in ("stable", "variable")
    }
    exchangeability_payload = {
        "schema_version": 1,
        "input": str(INPUT.relative_to(ROOT)),
        "method": (
            "For each configuration-task case, condition on the observed six "
            "actor-visible-equivalent no-context scores plus the evolved score. "
            "Uniformly relabel which of the seven scores is focal. A focal score is "
            "strictly outside the range of the other six only when it is a unique "
            "minimum or unique maximum; tied extrema contribute zero probability."
        ),
        "all_cases": aggregate(exchangeability_cases),
        "by_family": by_family,
        "by_control_task_class": by_control_task_class,
    }
    EXCHANGEABILITY_OUTPUT.write_text(
        json.dumps(exchangeability_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(exchangeability_payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
