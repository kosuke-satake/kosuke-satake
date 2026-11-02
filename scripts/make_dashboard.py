#!/usr/bin/env python3
"""Draw the activity dashboard for the profile README.

One picture: eight numbers, commits per month, languages, commits by weekday, the latest releases, the most recently
updated repositories and a stack sheet. It is built from the public repositories of the listed owners and written as
a light and a dark SVG into assets/. Standard library only. Set GITHUB_TOKEN to avoid the unauthenticated rate limit.

Counting rules:
  * Forks and the organization's ".github" repository are skipped.
  * Commits per month come from GitHub's contributor statistics (default branches). Bot accounts are left out, so
    scheduled data-refresh commits do not inflate the chart. A commit is counted in the month its week starts.
  * Weekday, active days, streak and busiest day come from the per-day commit statistics, which cannot tell bots
    apart; kosuke-satake.github.io (daily scheduled commits) is therefore left out of those. Days are UTC.
  * Languages are bytes of code as reported by GitHub. Repositories that would mislead are excluded (see below).
  * Repositories in HIDDEN are counted but never named in the lists.
"""

from __future__ import annotations

import datetime as dt
import json
import math
import os
import sys
import time
import urllib.request
from html import escape
from pathlib import Path

OWNERS = ("kosuke-satake", "kosuke-apps")
SKIP_REPOS = {"kosuke-apps/.github"}
HIDDEN = {"kosuke-apps/SpellBar"}

# scholar-static vendors a 600 KB library (lucide.js); jules_ws is code written by a bot for a trial.
EXCLUDED_FROM_LANGUAGES = {"kosuke-satake/scholar-static", "kosuke-satake/jules_ws"}
IGNORED_LANGUAGES = {"Roff", "Dockerfile", "Makefile", "HTML"}
# Daily scheduled commits would drown the per-day statistics.
EXCLUDED_FROM_DAILY = {"kosuke-satake/kosuke-satake.github.io"}

ROBOTICS = {"esp32-ros2-rover", "ros2_ws", "mujoco_ws", "go2-w_ws", "ros2_mac_workspace", "ros2_tutorial_ws"}
WEB = {"keyastro", "scholar-static", "kosuke-satake.github.io"}
AREAS = ("Robotics", "Apps", "Web")  # stacking order, bottom to top

# Written by hand: only tools that are visible in the repositories' own files.
STACK = (
    ("Robotics", ("ROS 2 Jazzy", "MuJoCo", "ESP32", "PlatformIO")),
    ("Web", ("Astro", "Tailwind CSS", "Keystatic", "Cloudflare")),
    ("Apps", ("Swift", "SwiftUI", "Xcode")),
    ("Tools", ("Git", "GitHub Actions", "Docker", "Claude Code")),
)

TOP_LANGUAGES = 6
MONTHS = 12
OUT_DIR = Path(__file__).resolve().parent.parent / "assets"

LANGUAGE_COLORS = {
    "Swift": "#F05138",
    "TypeScript": "#3178C6",
    "Astro": "#FF5A03",
    "Python": "#3572A5",
    "C": "#8B949E",
    "C++": "#F34B7D",
    "Shell": "#89E051",
    "JavaScript": "#F1E05A",
    "CSS": "#8957E5",
}
OTHER_COLOR = "#6E7781"

THEMES = {
    "light": {
        "text": "#1f2328",
        "muted": "#656d76",
        "panel": "#f6f8fa",
        "border": "#d1d9e0",
        "grid": "#d8dee4",
        "chip": "#eaeef2",
        "areas": {"Robotics": "#0969da", "Apps": "#8250df", "Web": "#bf8700"},
    },
    "dark": {
        "text": "#f0f6fc",
        "muted": "#9198a1",
        "panel": "#151b23",
        "border": "#3d444d",
        "grid": "#30363d",
        "chip": "#262c36",
        "areas": {"Robotics": "#58a6ff", "Apps": "#a371f7", "Web": "#d29922"},
    },
}

WIDTH = 888
GAP = 16
TILE_H = 84
PANEL_W = (WIDTH - GAP) // 2
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"


# --------------------------------------------------------------------------------------------- data


def api(path: str, statistics: bool = False):
    request = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "profile-readme"},
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    for _ in range(8 if statistics else 1):
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status != 202:  # 202: statistics are still being computed
                body = response.read()
                return json.loads(body) if body else None
        time.sleep(2)
    return None


