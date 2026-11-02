#!/bin/sh
# Capture the live demos of the web templates for the profile README.
#
# Needs macOS with Google Chrome and `sips` (both ship with or run on a normal Mac setup). Writes
# assets/web-<name>.jpg, 960 px wide. Run it again whenever a demo site changes.
set -eu

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
HERE="$(cd "$(dirname "$0")" && pwd)"
ASSETS="$HERE/../assets"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

capture() {
  name="$1"
  url="$2"
  budget="$3" # virtual milliseconds to wait: long enough for the page to load its data and finish its intro
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --window-size=1280,800 \
    --virtual-time-budget="$budget" --run-all-compositor-stages-before-draw --user-data-dir="$WORK/profile" \
    --screenshot="$WORK/$name.png" "$url" >/dev/null 2>&1
  sips -s format jpeg -s formatOptions 82 --resampleWidth 960 "$WORK/$name.png" \
    --out "$ASSETS/web-$name.jpg" >/dev/null
  echo "web-$name.jpg"
}

mkdir -p "$ASSETS"
capture keyastro "https://key-astro.pages.dev/en/" 15000
capture scholar-static "https://scholar-static.pages.dev/" 30000
