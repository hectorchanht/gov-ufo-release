#!/usr/bin/env python3
# Generated input for the Phase 2 URL-CONTRACT drift gate. See .planning/REQUIREMENTS.md PMS-01.
"""Snapshot every public route + per-card anchor served by the live site.

Walks every git-tracked `*.html` file at the repo root and one level deep,
derives the public URL each file maps to under the current GitHub Pages
deployment convention, and ALSO extracts the implicit `#card-<id>` anchor
namespace from inline JSON manifests embedded in those pages
(`<script id="arch-data" type="application/json">` for the 15 archive
catalog pages; `<script id="archive-manifest" type="application/json">`
for the war.gov root landing). Per-card anchors are derived from each
asset's `ti`/`Title` field (lowercased, slugified, deduped) since the
current client-side renderer does not emit static `id` attributes.

The output is written to `URL-CONTRACT.txt` at the repo root, sorted,
one URL per line, with a provenance header recording the source commit
SHA and snapshot date. The file is exclusively generator output — never
hand-edit.

Why: Per research/PITFALLS.md Pitfall #2, SSG migrations silently break
URL contracts (trailing-slash policy disagreements between Astro,
Eleventy, GitHub Pages, Cloudflare Pages). The frozen snapshot from
`main` taken before any SSG code lands is the regression target for the
Phase 2 CI drift gate. PMS-01.

What it walks:
  - Root utility pages:   /, /search.html, /timeline.html, /map.html,
                          /about.html, /donate.html, /foia.html, …
  - Mirror index pages:   /aaro/, /nasa/, /nara/, /geipan/, /uk/,
                          /brazil/, /chile/, /argentina/, /canada/,
                          /italy/, /nz/, /peru/, /spain/, /uruguay/
  - Story / case pages:   /aaro/tic-tac.html, /uk/rendlesham.html, …
  - Per-card anchors:     <page>#card-<slug-from-title> for every asset
                          parseable from the inline JSON manifest.

CLI:
    python3 scripts/snapshot-urls.py            # write URL-CONTRACT.txt
    python3 scripts/snapshot-urls.py --stdout   # print to stdout (no write)
    python3 scripts/snapshot-urls.py --check    # CI: exit 1 on body drift

`--check` compares the structural URL body — the sorted list of routes
and `#card-<id>` anchors — not the volatile provenance header (SHA +
count), so the snapshot commit's own SHA advancing HEAD does not make
the file eternally "stale" against itself. Refresh the provenance line
by re-running without `--check`.

Exit codes:
    0 — wrote (or matched) URL-CONTRACT.txt successfully.
    1 — `--check` found drift in the URL body vs current tracked HTML.
    2 — failed to read the repo (git unavailable AND glob fallback empty).

Stdlib only — `os`, `sys`, `re`, `json`, `glob`, `subprocess`, `datetime`,
`argparse`. No BeautifulSoup, no lxml. Matches the
`stdlib-only except curl_cffi` convention from CLAUDE.md §6.2.
"""
from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(REPO, 'URL-CONTRACT.txt')

# Directories that may contain tracked .html files but must not appear
# in the public URL contract (build artifacts, vendor copies, caches).
# 'legacy/' is excluded post-Phase 04.1 — the legacy/ tree holds pre-SSG
# HTML that is NOT user-navigable from the active surface; its public
# URLs are surfaced indirectly via _redirects 301s (see Plan 04.1-06),
# not via direct enumeration.
EXCLUDE_DIR_PREFIXES = (
    '.git/',
    '.cache/',
    '.pdftext/',
    '__pycache__/',
    'node_modules/',
    'bundles/',
    'legacy/',
    'assets/vendor/',
    '_site/',
)

# Matches the inline JSON manifest contract documented in
# scripts/templates/archive.py and used by every archive's index.html.
# Two IDs supported per STRUCTURE.md / 01-CONTEXT.md §interfaces.
MANIFEST_RE = re.compile(
    r'<script id="(?:arch-data|archive-manifest)" type="application/json">(.*?)</script>',
    re.DOTALL,
)

# Slugify regex: any run of non-[a-z0-9] collapses to a single hyphen.
_SLUG_RE = re.compile(r'[^a-z0-9]+')