def public_repos() -> list[dict]:
    repos = []
    for owner in OWNERS:
        page = 1
        while True:
            batch = api(f"/users/{owner}/repos?type=owner&per_page=100&page={page}") or []
            if not batch:
                break
            repos += [r for r in batch if not r["fork"] and not r["private"] and r["full_name"] not in SKIP_REPOS]
            page += 1
    return repos


def area_of(full_name: str) -> str | None:
    owner, name = full_name.split("/")
    if owner == "kosuke-apps":
        return "Apps"
    if name in ROBOTICS:
        return "Robotics"
    if name in WEB:
        return "Web"
    return None


def month_keys(today: dt.date) -> list[tuple[int, int]]:
    keys = []
    year, month = today.year, today.month
    for _ in range(MONTHS):
        keys.append((year, month))
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    return keys[::-1]


def commits_by_month(repos: list[dict], months: list[tuple[int, int]]) -> dict[str, list[int]]:
    series = {area: [0] * len(months) for area in AREAS}
    index = {key: i for i, key in enumerate(months)}
    for repo in repos:
        area = area_of(repo["full_name"])
        if area is None:
            continue
        data = api(f"/repos/{repo['full_name']}/stats/contributors", statistics=True)
        if not isinstance(data, list):
            continue
        for contributor in data:
            login = (contributor.get("author") or {}).get("login", "")
            if login.endswith("[bot]"):
                continue
            for week in contributor["weeks"]:
                started = dt.datetime.fromtimestamp(week["w"], dt.timezone.utc)
                slot = index.get((started.year, started.month))
                if slot is not None:
                    series[area][slot] += week["c"]
    return series


def daily_commits(repos: list[dict]) -> dict[dt.date, int]:
    """Commits per UTC day over the last 52 weeks, for the repositories in the chart."""
    days: dict[dt.date, int] = {}
    for repo in repos:
        name = repo["full_name"]
        if area_of(name) is None or name in EXCLUDED_FROM_DAILY:
            continue
        data = api(f"/repos/{name}/stats/commit_activity", statistics=True)
        if not isinstance(data, list):
            continue
        for week in data:
            start = dt.datetime.fromtimestamp(week["week"], dt.timezone.utc).date()
            for offset, count in enumerate(week["days"]):
                if count:
                    day = start + dt.timedelta(days=offset)
                    days[day] = days.get(day, 0) + count
    return days


def streaks(days: dict[dt.date, int], today: dt.date) -> tuple[int, int, int]:
    """Active days, longest streak and busiest day in the 365 days up to today."""
    first = today - dt.timedelta(days=364)
    active = sorted(d for d, c in days.items() if first <= d <= today and c > 0)
    longest = run = 0
    previous = None
    for day in active:
        run = run + 1 if previous is not None and (day - previous).days == 1 else 1
        longest = max(longest, run)
        previous = day
    busiest = max((days[d] for d in active), default=0)
    return len(active), longest, busiest


def weekday_counts(days: dict[dt.date, int], today: dt.date) -> list[int]:
    first = today - dt.timedelta(days=364)
    counts = [0] * 7  # Monday first
    for day, count in days.items():
        if first <= day <= today:
            counts[day.weekday()] += count
    return counts


def latest_releases(repos: list[dict]) -> tuple[list[tuple[str, str, dt.datetime]], int]:
    rows, total = [], 0
    for repo in repos:
        releases = [r for r in (api(f"/repos/{repo['full_name']}/releases?per_page=100") or []) if not r["draft"]]
        total += len(releases)
        if releases and repo["full_name"] not in HIDDEN:
            published = dt.datetime.fromisoformat(releases[0]["published_at"].replace("Z", "+00:00"))
            rows.append((repo["name"], releases[0]["tag_name"], published))
    rows.sort(key=lambda row: row[2], reverse=True)
    return rows, total


