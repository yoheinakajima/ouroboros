#!/usr/bin/env python3
"""Generate publication-oriented SVG Figures 1–5 from frozen study artifacts.

Uses only the Python standard library. Every numeric figure reads generated
tables produced by posthoc_quantitative.py; no values are hand-entered except
diagram labels and axis limits.
"""

from __future__ import annotations

import csv
import html
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "data" / "generated"
OUTPUT = ROOT / "figures"
COLORS = {
    "workspace_v1_2": "#0072B2",
    "minimal_v2": "#E69F00",
    "hybrid_packs": "#009E73",
    "failure": "#D55E00",
    "pass": "#56B4E9",
    "ink": "#202124",
    "muted": "#62666A",
    "grid": "#D8DADD",
    "light": "#F2F4F5",
    "white": "#FFFFFF",
    "highlight": "#CC79A7",
}
LABELS = {
    "workspace_v1_2": "Workspace",
    "minimal_v2": "Minimal",
    "hybrid_packs": "Hybrid",
}
SUITE_LABELS = {
    "ouro_swe_50": "SWE-bench Verified subset",
    "ouro_terminal_12": "Terminal tasks",
    "ouro_activegraph_50": "ActiveGraph tasks",
}


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


class SVG:
    def __init__(self, width: int, height: int, title: str, description: str) -> None:
        self.width = width
        self.height = height
        self.parts = [
            (
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
                f'height="{height}" viewBox="0 0 {width} {height}" role="img" '
                f'aria-labelledby="title desc">'
            ),
            f"<title id=\"title\">{esc(title)}</title>",
            f"<desc id=\"desc\">{esc(description)}</desc>",
            "<defs>",
            (
                '<marker id="arrow" markerWidth="10" markerHeight="8" '
                'refX="9" refY="4" orient="auto">'
                f'<path d="M0,0 L10,4 L0,8 Z" fill="{COLORS["muted"]}"/>'
                "</marker>"
            ),
            "</defs>",
            (
                "<style>"
                "text{font-family:Arial,Helvetica,sans-serif;fill:#202124}"
                ".title{font-size:30px;font-weight:700}"
                ".subtitle{font-size:17px;fill:#62666A}"
                ".panel{font-size:21px;font-weight:700}"
                ".label{font-size:16px}"
                ".small{font-size:13px;fill:#62666A}"
                ".tiny{font-size:11px;fill:#62666A}"
                ".value{font-size:15px;font-weight:700}"
                ".axis{stroke:#62666A;stroke-width:1}"
                ".grid{stroke:#D8DADD;stroke-width:1}"
                "</style>"
            ),
            f'<rect width="{width}" height="{height}" fill="{COLORS["white"]}"/>',
        ]

    def add(self, value: str) -> None:
        self.parts.append(value)

    def text(
        self,
        x: float,
        y: float,
        value: Any,
        *,
        css: str = "label",
        anchor: str = "start",
        rotate: float | None = None,
        fill: str | None = None,
    ) -> None:
        transform = f' transform="rotate({rotate} {x} {y})"' if rotate is not None else ""
        color = f' fill="{fill}"' if fill else ""
        self.add(
            f'<text x="{x:.1f}" y="{y:.1f}" class="{css}" '
            f'text-anchor="{anchor}"{transform}{color}>{esc(value)}</text>'
        )

    def line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        *,
        stroke: str | None = None,
        width: float = 1,
        dash: str | None = None,
        arrow: bool = False,
        opacity: float = 1.0,
    ) -> None:
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        marker = ' marker-end="url(#arrow)"' if arrow else ""
        self.add(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{stroke or COLORS["ink"]}" stroke-width="{width}" '
            f'opacity="{opacity}"{dash_attr}{marker}/>'
        )

    def rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        fill: str = "none",
        stroke: str = "none",
        stroke_width: float = 1,
        radius: float = 0,
        opacity: float = 1.0,
    ) -> None:
        self.add(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}" '
            f'rx="{radius:.1f}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{stroke_width}" opacity="{opacity}"/>'
        )

    def circle(
        self,
        x: float,
        y: float,
        radius: float,
        *,
        fill: str,
        stroke: str = "none",
        stroke_width: float = 1,
        opacity: float = 1.0,
    ) -> None:
        self.add(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{stroke_width}" opacity="{opacity}"/>'
        )

    def polyline(
        self,
        points: Iterable[tuple[float, float]],
        *,
        stroke: str,
        width: float = 2,
        fill: str = "none",
    ) -> None:
        value = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        self.add(
            f'<polyline points="{value}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"/>'
        )

    def marker(
        self,
        x: float,
        y: float,
        *,
        approach: str,
        size: float = 8,
        fill: str | None = None,
        stroke: str | None = None,
        stroke_width: float = 1.5,
    ) -> None:
        color = fill or COLORS[approach]
        outline = stroke or COLORS["white"]
        if approach == "workspace_v1_2":
            points = f"{x:.1f},{y-size:.1f} {x-size:.1f},{y+size:.1f} {x+size:.1f},{y+size:.1f}"
            self.add(
                f'<polygon points="{points}" fill="{color}" stroke="{outline}" '
                f'stroke-width="{stroke_width}"/>'
            )
        elif approach == "minimal_v2":
            points = (
                f"{x:.1f},{y-size:.1f} {x+size:.1f},{y:.1f} "
                f"{x:.1f},{y+size:.1f} {x-size:.1f},{y:.1f}"
            )
            self.add(
                f'<polygon points="{points}" fill="{color}" stroke="{outline}" '
                f'stroke-width="{stroke_width}"/>'
            )
        else:
            self.rect(
                x - size,
                y - size,
                size * 2,
                size * 2,
                fill=color,
                stroke=outline,
                stroke_width=stroke_width,
                radius=1.5,
            )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        value = "\n".join([*self.parts, "</svg>", ""])
        path.write_text(value, encoding="utf-8")


