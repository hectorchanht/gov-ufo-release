#!/usr/bin/env python3
"""build-sitemap.py — emit dist/sitemap.xml listing every canonical realufo.org route.

Source of truth: URL-CONTRACT.txt (Plan 04.1-06 manifest of every public URL).
Run as a postbuild step (invoked from scripts/copy-legacy-archives.sh).

Why a hand-rolled sitemap instead of @astrojs/sitemap:
  - @astrojs/sitemap only indexes Astro-emitted routes (src/pages/**). The
    11 dormant-archive indexes ship via scripts/copy-legacy-archives.sh as
    plain HTML (CLAUDE.md §2 status table) — those slugs would be missing.
  - URL-CONTRACT.txt is already the canonical list used by
    scripts/build-redirects.py and the quality-gates.yml drift gate, so
    keeping the sitemap on the same source = single point of truth.

Output:
  dist/sitemap.xml — sitemaps.org v0.9 schema, listing every canonical
  route from URL-CONTRACT.txt. Trailing-slash form preserved per
  astro.config.mjs `trailingSlash: 'ignore'` + the Plan 04.1-06 redirect
  contract.

CLAUDE.md §13 — this is in the Phase-4 Python carve-out (verification +
infra scripts that survive Python retirement).
"""

import datetime
from pathlib import Path
import sys
import xml.sax.saxutils as sx

REPO = Path(__file__).resolve().parent.parent
URL_CONTRACT = REPO / "URL-CONTRACT.txt"
DIST = REPO / "dist"
SITE = "https://realufo.org"


def parse_url_contract() -> list[str]:
    """Read URL-CONTRACT.txt; return ordered list of canonical paths."""
    if not URL_CONTRACT.exists():
        print(f"build-sitemap: URL-CONTRACT.txt missing at {URL_CONTRACT}", file=sys.stderr)
        sys.exit(1)
    routes: list[str] = []
    for line in URL_CONTRACT.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if not line.startswith("/"):
            continue
        # /search.html is a legacy redirect target on CF Pages and not a
        # canonical SEO URL — the live route is /search/ (src/pages/search.astro).
        if line == "/search.html":
            line = "/search/"
        routes.append(line)
    # De-dup while preserving order.
    seen: set[str] = set()
    out: list[str] = []
    for r in routes:
        if r in seen:
            continue
        seen.add(r)
        out.append(r)
    return out


def priority_for(path: str) -> str:
    """Heuristic SEO priority by path depth + type."""
    if path == "/":
        return "1.0"
    if path in ("/aaro/", "/nasa/", "/nara/", "/stories/"):
        return "0.9"
    if path.startswith("/stories/"):
        return "0.7"
    if path in ("/about/", "/foia/", "/glossary/", "/map/", "/timeline/", "/whatsnew/", "/search/"):
        return "0.6"
    # Dormant archive indexes
    return "0.5"


def changefreq_for(path: str) -> str:
    if path == "/":
        return "weekly"
    if path.startswith("/stories/"):
        return "monthly"
    if path in ("/whatsnew/", "/timeline/", "/map/"):
        return "weekly"
    return "monthly"


def build_xml(routes: list[str]) -> str:
    today = datetime.date.today().isoformat()
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for r in routes:
        loc = sx.escape(f"{SITE}{r}")
        lines.append("  <url>")
        lines.append(f"    <loc>{loc}</loc>")
        lines.append(f"    <lastmod>{today}</lastmod>")
        lines.append(f"    <changefreq>{changefreq_for(r)}</changefreq>")
        lines.append(f"    <priority>{priority_for(r)}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def main() -> int:
    if not DIST.exists():
        print(f"build-sitemap: {DIST} does not exist; skipping (was astro build run?)", file=sys.stderr)
        return 0
    routes = parse_url_contract()
    xml = build_xml(routes)
    out = DIST / "sitemap.xml"
    out.write_text(xml, encoding="utf-8")
    print(f"build-sitemap: wrote {out} ({len(routes)} urls)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
