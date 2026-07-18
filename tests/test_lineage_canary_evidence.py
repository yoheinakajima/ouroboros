import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_lineage_canary_is_labeled_and_arithmetic_is_complete() -> None:
    evidence = json.loads((ROOT / "evidence/lineage_builder_canary.json").read_text())
    builders = evidence["builders"]
    reflection = evidence["reflection"]
    totals = evidence["paid_totals"]

    assert evidence["headline_eligible"] is False
    assert evidence["source_experience"]["shared_builder_calibration_only"] is True
    assert evidence["protocol_root_sha256"] == "a70921db5e05875a0eacf18d535c560bc82d02f46c71b729f7308c503452dad0"
    assert evidence["reproducibility_limit"]["generated_from_clean_protocol_commit"] is False
    assert builders["minimal_v2"]["additional_model_calls"] == 0
    assert builders["hybrid_packs"]["public"] == {"passed": 1, "total": 1}
    assert builders["hybrid_packs"]["private"] == {"passed": 1, "total": 1}
    assert builders["hybrid_packs"]["post_restart_transfer"] == {"passed": 1, "total": 1}
    assert builders["hybrid_packs"]["credentials_forwarded_to_pack_process"] is False
    assert builders["workspace_v1_2"]["invalid_timeout_attempt"]["retained_state_promoted"] is False
    assert builders["workspace_v1_2"]["valid_retry"]["candidate_public"]["passed"] == 4
    assert builders["workspace_v1_2"]["valid_retry"]["candidate_private"]["passed"] == 4

    component_cost = (
        reflection["cost_usd"]
        + builders["minimal_v2"]["cost_usd"]
        + builders["hybrid_packs"]["cost_usd"]
        + builders["workspace_v1_2"]["invalid_timeout_attempt"]["cost_usd"]
        + builders["workspace_v1_2"]["valid_retry"]["cost_usd"]
    )
    assert round(component_cost, 6) == totals["lineage_only_cost_usd"]
    assert round(totals["lineage_only_cost_usd"] + totals["prior_source_task_cost_usd"], 6) == totals[
        "source_plus_lineage_cost_usd"
    ]
