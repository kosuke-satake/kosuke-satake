#!/usr/bin/env python3
"""Draw the esp32-ros2-rover brain/body diagram for the profile README.

A simplified version of the architecture in the rover's README (docs/architecture.md has the full one). Writes a
light and a dark SVG into assets/. Standard library only.
"""

from __future__ import annotations

import sys
from html import escape
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "assets"
WIDTH, HEIGHT = 888, 256
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"

THEMES = {
    "light": {"text": "#1f2328", "muted": "#656d76", "panel": "#f6f8fa", "border": "#d1d9e0", "accent": "#0969da", "danger": "#cf222e"},
    "dark": {"text": "#f0f6fc", "muted": "#9198a1", "panel": "#151b23", "border": "#3d444d", "accent": "#58a6ff", "danger": "#ff7b72"},
}

BOX_W, BOX_H = 200, 84
BRAIN_X, BODY_X, MOTOR_X = 40, 344, 648
ROW_Y = 96


def box(x: int, y: int, w: int, h: int, title: str, lines: list[str], palette: dict, highlight: bool = False) -> str:
    stroke = palette["accent"] if highlight else palette["border"]
    width = 2 if highlight else 1
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{palette["panel"]}" stroke="{stroke}" stroke-width="{width}"/>']
    out.append(f'<text x="{x + w / 2}" y="{y + 28}" text-anchor="middle" class="box">{escape(title)}</text>')
    for i, line in enumerate(lines):
        out.append(f'<text x="{x + w / 2}" y="{y + 48 + i * 17}" text-anchor="middle" class="note">{escape(line)}</text>')
    return "".join(out)


def arrow(x1: float, y1: float, x2: float, y2: float, label: str, palette: dict, dashed: bool = False, color_key: str = "accent", label_dx: float = 0, label_dy: float = -8, anchor: str = "middle") -> str:
    dash = ' stroke-dasharray="5 5"' if dashed else ""
    color = palette[color_key]
    mid_x, mid_y = (x1 + x2) / 2 + label_dx, (y1 + y2) / 2 + label_dy
    return (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="2"{dash} marker-end="url(#head-{color_key})"/>'
        f'<text x="{mid_x}" y="{mid_y}" text-anchor="{anchor}" class="label" fill="{color}">{escape(label)}</text>'
    )


def render(theme: str) -> str:
    p = THEMES[theme]
    gap_l, gap_r = BRAIN_X + BOX_W, BODY_X
    gap2_l, gap2_r = BODY_X + BOX_W, MOTOR_X
    parts = [
        box(BODY_X, 4, BOX_W, 56, "Controller", ["iPhone, tilt to drive"], p),
        box(BRAIN_X, ROW_Y, BOX_W, BOX_H, "Brain", ["ROS 2", "Mac (Docker) now, phone next"], p),
        box(BODY_X, ROW_Y, BOX_W, BOX_H, "Body", ["ESP32: kinematics + PID,", "encoders, safety stop"], p, highlight=True),
        box(MOTOR_X, ROW_Y, BOX_W, BOX_H, "Motors", ["2 geared motors", "with encoders"], p),
        box(MOTOR_X, 208, BOX_W, 40, "Physical e-stop", [], p),
        arrow(gap_l + 6, 124, gap_r - 8, 124, "velocity", p),
        arrow(gap_r - 6, 156, gap_l + 8, 156, "odometry", p, label_dy=20),
        arrow(gap2_l + 6, 124, gap2_r - 8, 124, "PWM", p),
        arrow(gap2_r - 6, 156, gap2_l + 8, 156, "encoders", p, label_dy=20),
        arrow(BODY_X + BOX_W / 2, 62, BODY_X + BOX_W / 2, ROW_Y - 4, "velocity", p, dashed=True, label_dx=10, label_dy=4, anchor="start"),
        arrow(MOTOR_X + BOX_W / 2, 206, MOTOR_X + BOX_W / 2, ROW_Y + BOX_H + 4, "cuts motor power", p, dashed=True, color_key="danger", label_dx=10, label_dy=4, anchor="start"),
    ]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="esp32-ros2-rover architecture: a ROS 2 brain sends velocity to an ESP32 body and receives odometry; the body drives two motors; an iPhone can send velocity to the body; a physical e-stop cuts motor power">
  <defs>
    <marker id="head-accent" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{p['accent']}"/></marker>
    <marker id="head-danger" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{p['danger']}"/></marker>
  </defs>
  <style>
    text {{ font-family: {FONT}; }}
    .box {{ font-size: 15px; font-weight: 600; fill: {p['text']}; }}
    .note {{ font-size: 12.5px; fill: {p['muted']}; }}
    .label {{ font-size: 12.5px; font-weight: 500; }}
  </style>
  {''.join(parts)}
</svg>
"""


def main() -> int:
    OUT_DIR.mkdir(exist_ok=True)
    for theme in THEMES:
        (OUT_DIR / f"rover-architecture-{theme}.svg").write_text(render(theme), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
