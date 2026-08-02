#!/usr/bin/env python3
"""Compare two frozen architecture-masked update-proposal coding passes.

The output distinguishes cross-model coding sensitivity from independent
human inter-rater reliability. It never edits or adjudicates either source
label file.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from rate_mutation_taxonomy import ENUMS


def read_rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    by_id = {row["masked_id"]: row for row in rows}
    if len(by_id) != len(rows):
        raise ValueError(f"duplicate masked_id in {path}")
    return by_id


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def proportions(values: Iterable[str], categories: list[str]) -> dict[str, float]:
    counts = Counter(values)
    denominator = sum(counts.values())
    return {category: counts[category] / denominator for category in categories}


def cohen_kappa(
    labels_a: list[str], labels_b: list[str], categories: list[str]
) -> tuple[float, float, float | None]:
    n = len(labels_a)
    observed = sum(a == b for a, b in zip(labels_a, labels_b)) / n
    pa = proportions(labels_a, categories)
    pb = proportions(labels_b, categories)
    expected = sum(pa[category] * pb[category] for category in categories)
    if expected == 1.0:
        return observed, expected, None
    return observed, expected, (observed - expected) / (1.0 - expected)


def gwet_ac1(
    labels_a: list[str], labels_b: list[str], categories: list[str]
) -> tuple[float, float, float | None]:
    """Return observed agreement, AC1 chance agreement, and Gwet's AC1.

    The nominal multi-category chance term uses the full pre-specified field
    vocabulary, including categories absent from this sample.
    """

    n = len(labels_a)
    observed = sum(a == b for a, b in zip(labels_a, labels_b)) / n
    pa = proportions(labels_a, categories)
    pb = proportions(labels_b, categories)
    average = {
        category: (pa[category] + pb[category]) / 2.0
        for category in categories
    }
    category_count = len(categories)
    if category_count <= 1:
        return observed, 0.0, None
    expected = (
        sum(value * (1.0 - value) for value in average.values())
        / (category_count - 1)
    )
    if expected == 1.0:
        return observed, expected, None
    return observed, expected, (observed - expected) / (1.0 - expected)


def fmt(value: float | None) -> str:
    return "undefined" if value is None else f"{value:.3f}"


def main() -> None:
    parser = argparse.ArgumentParser()
    root = Path(__file__).resolve().parents[1]
    taxonomy = root / "analysis" / "taxonomy"
    parser.add_argument(
        "--labels-a",
        type=Path,
        default=taxonomy / "coder-sol-a" / "labels.csv",
    )
    parser.add_argument(
        "--labels-b",
        type=Path,
        default=taxonomy / "coder-terra-b" / "labels.csv",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=taxonomy / "coder-agreement.json",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=root / "paper" / "UPDATE_PROPOSAL_TAXONOMY_RELIABILITY.md",
    )
    parser.add_argument(
        "--metadata-key",
        type=Path,
        default=taxonomy / "metadata-key.csv",
    )
    args = parser.parse_args()

    labels_a_path = args.labels_a.resolve()
    labels_b_path = args.labels_b.resolve()
    rows_a = read_rows(labels_a_path)
    rows_b = read_rows(labels_b_path)
    metadata = read_rows(args.metadata_key.resolve())
    if set(rows_a) != set(rows_b):
        missing_a = sorted(set(rows_b) - set(rows_a))
        missing_b = sorted(set(rows_a) - set(rows_b))
        raise ValueError(f"masked-id mismatch missing_a={missing_a} missing_b={missing_b}")
    ids = sorted(rows_a)
    if set(metadata) != set(ids):
        raise ValueError("metadata key does not contain the same masked-id set")

    fields: dict[str, object] = {}
    disagreements: list[dict[str, str]] = []
    for field, categories in ENUMS.items():
        values_a = [rows_a[masked_id][field] for masked_id in ids]
        values_b = [rows_b[masked_id][field] for masked_id in ids]
        observed, kappa_expected, kappa = cohen_kappa(
            values_a, values_b, categories
        )
        _, ac1_expected, ac1 = gwet_ac1(values_a, values_b, categories)
        field_disagreements = [
            {
                "masked_id": masked_id,
                "field": field,
                "coder_a": rows_a[masked_id][field],
                "coder_b": rows_b[masked_id][field],
            }
            for masked_id in ids
            if rows_a[masked_id][field] != rows_b[masked_id][field]
        ]
        disagreements.extend(field_disagreements)
        fields[field] = {
            "items": len(ids),
            "agreements": len(ids) - len(field_disagreements),
            "disagreements": len(field_disagreements),
            "raw_agreement": observed,
            "cohen_expected_agreement": kappa_expected,
            "cohen_kappa": kappa,
            "gwet_expected_agreement": ac1_expected,
            "gwet_ac1": ac1,
            "coder_a_counts": dict(sorted(Counter(values_a).items())),
            "coder_b_counts": dict(sorted(Counter(values_b).items())),
        }

    payload = {
        "status": "exploratory cross-model architecture-masked reliability check",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "items": len(ids),
        "labels_a": {
            "path": str(labels_a_path),
            "sha256": sha256(labels_a_path),
            "coder_ids": sorted({row["coder_id"] for row in rows_a.values()}),
            "models": sorted({row["model"] for row in rows_a.values()}),
        },
        "labels_b": {
            "path": str(labels_b_path),
            "sha256": sha256(labels_b_path),
            "coder_ids": sorted({row["coder_id"] for row in rows_b.values()}),
            "models": sorted({row["model"] for row in rows_b.values()}),
        },
        "limitations": [
            "Both coding passes were produced by language models from the same frozen prompt and codebook.",
            "Agreement measures prompt and cross-model sensitivity; it is not independent human inter-rater reliability.",
            "Architecture masking may be incomplete because representational form can reveal substrate.",
            "Prevalence can make Cohen's kappa undefined or unstable; raw agreement and Gwet's AC1 are also reported.",
            "No disagreement was adjudicated before these results were frozen.",
        ],
        "fields": fields,
        "disagreements": disagreements,
        "post_unblinding": {
            "evidence_grounding_by_development_outcome": {
                coder_name: {
                    outcome: dict(
                        sorted(
                            Counter(
                                rows[masked_id]["evidence_grounding"]
                                for masked_id in ids
                                if metadata[masked_id]["score_passed"].lower()
                                == outcome
                            ).items()
                        )
                    )
                    for outcome in ("true", "false")
                }
                for coder_name, rows in (("coder_a", rows_a), ("coder_b", rows_b))
            }
        },
    }
    args.output_json.resolve().write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Update-proposal taxonomy reliability",
        "",
        f"Status: {payload['status']}",
        "",
        "This check compares two independent model-coding passes over the same",
        "84-item architecture-masked packet. It measures cross-model and prompt",
        "sensitivity. It does not replace independent human coding.",
        "",
        "| Field | Agreement | Cohen's kappa | Gwet's AC1 | Disagreements |",
        "|---|---:|---:|---:|---:|",
    ]
    for field in ENUMS:
        result = fields[field]
        lines.append(
            f"| {field.replace('_', ' ')} | "
            f"{result['agreements']}/{result['items']} "
            f"({100 * result['raw_agreement']:.1f}%) | "
            f"{fmt(result['cohen_kappa'])} | {fmt(result['gwet_ac1'])} | "
            f"{result['disagreements']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation rule",
            "",
            "Raw agreement is primary. Cohen's kappa is retained for familiarity",
            "and may be undefined when both coders use a single category. Gwet's",
            "AC1 is included as a prevalence-robust companion using each field's",
            "full pre-specified vocabulary.",
            "",
            "No taxonomy claim is upgraded to human-validated evidence on the basis",
            "of this comparison. Fields with substantive disagreement must remain",
            "qualified or undergo independent human adjudication.",
            "",
            "## What replicated",
            "",
            "Both coders assigned all 84 proposals to the same representational",
            "genre: natural-language, append-only, nonexecutable, operational",
            "guidance with no specified activation. They also agreed on failure",
            "specificity for 83/84 proposals and validation strategy for 82/84.",
            "These results support a robust descriptive claim about proposal form.",
            "",
            "Interpretive labels were less stable. Agreement was 59/84 for",
            "abstraction and evidence grounding, 63/84 for transfer scope, and",
            "47/84 for secondary target. The two coders assigned the same",
            "success-derived grounding totals, 39/42 direct-validated and 3/42",
            "inferred. For failure-derived proposals, Sol assigned 7/42",
            "direct-validated, 5/42 direct-unvalidated, and 30/42 inferred;",
            "Terra assigned 21/42, 6/42, and 15/42. The direction of the",
            "success-failure contrast replicated, while its magnitude did not.",
            "",
            "## Frozen inputs",
            "",
            f"- Coder A labels SHA-256: `{payload['labels_a']['sha256']}`",
            f"- Coder B labels SHA-256: `{payload['labels_b']['sha256']}`",
            "",
            "The machine-readable report preserves category distributions and every",
            "item-level disagreement in `analysis/taxonomy/coder-agreement.json`.",
            "",
        ]
    )
    args.output_md.resolve().write_text("\n".join(lines), encoding="utf-8")
    print(
        json.dumps(
            {
                "items": len(ids),
                "fields": len(fields),
                "disagreements": len(disagreements),
                "output_json": str(args.output_json.resolve()),
                "output_md": str(args.output_md.resolve()),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