def figure_header(svg: SVG, number: int, title: str, subtitle: str) -> None:
    svg.text(60, 55, f"Figure {number}. {title}", css="title")
    svg.text(60, 84, subtitle, css="subtitle")


def figure_1() -> None:
    svg = SVG(
        1600,
        790,
        "Figure 1. The expression bottleneck",
        "Three native self-modifying states pass through a shared evaluation interface before a shared agent and external grader.",
    )
    figure_header(
        svg,
        1,
        "The expression bottleneck",
        "Persistent change is filtered before it can affect action; each arrow is a distinct empirical claim.",
    )
    columns = [
        (70, 230, "Development\nexperience"),
        (350, 270, "Native retained state"),
        (710, 230, "Evaluation\nadapter"),
        (1010, 240, "Task-visible\nsurface"),
        (1315, 210, "Shared agent\n+ grader"),
    ]
    for x, width, label in columns:
        lines = label.split("\n")
        svg.rect(x, 125, width, 76, fill=COLORS["light"], stroke=COLORS["grid"], radius=10)
        for index, line in enumerate(lines):
            svg.text(x + width / 2, 157 + 21 * index, line, css="panel", anchor="middle")

    rows_y = [270, 430, 590]
    native = [
        ("workspace_v1_2", "Arbitrary workspace", "85 eligible files"),
        ("minimal_v2", "Procedure store", "13 procedures + 28 receipts"),
        ("hybrid_packs", "ActiveGraph Pack", "25 embedded lessons"),
    ]
    adapters = [
        ("Priority + alphabetical\n64 KB serialization", "static"),
        ("Full semantic export", "static"),
        ("Automatic top-3\nlexical retrieval", "task-adaptive"),
    ]
    surfaces = [
        ("18/85 files", "text only"),
        ("41/41 items", "text only"),
        ("3/25 lessons", "Pack executes, then text"),
    ]
    for y, (approach, title, detail), (adapter, mode), (surface, surface_detail) in zip(
        rows_y, native, adapters, surfaces
    ):
        color = COLORS[approach]
        svg.text(80, y + 20, LABELS[approach], css="panel", fill=color)
        svg.line(300, y, 345, y, stroke=color, width=4, arrow=True)
        svg.rect(350, y - 42, 270, 84, fill=COLORS["white"], stroke=color, stroke_width=3, radius=10)
        svg.text(485, y - 5, title, css="panel", anchor="middle")
        svg.text(485, y + 22, detail, css="small", anchor="middle")
        svg.line(620, y, 705, y, stroke=color, width=4, arrow=True)
        svg.rect(710, y - 48, 230, 96, fill=COLORS["light"], stroke=color, stroke_width=2, radius=10)
        for index, line in enumerate(adapter.split("\n")):
            svg.text(825, y - 12 + index * 21, line, css="label", anchor="middle")
        svg.text(825, y + 36, mode, css="small", anchor="middle")
        svg.line(940, y, 1005, y, stroke=color, width=4, arrow=True)
        svg.rect(1010, y - 42, 240, 84, fill=COLORS["white"], stroke=color, stroke_width=3, radius=10)
        svg.text(1130, y - 5, surface, css="panel", anchor="middle")
        svg.text(1130, y + 22, surface_detail, css="small", anchor="middle")
        svg.line(1250, y, 1310, y, stroke=color, width=4, arrow=True)
        svg.rect(1315, y - 42, 210, 84, fill=COLORS["white"], stroke=COLORS["ink"], radius=10)
        svg.text(1420, y - 5, "Sol outer agent", css="label", anchor="middle")
        svg.text(1420, y + 22, "external grader", css="small", anchor="middle")

    svg.rect(686, 215, 278, 430, fill="none", stroke=COLORS["highlight"], stroke_width=3, radius=18)
    svg.text(825, 678, "EXPRESSION BOTTLENECK", css="panel", anchor="middle", fill=COLORS["highlight"])
    svg.text(
        825,
        706,
        "Native structure becomes a narrower observation/action surface",
        css="subtitle",
        anchor="middle",
    )
    claims = [
        ("self-modification", 430),
        ("expression", 760),
        ("behavior", 1070),
        ("task score", 1380),
    ]
    for label, x in claims:
        svg.text(x, 758, label, css="small", anchor="middle")
    svg.save(OUTPUT / "figure-1-expression-bottleneck.svg")


