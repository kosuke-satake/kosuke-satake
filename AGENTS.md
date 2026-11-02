# kosuke-satake (profile README)

The special repository whose `README.md` GitHub shows at the top of the profile page `github.com/kosuke-satake`.
Workspace rules are in `~/Developer/AGENTS.md`; the licensing and publication rules there apply to everything written
here. This repository is managed directly by the GitHub thread for the personal account.

## Product

- Purpose: the first page a visitor (a recruiter, a collaborator, a user of an app) sees for the main account.
- Order of the page: Robotics, Web, Apps, Sandbox, Activity. Robotics leads; the apps and the sandbox are summaries
  that point to their organizations (`kosuke-apps`, `kosuke-sandbox`), which are the main place for them.
- Out of scope: visitor counters, badges, and any image or script served by a third party. Every graphic is either
  generated here or taken from our own repositories and sites.

## Technical context

- Stack: one Markdown file plus generated SVGs and two screenshots. No build step and no dependencies; the scripts use
  the Python standard library (3.11+) and, for screenshots, Google Chrome and `sips` on macOS.
- Files:
  - `README.md`: the profile page. Light/dark variants of each graphic are chosen with `<picture>`.
  - `assets/`: generated graphics (`banner-*`, `rover-architecture-*`, `rover-roadmap-*`, `dashboard-*`; `-light` and
    `-dark` each) and the demo screenshots `web-*.jpg`. `banner-*` are drawn by hand; the rest are generated.
  - `scripts/`: the generators (below).
  - `LICENSE` (MIT), the agent files, and the editor and Git settings.
- Constraints:
  - Must be a public repository named exactly like the account (`kosuke-satake`), or GitHub shows nothing.
  - English only, no personal data (no e-mail address, phone number or home address, no local paths).
  - Link only to repositories in publishable shape. `go2-w_ws` is left out until its local paths are fixed and it has a
    licence.
  - Held apps are not named in lists. App icons come from `kosuke-apps/.github` (our own repository).
  - The templates are described as supporting multiple languages (i18n), not as English and Japanese only.
- Graphics are snapshots. Numbers in `dashboard-*` and the stages in `rover-roadmap-*` are as of the last run, so
  regenerate before a visible change and after a notable release. A scheduled GitHub Action is not set up yet.
- Name, bio, status and the six pinned repositories are profile settings, not files. The user changes them in the
  GitHub UI (the CLI token has no `user` scope, and pins have no API). Recommended pins: Headway, Kitbag, Mantissa,
  esp32-ros2-rover, keyastro, scholar-static.

## Commands

- Roadmap (reads the rover's README): `python3 scripts/make_roadmap.py`
- Architecture diagram: `python3 scripts/make_architecture.py`
- Dashboard (public API data): `GITHUB_TOKEN="$(gh auth token)" python3 scripts/make_dashboard.py`
- Demo screenshots: `scripts/capture_demos.sh`
- Check SVGs: `xmllint --noout assets/*.svg`
- Check for secrets before a push: `gitleaks git --redact .`
- Preview: render `README.md` locally (for example with `pandoc -f gfm`) with the SVGs inlined, in light and dark, or
  read the page on GitHub after pushing.

## Definition of done

- Every link opens the intended page; every listed repository is public and has a README and a licence.
- The graphics read correctly in light and dark mode and at narrow widths; no label is clipped.
- The page matches the profile settings (name, bio, pins) and the sources of the numbers (`dashboard-*` rules are
  written at the top of `scripts/make_dashboard.py`).
