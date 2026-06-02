#!/usr/bin/env python3
"""Build /api/pages-index.json — a flat record list of every case + story
page on realufo.org, so the cross-archive search at /search.html can index
narrative prose alongside the per-archive manifests.

Each emitted record looks like a normalised manifest entry:

    {
      "title":  "Nimitz Tic-Tac, November 2004",
      "desc":   "first 280 chars of <meta name=description>",
      "agency": "AARO",
      "type":   "Case",
      "date":   "2004-11-14",
      "region": "SOCAL Operating Area",
      "url":    "/aaro/tic-tac.html",
      "src":    "https://www.aaro.mil/",
      "local":  "",
      "site":   "AARO",
      "siteId": "aaro",
      "siteDir":"aaro/",
      "kind":   "case"
    }

Usage:
    python3 scripts/build-pages-index.py
"""
from __future__ import annotations

import glob
import html
import json
import os
import re
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'api', 'pages-index.json')

ARCHIVE_LABEL = {
    'aaro': 'AARO', 'nasa': 'NASA', 'nara': 'NARA',
    'geipan': 'GEIPAN', 'uk': 'UK', 'brazil': 'Brazil',
    'chile': 'Chile', 'argentina': 'Argentina', 'canada': 'Canada',
    'italy': 'Italy', 'nz': 'NZ', 'peru': 'Peru',
    'spain': 'Spain', 'uruguay': 'Uruguay',
}

TITLE_RE = re.compile(r'<title>([^<]+)</title>', re.I)
DESC_RE  = re.compile(r'<meta\s+name="description"\s+content="([^"]+)"', re.I)
CANON_RE = re.compile(r'<link\s+rel="canonical"\s+href="([^"]+)"', re.I)
COORD_RE = re.compile(
    r'◉\s*[~≈]?\s*(?:\d+\.?\d*\s*°\s*[NS]\s*[·\.,]\s*[~≈]?\s*\d+\.?\d*\s*°\s*[EW]\s*[·\.,]?\s*)?([^<·]+)',
    re.I,
)
DATE_LD_RE = re.compile(r'"datePublished"\s*:\s*"([^"]+)"', re.I)
PUB_LD_RE  = re.compile(r'"sourceOrganization"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"', re.I)


def normalise_title(t: str) -> str:
    t = html.unescape(t).strip()
    # Strip the common " · " suffix patterns
    for sep in [' · realufo.org', ' — case file · ', ' · case file', ' — realufo.org']:
        if sep in t:
            t = t.split(sep)[0]
    return t.strip()


def extract(html_path: str) -> dict | None:
    try:
        src = open(html_path, encoding='utf-8').read()
    except FileNotFoundError:
        return None

    title_m = TITLE_RE.search(src)
    desc_m  = DESC_RE.search(src)
    canon_m = CANON_RE.search(src)
    date_m  = DATE_LD_RE.search(src)
    pub_m   = PUB_LD_RE.search(src)
    coord_m = COORD_RE.search(src)

    if not title_m:
        return None
    title = normalise_title(title_m.group(1))
    desc  = (desc_m.group(1) if desc_m else '').strip()
    url   = canon_m.group(1) if canon_m else ('/' + html_path)
    date  = (date_m.group(1)[:10] if date_m else '')
    agency = (pub_m.group(1) if pub_m else '')
    # Hero coord 'region' is the trailing text after the lat/lon — best-effort.
    region = ''
    if coord_m:
        region = re.sub(r'\s+', ' ', coord_m.group(1)).strip(' ·,')

    archive = html_path.split('/', 1)[0] if '/' in html_path else 'wargov'
    is_story = html_path.endswith('/story.html')
    kind = 'story' if is_story else 'case'
    label = ARCHIVE_LABEL.get(archive, archive)
    # Phase 04.1: case stories live at /stories/{slug}/ (Plan 04.1-03).
    # `/aaro/tic-tac.html` → `/stories/tic-tac/`; `/aaro/story.html` →
    # `/stories/aaro-overview/`. Same rewrite shape as build-geo.py (8b053c0).
    leaf = html_path.rsplit('/', 1)[-1].removesuffix('.html')
    if is_story:
        case_slug = f'{archive}-overview'
    else:
        case_slug = leaf
    rel_url = f'/stories/{case_slug}/'
    return {
        'title':       title,
        'desc':        desc,
        'agency':      agency or label,
        'type':        'Story' if is_story else 'Case',
        'date':        date,
        'region':      region[:140],
        'url':         rel_url,
        'src':         '',
        'local':       '',
        'site':        label,
        'siteId':      archive,
        'siteDir':     archive + '/',
        'kind':        kind,
    }


def main() -> int:
    targets = sorted(set(
        glob.glob('*/story.html')
    ) | set(
        f for f in glob.glob('*/*.html')
        if not f.endswith(('/index.html', '/details.html', '/story.html', '/cases.json'))
    ))
    records = []
    for rel in targets:
        rec = extract(rel)
        if rec:
            records.append(rec)
            print(f'  + {rel}')
        else:
            print(f'  - {rel} (skipped)')

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump({
            '_meta': {
                'description': 'Per-page index for case + story pages, so the cross-archive search can index narrative prose alongside per-archive manifests.',
                'count': len(records),
                'kinds': sorted(set(r['kind'] for r in records)),
            },
            'records': records,
        }, f, ensure_ascii=False, indent=2)
    print(f'\n→ wrote {os.path.relpath(OUT)} ({len(records)} pages)')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
