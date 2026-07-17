#!/usr/bin/env python3
"""No-model calibration of six task-family grading and audit paths."""

from __future__ import annotations

import argparse
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from research.audit import seal_attempt_bundle
from research.broker import AuthorityBroker, BrokerBudget, BrokerConfig
from research.contracts import AttemptRecord, ResourceUsage
from research.grading import GraderSpec, SealedGrader

CALIBRATION_IMAGE = (
    "python@sha256:db3ff2e1800a8581e2c48a27c3995339d47bdf046da21c7627accd3d51053a93"
)
FAMILY_FIXTURES: dict[str, dict[str, Any]] = {
    "swe": {"fixed": ["parser", "regression"], "tests": 2},
    "terminal": {"artifact": "normalized.log", "exit_code": 0},
    "mle": {"metric": "mae", "seed": 0.42, "candidate": 0.19},
    "rebench": {"correct": True, "speedup": 2.5},
    "paperbench": {"rubric": {"method": 1, "experiment": 1, "report": 1}},
    "activegraph": {"checks_passed": 50, "replay": True, "relations": 7},
}

GRADER_SOURCE = """\
import json
import os
from pathlib import Path

grader = Path('/grader')
submission = Path(os.environ['OUROBOROS_SUBMISSION'])
score_path = Path(os.environ['OUROBOROS_SCORE_PATH'])
expected = json.loads((grader / 'expected.json').read_text())
actual = json.loads((submission / 'answer.json').read_text())
passed = actual == expected
score = {
    'run_id': os.environ['OUROBOROS_RUN_ID'],
    'grader_id': 'ouroboros-calibration-fixture',
    'grader_revision': 'fixture-v1',
    'primary_score': 1.0 if passed else 0.0,
    'passed': passed,
    'components': {'exact_match': int(passed)},
}
score_path.write_text(json.dumps(score, sort_keys=True))
"""


def run_family(family: str, *, root: Path) -> dict[str, Any]:
    if family not in FAMILY_FIXTURES:
        raise ValueError(f"unknown calibration family: {family}")
    run_id = f"calibration-{family}"
    bundle = root / "bundles" / family
    submission = bundle / "submission"
    submission.mkdir(parents=True)
    (submission / "answer.json").write_text(
        json.dumps(FAMILY_FIXTURES[family], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    trace = bundle / "trace.jsonl"
    broker = AuthorityBroker(
        BrokerConfig(
            workspace=submission,
            trace_path=trace,
            image=CALIBRATION_IMAGE,
            budget=BrokerBudget(
                max_cost_usd=0,
                max_wall_seconds=60,
                max_model_calls=0,
                max_output_tokens=0,
                max_tool_calls=2,
            ),
        )
    )
    broker.list_files()
    now = datetime.now(UTC).isoformat()
    attempt = AttemptRecord(
        run_id=run_id,
        approach_id="calibration_oracle",
        study_id="harness_calibration",
        suite_id=f"fixture_{family}",
        task_id=f"fixture_{family}",
        arm="cold",
        replication=1,
        seed=0,
        model="none",
        task_image_digest=CALIBRATION_IMAGE,
        approach_source_hashes={},
        started_at=now,
        finished_at=now,
        status="completed",
        usage=ResourceUsage.model_validate(broker.usage.model_dump()),
        trace_path="trace.jsonl",
        submission_path="submission",
        metadata={"calibration_only": True, "family": family},
    )
    (bundle / "attempt.json").write_text(attempt.model_dump_json(indent=2) + "\n", encoding="utf-8")
    grader = root / "sealed" / family
    grader.mkdir(parents=True)
    (grader / "grader.py").write_text(GRADER_SOURCE, encoding="utf-8")
    (grader / "expected.json").write_text(
        json.dumps(FAMILY_FIXTURES[family], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    score = SealedGrader(
        GraderSpec(
            grader_id="ouroboros-calibration-fixture",
            grader_revision="fixture-v1",
            image=CALIBRATION_IMAGE,
            command=["python", "/grader/grader.py"],
            minimum_score=0,
            maximum_score=1,
            limits={"wall_seconds": 30, "memory_mb": 128, "cpus": 1, "pids": 32, "tmpfs_mb": 32},
        )
    ).grade(
        run_id=run_id,
        grader_workspace=grader,
        submission=submission,
        output_dir=bundle / "grader",
    )
    audit = seal_attempt_bundle(bundle, forbidden_canaries=("OUROBOROS_PRIVATE_CALIBRATION_CANARY",))
    return {
        "family": family,
        "passed": score.passed is True,
        "score": score.primary_score,
        "audit_valid": audit["valid"],
        "audit_seal_sha256": audit["seal_sha256"],
    }


def run_all(*, output: str | Path | None = None) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix=".ouroboros-calibration-", dir=Path.cwd()) as temporary:
        root = Path(temporary)
        results = [run_family(family, root=root) for family in FAMILY_FIXTURES]
    report = {
        "schema_version": 1,
        "calibration_only": True,
        "upstream_tasks_executed": False,
        "purpose": (
            "Verify broker-journal, sealed-grader, score-record, and audit plumbing; "
            "never report as capability evidence."
        ),
        "model_calls": 0,
        "image": CALIBRATION_IMAGE,
        "families": results,
        "passed": all(row["passed"] and row["audit_valid"] for row in results),
    }
    if output:
        target = Path(output)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + ".tmp")
        temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(target)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = run_all(output=args.output)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