def axis_ticks(
    svg: SVG,
    *,
    x: float,
    y: float,
    width: float,
    maximum: float,
    ticks: list[float],
    percent: bool = True,
) -> None:
    svg.line(x, y, x + width, y, stroke=COLORS["muted"])
    for tick in ticks:
        tx = x + width * tick / maximum
        svg.line(tx, y - 6, tx, y + 6, stroke=COLORS["muted"])
        label = f"{tick * 100:.0f}%" if percent else f"{tick:g}"
        svg.text(tx, y + 25, label, css="small", anchor="middle")


def figure_2() -> None:
    data = rows(GENERATED / "expression-profile.csv")
    by_approach = {row["approach_id"]: row for row in data}
    svg = SVG(
        1600,
        1120,
        "Figure 2. Expression profiles are multidimensional",
        "Five panels compare storage reach, eligible payload reach, semantic reach, adaptivity, and execution reach for three architectures.",
    )
    figure_header(
        svg,
        2,
        "Expression profiles are multidimensional",
        "Minimal's 1.35% storage reach coexists with 100% semantic reach; no single byte ratio is sufficient.",
    )
    approaches = list(LABELS)
    left = 250
    chart_width = 1120
    panel_tops = [140, 315, 490, 700]
    metrics = [
        ("A  Storage reach", "storage_reach", 0.16, [0, 0.04, 0.08, 0.12, 0.16]),
        ("B  Eligible-payload reach", "eligible_payload_reach", 1.0, [0, 0.25, 0.5, 0.75, 1.0]),
    ]
    for panel_top, (panel_title, key, maximum, ticks) in zip(panel_tops[:2], metrics):
        svg.text(60, panel_top, panel_title, css="panel")
        axis_y = panel_top + 130
        axis_ticks(svg, x=left, y=axis_y, width=chart_width, maximum=maximum, ticks=ticks)
        for index, approach in enumerate(approaches):
            row = by_approach[approach]
            y = panel_top + 38 + index * 30
            value = float(row[key])
            svg.text(left - 20, y + 5, LABELS[approach], css="label", anchor="end")
            svg.rect(left, y - 8, chart_width * value / maximum, 16, fill=COLORS[approach], radius=3)
            svg.text(
                left + chart_width * value / maximum + 10,
                y + 5,
                f"{value * 100:.2f}%",
                css="value",
            )

    panel_top = panel_tops[2]
    svg.text(60, panel_top, "C  Semantic reach: per task versus across the corpus", css="panel")
    axis_y = panel_top + 165
    axis_ticks(svg, x=left, y=axis_y, width=chart_width, maximum=1.0, ticks=[0, 0.25, 0.5, 0.75, 1.0])
    for index, approach in enumerate(approaches):
        row = by_approach[approach]
        y = panel_top + 42 + index * 38
        per_task = float(row["semantic_unit_reach_per_task"])
        corpus = float(row["corpus_unit_reach_across_probe"])
        svg.text(left - 20, y + 5, LABELS[approach], css="label", anchor="end")
        svg.line(
            left + chart_width * per_task,
            y,
            left + chart_width * corpus,
            y,
            stroke=COLORS[approach],
            width=8,
            opacity=0.35,
        )
        svg.circle(
            left + chart_width * per_task,
            y,
            8,
            fill=COLORS[approach],
            stroke=COLORS["white"],
            stroke_width=2,
        )
        svg.marker(
            left + chart_width * corpus,
            y,
            approach=approach,
            size=7,
            stroke=COLORS["ink"],
            stroke_width=1,
        )
        if approach == "minimal_v2":
            detail = "100% = 13 procedures + 28 receipts; 0 capabilities"
        elif approach == "workspace_v1_2":
            detail = "21.2% = the same 18/85 files on every task"
        else:
            detail = "12% per task; 68% across probe"
        detail_x = 1345 if approach == "minimal_v2" else 1510
        svg.text(detail_x, y + 5, detail, css="small", anchor="end")
    svg.circle(1010, panel_top + 145, 7, fill=COLORS["muted"])
    svg.text(1025, panel_top + 150, "per task", css="small")
    svg.marker(1130, panel_top + 145, approach="hybrid_packs", size=6, fill=COLORS["muted"], stroke=COLORS["muted"])
    svg.text(1145, panel_top + 150, "corpus", css="small")

    panel_top = panel_tops[3]
    svg.text(60, panel_top, "D  Adaptivity gap", css="panel")
    svg.text(60, panel_top + 26, "corpus reach minus per-task reach", css="small")
    axis_y = panel_top + 135
    axis_ticks(svg, x=left, y=axis_y, width=chart_width, maximum=0.6, ticks=[0, 0.2, 0.4, 0.6])
    for index, approach in enumerate(approaches):
        row = by_approach[approach]
        y = panel_top + 42 + index * 29
        gap = float(row["adaptivity_gap"])
        svg.text(left - 20, y + 5, LABELS[approach], css="label", anchor="end")
        if gap:
            svg.rect(left, y - 8, chart_width * gap / 0.6, 16, fill=COLORS[approach], radius=3)
        else:
            svg.circle(left, y, 6, fill=COLORS[approach])
        svg.text(
            left + chart_width * gap / 0.6 + 12,
            y + 5,
            f"{gap * 100:.0f} pp — {row['expression_mode'].split(':', 1)[0]}",
            css="value",
        )

    panel_top = 900
    svg.text(60, panel_top, "E  Execution reach", css="panel")
    headers = ["Automatic retained code", "Actor-callable retained capability"]
    for col, header in enumerate(headers):
        svg.text(600 + col * 410, panel_top, header, css="label", anchor="middle")
    for index, approach in enumerate(approaches):
        y = panel_top + 45 + index * 42
        svg.text(300, y + 6, LABELS[approach], css="label", anchor="end")
        automatic = approach == "hybrid_packs"
        for col, active in enumerate((automatic, False)):
            x = 600 + col * 410
            svg.circle(
                x,
                y,
                12,
                fill=COLORS[approach] if active else COLORS["white"],
                stroke=COLORS[approach],
                stroke_width=3,
            )
            svg.text(x + 24, y + 6, "yes, retrieval" if active else "no", css="small")
    svg.save(OUTPUT / "figure-2-expression-profile.svg")


