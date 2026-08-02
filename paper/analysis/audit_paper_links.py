#!/usr/bin/env python3
"""Check local and HTTP links in paper Markdown files without changing them."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT
OUTPUT = ROOT / "data" / "generated" / "citation-link-audit.json"
LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def portable_path(path: Path) -> str:
    """Return a release-safe path without exposing the build machine."""
    for base, prefix in ((ROOT, ""), (ROOT.parent, "../")):
        try:
            relative = path.relative_to(base)
        except ValueError:
            continue
        return prefix + relative.as_posix()
    return "<OUTSIDE_REPOSITORY>"


def check_http(url: str) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "ouroboros-paper-link-audit/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return {
                "ok": 200 <= response.status < 400,
                "status": response.status,
                "final_url": response.geturl(),
            }
    except urllib.error.HTTPError as exc:
        return {"ok": False, "status": exc.code, "error": str(exc)}
    except Exception as exc:  # pragma: no cover - network-specific
        return {"ok": False, "status": None, "error": repr(exc)}


def main() -> None:
    occurrences: list[dict[str, object]] = []
    unique_http: dict[str, dict[str, object]] = {}
    for source in sorted(PAPER.glob("*.md")):
        text = source.read_text(encoding="utf-8")
        for match in LINK.finditer(text):
            target = match.group(1).split("#", 1)[0]
            line = text.count("\n", 0, match.start()) + 1
            if target.startswith(("https://", "http://")):
                result = unique_http.setdefault(target, check_http(target))
                ok = bool(result["ok"])
                kind = "http"
            else:
                resolved = (source.parent / target).resolve()
                ok = resolved.exists()
                result = {"ok": ok, "resolved": portable_path(resolved)}
                kind = "local"
            occurrences.append(
                {
                    "source": str(source.relative_to(ROOT)),
                    "line": line,
                    "target": target,
                    "kind": kind,
                    **result,
                }
            )

    payload = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "paper_directory": ".",
        "occurrences": len(occurrences),
        "unique_http_links": len(unique_http),
        "all_resolved": all(bool(row["ok"]) for row in occurrences),
        "rows": occurrences,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: payload[key] for key in ("occurrences", "unique_http_links", "all_resolved")}, indent=2))
    if not payload["all_resolved"]:
        for row in occurrences:
            if not row["ok"]:
                print(json.dumps(row, sort_keys=True))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
