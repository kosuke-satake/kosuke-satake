#!/usr/bin/env python3
"""Check that every link and image on the profile README opens.

Reads README.md, collects each https URL (HTML attributes and Markdown links) and each local assets/ path, and
requests every URL once. Anything that does not answer 2xx, or a local file that is missing, makes the script exit
with 1. It runs in the scheduled workflow, so a renamed repository or a deleted icon shows up as a failed run
instead of a broken picture on the page. Standard library only.
"""

from __future__ import annotations

import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
URL = re.compile(r'(?:href|src|srcset)="(https://[^"]+)"|\]\((https://[^)\s]+)\)')
LOCAL = re.compile(r'(?:src|srcset)="(assets/[^"]+)"')
HEADERS = {"User-Agent": "profile-readme-link-check"}


def status(url: str) -> int:
    """HTTP status after redirects; HEAD first, GET when a server refuses HEAD. Transient errors are retried."""
    code = 0
    for attempt in range(3):
        for method in ("HEAD", "GET"):
            request = urllib.request.Request(url, headers=HEADERS, method=method)
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    return response.status
            except urllib.error.HTTPError as error:
                code = error.code
                if method == "HEAD" and code in (403, 405, 501):
                    continue  # try GET
                break
            except (urllib.error.URLError, TimeoutError):
                code = 0
                break
        if code and code < 429 and code != 0:
            return code  # a definite answer such as 404: no point retrying
        time.sleep(3 * (attempt + 1))
    return code


def main() -> int:
    text = README.read_text(encoding="utf-8")
    urls = sorted({(a or b).split("#")[0] for a, b in URL.findall(text)})
    local = sorted(set(LOCAL.findall(text)))
    broken = 0
    for path in local:
        if not (ROOT / path).is_file():
            print(f"MISSING  {path}")
            broken += 1
    for url in urls:
        code = status(url)
        if 200 <= code < 300:
            print(f"ok       {url}")
        else:
            print(f"BROKEN   {code or 'no answer'}  {url}")
            broken += 1
        time.sleep(0.3)
    print(f"{len(urls)} links and {len(local)} local files checked, {broken} broken")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