def language_totals(repos: list[dict]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for repo in repos:
        if repo["full_name"] in EXCLUDED_FROM_LANGUAGES:
            continue
        for language, size in (api(f"/repos/{repo['full_name']}/languages") or {}).items():
            if language not in IGNORED_LANGUAGES:
                totals[language] = totals.get(language, 0) + size
    return totals


def language_rows(totals: dict[str, int]) -> list[tuple[str, float, str]]:
    total = sum(totals.values())
    ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    rows = [(n, s / total * 100, LANGUAGE_COLORS.get(n, OTHER_COLOR)) for n, s in ranked[:TOP_LANGUAGES]]
    rest = sum(size for _, size in ranked[TOP_LANGUAGES:])
    if rest:
        rows.append(("Other", rest / total * 100, OTHER_COLOR))
    return rows


def ago(then: dt.datetime, now: dt.datetime) -> str:
    days = (now - then).days
    if days < 1:
        return "today"
    if days < 14:
        return f"{days} day{'s' if days != 1 else ''} ago"
    if days < 60:
        return f"{days // 7} weeks ago"
    return f"{days // 30} months ago"


def nice_max(value: int) -> int:
    for step in (10, 20, 40, 60, 100, 200, 400, 600, 1000):
        if value <= step:
            return step
    return int(math.ceil(value / 100) * 100)


# ------------------------------------------------------------------------------------------ drawing


def tiles(items: list[tuple[str, str]], palette: dict) -> str:
    width = (WIDTH - 3 * GAP) / 4
    out = []
    for i, (number, label) in enumerate(items):
        x = i * (width + GAP)
        out.append(
            f'<g transform="translate({x:.1f},0)">'
            f'<rect width="{width:.1f}" height="{TILE_H}" rx="12" fill="{palette["panel"]}" stroke="{palette["border"]}"/>'
            f'<text x="20" y="50" class="kpi">{escape(number)}</text>'
            f'<text x="20" y="71" class="sub">{escape(label)}</text></g>'
        )
    return "".join(out)


def panel(height: int, title: str, subtitle: str, palette: dict) -> str:
    return (
        f'<rect width="{PANEL_W}" height="{height}" rx="12" fill="{palette["panel"]}" stroke="{palette["border"]}"/>'
        f'<text x="20" y="34" class="title">{escape(title)}</text>'
        f'<text x="20" y="53" class="sub">{escape(subtitle)}</text>'
    )


def month_panel(height: int, series, months, palette: dict) -> str:
    left, right, top, base = 52, PANEL_W - 20, 96, height - 44
    totals = [sum(series[a][i] for a in AREAS) for i in range(len(months))]
    ceiling = nice_max(max(totals) if totals else 0)
    slot = (right - left) / len(months)
    bar = 18
    scale = (base - top) / ceiling
    parts = [panel(height, "Commits per month", "default branches, public repositories", palette)]
    for area, lx in zip(AREAS, (214, 294, 356)):
        parts.append(f'<circle cx="{lx}" cy="30" r="5" fill="{palette["areas"][area]}"/>')
        parts.append(f'<text x="{lx + 11}" y="34" class="legend">{area}</text>')
    for tick in (0, ceiling // 2, ceiling):
        y = base - tick * scale
        dash = "" if tick == 0 else "3 4"
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" stroke="{palette["grid"]}" stroke-dasharray="{dash}"/>')
        parts.append(f'<text x="{left - 8}" y="{y + 4:.1f}" text-anchor="end" class="axis">{tick}</text>')
    for i, (year, month) in enumerate(months):
        x = left + i * slot + (slot - bar) / 2
        y = base
        for area in AREAS:
            h = series[area][i] * scale
            if h > 0:
                y -= h
                parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar}" height="{h:.1f}" fill="{palette["areas"][area]}"/>')
        label = dt.date(year, month, 1).strftime("%b")
        parts.append(f'<text x="{left + i * slot + slot / 2:.1f}" y="{base + 20}" text-anchor="middle" class="axis">{label}</text>')
    return "".join(parts)


def language_panel(height: int, rows, palette: dict) -> str:
    cx, cy, r, stroke = 104, 160, 56, 22
    circumference = 2 * math.pi * r
    parts = [
        panel(height, "Languages", "bytes of code, public repositories", palette),
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{palette["grid"]}" stroke-width="{stroke}"/>',
    ]
    offset = 0.0
    for _, percent, color in rows:
        length = circumference * percent / 100
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="{stroke}" '
            f'stroke-dasharray="{max(length - 1.5, 0.1):.2f} {circumference:.2f}" stroke-dashoffset="{-offset:.2f}" '
            f'transform="rotate(-90 {cx} {cy})"/>'
        )
        offset += length
    top_name, top_percent, _ = rows[0]
    parts.append(f'<text x="{cx}" y="{cy - 3}" text-anchor="middle" class="sub">{escape(top_name)}</text>')
    parts.append(f'<text x="{cx}" y="{cy + 22}" text-anchor="middle" class="donut">{top_percent:.0f}%</text>')
    for i, (name, percent, color) in enumerate(rows):
        y = 100 + i * 24
        parts.append(f'<circle cx="200" cy="{y - 4}" r="5" fill="{color}"/>')
        parts.append(f'<text x="214" y="{y}" class="legend">{escape(name)}</text>')
        parts.append(f'<text x="{PANEL_W - 22}" y="{y}" text-anchor="end" class="sub">{percent:.1f}%</text>')
    return "".join(parts)


