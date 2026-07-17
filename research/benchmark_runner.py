#!/usr/bin/env python3
"""Benchmark control plane: no-model smoke, readiness, and scored-run lock."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from research.readiness import inspect_readiness
from research.smoke import run_all


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--dry-run", action="store_true", help="show readiness without executing an approach")
    parser.add_argument("--calibration-smoke", action="store_true", help="run six no-model local grading paths")
    parser.add_argument("--output", type=Path, help="receipt path for --calibration-smoke")
    parser.add_argument("--execute", action="store_true", help="request scored execution after the freeze gate passes")
    args = parser.parse_args(argv)
    if args.calibration_smoke:
        result = run_all(output=args.output)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["passed"] else 1
    report = inspect_readiness(args.root)
    if args.dry_run or not args.execute:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["ready_for_oracle_calibration"] else 1
    if not report["ready"]:
        raise SystemExit("benchmark execution refused: run `python -m research.readiness` for blockers")
    raise SystemExit(
        "global scheduling is intentionally manual in protocol v0.3; use `python -m research.attempt_runner` "
        "for each frozen task/arm/replication and retain every bundle"
    )


if __name__ == "__main__":
    raise SystemExit(main())
