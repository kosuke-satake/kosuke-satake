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

- Stack: one Markdown file plus generated SVGs, two screenshots and a small `data/taglines.json`. No build step and no
  dependencies; the scripts use the Python standard library (3.11+) and, for screenshots, Google Chrome and `sips` on
  macOS.
- Files:
  - `README.md`: the profile page. Light/dark variants of each graphic are chosen with `<picture>`.
  - `assets/`: generated graphics (`banner-*`, `rover-architecture-*`, `rover-roadmap-*`, `dashboard-*`; `-light` and
    `-dark` each) and the demo screenshots `web-*.jpg`. `banner-*` are drawn by hand; the rest are generated.
  - `scripts/`: the generators and the link check (below). `data/`: short lines for the apps grid.
  - `LICENSE` (MIT), the agent files, and the editor and Git settings.
- Constraints:
  - Must be a public repository named exactly like the account (`kosuke-satake`), or GitHub shows nothing.
  - English only, no personal data (no e-mail address, phone number or home address, no local paths).
  - Link only to repositories in publishable shape. `go2-w_ws` is left out until its local paths are fixed and it has a
    licence.
  - Held apps are not named in lists. App icons come from `kosuke-apps/.github` (our own repository).
  - The templates are described as supporting multiple languages (i18n), not as English and Japanese only.
- The page keeps itself current. `.github/workflows/refresh.yml` runs every day (and on a push, and by hand from the
  Actions tab) and rebuilds three things from live data: the apps grid between the `apps:start` and `apps:end` markers
  of `README.md` (read from the organization page `kosuke-apps/.github`, `profile/README.md`: its order, names and
  icons; apps in `HIDDEN` are skipped), `dashboard-*` (GitHub statistics) and `rover-roadmap-*` (the rover's README).
  It then checks that every link and image opens. If any step fails nothing is committed and the page keeps its last
  good version; GitHub e-mails the owner about the failed run.
- Never edit the apps grid by hand; change the organization page, or `data/taglines.json` for the short line under an
  icon (without an entry the line is the start of the repository description).
- By hand only: the Robotics and Web text, the Sandbox sentence, and the demo screenshots (they need macOS and Chrome:
  run `scripts/capture_demos.sh` when a demo changes).
- Name, bio, status and the six pinned repositories are profile settings, not files. The user changes them in the
  GitHub UI (the CLI token has no `user` scope, and pins have no API). Pins follow the order of the page: Robotics, Web, Apps.

## Commands

- Roadmap (reads the rover's README): `python3 scripts/make_roadmap.py`
- Architecture diagram: `python3 scripts/make_architecture.py`
- Apps grid (reads the organization page): `GITHUB_TOKEN="$(gh auth token)" python3 scripts/make_apps.py`
- Dashboard (public API data): `GITHUB_TOKEN="$(gh auth token)" python3 scripts/make_dashboard.py`
- Every link opens: `python3 scripts/check_links.py`
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