def short_sha() -> str:
    """Return the current HEAD short SHA, or a fallback if git is unavailable."""
    try:
        out = subprocess.run(
            ['git', '-C', REPO, 'rev-parse', '--short', 'HEAD'],
            capture_output=True, text=True, check=True, timeout=3,
        ).stdout.strip()
        return out or 'unknown'
    except Exception:
        return 'unknown'


def list_tracked_html() -> list[str]:
    """Return repo-relative paths of every tracked `.html` file.

    Uses `git ls-files` first (matching the repo convention from
    CLAUDE.md §6.2). Falls back to `glob.glob` under REPO if git fails
    (e.g. running on a freshly-extracted tarball without .git).
    """
    try:
        out = subprocess.run(
            ['git', '-C', REPO, 'ls-files', '*.html'],
            capture_output=True, text=True, check=True, timeout=10,
        ).stdout
        files = [line.strip() for line in out.splitlines() if line.strip()]
        if files:
            return files
    except Exception:
        pass
    # Fallback: glob root + one level deep + two levels deep (covers
    # aaro/pages/*.html and nara/pages/*.html).
    found = set()
    for pattern in ('*.html', '*/*.html', '*/*/*.html'):
        for p in glob.glob(os.path.join(REPO, pattern)):
            rel = os.path.relpath(p, REPO).replace(os.sep, '/')
            found.add(rel)
    return sorted(found)


def is_excluded(rel: str) -> bool:
    """True if the file's repo-relative path falls under a build-artifact dir."""
    norm = rel.replace(os.sep, '/')
    return any(norm.startswith(pfx) for pfx in EXCLUDE_DIR_PREFIXES)


def html_to_public_url(rel: str) -> str:
    """Map a repo-relative HTML path to its GitHub Pages public URL.

    Conventions (per CLAUDE.md §4 + research/PITFALLS.md §Pitfall 2):
      - `index.html`                      → `/`
      - `<slug>/index.html`               → `/<slug>/`
      - `<dir>/<dir>/index.html`          → `/<dir>/<dir>/`
      - `<path>/<name>.html` (non-index)  → `/<path>/<name>.html`
      - `<name>.html` at repo root        → `/<name>.html`
    """
    rel = rel.replace(os.sep, '/')
    if rel == 'index.html':
        return '/'
    if rel.endswith('/index.html'):
        return '/' + rel[:-len('index.html')]
    return '/' + rel


def slugify(text: str) -> str:
    """Reduce free-text to a stable URL anchor slug.

    Rules: lowercase → collapse runs of non-[a-z0-9] to a single hyphen
    → strip leading/trailing hyphens → truncate to 80 chars.
    """
    if not text:
        return ''
    s = _SLUG_RE.sub('-', text.lower()).strip('-')
    return s[:80].strip('-')


def asset_identity(asset: dict) -> str:
    """Pick the best slug source from one asset record.

    Preference order (per 01-02-PLAN.md task 1 step 3):
      1. explicit `id` field if present (future-proofing for SRC-04).
      2. `ti` (archive catalog convention — scripts/templates/archive.py).
      3. `Title` (root war.gov manifest convention — CSV-keyed rows).
      4. any string-valued field whose key suggests a title.
    """
    if isinstance(asset, dict):
        if asset.get('id'):
            return slugify(str(asset['id']))
        for key in ('ti', 'Title', 'title', 'Video Title'):
            v = asset.get(key)
            if v:
                return slugify(str(v))
    return ''


def extract_card_anchors(html: str, page_url: str, source_path: str) -> list[str]:
    """Parse inline arch-data / archive-manifest blocks and return anchor URLs.

    On malformed JSON, emits a stderr warning and returns []. The caller
    still records the bare page URL (T-02-02 mitigation).
    """
    anchors: list[str] = []
    seen: dict[str, int] = {}
    for match in MANIFEST_RE.finditer(html):
        payload = match.group(1)
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            print(
                f'warning: failed to parse inline manifest in {source_path}: {exc}',
                file=sys.stderr,
            )
            continue
        # Catalog shape: { "assets": [...], ... }
        # Root shape:    { "rows":   [...], ... }
        records: list = []
        if isinstance(data, dict):
            if isinstance(data.get('assets'), list):
                records = data['assets']
            elif isinstance(data.get('rows'), list):
                records = data['rows']
        for asset in records:
            slug = asset_identity(asset)
            if not slug:
                continue
            # Collision suffix: -2, -3, … in order of appearance.
            count = seen.get(slug, 0) + 1
            seen[slug] = count
            final = slug if count == 1 else f'{slug}-{count}'
            anchors.append(f'{page_url}#card-{final}')
    return anchors