def weekday_panel(height: int, counts: list[int], palette: dict) -> str:
    left, right, top, base = 24, PANEL_W - 24, 96, height - 40
    slot = (right - left) / 7
    bar = 30
    peak = max(counts) or 1
    scale = (base - top) / peak
    busiest = counts.index(max(counts))
    parts = [panel(height, "Commits by weekday", "last 12 months, UTC", palette)]
    parts.append(f'<line x1="{left}" y1="{base}" x2="{right}" y2="{base}" stroke="{palette["grid"]}"/>')
    for i, (name, count) in enumerate(zip(("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"), counts)):
        x = left + i * slot + (slot - bar) / 2
        h = count * scale
        color = palette["areas"]["Robotics"] if i == busiest else palette["grid"]
        parts.append(f'<rect x="{x:.1f}" y="{base - h:.1f}" width="{bar}" height="{h:.1f}" rx="4" fill="{color}"/>')
        parts.append(f'<text x="{x + bar / 2:.1f}" y="{base - h - 6:.1f}" text-anchor="middle" class="axis">{count}</text>')
        parts.append(f'<text x="{x + bar / 2:.1f}" y="{base + 20}" text-anchor="middle" class="axis">{name}</text>')
    return "".join(parts)


def release_panel(height: int, rows, now: dt.datetime, palette: dict) -> str:
    parts = [panel(height, "Latest releases", "kosuke-apps", palette)]
    for i, (name, tag, published) in enumerate(rows[:6]):
        y = 90 + i * 25
        parts.append(f'<text x="20" y="{y}" class="legend bold">{escape(name)}</text>')
        parts.append(f'<text x="150" y="{y}" class="mono">{escape(tag)}</text>')
        parts.append(f'<text x="{PANEL_W - 20}" y="{y}" text-anchor="end" class="sub">{ago(published, now)}</text>')
        if i < min(len(rows), 6) - 1:
            parts.append(f'<line x1="20" y1="{y + 10}" x2="{PANEL_W - 20}" y2="{y + 10}" stroke="{palette["grid"]}" stroke-opacity="0.6"/>')
    return "".join(parts)


def recent_panel(height: int, repos: list[dict], now: dt.datetime, palette: dict) -> str:
    rows = []
    for repo in repos:
        if repo["full_name"] in HIDDEN:
            continue
        pushed = dt.datetime.fromisoformat(repo["pushed_at"].replace("Z", "+00:00"))
        rows.append((repo["name"], pushed, area_of(repo["full_name"])))
    rows.sort(key=lambda row: row[1], reverse=True)
    parts = [panel(height, "Recently updated", "last push to any branch", palette)]
    bar_x, bar_w = 196, 110
    for i, (name, pushed, area) in enumerate(rows[:7]):
        y = 90 + i * 25
        days = max((now - pushed).days, 0)
        fill = max(0.06, 1 - min(days, 90) / 90)
        color = palette["areas"].get(area or "", palette["muted"])
        parts.append(f'<text x="20" y="{y}" class="legend">{escape(name)}</text>')
        parts.append(f'<rect x="{bar_x}" y="{y - 10}" width="{bar_w}" height="8" rx="4" fill="{palette["grid"]}"/>')
        parts.append(f'<rect x="{bar_x}" y="{y - 10}" width="{bar_w * fill:.1f}" height="8" rx="4" fill="{color}"/>')
        parts.append(f'<text x="{PANEL_W - 20}" y="{y}" text-anchor="end" class="sub">{ago(pushed, now)}</text>')
    return "".join(parts)


