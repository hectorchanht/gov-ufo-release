#!/usr/bin/env python3
"""rewrite-dist-legacy-links.py — eliminate legacy 301 hops in copied HTML.

Mirrors the rules in `src/scripts/extractLegacyBody.ts :: rewriteLegacyLinks()`
but applies them as a postbuild pass over `dist/<archive>/*.html` (the
files shipped by copy-legacy-archives.sh — Plan 04.1-02). Active Astro
routes already went through the extractor.

Production CF Pages handles every legacy URL via _redirects 301s (Plan
04.1-06), so this script doesn't BREAK anything if skipped — but
eliminating the redirect chain on internal nav reduces dev/preview-server
404s, improves crawl efficiency, and tightens HTTP 301 cache invariants.

Surfaced by /gsd:debug link-asset-seo-audit (2026-06-02) — TODO
`2026-06-02-legacy-internal-link-cleanup.md`.

Rewrite rule set (kept in sync with extractLegacyBody.ts):
  /<slug>.html          → /<slug>/      (6 site-page slugs)
  /<archive>/<case>.html → /stories/<case>/ (stories.json map)
  ../search.html(?q=…)   → /search/(?q=…)
  ./*.html               → /stories/<case>/ when within same archive dir
  ../<archive>/          → /<archive>/   (relative archive index → absolute)

Conservative: only rewrites `href="…"` + `src="…"` attribute values.
Verbatim text content (CLAUDE.md §9 trust boundary) is untouched.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parent.parent
DIST = REPO / 'dist'
STORIES_JSON = REPO / 'src' / 'data' / 'stories.json'

SITE_PAGE_SLUGS = {'about', 'foia', 'glossary', 'map', 'timeline', 'whatsnew'}

# Parked utility slugs — production redirects to /about/ via _redirects.
# Mirror that here so dev preview matches.
PARKED_SLUGS = {'donate', 'embed', 'compare', 'stats'}

ACTIVE_ARCHIVES = {'aaro', 'nasa', 'nara'}
DORMANT_ARCHIVES = {
    'geipan', 'uk', 'brazil', 'chile', 'argentina', 'canada',
    'italy', 'nz', 'peru', 'spain', 'uruguay',
}
ALL_ARCHIVES = ACTIVE_ARCHIVES | DORMANT_ARCHIVES | {'wargov'}

# Build LEGACY_TO_STORY map from stories.json (single source of truth).
def load_story_map() -> dict[str, str]:
    if not STORIES_JSON.exists():
        return {}
    data = json.loads(STORIES_JSON.read_text(encoding='utf-8'))
    m = {}
    for entry in data:
        legacy_path = entry.get('legacyPath', '')
        slug = entry.get('slug', '')
        # legacyPath format: "legacy/aaro/tic-tac.html"
        if legacy_path.startswith('legacy/') and slug:
            m[legacy_path[len('legacy/'):]] = slug
    return m


LEGACY_TO_STORY = load_story_map()


def source_archive(html_path: Path) -> str | None:
    """Given dist/<archive>/<file>.html, return <archive> if known."""
    try:
        rel = html_path.relative_to(DIST)
    except ValueError:
        return None
    parts = rel.parts
    if len(parts) >= 2 and parts[0] in ALL_ARCHIVES:
        return parts[0]
    return None


def rewrite_url(url: str, archive: str | None) -> str:
    """Apply rewrite rules. Return original on no match."""
    # Skip external + anchor-only + mailto/tel + protocol-relative
    if url.startswith(('http://', 'https://', '//', 'mailto:', 'tel:', '#', 'javascript:', 'data:')):
        return url
    if not url:
        return url

    # Split query / fragment off
    qmark = url.find('?')
    hash_ = url.find('#')
    split = min(p for p in (qmark, hash_, len(url)) if p >= 0)
    path = url[:split]
    suffix = url[split:]

    # Normalise relative parts. We don't fully URL-resolve — we pattern-match.
    # Cases:
    #   /about.html                → /about/
    #   /<archive>/<case>.html     → /stories/<case>/
    #   ../search.html             → /search/
    #   ../<archive>/<case>.html   → /stories/<case>/
    #   ../<archive>/              → /<archive>/
    #   ./<case>.html              → /stories/<case>/  (when same-archive)
    #   <case>.html                → /stories/<case>/  (when same-archive)

    # 1. Root-absolute site-page: /<slug>.html → /<slug>/
    m = re.match(r'^/([a-z0-9-]+)\.html$', path)
    if m and m.group(1) in SITE_PAGE_SLUGS:
        return f'/{m.group(1)}/' + suffix
    if m and m.group(1) in PARKED_SLUGS:
        return '/about/' + suffix

    # 2. Root-absolute archive case: /<archive>/<case>.html → /stories/<case>/
    m = re.match(r'^/([a-z0-9-]+)/([a-z0-9-]+)\.html$', path)
    if m:
        key = f'{m.group(1)}/{m.group(2)}.html'
        if key in LEGACY_TO_STORY:
            return f'/stories/{LEGACY_TO_STORY[key]}/' + suffix

    # 3. Root-absolute search: /search.html → /search/
    if path == '/search.html':
        return '/search/' + suffix

    # 4. Relative `../search.html`
    if path.endswith('search.html') and (path.startswith('../') or path.startswith('./') or '/' not in path):
        return '/search/' + suffix

    # 5. Relative `../<slug>.html` (site-page or parked)
    m = re.match(r'^\.\./([a-z0-9-]+)\.html$', path)
    if m and m.group(1) in SITE_PAGE_SLUGS:
        return f'/{m.group(1)}/' + suffix
    if m and m.group(1) in PARKED_SLUGS:
        return '/about/' + suffix

    # 6. Relative `../<archive>/<case>.html` → /stories/<case>/
    m = re.match(r'^\.\./([a-z0-9-]+)/([a-z0-9-]+)\.html$', path)
    if m:
        key = f'{m.group(1)}/{m.group(2)}.html'
        if key in LEGACY_TO_STORY:
            return f'/stories/{LEGACY_TO_STORY[key]}/' + suffix

    # 7. Relative `../<archive>/` (or with index.html) → /<archive>/
    m = re.match(r'^\.\./([a-z0-9-]+)/(?:index\.html)?$', path)
    if m and m.group(1) in ALL_ARCHIVES:
        return f'/{m.group(1)}/' + suffix

    # 8. Relative `../` from within an archive dir (back to root) → /
    if path == '../':
        return '/' + suffix
    if path == '../index.html':
        return '/' + suffix

    # 9. Same-dir `./<case>.html` or bare `<case>.html` → /stories/<case>/ (if known)
    if archive:
        stripped = path[2:] if path.startswith('./') else path
        m = re.match(r'^([a-z0-9-]+)\.html$', stripped)
        if m:
            key = f'{archive}/{m.group(1)}.html'
            if key in LEGACY_TO_STORY:
                return f'/stories/{LEGACY_TO_STORY[key]}/' + suffix

    return url


HREF_SRC_RE = re.compile(r'''((?:href|src)=)(["'])([^"']+)\2''', re.IGNORECASE)


def rewrite_file(path: Path) -> int:
    """Rewrite a single HTML file in-place. Returns count of URLs changed."""
    archive = source_archive(path)
    text = path.read_text(encoding='utf-8', errors='replace')
    changed = 0

    def repl(m: re.Match) -> str:
        nonlocal changed
        attr, quote, url = m.group(1), m.group(2), m.group(3)
        new_url = rewrite_url(url, archive)
        if new_url != url:
            changed += 1
            return f'{attr}{quote}{new_url}{quote}'
        return m.group(0)

    new_text = HREF_SRC_RE.sub(repl, text)
    if changed:
        path.write_text(new_text, encoding='utf-8')
    return changed


def main() -> int:
    if not DIST.exists():
        print('rewrite-dist-legacy-links: dist/ missing — run after copy-legacy-archives.sh', file=sys.stderr)
        return 1

    if not LEGACY_TO_STORY:
        print('rewrite-dist-legacy-links: WARN stories.json empty — skipping case rewrites', file=sys.stderr)

    target_dirs = ALL_ARCHIVES
    total_files = 0
    total_rewrites = 0

    print('[postbuild] rewrite-dist-legacy-links: walking dormant + partial-port archive HTML')
    for archive in sorted(target_dirs):
        d = DIST / archive
        if not d.exists():
            continue
        for html_file in d.rglob('*.html'):
            # Skip the Astro-owned <archive>/index.html for partial-port archives —
            # those went through the extractor's rewriteLegacyLinks already.
            rel = html_file.relative_to(DIST)
            if str(rel) in {f'{a}/index.html' for a in ACTIVE_ARCHIVES | {'nz', 'uruguay'}}:
                continue
            n = rewrite_file(html_file)
            if n:
                total_files += 1
                total_rewrites += n

    print(f'  → rewrote {total_rewrites} URLs across {total_files} files')
    return 0


if __name__ == '__main__':
    sys.exit(main())
