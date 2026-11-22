#!/usr/bin/env python3
"""Fill the apps grid of the profile README from the apps organization.

The profile page of the organization (kosuke-apps/.github, profile/README.md) is the one place that keeps the list of
apps: their order, names and icons. This script reads it, drops the apps in HIDDEN, takes a short line for each app
(data/taglines.json, else the start of the repository description) and rewrites the block between the markers
<!-- apps:start --> and <!-- apps:end --> in README.md. Standard library only.

A renamed or added app therefore appears here by itself once the organization page lists it. The script stops without
writing when the organization page cannot be read, lists no app, or names a repository that is not public, so a broken
source never replaces a good page.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from html import escape
from pathlib import Path

from make_dashboard import HIDDEN, api

ORG = "kosuke-apps"
SOURCE = f"https://raw.githubusercontent.com/{ORG}/.github/main/profile/README.md"
ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
TAGLINES = ROOT / "data" / "taglines.json"
START, END = "<!-- apps:start -->", "<!-- apps:end -->"
COLUMNS = 3
MAX_LINE = 60

# One app row of the organization page: the icon cell that links to the repository.
ROW = re.compile(
    rf'<td[^>]*>\s*<a href="https://github\.com/{ORG}/(?P<name>[A-Za-z0-9._-]+)">\s*'
    r'<img src="(?P<icon>[^"]+/icons/[^"]+)"'
)


def fail(message: str) -> None:
    print(f"make_apps: {message}", file=sys.stderr)
    sys.exit(1)


def listed_apps() -> list[tuple[str, str]]:
    request = urllib.request.Request(SOURCE, headers={"User-Agent": "profile-readme"})
    with urllib.request.urlopen(request, timeout=30) as response:
        text = response.read().decode("utf-8")
    apps: list[tuple[str, str]] = []
    for match in ROW.finditer(text):
        item = (match["name"], match["icon"])
        if item[0] not in [name for name, _ in apps]:
            apps.append(item)
    return apps


def short_line(description: str) -> str:
    """The start of a repository description: up to the first colon or full stop, at most MAX_LINE characters."""
    text = re.split(r": |\. ", description.strip(), maxsplit=1)[0].rstrip(".")
    if len(text) > MAX_LINE:
        text = text[: MAX_LINE - 1].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return text


def cell(name: str, icon: str, line: str) -> str:
    url = f"https://github.com/{ORG}/{name}"
    return (
        f'    <td width="33%" align="center" valign="top"><a href="{url}"><img src="{escape(icon)}" width="56" '
        f'alt="{escape(name)}"><br><b>{escape(name)}</b></a><br><sub>{escape(line, quote=False)}</sub></td>'
    )


def grid(cells: list[str]) -> str:
    rows = []
    for start in range(0, len(cells), COLUMNS):
        row = cells[start : start + COLUMNS]
        row += ['    <td width="33%"></td>'] * (COLUMNS - len(row))
        rows.append("  <tr>\n" + "\n".join(row) + "\n  </tr>")
    return "<table>\n" + "\n".join(rows) + "\n</table>"


def main() -> int:
    apps = [(n, i) for n, i in listed_apps() if f"{ORG}/{n}" not in HIDDEN]
    if not apps:
        fail("the organization page lists no app; leaving README.md as it is")
    taglines = json.loads(TAGLINES.read_text(encoding="utf-8")) if TAGLINES.exists() else {}
    cells = []
    for name, icon in apps:
        try:
            info = api(f"/repos/{ORG}/{name}")
        except urllib.error.HTTPError as error:
            fail(f"{ORG}/{name} is listed on the organization page but GitHub answers {error.code}")
        if info["private"]:
            fail(f"{ORG}/{name} is listed on the organization page but is not public")
        if info["archived"]:
            print(f"make_apps: {name} is archived, left out")
            continue
        line = taglines.get(name) or short_line(info["description"] or name)
        cells.append(cell(name, icon, line))
        print(f"{name:<12} {line}")
    for name in sorted(set(taglines) - {n for n, _ in apps}):
        print(f"make_apps: data/taglines.json has '{name}', which the organization page no longer lists")
    if not cells:
        fail("every listed app is archived; leaving README.md as it is")

    text = README.read_text(encoding="utf-8")
    if text.count(START) != 1 or text.count(END) != 1 or text.index(START) > text.index(END):
        fail("README.md needs exactly one apps:start and one apps:end marker, in that order")
    head, rest = text.split(START)
    _, tail = rest.split(END)
    updated = f"{head}{START}\n{grid(cells)}\n{END}{tail}"
    if updated == text:
        print("make_apps: README.md is already current")
    else:
        README.write_text(updated, encoding="utf-8")
        print("make_apps: README.md updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
