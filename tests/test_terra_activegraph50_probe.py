import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_terra_activegraph50_probe_is_labeled_and_arithmetic_is_complete() -> None:
    evidence = json.loads((ROOT / "evidence/terra_activegraph50_probe.json").read_text())
    totals = evidence["totals"]
    development = evidence["development_attempts"]
    retained = evidence["retained_states"]
    evolved = evidence["evolved_scores"]

    assert evidence["headline_eligible"] is False
    assert evidence["model"] == "gpt-5.6-terra"
    assert evidence["frozen_sol_study_overwritten"] is False
    assert evidence["interpretation"]["detected_recursive_uplift"] is False
    assert evidence["local_image_deviation"]["manifest_image"] != evidence["local_image_deviation"]["used_local_image"]

    attempt_calls = sum(row["model_calls"] for row in development)
    attempt_cost = sum(row["cost_usd"] for row in development)
    attempt_calls += sum(row["model_calls"] for row in evidence["cold_baseline"].get("attempts", []))
    attempt_cost += sum(row["cost_usd"] for row in evidence["cold_baseline"].get("attempts", []))
    for approach in evolved.values():
        for task_id, row in approach.items():
            if task_id.startswith("mean_"):
                continue
            attempt_calls += row["model_calls"]
            attempt_cost += row["cost_usd"]

    # Cold-baseline attempt totals are recorded only in the aggregate because
    # their detailed rows are in ignored raw artifacts.
    assert totals["attempt_model_calls"] == 141
    assert round(totals["attempt_cost_usd"], 6) == 4.900535
    assert attempt_calls < totals["attempt_model_calls"]
    assert attempt_cost < totals["attempt_cost_usd"]

    native_calls = sum(row["native_lineage_model_calls"] for row in retained.values())
    native_cost = sum(row["native_lineage_cost_usd"] for row in retained.values())
    assert totals["native_lineage_model_calls"] == native_calls
    assert round(totals["native_lineage_cost_usd"], 6) == round(native_cost, 6)
    assert totals["total_model_calls"] == (
        totals["attempt_model_calls"] + totals["reflection_model_calls"] + totals["native_lineage_model_calls"]
    )
    assert round(totals["total_cost_usd"], 6) == round(
        totals["attempt_cost_usd"] + totals["reflection_cost_usd"] + totals["native_lineage_cost_usd"],
        6,
    )
