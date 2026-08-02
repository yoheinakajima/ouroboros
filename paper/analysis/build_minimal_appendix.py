#!/usr/bin/env python3
"""Build the minimal paper appendix from frozen study artifacts."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "analysis" / "generated"
PAPER = ROOT / "paper"


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def normalized_score(row: dict[str, object]) -> float:
    maximum = float(row["maximum_score"])
    return float(row["score"]) / maximum if maximum else 0.0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def grouped_means(
    rows: list[dict[str, object]], *, valid_only: bool
) -> dict[tuple[str, str, str], float]:
    values: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for row in rows:
        if valid_only and not bool(row["valid"]):
            continue
        key = (
            str(row["suite_id"]),
            str(row["approach_id"]),
            str(row["arm"]),
        )
        values[key].append(normalized_score(row))
    return {key: mean(scores) for key, scores in values.items()}


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    raw_path = ROOT / "results-probe.jsonl"
    final_path = ROOT / "results-probe-adjudicated.jsonl"
    raw = read_jsonl(raw_path)
    final = read_jsonl(final_path)

    raw_zero = grouped_means(raw, valid_only=False)
    raw_complete = grouped_means(raw, valid_only=True)
    final_means = grouped_means(final, valid_only=False)

    sensitivity: list[dict[str, object]] = []
    suite_approach = sorted({(key[0], key[1]) for key in final_means})
    for suite, approach in suite_approach:
        evolved = (suite, approach, "evolved")
        ablation = (suite, approach, "cold_ablation")
        sensitivity.append(
            {
                "suite_id": suite,
                "approach_id": approach,
                "final_evolved_minus_ablation": (
                    final_means[evolved] - final_means[ablation]
                ),
                "raw_invalid_as_zero_evolved_minus_ablation": (
                    raw_zero[evolved] - raw_zero[ablation]
                ),
                "raw_complete_case_evolved_minus_ablation": (
                    raw_complete.get(evolved, float("nan"))
                    - raw_complete.get(ablation, float("nan"))
                ),
            }
        )
    sensitivity_path = GENERATED / "adjudication-sensitivity.csv"
    write_csv(sensitivity_path, sensitivity)

    success_efficiency: list[dict[str, object]] = []
    binary_suites = {"ouro_swe_50", "ouro_terminal_12"}
    groups: dict[tuple[str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in final:
        if str(row["suite_id"]) not in binary_suites:
            continue
        if normalized_score(row) == 1.0:
            groups[
                (
                    str(row["suite_id"]),
                    str(row["approach_id"]),
                    str(row["arm"]),
                )
            ].append(row)
    for (suite, approach, arm), rows in sorted(groups.items()):
        success_efficiency.append(
            {
                "suite_id": suite,
                "approach_id": approach,
                "arm": arm,
                "successful_tasks": len(rows),
                "mean_cost_usd_given_success": mean(
                    float(row["cost_usd"]) for row in rows
                ),
                "mean_wall_seconds_given_success": mean(
                    float(row["wall_seconds"]) for row in rows
                ),
            }
        )
    efficiency_path = GENERATED / "success-conditional-efficiency.csv"
    write_csv(efficiency_path, success_efficiency)

    provenance_paths = [
        ROOT / "study.json",
        raw_path,
        final_path,
        ROOT / "report-probe.json",
        ROOT / "report-probe-adjudicated.json",
        ROOT / "probe-adjudication.json",
        ROOT / "analysis" / "generated" / "posthoc-metrics.json",
        ROOT / "analysis" / "taxonomy" / "masked-packet.jsonl",
        ROOT / "analysis" / "taxonomy" / "coder-sol-a" / "labels.csv",
        ROOT / "analysis" / "taxonomy" / "coder-terra-b" / "labels.csv",
        ROOT / "analysis" / "taxonomy" / "coder-agreement.json",
        PAPER / "MANUSCRIPT.md",
    ]
    provenance = {
        "kind": "paper-provenance-manifest",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": [
            {
                "path": str(path.relative_to(ROOT)),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in provenance_paths
        ],
    }
    provenance_path = PAPER / "provenance-manifest.json"
    provenance_path.write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    adjudication = json.loads(
        (ROOT / "probe-adjudication.json").read_text(encoding="utf-8")
    )
    changed_contrasts = [
        row
        for row in sensitivity
        if abs(
            float(row["final_evolved_minus_ablation"])
            - float(row["raw_invalid_as_zero_evolved_minus_ablation"])
        )
        >= 1e-12
    ]
    stable_contrasts = len(sensitivity) - len(changed_contrasts)

    appendix = f"""# Minimal appendix

