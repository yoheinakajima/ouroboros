import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_terra_model_tier_calibration_is_labeled_and_sums() -> None:
    evidence = json.loads((ROOT / "evidence/terra_model_tier_calibration.json").read_text())
    runs = evidence["runs"]
    totals = evidence["totals"]
    hybrid_runs = [row for row in runs if row["approach"] == "hybrid_docs_grounded_pack"]
    hybrid_totals = evidence["hybrid_subset_totals"]

    assert evidence["headline_eligible"] is False
    assert evidence["candidate_model"] == "gpt-5.6-terra"
    assert evidence["primary_study_model"] == "gpt-5.6-sol"
    assert len(runs) == 4
    assert all(row["research_success"] is True for row in runs)
    assert all(row["author_attempts"] == 1 for row in runs)
    assert all(row["model_calls"] == 1 for row in runs)
    assert all(row["post_restart_transfer"]["passed"] == row["post_restart_transfer"]["total"] for row in runs)

    assert totals["model_calls"] == sum(row["model_calls"] for row in runs)
    assert totals["input_tokens"] == sum(row["input_tokens"] for row in runs)
    assert totals["output_tokens"] == sum(row["output_tokens"] for row in runs)
    assert round(totals["cost_usd"], 7) == round(sum(row["cost_usd"] for row in runs), 7)
    assert round(totals["elapsed_seconds"], 6) == round(sum(row["elapsed_seconds"] for row in runs), 6)

    assert hybrid_totals["model_calls"] == sum(row["model_calls"] for row in hybrid_runs)
    assert hybrid_totals["input_tokens"] == sum(row["input_tokens"] for row in hybrid_runs)
    assert hybrid_totals["output_tokens"] == sum(row["output_tokens"] for row in hybrid_runs)
    assert round(hybrid_totals["cost_usd"], 7) == round(sum(row["cost_usd"] for row in hybrid_runs), 7)
