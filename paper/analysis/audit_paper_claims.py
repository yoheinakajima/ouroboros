#!/usr/bin/env python3
"""Machine-check central paper claims against frozen analytical artifacts."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT
GENERATED = ROOT / "data" / "generated"
OUTPUT = GENERATED / "paper-claim-audit.json"


class Audit:
    def __init__(self) -> None:
        self.rows: list[dict[str, object]] = []

    def check(self, claim: str, observed: object, expected: object) -> None:
        if isinstance(expected, float) and isinstance(observed, (float, int)):
            ok = math.isclose(float(observed), expected, rel_tol=1e-9, abs_tol=1e-9)
        else:
            ok = observed == expected
        self.rows.append(
            {"claim": claim, "ok": ok, "observed": observed, "expected": expected}
        )

    def truth(self, claim: str, value: object) -> None:
        self.rows.append({"claim": claim, "ok": bool(value), "observed": value, "expected": True})


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    audit = Audit()
    primary = read_json(ROOT / "data" / "report-probe-adjudicated.json")
    metrics = read_json(GENERATED / "posthoc-metrics.json")
    taxonomy = read_json(ROOT / "data" / "taxonomy" / "taxonomy-summary.json")
    citations = read_json(GENERATED / "citation-link-audit.json")

    audit.check("held-out rows", primary["attempts"], 228)
    audit.check("final valid rows", primary["valid_attempts"], 228)
    audit.check("raw immediately valid rows", primary["raw_valid_attempts"], 215)
    audit.check("held-out model cost", primary["cost_usd"], 194.068625)
    audit.check(
        "adjudicated dataset hash",
        primary["adjudicated_results_sha256"],
        "c83e750719972d2e0dcb5e3514f190c372eb984ab305f00883480fa36ef28afa",
    )
    for approach, result in primary["comparison"]["recursive_claims"].items():
        audit.check(f"{approach} strong evidence threshold", result["strong_evidence_threshold_met"], False)

    noise = metrics["equivalent_control_noise"]["all_families"]
    audit.check("held-out tasks", noise["tasks"], 19)
    audit.check("stable equivalent-input tasks", noise["stable_tasks"], 12)
    audit.check("variable equivalent-input tasks", noise["variable_tasks"], 7)
    audit.check("fixed equivalent passes", noise["fixed_pass_tasks"], 10)
    audit.check("fixed equivalent failures", noise["fixed_fail_tasks"], 2)
    audit.check(
        "evolved outcomes outside exact task range",
        noise["evolved_task_architecture_results_outside_task_specific_equivalent_range"],
        1,
    )
    outside = noise["outside_range_results"][0]
    audit.check("outside-range architecture", outside["approach_id"], "minimal_v2")
    audit.check(
        "outside-range task",
        outside["task_id"],
        "scikit-learn__scikit-learn-13124",
    )
    audit.check("outside-range evolved score", outside["score"], 0.0)
    audit.check("outside-range equivalent minimum", outside["equivalent_minimum"], 1.0)

    profiles = {row["approach_id"]: row for row in metrics["expression_profiles"]}
    audit.check("Workspace per-task reach", profiles["workspace_v1_2"]["semantic_unit_reach_per_task"], 18 / 85)
    audit.check("Workspace corpus reach", profiles["workspace_v1_2"]["corpus_unit_reach_across_probe"], 18 / 85)
    audit.check("Minimal per-task reach", profiles["minimal_v2"]["semantic_unit_reach_per_task"], 1.0)
    audit.check("Minimal procedures", profiles["minimal_v2"]["procedures"], 13)
    audit.check("Minimal receipts", profiles["minimal_v2"]["evidence_receipts"], 28)
    audit.check("Minimal capabilities", profiles["minimal_v2"]["capabilities"], 0)
    audit.check("Hybrid per-task reach", profiles["hybrid_packs"]["semantic_unit_reach_per_task"], 0.12)
    audit.check("Hybrid corpus reach", profiles["hybrid_packs"]["corpus_unit_reach_across_probe"], 0.68)
    audit.check("Hybrid adaptivity gap", profiles["hybrid_packs"]["adaptivity_gap"], 0.56)

    memory = metrics["hybrid_memory"]
    audit.check("Hybrid failure retrieval slots", memory["failing_retrieval_slots"], 37)
    audit.check("Hybrid retrieval slots", memory["retrieval_slots"], 57)
    audit.check("Hybrid vocabulary Spearman", memory["index_vocabulary_retrieval_spearman"], 0.7529810985482163)
    ols = memory["retrieval_on_index_vocabulary_and_failure_ols"]
    audit.check("Hybrid adjusted vocabulary coefficient", ols["index_vocabulary_coefficient"], 0.19419237749546506)
    audit.check("Hybrid adjusted failure coefficient", ols["failure_flag_coefficient"], -0.09310344827588779)
    audit.check("Hybrid stratified permutation draws", ols["permutations"], 50_000)

    audit.check("taxonomy items", taxonomy["items"], 84)
    audit.check(
        "taxonomy label freeze hash",
        taxonomy["labels_sha256_before_unblinding"],
        "9290e7358b1b2d384805e75be7cc612d1dce6a0d8699ed27ac4f7193e433a667",
    )
    overall = taxonomy["overall"]
    audit.check("natural-language proposals", overall["representational_form"]["counts"], {"natural_language": 84})
    audit.check("append proposals", overall["consolidation_operation"]["counts"], {"append": 84})
    audit.check("nonexecutable proposals", overall["executable_status"]["counts"], {"nonexecutable": 84})
    audit.check("procedure targets", overall["primary_update_target"]["counts"]["procedure"], 76)
    audit.check("validation-asset targets", overall["primary_update_target"]["counts"]["validation_asset"], 8)

    audit.truth("all citation and local links resolve", citations["all_resolved"])
    for number in range(1, 6):
        figures = list((PAPER / "figures").glob(f"figure-{number}-*.svg"))
        audit.check(f"Figure {number} exists exactly once", len(figures), 1)
        if figures:
            audit.truth(f"Figure {number} is nonempty", figures[0].stat().st_size > 1_000)

    paper_text = "\n".join(path.read_text(encoding="utf-8") for path in PAPER.glob("*.md"))
    audit.check("retired concept name absent", "adapter bottleneck" in paper_text.lower(), False)
    audit.check(
        "empirical pairwise values not called assumption-free null",
        "is an assumption-free null" in paper_text.lower(),
        False,
    )

    payload = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "checks": len(audit.rows),
        "passed": sum(bool(row["ok"]) for row in audit.rows),
        "all_passed": all(bool(row["ok"]) for row in audit.rows),
        "rows": audit.rows,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {key: payload[key] for key in ("checks", "passed", "all_passed")},
            indent=2,
        )
    )
    if not payload["all_passed"]:
        for row in audit.rows:
            if not row["ok"]:
                print(json.dumps(row, sort_keys=True))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
