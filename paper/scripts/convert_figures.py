#!/usr/bin/env python3
"""Convert release SVG figures to vector PDF files for the LaTeX build."""

from __future__ import annotations

import argparse
from pathlib import Path

from reportlab.graphics import renderPDF
from svglib.svglib import svg2rlg


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Paper release root.",
    )
    args = parser.parse_args()
    source = args.root.resolve() / "figures"
    output = source / "pdf"
    output.mkdir(parents=True, exist_ok=True)

    converted = 0
    for svg_path in sorted(source.glob("figure-*.svg")):
        drawing = svg2rlg(str(svg_path))
        if drawing is None:
            raise SystemExit(f"unable to parse {svg_path}")
        pdf_path = output / f"{svg_path.stem}.pdf"
        renderPDF.drawToFile(drawing, str(pdf_path))
        if pdf_path.stat().st_size < 1_000:
            raise SystemExit(f"suspiciously small output: {pdf_path}")
        print(f"{svg_path.name} -> {pdf_path.relative_to(args.root)}")
        converted += 1
    if converted != 5:
        raise SystemExit(f"expected 5 figures, converted {converted}")


if __name__ == "__main__":
    main()
