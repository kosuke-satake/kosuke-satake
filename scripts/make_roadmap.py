#!/usr/bin/env python3
"""Draw the esp32-ros2-rover roadmap graphic for the profile README.

Reads the roadmap table (| Stage | Goal | Status |) from the rover's own README, so the picture never drifts from the
repository, and writes a light and a dark SVG into assets/. Standard library only.
"""

from __future__ import annotations

import re
import sys
import textwrap
import urllib.request
from dataclasses import dataclass
from html import escape
from pathlib import Path

README_URL = "https://raw.githubusercontent.com/kosuke-satake/esp32-ros2-rover/main/README.md"
OUT_DIR = Path(__file__).resolve().parent.parent / "assets"

WIDTH = 888
HEIGHT = 168
MARGIN = 90
LINE_Y = 44
RADIUS = 14

THEMES = {
    "light": {
        "accent": "#0969da",
        "text": "#1f2328",
        "muted": "#656d76",
        "idle": "#afb8c1",
        "surface": "#ffffff",
        "done": "#1a7f37",
    },
    "dark": {
        "accent": "#58a6ff",
        "text": "#f0f6fc",
        "muted": "#8b949e",
        "idle": "#484f58",
        "surface": "#0d1117",
        "done": "#3fb950",
    },
}


@dataclass
class Stage:
    number: str
    title: str
    state: str  # "done", "active" or "planned"
    status: str


def fetch_readme() -> str:
    request = urllib.request.Request(README_URL, headers={"User-Agent": "profile-readme"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def parse(readme: str) -> list[Stage]:
    stages = []
    for line in readme.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 3 or not cells[0].isdigit():
            continue
        number, goal, status = cells
        bold = re.match(r"\*\*(.+?)\*\*", goal)
        title = (bold.group(1) if bold else goal).rstrip(".")
        status_text = status.replace("*", "").strip()
        lowered = status_text.lower()
        if "progress" in lowered:
            state = "active"
        elif "done" in lowered or "complete" in lowered:
            state = "done"
        else:
            state = "planned"
        stages.append(Stage(number, title, state, status_text))
    if not stages:
        raise SystemExit("roadmap table not found in the rover README")
    return stages


def render(theme: str, stages: list[Stage]) -> str:
    palette = THEMES[theme]
    step = (WIDTH - 2 * MARGIN) / (len(stages) - 1)
    xs = [MARGIN + index * step for index in range(len(stages))]
    parts = []

    for index in range(len(stages) - 1):
        solid = stages[index].state == "done"
        color = palette["done"] if solid else palette["idle"]
        dash = "" if solid else ' stroke-dasharray="6 6"'
        parts.append(
            f'<line x1="{xs[index] + RADIUS:.1f}" y1="{LINE_Y}" x2="{xs[index + 1] - RADIUS:.1f}" y2="{LINE_Y}" '
            f'stroke="{color}" stroke-width="3" stroke-linecap="round"{dash}/>'
        )

    for x, stage in zip(xs, stages):
        if stage.state == "active":
            parts.append(f'<circle cx="{x:.1f}" cy="{LINE_Y}" r="{RADIUS + 7}" fill="{palette["accent"]}" fill-opacity="0.18"/>')
            parts.append(f'<circle cx="{x:.1f}" cy="{LINE_Y}" r="{RADIUS}" fill="{palette["accent"]}"/>')
            number_fill, label_weight, status_fill = palette["surface"], 600, palette["accent"]
        elif stage.state == "done":
            parts.append(f'<circle cx="{x:.1f}" cy="{LINE_Y}" r="{RADIUS}" fill="{palette["done"]}"/>')
            number_fill, label_weight, status_fill = palette["surface"], 600, palette["done"]
        else:
            parts.append(
                f'<circle cx="{x:.1f}" cy="{LINE_Y}" r="{RADIUS}" fill="{palette["surface"]}" '
                f'stroke="{palette["idle"]}" stroke-width="2.5"/>'
            )
            number_fill, label_weight, status_fill = palette["muted"], 400, palette["muted"]
        parts.append(
            f'<text x="{x:.1f}" y="{LINE_Y + 5}" text-anchor="middle" class="num" fill="{number_fill}">{escape(stage.number)}</text>'
        )
        lines = textwrap.wrap(stage.title, 19)[:2]
        for row, text in enumerate(lines):
            parts.append(
                f'<text x="{x:.1f}" y="{92 + row * 20}" text-anchor="middle" class="label" '
                f'font-weight="{label_weight}">{escape(text)}</text>'
            )
        parts.append(
            f'<text x="{x:.1f}" y="146" text-anchor="middle" class="status" fill="{status_fill}">{escape(stage.status)}</text>'
        )

    family = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="esp32-ros2-rover roadmap: {escape('; '.join(f'stage {s.number} {s.title}, {s.status}' for s in stages))}">
  <style>
    text {{ font-family: {family}; }}
    .num {{ font-size: 14px; font-weight: 700; }}
    .label {{ font-size: 14px; fill: {palette['text']}; }}
    .status {{ font-size: 12.5px; }}
  </style>
  {''.join(parts)}
</svg>
"""


def main() -> int:
    stages = parse(fetch_readme())
    OUT_DIR.mkdir(exist_ok=True)
    for theme in THEMES:
        (OUT_DIR / f"rover-roadmap-{theme}.svg").write_text(render(theme, stages), encoding="utf-8")
    for stage in stages:
        print(f"{stage.number} [{stage.state:<7}] {stage.title}  ({stage.status})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