def figure_3() -> None:
    corpus = rows(GENERATED / "hybrid-lesson-corpus.csv")
    summary = json.loads((GENERATED / "posthoc-metrics.json").read_text(encoding="utf-8"))
    memory = summary["hybrid_memory"]
    counter = summary["hybrid_retrieval_counterfactuals"]
    svg = SVG(
        1600,
        1040,
        "Figure 4. Vocabulary-mediated retrieval concentration",
        "Corpus and retrieval composition, per-lesson vocabulary versus retrieval counts, and offline ranker diagnostics.",
    )
    figure_header(
        svg,
        4,
        "Vocabulary-mediated retrieval concentration",
        "Failures are 40% of memory but 64.9% of retrievals; vocabulary predicts selection within both outcome groups.",
    )

    svg.text(60, 145, "A  Composition shift", css="panel")
    bar_x, bar_width = 180, 450
    values = [
        ("Retained corpus", memory["failing_corpus_fraction"]),
        ("Retrieved slots", memory["failing_retrieval_fraction"]),
    ]
    for index, (label, failure_fraction) in enumerate(values):
        y = 205 + index * 95
        svg.text(bar_x, y - 15, label, css="label")
        svg.rect(bar_x, y, bar_width * (1 - failure_fraction), 34, fill=COLORS["pass"])
        svg.rect(
            bar_x + bar_width * (1 - failure_fraction),
            y,
            bar_width * failure_fraction,
            34,
            fill=COLORS["failure"],
        )
        svg.text(
            bar_x + bar_width * (1 - failure_fraction) / 2,
            y + 23,
            f"{(1 - failure_fraction) * 100:.1f}% pass",
            css="value",
            anchor="middle",
        )
        svg.text(
            bar_x + bar_width * (1 - failure_fraction) + bar_width * failure_fraction / 2,
            y + 23,
            f"{failure_fraction * 100:.1f}% failure",
            css="value",
            anchor="middle",
            fill=COLORS["white"],
        )
    svg.text(
        180,
        405,
        f"Failure lessons are selected {memory['failure_to_passing_selection_rate_ratio']:.2f}× as often per lesson-task opportunity.",
        css="subtitle",
    )

    svg.text(780, 145, "B  Indexed vocabulary versus retrieval count", css="panel")
    plot_x, plot_y, plot_w, plot_h = 850, 190, 640, 300
    x_values = [float(row["index_vocabulary"]) for row in corpus]
    y_values = [float(row["retrieval_count"]) for row in corpus]
    xmin, xmax = 35, max(x_values) + 5
    ymin, ymax = 0, max(y_values) + 1
    for tick in range(0, int(ymax) + 1, 2):
        py = plot_y + plot_h - plot_h * (tick - ymin) / (ymax - ymin)
        svg.line(plot_x, py, plot_x + plot_w, py, stroke=COLORS["grid"])
        svg.text(plot_x - 12, py + 5, tick, css="small", anchor="end")
    for tick in range(40, int(xmax) + 1, 10):
        px = plot_x + plot_w * (tick - xmin) / (xmax - xmin)
        svg.line(px, plot_y, px, plot_y + plot_h, stroke=COLORS["grid"])
        svg.text(px, plot_y + plot_h + 24, tick, css="small", anchor="middle")
    svg.line(plot_x, plot_y, plot_x, plot_y + plot_h, stroke=COLORS["muted"])
    svg.line(plot_x, plot_y + plot_h, plot_x + plot_w, plot_y + plot_h, stroke=COLORS["muted"])
    for row in corpus:
        x = float(row["index_vocabulary"])
        y = float(row["retrieval_count"])
        px = plot_x + plot_w * (x - xmin) / (xmax - xmin)
        py = plot_y + plot_h - plot_h * (y - ymin) / (ymax - ymin)
        failed = row["score_passed"].lower() == "false"
        svg.circle(
            px,
            py,
            7,
            fill=COLORS["failure"] if failed else COLORS["pass"],
            stroke=COLORS["white"],
            stroke_width=1.5,
            opacity=0.88,
        )
        if y >= 10:
            svg.text(px + 8, py - 8, row["task_id"].split("__")[-1], css="tiny")
    regression = memory["retrieval_on_index_vocabulary_and_failure_ols"]
    for flag, color in ((0, COLORS["pass"]), (1, COLORS["failure"])):
        line_points = []
        zero_crossing = -(
            regression["intercept"] + regression["failure_flag_coefficient"] * flag
        ) / regression["index_vocabulary_coefficient"]
        for x in (max(xmin, zero_crossing), xmax):
            y = (
                regression["intercept"]
                + regression["index_vocabulary_coefficient"] * x
                + regression["failure_flag_coefficient"] * flag
            )
            px = plot_x + plot_w * (x - xmin) / (xmax - xmin)
            py = plot_y + plot_h - plot_h * (y - ymin) / (ymax - ymin)
            line_points.append((px, py))
        svg.polyline(line_points, stroke=color, width=2)
    svg.text(plot_x + plot_w / 2, plot_y + plot_h + 52, "Indexed vocabulary (unique terms)", css="label", anchor="middle")
    svg.text(plot_x - 58, plot_y + plot_h / 2, "Retrieval count", css="label", anchor="middle", rotate=-90)
    svg.text(
        plot_x,
        plot_y + plot_h + 82,
        "Within-group Spearman ρ: pass .743; failure .763. Adjusted vocabulary β=.194; descriptive pMC≈.0045.",
        css="small",
    )

    svg.text(60, 555, "C  Offline ranking diagnostic on the same 19 prompts", css="panel")
    methods = [("overlap", "Raw overlap"), ("jaccard", "Jaccard"), ("cosine", "Binary cosine"), ("bm25", "BM25")]
    chart_x, chart_y, chart_w = 350, 625, 1050
    axis_ticks(svg, x=chart_x, y=920, width=chart_w, maximum=0.7, ticks=[0, 0.2, 0.4, 0.6])
    svg.line(
        chart_x + chart_w * memory["failing_corpus_fraction"] / 0.7,
        chart_y - 25,
        chart_x + chart_w * memory["failing_corpus_fraction"] / 0.7,
        920,
        stroke=COLORS["muted"],
        width=2,
        dash="7 6",
    )
    svg.text(
        chart_x + chart_w * memory["failing_corpus_fraction"] / 0.7,
        chart_y - 35,
        "40% corpus baseline",
        css="small",
        anchor="middle",
    )
    for index, (key, label) in enumerate(methods):
        y = chart_y + index * 67
        failure = counter[key]["failure_fraction"]
        top_two = counter[key]["top_two_fraction"]
        svg.text(chart_x - 20, y + 6, label, css="label", anchor="end")
        svg.rect(chart_x, y - 17, chart_w * failure / 0.7, 20, fill=COLORS["failure"], radius=3)
        svg.rect(chart_x, y + 9, chart_w * top_two / 0.7, 13, fill=COLORS["highlight"], radius=3)
        svg.text(chart_x + chart_w * failure / 0.7 + 8, y - 1, f"{failure * 100:.1f}% failure slots", css="value")
        svg.text(chart_x + chart_w * top_two / 0.7 + 8, y + 21, f"{top_two * 100:.1f}% top-two share", css="small")
    svg.text(350, 1000, "Offline composition only; this figure does not estimate downstream task performance.", css="subtitle")
    svg.save(OUTPUT / "figure-4-failure-memory-stickiness.svg")


