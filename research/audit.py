"""Validate and hash-seal complete benchmark attempt bundles."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from research.broker import verify_journal
from research.contracts import AttemptRecord, ScoreRecord


def _inside(root: Path, relative: str) -> Path:
    path = (root / relative).resolve(strict=True)
    if root != path and root not in path.parents:
        raise ValueError(f"bundle path escapes its root: {relative}")
    return path


def verify_attempt_bundle(
    bundle: str | Path,
    *,
    forbidden_canaries: tuple[str, ...] = (),
) -> dict[str, Any]:
    root = Path(bundle).resolve(strict=True)
    attempt_path = root / "attempt.json"
    attempt = AttemptRecord.model_validate_json(attempt_path.read_text(encoding="utf-8"))
    trace = _inside(root, attempt.trace_path)
    journal = verify_journal(trace)
    lines = trace.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise ValueError("attempt broker journal is empty")
    last_usage = json.loads(lines[-1])["usage_after"]
    recorded_usage = attempt.usage.model_dump(mode="json")
    for field in ("model_calls", "input_tokens", "output_tokens", "tool_calls"):
        if int(last_usage[field]) != int(recorded_usage[field]):
            raise ValueError(f"attempt usage mismatch for {field}")
    for field in ("cost_usd",):
        if abs(float(last_usage[field]) - float(recorded_usage[field])) > 1e-9:
            raise ValueError(f"attempt usage mismatch for {field}")
    if attempt.submission_path:
        _inside(root, attempt.submission_path)
    score_path = root / "grader" / "score.json"
    score = None
    if score_path.is_file():
        score = ScoreRecord.model_validate_json(score_path.read_text(encoding="utf-8"))
        if score.run_id != attempt.run_id:
            raise ValueError("attempt and grader run_id differ")
    raw = b"\n".join(path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file())
    for canary in forbidden_canaries:
        if canary.encode() in raw:
            raise ValueError("forbidden evaluator canary leaked into attempt bundle")
    files = {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != "audit.json"
    }
    return {
        "schema_version": 1,
        "valid": True,
        "run_id": attempt.run_id,
        "status": attempt.status,
        "journal": journal,
        "has_score": score is not None,
        "files": files,
    }


def seal_attempt_bundle(bundle: str | Path, *, forbidden_canaries: tuple[str, ...] = ()) -> dict[str, Any]:
    root = Path(bundle).resolve(strict=True)
    report = verify_attempt_bundle(root, forbidden_canaries=forbidden_canaries)
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"))
    report["seal_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    output = root / "audit.json"
    temporary = output.with_name(output.name + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(output)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--forbidden-canary", action="append", default=[])
    args = parser.parse_args(argv)
    report = seal_attempt_bundle(args.bundle, forbidden_canaries=tuple(args.forbidden_canary))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
