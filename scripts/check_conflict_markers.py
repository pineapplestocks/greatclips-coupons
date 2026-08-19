#!/usr/bin/env python3
"""
Fail if any published file still contains git conflict markers.

This exists because it already happened: a `git stash pop || true` in the scrape
workflow swallowed a conflict, and 59 pages under docs/ were committed and
deployed with literal "<<<<<<< Updated upstream" text in their <head>, alongside
119 pages that silently lost their AdSense meta tag. Regenerating cannot catch
that on its own, so this runs as a gate before any commit.

Exit codes:
    0  clean
    1  markers found (prints every file and line)

Usage:
    python scripts/check_conflict_markers.py [path ...]
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TARGETS = ["docs", "pages", "data", "template.html"]

# Anchored at line start so ordinary prose or code containing "=======" as a rule
# or underline is not flagged.
MARKERS = ("<<<<<<< ", ">>>>>>> ", "|||||||  ")
TEXT_SUFFIXES = {".html", ".xml", ".json", ".js", ".css", ".md", ".txt", ".py"}


def iter_files(targets: list[str]):
    for target in targets:
        path = REPO_ROOT / target
        if path.is_file():
            yield path
        elif path.is_dir():
            for child in path.rglob("*"):
                if child.is_file() and child.suffix.lower() in TEXT_SUFFIXES:
                    yield child


def main() -> int:
    targets = sys.argv[1:] or DEFAULT_TARGETS
    hits: list[tuple[Path, int, str]] = []
    scanned = 0

    for path in iter_files(targets):
        scanned += 1
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not any(m.strip() in text for m in MARKERS):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if line.startswith(MARKERS) or line.rstrip() == "=======":
                hits.append((path, lineno, line[:70]))

    if not hits:
        print(f"No conflict markers found ({scanned:,} files scanned).")
        return 0

    print(f"Conflict markers found in {len({h[0] for h in hits})} file(s):")
    for path, lineno, line in hits[:60]:
        print(f"  {path.relative_to(REPO_ROOT).as_posix()}:{lineno}: {line}")
    if len(hits) > 60:
        print(f"  ... and {len(hits) - 60} more")
    print("\nResolve these before committing - do not publish conflict markers.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
