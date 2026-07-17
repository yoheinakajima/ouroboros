import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_swe_canary_keeps_calibration_and_capability_claims_separate() -> None:
    evidence = json.loads((ROOT / "evidence/swe_canary_workspace_v1_2.json").read_text())
    attempts = evidence["attempts"]
    assert evidence["headline_eligible"] is False
    assert evidence["split"] == "development"
    assert attempts[0]["model_calls"] == 0
    assert attempts[0]["valid_model_attempt"] is False
    assert attempts[1]["official_resolved"] is False
    assert attempts[2]["protocol_version"] == "0.5-local-frozen"
    assert attempts[2]["official_resolved"] is True
    assert attempts[2]["fail_to_pass"] == {"success": 1, "failure": 0}
    assert attempts[2]["pass_to_pass"] == {"success": 137, "failure": 0}
    assert evidence["paid_totals"]["model_calls"] == sum(row.get("model_calls", 0) for row in attempts)
    assert evidence["security"]["provider_credentials_forwarded_to_task"] is False
    assert evidence["reproducibility_limit"]["official_grader_fully_offline_hermetic"] is False
