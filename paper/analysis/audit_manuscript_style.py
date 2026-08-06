#!/usr/bin/env python3
"""Audit locked manuscript terminology, voice, and caption requirements."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = ROOT / "MANUSCRIPT.md"
CAPTIONS = ROOT / "FIGURE_CAPTIONS.md"
POINTED_SENTENCE = (
    "It is currently unknown how many published self-improvement effects "
    "would survive them."
)


def count_pattern(text: str, pattern: str, flags: int = 0) -> int:
    return len(re.findall(pattern, text, flags))


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def main() -> None:
    if not MANUSCRIPT.exists():
        raise SystemExit(f"missing manuscript: {MANUSCRIPT}")
    manuscript = MANUSCRIPT.read_text(encoding="utf-8")
    captions = CAPTIONS.read_text(encoding="utf-8")
    combined = manuscript + "\n" + captions
    normalized_manuscript = normalize_whitespace(manuscript)

    checks: list[tuple[str, bool, str]] = []

    checks.append(
        ("no em dash", "—" not in combined, f"count={combined.count('—')}")
    )
    for word in ("genuinely", "honestly", "actually"):
        count = count_pattern(combined, rf"\b{word}\b", re.IGNORECASE)
        checks.append((f"banned word: {word}", count == 0, f"count={count}"))

    prohibited_terms = ("mutation taxonomy", "adapter bottleneck")
    for phrase in prohibited_terms:
        count = combined.lower().count(phrase)
        checks.append((f"prohibited term: {phrase}", count == 0, f"count={count}"))

    contrast_hits = re.findall(
        r"\bnot\b[^.!?\n]{0,100}\bbut\b", combined, flags=re.IGNORECASE
    )
    checks.append(
        (
            "no single-sentence not-X-but-Y contrast",
            not contrast_hits,
            f"count={len(contrast_hits)}",
        )
    )

    pointed_count = normalized_manuscript.count(POINTED_SENTENCE)
    checks.append(
        (
            "external-effects insinuation absent",
            pointed_count == 0,
            f"count={pointed_count}",
        )
    )

    for term in (
        "expression bottleneck",
        "expression profile",
        "equivalent duplicates",
        "control ladder",
        "failure-memory stickiness",
        "update-proposal taxonomy",
    ):
        count = manuscript.lower().count(term)
        checks.append((f"required term: {term}", count >= 1, f"count={count}"))

    figure_one = normalize_whitespace(
        captions.split("## Figure 2:", maxsplit=1)[0]
    ).lower()
    for construct in (
        "retention",
        "expression",
        "behavioral mediation",
        "task improvement",
        "recursive improvement",
    ):
        checks.append(
            (
                f"Figure 1 construct: {construct}",
                construct in figure_one,
                f"present={construct in figure_one}",
            )
        )

    figure_three = normalize_whitespace(
        captions.split("## Figure 3:", maxsplit=1)[-1].split(
            "## Figure 4:", maxsplit=1
        )[0]
    ).lower()
    required_figure_three = (
        "15 dependent absolute pairwise label-mean gaps",
        "descriptive rather than a formal significance threshold",
    )
    for phrase in required_figure_three:
        checks.append(
            (
                f"Figure 3 hedge: {phrase}",
                phrase in figure_three,
                f"present={phrase in figure_three}",
            )
        )

    failures = [row for row in checks if not row[1]]
    for name, passed, detail in checks:
        status = "PASS" if passed else "FAIL"
        print(f"{status}: {name} ({detail})")
    print(f"\n{len(checks) - len(failures)}/{len(checks)} checks passed")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
