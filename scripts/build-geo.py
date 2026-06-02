#!/usr/bin/env python3
"""Bake /api/geo.json — geo-coded case pins for the /map.html viewer.

Sources lat/lon in this priority order:
  1. Explicit "◉ DD.DDDD° N · DD.DDDD° W" hero coord lines on case detail pages.
  2. Per-archive HQ centroid (fallback) — same table /map.html already uses.

Each entry contains enough metadata to render a popup linking back to the
detail page.

Usage:
    python3 scripts/build-geo.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from typing import List

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'api', 'geo.json')

# Case detail pages with coord lines.
CASE_PAGES = [
    'uk/rendlesham.html',
    'aaro/tic-tac.html',
    'aaro/gimbal.html',
    'aaro/phoenix-lights.html',
    'aaro/belgian-wave.html',
    'brazil/operacao-prato.html',
    'brazil/varginha.html',
    'brazil/trindade.html',
    'nz/kaikoura.html',
    'spain/manises.html',
    'geipan/trans-en-provence.html',
    'nara/roswell.html',
    'aaro/tehran.html',
    'nara/socorro.html',
    'aaro/jal-1628.html',
    'aaro/coyne.html',
    'aaro/travis-walton.html',
    'aaro/cash-landrum.html',
    'nara/robertson-panel.html',
    'nara/condon-committee.html',
    'geipan/valensole.html',
    'chile/el-bosque.html',
    'aaro/ohare-2006.html',
    'aaro/stephenville.html',
    'nara/lubbock-lights.html',
    'nara/mantell.html',
    'nara/chiles-whitted.html',
    'nara/levelland.html',
    'nara/mcminnville.html',
    'canada/shag-harbour.html',
    'canada/falcon-lake.html',
    'uk/cosford.html',
]


ARCHIVE_HQ = [
    ('wargov',    'War.gov / PURSUE',           '/',           38.8951, -77.0364),
    ('aaro',      'AARO',                       'aaro/',       38.8703, -77.0566),
    ('nasa',      'NASA UAP',                   'nasa/',       38.8830, -77.0163),
    ('nara',      'NARA',                       'nara/',       38.8929, -77.0227),
    ('geipan',    'France · GEIPAN',            'geipan/',     43.6047,   1.4442),
    ('uk',        'UK · National Archives',     'uk/',         51.4810,  -0.2790),
    ('brazil',    'Brazil · FAB',               'brazil/',    -15.7942, -47.8825),
    ('chile',     'Chile · SEFAA',              'chile/',     -33.4489, -70.6693),
    ('argentina', 'Argentina · CEFAe',          'argentina/', -34.6037, -58.3816),
    ('canada',    'Canada · LAC / Magnet',      'canada/',     45.4215, -75.6972),
    ('italy',     'Italy · Aeronautica',        'italy/',      41.9028,  12.4964),
    ('nz',        'NZ · NZDF',                  'nz/',        -41.2865, 174.7762),
    ('peru',      'Peru · OIFAA',               'peru/',      -12.0464, -77.0428),
    ('spain',     'Spain · Ejército del Aire',  'spain/',      40.4168,  -3.7038),
    ('uruguay',   'Uruguay · CRIDOVNI',         'uruguay/',   -34.9011, -56.1645),
]

# Match "◉ 52.0848° N · 1.4423° E" or "◉ 21.5519° S · 45.4297° W"
# Tolerate optional approximation markers ~ or ≈.
COORD_RE = re.compile(
    r'◉\s*[~≈]?\s*(\d+\.?\d*)\s*°\s*([NS])\s*[·\.,]\s*[~≈]?\s*(\d+\.?\d*)\s*°\s*([EW])',
    re.IGNORECASE,
)

# Manual coord overrides for case pages whose hero line is textual.
MANUAL_COORDS = {
    'aaro/gimbal.html':           (36.85, -75.30,   'Atlantic test range, US east coast'),
    'brazil/operacao-prato.html': (-0.92, -48.30,   'Colares, Pará, Brazil'),
    'aaro/jal-1628.html':         (64.00, -152.00,  'Yukon-Kuskokwim, interior Alaska'),
    'aaro/coyne.html':            (40.70, -81.40,   'Mansfield, Ohio'),
    'nara/robertson-panel.html':  (38.95, -77.15,   'CIA HQ Langley, Virginia'),
    'nara/condon-committee.html': (40.01, -105.27,  'University of Colorado, Boulder'),
}
TITLE_RE = re.compile(r'<title>([^<]+)</title>', re.I)
DESC_RE  = re.compile(r'<meta\s+name="description"\s+content="([^"]+)"', re.I)
PUB_RE   = re.compile(r'"datePublished"\s*:\s*"([^"]+)"', re.I)


def parse_case(rel: str) -> dict | None:
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        return None
    src = open(path, encoding='utf-8').read()
    override = MANUAL_COORDS.get(rel)
    if override:
        lat, lon, _ = override
    else:
        m = COORD_RE.search(src)
        if not m:
            return None
        lat = float(m.group(1)) * (1 if m.group(2).upper() == 'N' else -1)
        lon = float(m.group(3)) * (1 if m.group(4).upper() == 'E' else -1)

    title = ''
    tm = TITLE_RE.search(src)
    if tm:
        title = tm.group(1).split(' · ')[0].split(' — ')[0].strip()

    desc = ''
    dm = DESC_RE.search(src)
    if dm:
        desc = dm.group(1).strip()
        if len(desc) > 220:
            desc = desc[:220].rsplit(' ', 1)[0] + '…'

    date = ''
    pm = PUB_RE.search(src)
    if pm:
        date = pm.group(1)[:10]

    archive = rel.split('/', 1)[0]
    # Phase 04.1: case stories live at /stories/{slug}/ (Plan 04.1-03).
    # Strip archive directory + `.html` extension to derive the new slug.
    # E.g. 'aaro/tic-tac.html' → '/stories/tic-tac/'.
    case_slug = rel.rsplit('/', 1)[-1].removesuffix('.html')
    return {
        'kind': 'case',
        'archive': archive,
        'href': f'/stories/{case_slug}/',
        'lat': lat, 'lon': lon,
        'title': title, 'date': date, 'description': desc,
    }


def main() -> int:
    cases: List[dict] = []
    for rel in CASE_PAGES:
        c = parse_case(rel)
        if c:
            cases.append(c)
            print(f'  ✓ {rel:34s} ({c["lat"]:.4f}, {c["lon"]:.4f})')
        else:
            print(f'  · {rel:34s} no coords')

    archives = [
        {
            'kind': 'archive',
            'archive': slug,
            'href': '/' + d if d != '/' else '/',
            'lat': lat, 'lon': lon,
            'title': label,
            'description': '',
        }
        for slug, label, d, lat, lon in ARCHIVE_HQ
    ]

    payload = {
        '_meta': {
            'description': 'realufo.org per-event geocode dump. Used by /map.html for case pins. Archive HQ centroids included as fallback.',
            'docs': 'https://realufo.org/api/',
            'units': 'WGS84 decimal degrees',
        },
        'cases': cases,
        'archives': archives,
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f'\n→ wrote {os.path.relpath(OUT)} ({len(cases)} cases + {len(archives)} archives)')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