def stack_panel(height: int, palette: dict) -> str:
    parts = [panel(height, "Stack", "tools used in these repositories", palette)]
    for row, (label, items) in enumerate(STACK):
        y = 92 + row * 38
        parts.append(f'<text x="20" y="{y + 5}" class="sub">{escape(label)}</text>')
        x = 96.0
        for item in items:
            width = 6.5 * len(item) + 14
            parts.append(f'<rect x="{x:.1f}" y="{y - 12}" width="{width:.1f}" height="26" rx="13" fill="{palette["chip"]}"/>')
            parts.append(f'<text x="{x + width / 2:.1f}" y="{y + 5}" text-anchor="middle" class="chip">{escape(item)}</text>')
            x += width + 8
    return "".join(parts)


def render(theme: str, first, second, charts, now: dt.datetime) -> str:
    palette = THEMES[theme]
    series, months, rows, weekdays, releases, repos = charts
    row1_y = TILE_H + 12
    panels_y = row1_y + TILE_H + 24
    h1, h2, h3 = 270, 250, 250
    y2 = panels_y + h1 + GAP
    y3 = y2 + h2 + GAP
    height = y3 + h3
    right_x = WIDTH - PANEL_W
    label = "; ".join(f"{n} {l}" for n, l in first + second)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" role="img" aria-label="Activity dashboard: {escape(label)}">
  <style>
    text {{ font-family: {FONT}; }}
    .kpi {{ font-size: 32px; font-weight: 700; fill: {palette['text']}; }}
    .title {{ font-size: 15px; font-weight: 600; fill: {palette['text']}; }}
    .sub {{ font-size: 13px; fill: {palette['muted']}; }}
    .legend {{ font-size: 13px; fill: {palette['text']}; }}
    .bold {{ font-weight: 600; }}
    .mono {{ font-size: 13px; fill: {palette['text']}; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
    .axis {{ font-size: 11px; fill: {palette['muted']}; }}
    .chip {{ font-size: 12.5px; fill: {palette['text']}; }}
    .donut {{ font-size: 24px; font-weight: 700; fill: {palette['text']}; }}
  </style>
  {tiles(first, palette)}
  <g transform="translate(0,{row1_y})">{tiles(second, palette)}</g>
  <g transform="translate(0,{panels_y})">{month_panel(h1, series, months, palette)}</g>
  <g transform="translate({right_x},{panels_y})">{language_panel(h1, rows, palette)}</g>
  <g transform="translate(0,{y2})">{weekday_panel(h2, weekdays, palette)}</g>
  <g transform="translate({right_x},{y2})">{release_panel(h2, releases, now, palette)}</g>
  <g transform="translate(0,{y3})">{recent_panel(h3, repos, now, palette)}</g>
  <g transform="translate({right_x},{y3})">{stack_panel(h3, palette)}</g>
</svg>
"""


def main() -> int:
    now = dt.datetime.now(dt.timezone.utc)
    today = now.date()
    repos = public_repos()
    months = month_keys(today)
    series = commits_by_month(repos, months)
    totals = language_totals(repos)
    rows = language_rows(totals)
    days = daily_commits(repos)
    active, longest, busiest = streaks(days, today)
    weekdays = weekday_counts(days, today)
    releases, release_total = latest_releases(repos)
    recent = sum(
        1 for repo in repos if (now - dt.datetime.fromisoformat(repo["pushed_at"].replace("Z", "+00:00"))).days <= 30
    )
    commits = sum(sum(values) for values in series.values())
    first = [
        (str(len(repos)), "public repositories"),
        (str(commits), "commits in 12 months"),
        (str(len(totals)), "languages"),
        (str(recent), "repos active this month"),
    ]
    second = [
        (str(active), "active days, 12 months"),
        (str(longest), "longest streak, days"),
        (str(busiest), "busiest day, commits"),
        (str(release_total), "releases published"),
    ]
    OUT_DIR.mkdir(exist_ok=True)
    for theme in THEMES:
        svg = render(theme, first, second, (series, months, rows, weekdays, releases, repos), now)
        (OUT_DIR / f"dashboard-{theme}.svg").write_text(svg, encoding="utf-8")
    for number, label in first + second:
        print(f"{number:>5}  {label}")
    for area in AREAS:
        print(f"{area:<9}{series[area]}")
    print("weekday  ", weekdays)
    print("releases ", [(n, t) for n, t, _ in releases[:6]])
    return 0


if __name__ == "__main__":
    sys.exit(main())
