#!/usr/bin/env python3
"""build-dir-index.py — emit minimal directory-index HTML for /api/ + /feeds/.

CF Pages returns 404 for directory URLs that have no `index.html`. The
api/ + feeds/ directories ship JSON + XML payloads (consumed by the
whatsnew + about pages and external scrapers/LLMs), but without an
index.html the bare `/api/` and `/feeds/` URLs 404.

This script walks `dist/api/` and `dist/feeds/` (post copy-legacy-archives)
and emits one `index.html` per directory listing the contents. Designed
to be invoked from `scripts/copy-legacy-archives.sh` AFTER the copy block.

Output shape:
  <h1>{title}</h1>
  <p>{description}</p>
  <ul>
    <li><a href="all.json">all.json</a> <span>{size}</span></li>
    ...
  </ul>

Includes SEO meta: <title>, <meta description>, <link rel=canonical>.
Surfaced by /gsd:debug link-asset-seo-audit (2026-06-02).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DIST = REPO / 'dist'

# Per-directory metadata. Keys are dist-relative directory paths.
DIR_META = {
    'api': {
        'title': 'API · realufo.org',
        'description': 'Static JSON dump of every government UAP record across 15 archives — for researchers, LLM scrapers, and downstream tools.',
        'lede': 'Static JSON snapshots regenerated on each archive sync. CC0-equivalent public-domain content per per-archive licensing (see <a href="/about/">/about/</a>).',
    },
    'feeds': {
        'title': 'Feeds · realufo.org',
        'description': 'Atom/RSS feeds of every government UAP archive. Subscribe to the firehose or any single agency.',
        'lede': 'Per-archive Atom feeds plus an all-archive firehose. Refreshed weekly via the scrape automation pipeline.',
    },
}

HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="https://realufo.org/{slug}/">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="https://realufo.org/{slug}/">
<meta property="og:type" content="website">
<link rel="icon" type="image/svg+xml" href="/assets/favicon.svg">
<style>
:root{{--bg:#0a0a0c;--ink:#e8e3d8;--ink-dim:#a8a298;--ink-faint:#6b665d;--rule:rgba(232,227,216,0.12);--caution:#d4a017;--mono:"JetBrains Mono",monospace;--serif:"Source Serif 4",Georgia,serif}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--ink);font-family:var(--serif);max-width:65ch;margin:64px auto;padding:0 16px;line-height:1.6}}
h1{{font-family:var(--serif);font-size:32px;margin-bottom:8px}}
.subtitle{{color:var(--ink-dim);margin-bottom:24px}}
.lede{{font-size:14px;color:var(--ink-dim);margin-bottom:32px;padding-bottom:16px;border-bottom:1px solid var(--rule)}}
.lede a{{color:var(--caution)}}
ul{{list-style:none}}
li{{padding:10px 0;border-bottom:1px solid var(--rule);display:flex;justify-content:space-between;align-items:baseline;gap:12px}}
a{{color:var(--caution);text-decoration:none;font-family:var(--mono);font-size:13px;letter-spacing:0.04em}}
a:hover{{text-decoration:underline}}
.size{{color:var(--ink-faint);font-family:var(--mono);font-size:11px}}
nav{{margin-top:48px;font-family:var(--mono);font-size:12px;color:var(--ink-faint)}}
nav a{{color:var(--ink-dim)}}
</style>
</head>
<body>
<h1>{title}</h1>
<p class="subtitle">{description}</p>
<p class="lede">{lede}</p>
<ul>
{entries}
</ul>
<nav>← <a href="/">realufo.org</a></nav>
</body>
</html>
"""


def human_size(bytes_: int) -> str:
    for unit in ('B', 'KB', 'MB', 'GB'):
        if bytes_ < 1024:
            return f'{bytes_:.0f} {unit}' if unit == 'B' else f'{bytes_:.1f} {unit}'
        bytes_ /= 1024
    return f'{bytes_:.1f} TB'


def emit_index(dir_path: Path, slug: str, meta: dict) -> None:
    files = sorted(
        f for f in dir_path.iterdir()
        if f.is_file() and f.name != 'index.html'
    )
    if not files:
        return

    entries_html = '\n'.join(
        f'  <li><a href="{f.name}">{f.name}</a> <span class="size">{human_size(f.stat().st_size)}</span></li>'
        for f in files
    )

    html = HTML_TEMPLATE.format(
        title=meta['title'],
        description=meta['description'],
        lede=meta['lede'],
        slug=slug,
        entries=entries_html,
    )

    (dir_path / 'index.html').write_text(html, encoding='utf-8')
    print(f'  → dist/{slug}/index.html ({len(files)} entries)')


def main() -> int:
    if not DIST.exists():
        print('build-dir-index: dist/ missing — run after `astro build`', file=sys.stderr)
        return 1

    print('[postbuild] build-dir-index: emitting directory indexes')
    for slug, meta in DIR_META.items():
        d = DIST / slug
        if d.exists():
            emit_index(d, slug, meta)
        else:
            print(f'  · dist/{slug}/ missing — skip', file=sys.stderr)

    return 0


if __name__ == '__main__':
    sys.exit(main())
