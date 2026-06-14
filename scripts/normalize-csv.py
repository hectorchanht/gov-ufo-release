#!/usr/bin/env python3
"""CSV → data/wargov.json + per-50-card shard normaliser (Plan 03-03 / SSG-02).

Reads the wargov source-of-truth CSV (`uap-data.csv` if present else
`uap-release001.csv`, matching `scripts/build-wargov.py` precedence) and
writes:

  data/wargov.json
    Astro `file()` loader entries-object form:
      { "v1": { "schemaVersion": 1, "slug": "wargov",
                "rows": [<first 50 raw rows>],
                "shards": [{ "index": 2, "file": "data/wargov-shard-2.json" }, ...] } }
    Validated against `wargovEnvelopeSchema` from `src/content.config.ts`
    (Plan 03-02) at `pnpm build` time. Astro Card.astro server-renders the
    first 50 rows directly at build time (D-08).

  data/wargov-shard-N.json   (N starts at 2)
    Pre-rendered HTML strings per D-10 (LOCKED, reaffirmed by user):
      { "schemaVersion": 1, "slug": "wargov", "shardIndex": <N>,
        "cards": [ { "id": "card-<slug>", "html": "<article ...></article>" }, ... ] }
    These are *not* registered as Astro collection entries — they are static
    sibling JSON assets that the runtime lazy-loader fetches and inserts via
    `el.insertAdjacentHTML('beforeend', card.html)`. Zero client-side
    templating logic. The Python `render_card_html()` function is the single
    point of truth that mirrors `src/components/Card.astro`'s compiled
    output (Plan 03-05 verifies the contract).

### Invariants (cite for any future agent before editing)

- **CLAUDE.md §11**: `uap-release001.csv` / `uap-data.csv` are UNTOUCHABLE.
  This script opens them in read mode only. `_assert_csv_unchanged()` runs
  after every write to fail loudly if the script accidentally mutates a CSV.
- **D-04** (idempotent committed output): `json.dumps(..., sort_keys=True,
  ensure_ascii=False, indent=2)` + trailing newline → same CSV input + same
  git state produces a byte-identical `data/wargov.json` on every run.
- **D-08** (50-card boundary): first 50 rows in primary; rest in shards
  of 50. Tunable via `--page-size`.
- **D-09 / D-10** (LOCKED): lazy-loaded cards are pre-rendered HTML strings,
  not raw data. No client-side templating helper anywhere. Phase 4 PERF-01
  GEIPAN sharding will reuse this exact seam.
- **D-26..D-28** (fidelity guards): no `.strip()` on text fields (only on
  Title-truthiness), no Unicode-normalisation imports (the `unico` + `data`
  stdlib module is deliberately NOT imported — see import block), no regex
  rewrites against the row text. `html.escape(value, quote=True)` is the
  only transform applied at render time — it is reversible (entity-encodes
  `&`, `<`, `>`, `"`, `'` only). PITFALLS.md #6 typographer drift defended.
- **D-32** (build pipeline): runs as `pnpm prebuild` before `astro build`
  (wired by Task 2 of this plan).
- **D-39** (coexistence): this script does NOT replace `scripts/build-
  wargov.py`. That script continues to emit `index.html` for the GH Pages
  legacy build until Phase 6.

### Threat mitigations

- **T-03-07 (CSV writeback)**: `_assert_csv_unchanged()` runs post-write
  and exits 1 with a clear error if either CSV shows a diff.
- **T-03-08 (typographer drift)**: zero `.translate()`, zero NFC/NFD
  Unicode-normalisation calls (stdlib's `unico`+`data` module is not
  imported), zero `.strip()` on text fields. Round-trip fixture test
  (T-03-08) exercised by the verifier.
- **T-03-25 (XSS in pre-rendered HTML)**: `_e()` helper pipes every row
  field through `html.escape(value, quote=True)` before string
  interpolation. Round-trip test injects `<script>alert(1)</script>` into
  a synthetic Title and asserts the shard JSON contains `&lt;script&gt;`.
- **T-03-26 (markup drift vs Card.astro)**: `render_card_html()` markers
  (`<article`, `class="arch-card"`, `data-id="r"`, `data-action="open"`,
  `class="card-title"`) are asserted in Task 2 verify. Plan 03-05 verifies
  the byte-level contract against `dist/index.html` Card.astro output.

### Post-Phase-5 VID hydration (2026-05-29)

CSV columns `PDF | Image Link` and `Modal Image` are EMPTY for most VID
rows (78 VID total: 66 have empty url, all 78 have empty thumb). The
binary mp4 assets live in R2 at
``https://assets.realufo.org/videos/wargov/DOD_<id>.mp4``, but the CSV's
``DVIDS Video ID`` column carries the DVIDS *catalog page* ID
(``1007706``) not the DVIDS *asset* ID (``111719709``). The bridge JSONs
``scripts/dvids2dod-r01.json`` + ``scripts/dvids2dod-r02.json`` (emitted
by ``scripts/resolve-dvids-r01.py``) carry the catalog→asset mapping for
73 of 78 VID rows. The remaining 5 are R01 entries whose DVIDS resolution
has not yet been run.

`_hydrate_vid_url()` + `_hydrate_thumb()` patch each VID row at read time
ONLY when the source CSV field is empty/non-mp4 — never mutating CSV on
disk (CLAUDE.md §11 unchanged). The hydration is purely additive and
data-side: Card.astro + render_card_html() are unchanged, byte-equivalent
contract D-10 stays intact.

CLI:
    python3 scripts/normalize-csv.py
        Read CSV → write data/wargov.json + shards. Exit 0 on success.

    python3 scripts/normalize-csv.py --check
        Re-run pipeline against an in-memory buffer; diff against the
        on-disk wargov.json + shards. Exit 0 if byte-identical, 1 on drift.

    python3 scripts/normalize-csv.py --page-size N
        Override the 50-card boundary (D-08 tunable).

Exit codes:
    0 — success (write or `--check` clean)
    1 — drift detected (`--check` mode) OR CSV mutation detected
    2 — neither CSV present (initial-clone case)

Stdlib only — matches `stdlib-only except curl_cffi` convention from
CLAUDE.md §6.2 and the Phase 1/2 precedent (snapshot-urls.py,
capture-baselines.py).
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

# Local-import: scripts/_archive_common.py exposes the R2 URL rewrite helper
# consumed by every Wave 3+ per-archive normaliser. Phase 4 plan 04-02 Task 3
# wires this here for the wargov pipeline. Inserting the scripts/ directory
# at sys.path[0] keeps this script runnable from any cwd
# (e.g. `python3 scripts/normalize-csv.py` from repo root) without requiring
# package install. The slug `scripts._archive_common` is intentionally NOT
# used as a package import because scripts/ has no __init__.py and the
# stdlib-only convention (CLAUDE.md §6.2 + Phase 1/2 precedent) excludes
# turning scripts/ into a package.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _archive_common import pdf_thumb_url, rewrite_to_r2  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
CSV_COMBINED = REPO / 'uap-data.csv'
CSV_LEGACY = REPO / 'uap-release001.csv'
DATA_DIR = REPO / 'data'
OUT_PRIMARY = DATA_DIR / 'wargov.json'
SHARD_TEMPLATE = 'data/wargov-shard-{n}.json'
PAGE_SIZE = 50  # D-08 — tunable via --page-size
SOURCE_URL = 'https://www.war.gov/UFO/'  # wargov official source (CLAUDE.md §2)
# Plan 03-05 (Rule 3 — auto-fix blocking issue): the wargov page's lazy-loader
# fetches `/data/wargov-shard-N.json` at runtime, but Astro only serves files
# from `public/` at the URL root. We mirror the shards into `public/data/` so
# the same path resolves both at build time (Astro file() loader reads from
# `data/`) AND at runtime (browser fetch hits `dist/data/` via public/).
PUBLIC_DATA_DIR = REPO / 'public' / 'data'

# Slugify regex — BYTE-FOR-BYTE port from scripts/snapshot-urls.py line 92.
# Same algorithm guarantees `#card-<slug>` anchor parity with URL-CONTRACT.txt.
_SLUG_RE = re.compile(r'[^a-z0-9]+')


# -----------------------------------------------------------------------------
# VID hydration — DVIDS catalog ID → DOD asset ID → R2 mp4 URL
# (post-Phase-5 / 2026-05-29; see module docstring "Post-Phase-5 VID hydration")
# -----------------------------------------------------------------------------

# DVIDS catalog-ID → DOD asset-ID maps. r01 covers the May 8, 2026 tranche;
# r02 covers the May 22, 2026 tranche; r03 covers the June 12, 2026 tranche.
# `scripts/resolve-dvids-r0{1,3}.py` emit these files (Akamai blocks GH
# Actions egress so the scripts are dev-only).
DVIDS_MAP_PATHS = (
    REPO / 'scripts' / 'dvids2dod-r01.json',
    REPO / 'scripts' / 'dvids2dod-r02.json',
    REPO / 'scripts' / 'dvids2dod-r03.json',
)

# Slideshow thumbnail directories. `slideshow/` carries the R01 imagery
# (legacy snake_case filenames); `slideshow-2/` carries R02 highlights.
# Both are static-served by Astro from the repo root (public/ symlinked in
# astro.config.mjs or copied via Astro's public-dir conventions).
SLIDESHOW_DIRS = (
    ('slideshow-2', REPO / 'slideshow-2'),
    ('slideshow', REPO / 'slideshow'),
)

# Match `PRddd` or `PR-ddd` inside a CSV title to derive a slideshow PR-ID.
# Case-insensitive; matches the first PR-ID per title (titles have one).
_PR_ID_RE = re.compile(r'PR-?(\d+)', re.IGNORECASE)

R2_VIDEO_BASE = 'https://assets.realufo.org/videos/wargov'


def _load_dvids_to_dod() -> dict[str, str]:
    """Load DVIDS catalog-ID → DOD asset-ID map, merging r01 + r02 JSON files.

    Returns an empty dict on any I/O / JSON error so the normaliser stays
    operational even on a fresh clone where the mapping files have not yet
    been regenerated. Each entry maps a catalog ID (e.g. ``"1007706"``) to
    a DOD asset ID (e.g. ``"111719709"``); empty / falsy values are
    filtered (a missing DOD ID is treated the same as a missing entry).
    """
    merged: dict[str, str] = {}
    for path in DVIDS_MAP_PATHS:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as exc:
            sys.stderr.write(f'[warn] could not load {path.name}: {exc}\n')
            continue
        if not isinstance(data, dict):
            continue
        for k, v in data.items():
            if isinstance(v, str) and v:
                merged[str(k)] = v
    return merged


def _load_pr_thumbs() -> dict[str, str]:
    """Scan slideshow/ + slideshow-2/ and build a PR-ID → relative-URL map.

    Both zero-padded (``PR050``) and unpadded (``PR50``) keys are emitted
    so the lookup tolerates either CSV title convention. ``slideshow-2/``
    wins on conflict (R02 imagery is the higher-quality canonical set).
    Returned URLs are absolute paths (e.g. ``/slideshow-2/DOW...jpg``)
    suitable for the ``Modal Image`` field consumed by Card.astro.
    """
    thumbs: dict[str, str] = {}
    # Iterate slideshow before slideshow-2 so slideshow-2 entries
    # overwrite (priority semantics — newer R02 image wins).
    ordered = list(reversed(SLIDESHOW_DIRS))  # slideshow then slideshow-2
    for folder_name, folder in ordered:
        if not folder.is_dir():
            continue
        try:
            names = sorted(os.listdir(folder))
        except OSError as exc:
            sys.stderr.write(f'[warn] could not list {folder_name}/: {exc}\n')
            continue
        for fname in names:
            for m in _PR_ID_RE.finditer(fname):
                n = int(m.group(1))
                url = f'/{folder_name}/{fname}'
                thumbs[f'PR{n:03d}'] = url
                thumbs[f'PR{n}'] = url
    return thumbs


def _hydrate_vid_url(
    row: dict[str, str],
    dvids_to_dod: dict[str, str],
) -> str | None:
    """Return an R2 mp4 URL for a VID row, or None when no DOD mapping exists.

    Used by `_read_rows` to populate `PDF | Image Link` when the CSV field
    is empty or points at the paired PDF (the historical convention until
    Phase 5). The R2 URL format matches `_archive_common.rewrite_to_r2`'s
    output for ``asset_type='videos'``.

    Returns
    -------
    str | None
        ``https://assets.realufo.org/videos/wargov/DOD_<id>.mp4`` if the
        DVIDS catalog ID resolves, else None (caller leaves field unchanged).
    """
    dvids = (row.get('DVIDS Video ID') or '').strip()
    if not dvids:
        return None
    dod = dvids_to_dod.get(dvids)
    if not dod:
        return None
    return f'{R2_VIDEO_BASE}/DOD_{dod}.mp4'


def _hydrate_thumb(
    row: dict[str, str],
    pr_thumbs: dict[str, str],
) -> str | None:
    """Return a slideshow-folder thumb path for a VID row, or None on miss.

    Extracts the first ``PR\\d+`` token from the Title and tries both
    zero-padded and unpadded keys against the PR-ID map. Returns None
    when neither matches; caller leaves the ``Modal Image`` field as-is
    (typically empty for VID rows — Card.astro's ``{thumb && <img …>}``
    guard short-circuits rendering when blank).
    """
    title = row.get('Title') or ''
    m = _PR_ID_RE.search(title)
    if not m:
        return None
    n = int(m.group(1))
    return pr_thumbs.get(f'PR{n:03d}') or pr_thumbs.get(f'PR{n}')


# -----------------------------------------------------------------------------
# CSV ingest (read-only)
# -----------------------------------------------------------------------------


def _pick_csv() -> Path:
    """Pick `uap-data.csv` if present else `uap-release001.csv`.

    Matches `scripts/build-wargov.py` precedence verbatim (lines 27-29).
    Exit code 2 if neither CSV exists (initial-clone case).
    """
    if CSV_COMBINED.exists():
        chosen = CSV_COMBINED
    elif CSV_LEGACY.exists():
        chosen = CSV_LEGACY
    else:
        sys.stderr.write(
            f'[error] neither {CSV_COMBINED.name} nor {CSV_LEGACY.name} '
            f'found in {REPO}. Cannot normalise wargov.\n'
        )
        sys.exit(2)
    sys.stderr.write(f'[info] reading wargov source-of-truth: {chosen.name}\n')
    return chosen


def _read_rows(csv_path: Path) -> list[dict[str, str]]:
    """Read CSV in read-only mode and return rows in CSV order.

    Drops rows where `Title` is blank (truthiness filter only — row VALUES
    are preserved verbatim per D-26..D-28; `.strip()` is applied solely to
    the Title-truthiness check, never to any committed text).

    Phase 4 plan 04-02 Task 3: the `PDF | Image Link` field for PDF/VID rows
    is rewritten to its R2 custom-domain URL
    (https://assets.realufo.org/<pdfs|videos>/wargov/<basename>) via
    `_archive_common.rewrite_to_r2`. This is a build-time transform; the
    source CSV is untouched (T-03-07 guard + CLAUDE.md §11). IMG-type rows
    and any row whose `PDF | Image Link` ends in an image extension are
    preserved verbatim per D-01 refinement + Pitfall #7 — Astro Image
    processes LOCAL files only, so thumbnails must not be R2-rewritten.

    Post-Phase-5 VID hydration (2026-05-29): for VID rows whose CSV
    `PDF | Image Link` is empty or non-mp4 (the historical convention
    pointed at the paired PDF, which is not the video asset), look up the
    DVIDS catalog ID in `scripts/dvids2dod-r0{1,2}.json` and synthesise
    an R2 mp4 URL. Likewise, when `Modal Image` is empty, derive a
    slideshow-folder thumb from the title PR-ID. Both transforms are
    additive (only fill blanks / wrong-type values) — CSV files on disk
    remain untouched (T-03-07 guard still holds).
    """
    # Load hydration tables once per read (cheap — file I/O on small JSON
    # + a dir listing). Empty dicts on missing inputs keep the pipeline
    # working on a fresh clone without slideshow/ checked in.
    dvids_to_dod = _load_dvids_to_dod()
    pr_thumbs = _load_pr_thumbs()
    hydrated_urls = 0
    hydrated_thumbs = 0
    cleared_urls = 0
    derived_pdf_thumbs = 0

    rows: list[dict[str, str]] = []
    # 'utf-8-sig' handles the BOM that spreadsheet exports prepend.
    # `newline=''` is mandatory for csv module per stdlib docs.
    with open(csv_path, 'r', encoding='utf-8-sig', newline='') as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            title = row.get('Title', '') or ''
            if title.strip() == '':
                continue
            # Filter out spreadsheet-export sentinel columns (empty-string
            # header keys from trailing-comma artefacts in the CSV header).
            # Values still preserved verbatim — we just drop the unnamed
            # `'': None` key the DictReader synthesises when row width
            # exceeds header width.
            cleaned = {
                k: ('' if v is None else v)
                for k, v in row.items()
                if k is not None and k != ''
            }
            rtype = (cleaned.get('Type', '') or '').strip()

            # Phase 5 VID hydration — run BEFORE the existing R2 rewrite so
            # the catalogue→asset lookup populates the field with the
            # correct DOD_<id>.mp4 basename. Without this, VID rows whose
            # CSV `PDF | Image Link` carried the paired-PDF link would
            # end up rewritten to `videos/wargov/<paired-pdf>.pdf` (wrong
            # extension AND wrong file). Empty-link rows would render
            # without a Play button at all (the user-visible bug).
            # Hydrate VID + AUD identically: NASA Mercury/Gemini/Apollo
            # audio excerpts live on DVIDS as audio-served-as-mp4 (see
            # resolve-dvids-r01.py header comment). All 8 AUD rows in
            # uap-data.csv have DVIDS Video IDs that resolve to DOD_*.mp4
            # via the same lookup table. Without including AUD here, AUD
            # cards rendered no Play button and the lightbox showed
            # nothing on click. 2026-05-29 fix.
            if rtype in ('VID', 'AUD'):
                raw_url = (cleaned.get('PDF | Image Link') or '').strip()
                # Override when the CSV field is empty OR points at a
                # non-mp4 (the paired-PDF convention). Preserve direct mp4
                # links verbatim — the operator may add them later.
                if not raw_url.lower().endswith('.mp4'):
                    hydrated = _hydrate_vid_url(cleaned, dvids_to_dod)
                    if hydrated:
                        cleaned['PDF | Image Link'] = hydrated
                        hydrated_urls += 1
                    elif raw_url:
                        # No DVIDS→DOD mapping AND the source URL is a
                        # paired-PDF (non-mp4). Clearing the field avoids
                        # the downstream rewrite_to_r2() emitting a
                        # `videos/wargov/<paired-pdf>.pdf` URL that 404s
                        # against R2. Card.astro then omits Open/Download
                        # for this row; the DVIDS ↗ external button is
                        # still rendered (it reads `DVIDS Video ID`).
                        cleaned['PDF | Image Link'] = ''
                        cleared_urls += 1
                # Always try thumb hydration when the field is empty —
                # CSV-supplied thumbs (none in practice for VID/AUD rows)
                # always win.
                if not (cleaned.get('Modal Image') or '').strip():
                    thumb = _hydrate_thumb(cleaned, pr_thumbs)
                    if thumb:
                        cleaned['Modal Image'] = thumb
                        hydrated_thumbs += 1

            # Phase 4 plan 04-02 — rewrite the binary asset URL to R2 for
            # PDF + VID rows. Card.astro reads `PDF | Image Link` directly
            # (src/components/Card.astro line ~66), so mutating this field
            # at read time propagates to BOTH the first 50 raw rows (Astro
            # server-renders them via Card.astro) AND the shard HTML strings
            # (render_card_html reads the same field). Rewrite is idempotent:
            # the helper returns the input unchanged if it already starts
            # with the R2 custom domain (basename extraction collapses to
            # the same path).
            raw_url = cleaned.get('PDF | Image Link', '') or ''
            if raw_url:
                if rtype == 'VID':
                    asset_type = 'videos'
                elif rtype in ('PDF', 'DOC'):
                    asset_type = 'pdfs'
                else:
                    asset_type = None
                if asset_type:
                    cleaned['PDF | Image Link'] = rewrite_to_r2(
                        raw_url, 'wargov', asset_type,
                    )
            # Plan post-05-01 (PDF page-1 thumbnail) — for PDF/DOC rows
            # whose `Modal Image` is empty, derive
            # `https://assets.realufo.org/pdf-thumbs/wargov/<basename>.jpg`
            # from the R2-rewritten `PDF | Image Link`. The matching JPG
            # is rendered + uploaded to R2 by `scripts/build-pdf-thumbs.py`.
            # Card.astro reads `Modal Image` directly and its <img> onerror
            # falls back to `data-fallback` (the PDF URL) — so a missing
            # thumb degrades gracefully to the SVG placeholder via the
            # CSS `:before` rule on `.arch-card[data-type=PDF]:not(:has(>img))`.
            # Mutation is additive (only fills blank field); CSV unchanged.
            if rtype in ('PDF', 'DOC'):
                existing_thumb = (cleaned.get('Modal Image') or '').strip()
                # Always prefer R2 pdf-thumbs over war.gov Akamai-fronted
                # thumbnails: live war.gov CDN URLs 403 against any non-
                # browser UA (CLAUDE.md §11 — Akamai blocks egress). Also
                # populate when the CSV field is empty. Any non-war.gov
                # thumb (rare) is preserved verbatim.
                if (not existing_thumb) or 'www.war.gov/medialink/' in existing_thumb:
                    final_url = cleaned.get('PDF | Image Link', '') or ''
                    derived = pdf_thumb_url(final_url)
                    if derived:
                        cleaned['Modal Image'] = derived
                        derived_pdf_thumbs += 1
            rows.append(cleaned)
    sys.stderr.write(f'[info] read {len(rows)} non-empty-Title rows\n')
    if hydrated_urls or hydrated_thumbs or cleared_urls:
        sys.stderr.write(
            f'[info] VID hydration: {hydrated_urls} mp4 URLs '
            f'(from DVIDS map), {hydrated_thumbs} thumbs '
            f'(from slideshow-folder PR-ID match), '
            f'{cleared_urls} stale paired-PDF URLs cleared\n'
        )
    if derived_pdf_thumbs:
        sys.stderr.write(
            f'[info] PDF thumb hydration: {derived_pdf_thumbs} `Modal Image` '
            f'fields populated from pdf-thumbs/wargov/<basename>.jpg derivation\n'
        )
    return rows


# -----------------------------------------------------------------------------
# Slug + HTML rendering (mirrors Card.astro per D-10)
# -----------------------------------------------------------------------------


def _slugify(text: str) -> str:
    """Reduce free-text to a stable `#card-<slug>` anchor.

    BYTE-FOR-BYTE port from scripts/snapshot-urls.py:158-167. Guarantees
    that `data/wargov-shard-N.json` card `id` values match the anchors in
    `URL-CONTRACT.txt` exactly.

    Rules: lowercase → collapse runs of non-[a-z0-9] to single hyphen →
    strip leading/trailing hyphens → truncate to 80 chars → strip again.
    """
    if not text:
        return ''
    s = _SLUG_RE.sub('-', text.lower()).strip('-')
    return s[:80].strip('-')


def _e(value: str) -> str:
    """HTML-escape an attribute or text-node value.

    `quote=True` escapes `&`, `<`, `>`, `"`, `'`. This is the ONLY
    transform applied to row text. It is reversible (entity encoding
    preserves source bytes on decode) and is the T-03-25 (XSS) mitigation.
    """
    return html.escape(value or '', quote=True)


def render_card_html(row: dict[str, str], idx: int) -> str:
    """Render a single card as an HTML string per D-10.

    Mirrors the compiled output structure of `src/components/Card.astro`
    (Plan 03-05). Markup contract:

      <article class="arch-card"
               id="card-<slug>"
               data-id="r<NNN>"          # 1-based, 3-digit padded
               data-row-id="r<NNN>"      # NEW (Plan 04-01) — stable lightbox key
               data-idx="<idx>"          # 0-based global row index
               data-action="open"
               data-type="<row.Type>"
               data-agency="<row.Agency>"
               data-date="<row['Incident Date']>">
        <img ...>           (if Modal Image present)
        <h3 class="card-title">...</h3>
        <p class="card-desc">...</p>     (if Description Blurb non-empty)
        <dl class="card-meta">...</dl>
        <div class="card-actions">
          <a class="btn-open" data-action="open"
             data-row-id="r<NNN>" data-url="<url>" data-local="<local>">Open</a>
          <a class="btn-download" data-url="<url>" data-local="<local>" download>Download</a>
          <a class="btn-source" target="_blank" rel="noopener">Source ↗</a>
          <a class="btn-dvids" target="_blank" rel="noopener">DVIDS ↗</a>
        </div>
      </article>

    Every row field value is piped through `_e()` before interpolation
    (T-03-25 XSS mitigation). NO `.strip()` on any value — fidelity
    preserved per D-26..D-28.

    Parameters
    ----------
    row : dict[str, str]
        CSV row keyed by uap-release001.csv header columns verbatim.
    idx : int
        GLOBAL 0-based row index across all rows (offset by shard start).
        Plan 03-05 lazy-loader relies on monotonic `data-idx` for the
        lightbox `openAt(idx)` invariant.

    Returns
    -------
    str
        Single-line HTML string. Trailing newline NOT appended (caller
        joins into JSON string field).
    """
    row_id = f'r{idx + 1:03d}'  # 1-based, 3-digit zero-padded
    title = row.get('Title', '') or ''
    slug = _slugify(title)
    # Phase 4 plan 04-02 Task 3 — `PDF | Image Link` has already been
    # rewritten to its R2 custom-domain URL by `_read_rows` for PDF + VID
    # type rows. IMG rows and image-extension URLs were preserved
    # verbatim. The URL we read here is the FINAL card URL — no per-card
    # rewrite needed at render time.
    url = row.get('PDF | Image Link', '') or ''
    thumb = row.get('Modal Image', '') or ''
    alt = row.get('Image Alt Text', '') or title
    desc = row.get('Description Blurb', '') or ''
    agency = row.get('Agency', '') or ''
    date = row.get('Incident Date', '') or ''
    rtype = row.get('Type', '') or ''
    dvids = row.get('DVIDS Video ID', '') or ''
    # Scope pivot 2026-05-28 — Card.astro now emits data-desc/region/
    # category/src for lightbox meta-panel consumption. Mirror byte-
    # equivalent (D-10 LOCKED pair).
    region = row.get('Incident Location', '') or ''
    category = rtype  # Card.astro uses rtype for both data-type + data-category
    # Operator spec 4 (2026-05-29) — release-batch filter. Map the CSV
    # `Release Date` column to a stable two-digit batch identifier so the
    # client-side filter can match cards by release. Mirrors Card.astro's
    # releaseBatch() byte-for-byte (D-10 LOCKED pair).
    release_date = row.get('Release Date', '') or ''
    if release_date == '5/8/26':
        release = '01'
    elif release_date == '5/22/26':
        release = '02'
    elif release_date == '6/12/26':
        release = '03'
    else:
        release = ''

    parts: list[str] = []
    local = row.get('local', '') or ''
    parts.append(
        f'<article class="arch-card" id="card-{_e(slug)}" '
        f'data-id="{_e(row_id)}" data-row-id="{_e(row_id)}" '
        f'data-idx="{idx}" data-action="open" '
        f'data-type="{_e(rtype)}" data-agency="{_e(agency)}" '
        f'data-date="{_e(date)}" data-desc="{_e(desc)}" '
        f'data-region="{_e(region)}" data-category="{_e(category)}" '
        f'data-release="{_e(release)}" '
        f'data-src="{_e(SOURCE_URL)}">'
    )
    if thumb:
        parts.append(
            f'<img loading="lazy" src="{_e(thumb)}" '
            f'data-fallback="{_e(url)}" alt="{_e(alt)}" '
            f'onerror="this.onerror=null;this.src=this.dataset.fallback||\'\'" />'
        )
    parts.append(f'<h3 class="card-title">{_e(title)}</h3>')
    if desc:
        parts.append(f'<p class="card-desc">{_e(desc)}</p>')
    parts.append('<dl class="card-meta">')
    parts.append(f'<dt>Agency</dt><dd>{_e(agency)}</dd>')
    parts.append(f'<dt>Date</dt><dd>{_e(date)}</dd>')
    parts.append(f'<dt>Type</dt><dd>{_e(rtype)}</dd>')
    parts.append('</dl>')
    parts.append('<div class="card-actions">')
    if url:
        parts.append(
            f'<a href="#" class="btn-open" data-action="open" '
            f'data-row-id="{_e(row_id)}" data-url="{_e(url)}" '
            f'data-local="{_e(local)}">Open</a>'
        )
        parts.append(
            f'<a href="{_e(local or url)}" class="btn-download" '
            f'data-url="{_e(url)}" data-local="{_e(local)}" '
            f'download>Download</a>'
        )
    parts.append(
        f'<a href="{SOURCE_URL}" class="btn-source" '
        f'target="_blank" rel="noopener">Source ↗</a>'
    )
    if dvids:
        parts.append(
            f'<a href="https://www.dvidshub.net/video/{_e(dvids)}" '
            f'class="btn-dvids" target="_blank" rel="noopener">DVIDS ↗</a>'
        )
    parts.append('</div>')
    parts.append('</article>')
    return ''.join(parts)


# -----------------------------------------------------------------------------
# Sharding (D-08..D-10)
# -----------------------------------------------------------------------------


def _shard_cards(
    rows: list[dict[str, str]],
    page_size: int,
) -> tuple[list[dict[str, str]], list[list[dict[str, str]]]]:
    """Split rows into (first_page_rows, shard_card_lists).

    - `first_page_rows = rows[:page_size]` (raw rows — Astro Card.astro
      server-renders these at build time per D-08).
    - `shard_card_lists` is a list-of-lists where each inner list contains
      `{"id": "card-<slug>", "html": <render_card_html output>}` dicts for
      the rows in that shard (D-10 LOCKED — server-rendered HTML strings,
      no raw row data emitted in shards).

    The `idx` passed to render_card_html is the GLOBAL row index across
    ALL rows (offset by page_size for shard 2, page_size*2 for shard 3,
    etc.). Plan 03-05 lazy-loader's `openAt(idx)` lightbox-anchor depends
    on monotonic `data-idx`.
    """
    first_page = rows[:page_size]
    rest = rows[page_size:]
    shard_lists: list[list[dict[str, str]]] = []
    for shard_offset_start in range(0, len(rest), page_size):
        shard_rows = rest[shard_offset_start:shard_offset_start + page_size]
        cards: list[dict[str, str]] = []
        for local_i, row in enumerate(shard_rows):
            global_idx = page_size + shard_offset_start + local_i
            title = row.get('Title', '') or ''
            cards.append({
                'id': f'card-{_slugify(title)}',
                'html': render_card_html(row, global_idx),
            })
        shard_lists.append(cards)
    return first_page, shard_lists


# -----------------------------------------------------------------------------
# CSV write-back guard (T-03-07)
# -----------------------------------------------------------------------------


def _assert_csv_unchanged() -> None:
    """Fail loudly if the script accidentally mutated either CSV.

    CLAUDE.md §11 declares both CSVs untouchable. This post-step runs
    `git diff --quiet -- uap-release001.csv uap-data.csv` and exits 1 if
    either shows a diff. T-03-07 mitigation.
    """
    try:
        rc = subprocess.run(
            ['git', '-C', str(REPO), 'diff', '--quiet', '--',
             'uap-release001.csv', 'uap-data.csv'],
            check=False,
        ).returncode
    except FileNotFoundError:
        # git not available — best-effort skip (script is offline-tolerant)
        sys.stderr.write('[warn] git not on PATH; skipping CSV-unchanged assertion\n')
        return
    if rc != 0:
        sys.stderr.write(
            '[error] CSV mutation detected — CLAUDE.md §11 forbids '
            'writing back to uap-release001.csv / uap-data.csv. Revert '
            'with `git checkout -- uap-release001.csv uap-data.csv` and '
            'fix the normaliser.\n'
        )
        sys.exit(1)


# -----------------------------------------------------------------------------
# JSON write (deterministic per D-04)
# -----------------------------------------------------------------------------


def _serialise(data: Any) -> str:
    """Deterministic JSON serialisation per D-04 idempotency requirement.

    - `sort_keys=True` — stable key ordering across runs / Python versions
    - `ensure_ascii=False` — preserves Unicode bytes verbatim per D-26..D-28
    - `indent=2` — fixed indent so byte-diff catches semantic-only drift
    - trailing newline — POSIX convention; consistent with `data/aaro.json`
    """
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + '\n'


def _write_json(path: Path, data: Any) -> None:
    """Write `data` to `path` as deterministic JSON."""
    path.write_text(_serialise(data), encoding='utf-8')


# -----------------------------------------------------------------------------
# Build the wargov envelopes
# -----------------------------------------------------------------------------


def _build_primary(
    first_page: list[dict[str, str]],
    shard_count: int,
) -> dict[str, Any]:
    """Construct the primary `data/wargov.json` envelope.

    Matches the Astro 5 file() loader entries-object form documented in
    `src/content.config.ts` (Plan 03-02) and `data/aaro.json` (skeleton).

    Shape:
        {
          "v1": {
            "schemaVersion": 1,
            "slug": "wargov",
            "rows": [<first 50 raw rows>],
            "shards": [
              { "index": 2, "file": "data/wargov-shard-2.json" },
              ...
            ]
          }
        }
    """
    return {
        'v1': {
            'schemaVersion': 1,
            'slug': 'wargov',
            'rows': first_page,
            'shards': [
                {
                    'index': i + 2,
                    'file': SHARD_TEMPLATE.format(n=i + 2),
                }
                for i in range(shard_count)
            ],
        },
    }


def _build_shard(
    shard_index: int,
    cards: list[dict[str, str]],
) -> dict[str, Any]:
    """Construct one `data/wargov-shard-N.json` envelope (D-10 LOCKED).

    Shape:
        {
          "schemaVersion": 1,
          "slug": "wargov",
          "shardIndex": <N>,
          "cards": [
            { "id": "card-<slug>", "html": "<article ...></article>" },
            ...
          ]
        }
    """
    return {
        'schemaVersion': 1,
        'slug': 'wargov',
        'shardIndex': shard_index,
        'cards': cards,
    }


# -----------------------------------------------------------------------------
# Normalisation pipeline (pure — for `--check` reuse)
# -----------------------------------------------------------------------------


def _normalise(page_size: int) -> tuple[dict[str, Any], list[tuple[Path, dict[str, Any]]]]:
    """Run the full normalisation pipeline and return (primary, shards).

    `shards` is `[(out_path, envelope), ...]`. Caller decides whether to
    persist (write mode) or compare (check mode).
    """
    csv_path = _pick_csv()
    rows = _read_rows(csv_path)
    first_page, shard_card_lists = _shard_cards(rows, page_size)
    primary = _build_primary(first_page, len(shard_card_lists))
    shards: list[tuple[Path, dict[str, Any]]] = []
    for i, cards in enumerate(shard_card_lists):
        shard_index = i + 2
        shard_path = REPO / SHARD_TEMPLATE.format(n=shard_index)
        shards.append((shard_path, _build_shard(shard_index, cards)))
    return primary, shards


# -----------------------------------------------------------------------------
# CLI entrypoints
# -----------------------------------------------------------------------------


def _write_mode(page_size: int) -> int:
    """Default mode: normalise CSV → write JSON files."""
    primary, shards = _normalise(page_size)
    DATA_DIR.mkdir(exist_ok=True)
    _write_json(OUT_PRIMARY, primary)
    for shard_path, shard_envelope in shards:
        _write_json(shard_path, shard_envelope)
    # Plan 03-05 (Rule 3): also mirror the primary + shards into public/data/
    # so the runtime lazy-loader's `fetch('/data/wargov-shard-N.json')` resolves
    # against Astro's built static assets. Astro copies public/* into dist/
    # verbatim, so this gives us URL-equivalent access without changing the
    # content-collection input path (which still reads from data/).
    PUBLIC_DATA_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(PUBLIC_DATA_DIR / 'wargov.json', primary)
    for shard_path, shard_envelope in shards:
        _write_json(PUBLIC_DATA_DIR / shard_path.name, shard_envelope)
    _assert_csv_unchanged()
    total_rows = len(primary['v1']['rows']) + sum(
        len(s[1]['cards']) for s in shards
    )
    sys.stderr.write(
        f'[ok] wargov: {total_rows} rows, {len(shards)} shards written '
        f'(first {page_size} as raw rows for Astro server-render; '
        f'remaining as pre-rendered HTML strings per D-10)\n'
    )
    return 0


def _check_mode(page_size: int) -> int:
    """`--check`: normalise to memory + diff against on-disk files.

    Exit 0 if every output is byte-identical to its on-disk counterpart.
    Exit 1 if any output drifts (CI signal that the normaliser would
    rewrite committed files).
    """
    primary, shards = _normalise(page_size)
    drift: list[str] = []

    expected_primary = _serialise(primary)
    if not OUT_PRIMARY.exists():
        drift.append(f'{OUT_PRIMARY.relative_to(REPO)} missing on disk')
    else:
        actual = OUT_PRIMARY.read_text(encoding='utf-8')
        if actual != expected_primary:
            drift.append(f'{OUT_PRIMARY.relative_to(REPO)} drift')

    # Track which shard files we expected so we can detect orphan shards
    # from a previous (larger) CSV that should now be removed.
    expected_paths = {OUT_PRIMARY}
    for shard_path, shard_envelope in shards:
        expected_paths.add(shard_path)
        expected = _serialise(shard_envelope)
        if not shard_path.exists():
            drift.append(f'{shard_path.relative_to(REPO)} missing on disk')
            continue
        actual = shard_path.read_text(encoding='utf-8')
        if actual != expected:
            drift.append(f'{shard_path.relative_to(REPO)} drift')

    # Orphan-shard detection — committed shards no longer produced by the CSV
    for orphan in sorted(DATA_DIR.glob('wargov-shard-*.json')):
        if orphan not in expected_paths:
            drift.append(f'{orphan.relative_to(REPO)} orphan (re-run normaliser)')

    if drift:
        sys.stderr.write('[drift] wargov normaliser output diverges:\n')
        for line in drift:
            sys.stderr.write(f'  - {line}\n')
        sys.stderr.write(
            '[hint] re-run `python3 scripts/normalize-csv.py` (without '
            '--check) to regenerate the committed JSON files.\n'
        )
        return 1
    sys.stderr.write('[ok] wargov: --check clean (no drift)\n')
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            'Normalise the wargov source-of-truth CSV into '
            'data/wargov.json + per-50-card shards. Reads '
            'uap-data.csv if present else uap-release001.csv (CLAUDE.md '
            '§11 — CSV is read-only). Idempotent + deterministic per D-04.'
        ),
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help=(
            'Run the pipeline and compare to on-disk JSON files without '
            'writing. Exit 1 on drift.'
        ),
    )
    parser.add_argument(
        '--page-size',
        type=int,
        default=PAGE_SIZE,
        help=(
            f'Rows per shard (D-08 tunable). Default {PAGE_SIZE}.'
        ),
    )
    args = parser.parse_args(argv)

    if args.page_size <= 0:
        sys.stderr.write('[error] --page-size must be > 0\n')
        return 1

    if args.check:
        return _check_mode(args.page_size)
    return _write_mode(args.page_size)


if __name__ == '__main__':
    sys.exit(main())