def scale_points(
    values: list[float], x: float, y: float, width: float, height: float, maximum: float | None = None
) -> list[tuple[float, float]]:
    upper = maximum if maximum is not None else max(values)
    if upper == 0:
        upper = 1.0
    return [
        (x + width * index / max(1, len(values) - 1), y + height - height * value / upper)
        for index, value in enumerate(values)
    ]


def timeline_axes(svg: SVG, x: float, y: float, width: float, height: float, y_ticks: list[tuple[float, str]], maximum: float) -> None:
    for value, label in y_ticks:
        py = y + height - height * value / maximum
        svg.line(x, py, x + width, py, stroke=COLORS["grid"])
        svg.text(x - 12, py + 5, label, css="small", anchor="end")
    for generation in (1, 7, 14, 21, 28):
        px = x + width * (generation - 1) / 27
        svg.text(px, y + height + 25, generation, css="small", anchor="middle")
    svg.text(x + width / 2, y + height + 52, "Development generation", css="label", anchor="middle")


def figure_4() -> None:
    growth = rows(GENERATED / "state-growth.csv")
    process = rows(GENERATED / "development-process.csv")
    by_approach_growth: dict[str, list[dict[str, str]]] = defaultdict(list)
    by_approach_process: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in growth:
        by_approach_growth[row["approach_id"]].append(row)
    for row in process:
        by_approach_process[row["approach_id"]].append(row)
    svg = SVG(
        1600,
        1190,
        "Figure 5. Accumulation, selective promotion, and saturation",
        "Three architecture timelines show Workspace state and cost, Minimal procedures and receipts, and Hybrid Pack source size and rejected updates.",
    )
    figure_header(
        svg,
        5,
        "Accumulation, selective promotion, and saturation",
        "All substrates retained state; only Hybrid encountered an explicit capacity ceiling.",
    )
    x, width, height = 230, 1260, 245

    y = 145
    svg.text(60, y, "A  Workspace: artifact growth and authoring cost", css="panel")
    plot_y = y + 35
    workspace_growth = by_approach_growth["workspace_v1_2"]
    workspace_process = by_approach_process["workspace_v1_2"]
    sizes = [float(row["artifact_bytes"]) / 1000 for row in workspace_growth]
    costs = [float(row["author_cost_usd"]) for row in workspace_process]
    timeline_axes(svg, x, plot_y, width, height, [(0, "0"), (200, "200 KB"), (400, "400 KB")], 450)
    svg.polyline(scale_points(sizes, x, plot_y, width, height, 450), stroke=COLORS["workspace_v1_2"], width=4)
    for index, cost in enumerate(costs):
        px = x + width * index / 27
        bar_height = 60 * cost / max(costs)
        svg.rect(px - 3, plot_y + height - bar_height, 6, bar_height, fill=COLORS["highlight"], opacity=0.65)
        if index in (0, len(costs) - 1):
            anchor = "start" if index == 0 else "end"
            svg.text(px, plot_y + height - bar_height - 9, f"${cost:.2f}", css="small", anchor=anchor)
    svg.text(x + 15, plot_y + 18, "blue line: artifact KB", css="small")
    svg.text(x + 220, plot_y + 18, "pink bars: author cost (scaled)", css="small")
    svg.text(x + width - 5, plot_y + 45, f"{sizes[-1]:.1f} KB", css="value", anchor="end")

    y = 500
    svg.text(60, y, "B  Minimal: success-gated procedures and universal receipts", css="panel")
    plot_y = y + 35
    minimal = by_approach_growth["minimal_v2"]
    procedures = [float(row["procedures"]) for row in minimal]
    receipts = [float(row["evidence_receipts"]) for row in minimal]
    timeline_axes(svg, x, plot_y, width, height, [(0, "0"), (10, "10"), (20, "20"), (30, "30")], 30)
    svg.polyline(scale_points(receipts, x, plot_y, width, height, 30), stroke=COLORS["minimal_v2"], width=4)
    svg.polyline(scale_points(procedures, x, plot_y, width, height, 30), stroke=COLORS["highlight"], width=4)
    svg.text(x + 15, plot_y + 18, "orange: receipts", css="small")
    svg.text(x + 155, plot_y + 18, "pink: promoted procedures", css="small")
    svg.text(x + width - 5, plot_y + 45, "28 receipts; 13 procedures; 0 capabilities", css="value", anchor="end")

    y = 855
    svg.text(60, y, "C  Hybrid: Pack source reaches the 64 KB policy ceiling", css="panel")
    plot_y = y + 35
    hybrid_growth = by_approach_growth["hybrid_packs"]
    hybrid_process = by_approach_process["hybrid_packs"]
    pack_sizes = [float(row["pack_source_bytes"]) / 1000 for row in hybrid_growth]
    timeline_axes(svg, x, plot_y, width, height, [(0, "0"), (20, "20 KB"), (40, "40 KB"), (64, "64 KB")], 70)
    cap_y = plot_y + height - height * 64 / 70
    svg.line(x, cap_y, x + width, cap_y, stroke=COLORS["failure"], width=2, dash="8 6")
    svg.text(x + width - 5, cap_y - 8, "64 KB policy", css="small", anchor="end")
    svg.polyline(scale_points(pack_sizes, x, plot_y, width, height, 70), stroke=COLORS["hybrid_packs"], width=4)
    for index, row in enumerate(hybrid_process):
        px = x + width * index / 27
        accepted = row["mutation_accepted"] == "True"
        requests = float(row["author_requests"])
        py = plot_y + height - height * pack_sizes[index] / 70
        if accepted:
            svg.circle(px, py, 5 + requests, fill=COLORS["hybrid_packs"], stroke=COLORS["white"], stroke_width=1)
        else:
            svg.line(px - 8, py - 8, px + 8, py + 8, stroke=COLORS["failure"], width=3)
            svg.line(px + 8, py - 8, px - 8, py + 8, stroke=COLORS["failure"], width=3)
    for generation in (25, 26, 27, 28):
        index = generation - 1
        px = x + width * index / 27
        py = plot_y + height - height * pack_sizes[index] / 70
        svg.text(px, py - 18 - (generation % 2) * 15, f"g{generation}", css="small", anchor="middle")
    svg.text(x + 15, plot_y + 18, "circles: accepted updates; red ×: rejected update", css="small")
    legend_y = plot_y + 43
    svg.text(x + 15, legend_y + 4, "author requests:", css="small")
    for legend_x, requests in ((x + 125, 1), (x + 185, 2), (x + 245, 4)):
        svg.circle(
            legend_x,
            legend_y,
            5 + requests,
            fill=COLORS["hybrid_packs"],
            stroke=COLORS["white"],
            stroke_width=1,
        )
        svg.text(legend_x + 12, legend_y + 4, str(requests), css="small")
    svg.text(x + width - 5, plot_y + 45, "62.5 KB retained after g25; g26–g28 rejected", css="value", anchor="end")
    svg.save(OUTPUT / "figure-5-accumulation-saturation.svg")


