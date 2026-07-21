#!/usr/bin/env python3
"""Resolve Release 04 DVIDS video IDs → DOD_<record-id> filenames.

Release 04 (7/10/26) video + audio rows in uap-data.csv carry only a
DVIDS Video ID, not a direct media link. The corresponding DOD_*.mp4
lives in the release_04 video bundle (uploaded to R2 at
videos/wargov/DOD_<id>.mp4), but we need the DVIDS→DOD mapping to know
which file each card links to.

Hits https://www.dvidshub.net/video/<DVIDS_ID> once per ID, scrapes the
embedded asset URL, extracts DOD_<numeric>, writes a JSON dict:
    { "<DVIDS_ID>": "<DOD_RECORD_ID>", ... }

Idempotent: existing entries are kept and skipped. Re-run safely to fill
gaps.

Run once locally — DVIDS blocks GitHub Actions IPs (Akamai), so this
script is dev-only. Modelled verbatim on scripts/resolve-dvids-r03.py;
only the release-date filter and output path differ.
"""
from __future__ import annotations
import csv
import json
import os
import re
import sys
import time
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(REPO, 'uap-data.csv')
OUT_PATH = os.path.join(REPO, 'scripts', 'dvids2dod-r04.json')
RELEASE_DATE = '7/10/26'

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
# R04's AUD (Apollo-debriefing) pages expose the asset as
# cloudfront.net/video/<n>/DOD_<id>/DOD_<id>-1920x1080-9000k.mp4 rather than
# a bare DOD_<id>.mp4, so match DOD_<digits> followed by `.mp4`, `-`, or `/`.
DOD_RE = re.compile(r'DOD_(\d+)(?:\.mp4|[-/])')


def fetch_dod_id(dvids_id: str) -> str | None:
    url = f'https://www.dvidshub.net/video/{dvids_id}'
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            body = r.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f'  ! {dvids_id}: {e}', file=sys.stderr)
        return None
    m = DOD_RE.search(body)
    return m.group(1) if m else None


def main() -> int:
    # Load existing mapping (resume support).
    existing: dict[str, str] = {}
    if os.path.exists(OUT_PATH):
        existing = json.load(open(OUT_PATH))

    # Gather R04 DVIDS IDs from CSV where PDF|Image Link is empty. Include
    # AUD (audio-served-as-mp4) rows too — they share the same DVIDS → DOD
    # mapping pattern as VID rows.
    needed: list[str] = []
    with open(CSV_PATH, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            if (r.get('Type') or '').strip() not in ('VID', 'AUD'):
                continue
            if (r.get('Release Date') or '').strip() != RELEASE_DATE:
                continue
            d = (r.get('DVIDS Video ID') or '').strip()
            if not d:
                continue
            if (r.get('PDF | Image Link') or '').strip():
                continue
            if d in existing:
                continue
            needed.append(d)

    print(f'{len(existing)} cached, {len(needed)} to resolve.')
    for i, d in enumerate(needed, 1):
        dod = fetch_dod_id(d)
        if dod:
            existing[d] = dod
            print(f'  [{i}/{len(needed)}] {d} → {dod}')
        else:
            print(f'  [{i}/{len(needed)}] {d} → ??')
        time.sleep(0.6)  # courtesy delay

    # Write sorted by DVIDS ID.
    out = {k: existing[k] for k in sorted(existing, key=lambda x: int(x))}
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2)
        f.write('\n')
    print(f'\nwrote {OUT_PATH} ({len(out)} entries)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
