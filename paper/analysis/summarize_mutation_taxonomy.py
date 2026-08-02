#!/usr/bin/env python3
"""Freeze, unblind, and summarize the architecture-masked taxonomy pilot."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TAXONOMY = ROOT / "analysis" / "taxonomy"
LABELS = TAXONOMY / "coder-sol-a" / "labels.csv"
KEY = TAXONOMY / "metadata-key.csv"
JOINED = TAXONOMY / "taxonomy-labeled-unblinded.csv"
SUMMARY = TAXONOMY / "taxonomy-summary.json"

FIELDS = [
    "primary_update_target",
    "secondary_update_target",
    "representational_form",
    "transfer_scope",
    "abstraction_level",
    "evidence_grounding",
    "failure_specificity",
    "validation_strategy",
    "consolidation_operation",
    "executable_status",
    "anticipated_activation",
    "counterfactual_actionability",
    "novelty_relative_to_prior_state",
    "confidence",
]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def counts(rows: list[dict[str, str]], field: str) -> dict[str, int]:
    return dict(sorted(Counter(row[field] for row in rows).items()))


def rates(rows: list[dict[str, str]], field: str) -> dict[str, float]:
    denominator = len(rows)
    return {
        key: value / denominator
        for key, value in counts(rows, field).items()
    }


def boolean_rate(rows: list[dict[str, str]], field: str) -> dict[str, object]:
    values = Counter(row[field].lower() == "true" for row in rows)
    return {
        "true": values[True],
        "false": values[False],
        "rate": values[True] / len(rows),
    }


def main() -> None:
    labels = read_rows(LABELS)
    metadata = read_rows(KEY)
    if len(labels) != 84 or len(metadata) != 84:
        raise SystemExit(
            f"Expected 84 labels and 84 metadata rows; got {len(labels)} and {len(metadata)}"
        )
    label_ids = [row["masked_id"] for row in labels]
    key_ids = [row["masked_id"] for row in metadata]
    if len(set(label_ids)) != 84 or set(label_ids) != set(key_ids):
        raise SystemExit("Masked IDs are non-unique or label/key sets differ")

    key_by_id = {row["masked_id"]: row for row in metadata}
    joined: list[dict[str, str]] = []
    for label in labels:
        meta = key_by_id[label["masked_id"]]
        joined.append({**meta, **label})
    joined.sort(key=lambda row: (row["approach_id"], int(row["sequence"])))

    with JOINED.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(joined[0]))
        writer.writeheader()
        writer.writerows(joined)

    by_approach: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in joined:
        by_approach[row["approach_id"]].append(row)

    payload: dict[str, object] = {
        "status": "exploratory single-coder architecture-masked pilot",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "coder_id": sorted(set(row["coder_id"] for row in labels)),
        "model": sorted(set(row["model"] for row in labels)),
        "labels_sha256_before_unblinding": sha256(LABELS),
        "metadata_key_sha256": sha256(KEY),
        "items": len(joined),
        "limitations": [
            "Architecture-masked, not double-blind; mutation form can reveal substrate.",
            "One model coder; no inter-rater reliability estimate.",
            "The unit is the reflection/update proposal, not every native file-level mutation.",
            "Architecture and task are confounded because each lineage used independent stochastic development runs.",
            "Labels are descriptive and do not establish downstream causal effects.",
        ],
        "overall": {
            field: {"counts": counts(joined, field), "rates": rates(joined, field)}
            for field in FIELDS
        },
        "by_approach": {},
    }
    for approach, rows in sorted(by_approach.items()):
        payload["by_approach"][approach] = {
            "items": len(rows),
            "score_passed": boolean_rate(rows, "score_passed"),
            "mutation_accepted": boolean_rate(rows, "mutation_accepted"),
            "fields": {
                field: {"counts": counts(rows, field), "rates": rates(rows, field)}
                for field in FIELDS
            },
        }

    SUMMARY.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "items": len(joined),
                "labels_sha256_before_unblinding": payload[
                    "labels_sha256_before_unblinding"
                ],
                "joined": str(JOINED),
                "summary": str(SUMMARY),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