def task_short(task: str) -> str:
    aliases = {
        "configure-git-webserver": "git web",
        "polyglot-rust-c": "Rust/C",
        "extract-moves-from-video": "video",
        "db-wal-recovery": "WAL",
        "sqlite-with-gcov": "gcov",
        "tune-mjcf": "MJCF",
        "llm-inference-batching-scheduler": "batching",
        "recursive_kb": "recursive KB",
        "quota_scheduler": "quota",
        "delegated_research": "delegated",
    }
    if task in aliases:
        return aliases[task]
    if "__" in task:
        repo, issue = task.split("__", 1)
        repo = repo.split("-")[0]
        return f"{repo} {issue.split('-')[-1]}"
    return task[:13]


def figure_5() -> None:
    data = rows(GENERATED / "task-level-noise-and-evolved.csv")
    metrics = json.loads((GENERATED / "posthoc-metrics.json").read_text(encoding="utf-8"))
    by_suite_task: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(lambda: defaultdict(list))
    for row in data:
        by_suite_task[row["suite_id"]][row["task_id"]].append(row)
    svg = SVG(
        1900,
        1850,
        "Figure 3. Evolved outcomes versus task-specific duplicate-execution clouds",
        "Nineteen task-level clouds of six equivalent no-context outcomes with three evolved architecture outcomes overlaid.",
    )
    figure_header(
        svg,
        3,
        "Evolved outcomes versus task-specific duplicate-execution clouds",
        "Six byte-identical no-context requests define each gray cloud; Minimal/scikit-learn is the only evolved result outside a cloud.",
    )
    facet_specs = [
        ("ouro_swe_50", 130, 350),
        ("ouro_terminal_12", 675, 350),
        ("ouro_activegraph_50", 1220, 350),
    ]
    jitter = [-15, -9, -3, 3, 9, 15]
    evolved_offsets = [-12, 0, 12]
    for suite, top, plot_h in facet_specs:
        tasks = list(by_suite_task[suite])
        plot_x, plot_w = 165, 1550
        plot_y = top + 55
        svg.text(60, top + 20, SUITE_LABELS[suite], css="panel")
        family = metrics["equivalent_control_noise"][suite]
        svg.text(
            1840,
            top + 20,
            (
                f"maximum equivalent-label |Δ|={family['empirical_null_p95_absolute_delta']:.3f}; "
                f"design MDE={family['approximate_80pct_power_mde']:.3f}"
            ),
            css="small",
            anchor="end",
        )
        for tick in (0, 0.25, 0.5, 0.75, 1.0):
            py = plot_y + plot_h - plot_h * tick
            svg.line(plot_x, py, plot_x + plot_w, py, stroke=COLORS["grid"])
            svg.text(plot_x - 14, py + 5, f"{tick:.2f}", css="small", anchor="end")
        svg.line(plot_x, plot_y, plot_x, plot_y + plot_h, stroke=COLORS["muted"])
        spacing = plot_w / len(tasks)
        for task_index, task in enumerate(tasks):
            center = plot_x + spacing * (task_index + 0.5)
            task_rows = by_suite_task[suite][task]
            equivalent = [row for row in task_rows if row["condition_type"] == "equivalent_no_context"]
            evolved = [row for row in task_rows if row["condition_type"] == "evolved"]
            minimum = min(float(row["score"]) for row in equivalent)
            maximum = max(float(row["score"]) for row in equivalent)
            y_min = plot_y + plot_h - plot_h * minimum
            y_max = plot_y + plot_h - plot_h * maximum
            if minimum == maximum:
                svg.rect(
                    center - spacing * 0.38,
                    y_min - 9,
                    spacing * 0.76,
                    18,
                    fill=COLORS["light"],
                    radius=7,
                )
            else:
                svg.line(center, y_min, center, y_max, stroke=COLORS["muted"], width=8, opacity=0.18)
            for index, row in enumerate(equivalent):
                score = float(row["score"])
                py = plot_y + plot_h - plot_h * score
                svg.circle(
                    center + jitter[index],
                    py,
                    5,
                    fill=COLORS["muted"],
                    opacity=0.5,
                )
            evolved.sort(key=lambda row: list(LABELS).index(row["approach_id"]))
            for index, row in enumerate(evolved):
                score = float(row["score"])
                py = plot_y + plot_h - plot_h * score
                approach = row["approach_id"]
                svg.marker(
                    center + evolved_offsets[index],
                    py,
                    approach=approach,
                    size=8,
                    stroke=COLORS["white"],
                    stroke_width=1.5,
                )
                if row["inside_equivalent_range"] == "False":
                    svg.circle(
                        center + evolved_offsets[index],
                        py,
                        15,
                        fill="none",
                        stroke=COLORS["highlight"],
                        stroke_width=3,
                    )
                    svg.text(
                        center + evolved_offsets[index] + 18,
                        py - 12,
                        "only outside-range result",
                        css="tiny",
                        fill=COLORS["highlight"],
                    )
            svg.text(
                center,
                plot_y + plot_h + 26,
                task_short(task),
                css="small",
                anchor="end",
                rotate=-48,
            )

        ref_x = 1760
        ref_y = top + 58
        ref_w = 95
        svg.text(ref_x, ref_y, "Family-mean", css="tiny")
        svg.text(ref_x, ref_y + 15, "dispersion", css="tiny")
        svg.line(ref_x, ref_y + 32, ref_x + ref_w, ref_y + 32, stroke=COLORS["grid"], width=5)
        empirical = family["empirical_null_p95_absolute_delta"]
        mde = family["approximate_80pct_power_mde"]
        svg.line(
            ref_x,
            ref_y + 32,
            ref_x + ref_w * empirical / 0.5,
            ref_y + 32,
            stroke=COLORS["muted"],
            width=7,
        )
        svg.line(
            ref_x + ref_w * mde / 0.5,
            ref_y + 23,
            ref_x + ref_w * mde / 0.5,
            ref_y + 41,
            stroke=COLORS["highlight"],
            width=3,
        )

    legend_y = 1800
    svg.circle(80, legend_y, 5, fill=COLORS["muted"], opacity=0.5)
    svg.text(95, legend_y + 5, "equivalent no-context", css="small")
    for index, approach in enumerate(LABELS):
        x = 300 + index * 180
        svg.marker(x, legend_y, approach=approach, size=7)
        svg.text(x + 15, legend_y + 5, LABELS[approach] + " evolved", css="small")
    svg.text(
        1830,
        legend_y + 5,
        "Maximum |Δ| uses 15 dependent pairwise label deltas; descriptive reference, not a formal significance test.",
        css="small",
        anchor="end",
    )
    svg.save(OUTPUT / "figure-3-task-level-noise.svg")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    figure_1()
    figure_2()
    figure_3()
    figure_4()
    figure_5()
    manifest = {
        "status": "exploratory paper figures",
        "generator": "analysis/make_figures.py",
        "figures": sorted(path.name for path in OUTPUT.glob("figure-*.svg")),
        "numeric_sources": [
            "data/generated/expression-profile.csv",
            "data/generated/hybrid-lesson-corpus.csv",
            "data/generated/development-process.csv",
            "data/generated/state-growth.csv",
            "data/generated/task-level-noise-and-evolved.csv",
            "data/generated/empirical-null-pairwise-deltas.csv",
            "data/generated/posthoc-metrics.json",
        ],
    }
    (OUTPUT / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