def build_url_list() -> tuple[list[str], int, int]:
    """Walk tracked HTML, return (sorted_urls, page_count, anchor_count)."""
    urls: set[str] = set()
    page_count = 0
    anchor_count = 0
    for rel in list_tracked_html():
        if is_excluded(rel):
            continue
        abs_path = os.path.join(REPO, rel)
        if not os.path.isfile(abs_path):
            continue
        try:
            html = open(abs_path, encoding='utf-8').read()
        except OSError as exc:
            print(f'warning: cannot read {rel}: {exc}', file=sys.stderr)
            continue
        page_url = html_to_public_url(rel)
        urls.add(page_url)
        page_count += 1
        for anchor in extract_card_anchors(html, page_url, rel):
            if anchor not in urls:
                anchor_count += 1
            urls.add(anchor)
    return sorted(urls), page_count, anchor_count


def render_contract() -> tuple[str, int, int, int]:
    """Render the full URL-CONTRACT.txt body. Returns (text, total, pages, anchors)."""
    urls, page_count, anchor_count = build_url_list()
    sha = short_sha()
    date = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')
    total = len(urls)
    header = (
        '# URL-CONTRACT.txt\n'
        f'# Snapshot taken from main @ {sha} on {date}\n'
        f'# Total routes + anchors: {total}\n'
        '# Generator: scripts/snapshot-urls.py (idempotent — re-run to refresh)\n'
    )
    body = '\n'.join(urls)
    text = header + body + '\n'
    return text, total, page_count, anchor_count


def _strip_volatile_header(text: str) -> str:
    """Drop the dynamic-provenance header lines so --check compares structure only.

    The `# Snapshot taken from main @ <sha> on <date>` line and the
    `# Total routes + anchors: <count>` line both change with every
    commit (the SHA advances; the count is informational). Comparing
    them byte-for-byte would mean --check is unsatisfiable as soon as
    the snapshot itself lands in a commit (HEAD moves to the snapshot
    commit; next regen records the new SHA). The structural body —
    the sorted URL list — is what the CI drift gate actually polices.
    Keep `# URL-CONTRACT.txt` and `# Generator: ...` since those are
    static markers, not provenance.
    """
    lines = []
    for line in text.splitlines(keepends=True):
        if line.startswith('# Snapshot taken from main @'):
            continue
        if line.startswith('# Total routes + anchors:'):
            continue
        lines.append(line)
    return ''.join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Snapshot the live URL contract (routes + #card-<id> anchors).',
    )
    parser.add_argument(
        '--stdout', action='store_true',
        help='Print the generated contract to stdout instead of writing the file.',
    )
    parser.add_argument(
        '--check', action='store_true',
        help='Regenerate in memory and exit non-zero if URL-CONTRACT.txt is stale.',
    )
    args = parser.parse_args()

    text, total, page_count, anchor_count = render_contract()

    if args.stdout:
        sys.stdout.write(text)
        return 0

    if args.check:
        if not os.path.exists(OUTPUT):
            print(f'URL-CONTRACT.txt missing at {OUTPUT}', file=sys.stderr)
            return 1
        existing = open(OUTPUT, encoding='utf-8').read()
        # Compare structural content (sorted URL body + static markers)
        # ignoring volatile provenance fields (SHA, count) — the SHA
        # changes every commit, making the snapshot commit itself
        # eternally "stale" against its own --check otherwise.
        if _strip_volatile_header(existing) != _strip_volatile_header(text):
            print('URL-CONTRACT.txt is stale — re-run scripts/snapshot-urls.py', file=sys.stderr)
            return 1
        print(f'URL-CONTRACT.txt up-to-date ({total} entries: {page_count} pages + {anchor_count} anchors).')
        return 0

    with open(OUTPUT, 'w', encoding='utf-8') as fh:
        fh.write(text)
    print(f'Wrote {os.path.relpath(OUTPUT, REPO)} — {total} entries ({page_count} pages + {anchor_count} anchors).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