## A. Adjudication sensitivity

The raw run contained 215 immediately valid rows and 13 rows requiring
policy adjudication. The final dataset retained all 228 attempts. Categories
were six official SWE task timeouts, six Terminal agent-budget timeouts with
completed zero verifiers, and one ActiveGraph snapshot contradiction resolved
by a sealed grader-only retry of the hash-identical submission.

Eight of nine preregistered `evolved - cold ablation` contrasts are identical
when raw invalid rows are scored zero and when the frozen adjudication
decisions are applied. The exception is Hybrid ActiveGraph: the contrast moves
from -26.0 points under raw-invalid-as-zero to -10.0 points after the
hash-identical quota-scheduler regrade. It remains negative and the
preregistered conclusion is unchanged. A raw complete-case analysis gives
+7.3 points for this cell because it drops the evolved invalid row.
Complete-case contrasts are reported only as sensitivity analyses because
dropping bounded failures changes the estimand and can favor arms with more
invalid outcomes.

The study's single adjudication judgment moved a score in the evolved arm's
favor, and the preregistered conclusion remained null.

Machine-readable table:
[`../analysis/generated/adjudication-sensitivity.csv`](../analysis/generated/adjudication-sensitivity.csv)

## B. Timeout taxonomy

| Category | Count | Treatment | Interpretation |
|---|---:|---|---|
| Official SWE task timeout | {adjudication['categories']['official_task_timeout']} | Scored zero | The patch-bound official evaluation exceeded the frozen 3,600-second task limit. |
| Terminal agent-budget timeout with verifier zero | {adjudication['categories']['agent_budget_timeout_with_verifier_zero']} | Scored zero | The agent exhausted the frozen 1,800-second budget and the completed verifier returned zero. |
| ActiveGraph snapshot regrade | {adjudication['categories']['activegraph_snapshot_regrade']} | Hash-identical grader-only retry | The original grader contradicted a receipt-bound parsable submission; no model action was rerun. |

Timeouts remain outcomes under the bounded-agent estimand. The taxonomy
separates agent budget exhaustion, official evaluator limits, and
infrastructure contradiction.

## C. Success-conditional efficiency

For the binary SWE and Terminal families, the companion table reports mean
cost and wall time among successful attempts for every architecture and arm:
[`../analysis/generated/success-conditional-efficiency.csv`](../analysis/generated/success-conditional-efficiency.csv).

These quantities describe the resource profile of observed successes. They do
not estimate causal efficiency because conditioning on success selects
different tasks and trajectories across arms. Unconditional costs remain the
primary resource comparison.

## D. Provenance

The provenance manifest records byte counts and SHA-256 hashes for the frozen
study specification, raw and adjudicated datasets and reports, adjudication
ledger, post-hoc metrics, masked coding packet, both original coder label
files, agreement report, and manuscript:
[`provenance-manifest.json`](provenance-manifest.json).

The adjudication ledger separately hashes each changed row and its supporting
evidence. No taxonomy disagreement was adjudicated before the two original
label files were frozen.
"""
    (PAPER / "APPENDIX.md").write_text(appendix, encoding="utf-8")

    print(
        json.dumps(
            {
                "sensitivity_rows": len(sensitivity),
                "success_efficiency_rows": len(success_efficiency),
                "provenance_files": len(provenance["files"]),
                "primary_contrasts_stable_under_raw_zero": stable_contrasts,
                "primary_contrasts_changed_under_raw_zero": len(
                    changed_contrasts
                ),
                "appendix": str(PAPER / "APPENDIX.md"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
