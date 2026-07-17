#!/usr/bin/env python3
"""Locked benchmark entrypoint. It refuses all execution until preflight passes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from research.readiness import inspect_readiness


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--dry-run", action="store_true", help="show the frozen design without executing an approach")
    args = parser.parse_args(argv)
    report = inspect_readiness(args.root)
    if args.dry_run:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    if not report["ready"]:
        raise SystemExit("benchmark execution refused: run `python -m research.readiness` for blockers")
    raise SystemExit("benchmark execution is not implemented; unlock only after frozen adapter review")


if __name__ == "__main__":
    raise SystemExit(main())
