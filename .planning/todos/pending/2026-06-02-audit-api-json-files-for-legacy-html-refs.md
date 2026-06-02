---
created: 2026-06-02T08:51:13.415Z
title: Audit other API JSON files for legacy .html refs
area: api
files:
  - api/geo.json (fixed 8b053c0 — case hrefs rewritten)
  - api/by-archive.json
  - api/pages-index.json
  - api/stats.json
  - api/all.json
  - api/README.md
  - scripts/build-api.py
  - scripts/build-geo.py (patched 8b053c0)
  - scripts/build-feeds.py
  - feeds/*.xml
---

## Problem

Surfaced during `/gsd:debug` session `map-open-case-wrong-slug` (commit `8b053c0`). The /map/ "Open case →" button pointed to `/aaro/tic-tac.html` etc. because `api/geo.json` still carried Phase-4 legacy hrefs. After Phase 04.1 moved case narratives to `/stories/{slug}/`, only `geo.json` got rewritten — other API/feed JSON + XML may also reference the old `/<archive>/<slug>.html` form.

Production `_redirects` (Plan 04.1-06) handles the 301 chain so prod doesn't visibly break, but:
- Dev server (python http.server, wrangler pages dev) bypasses `_redirects` → silent 404 on any consumer that fetches a legacy href.
- Crawlers / external tools / RSS readers consuming `/feeds/*.xml` will hit redirects on every poll — wasteful + adds latency.
- Phase 6 hosting cutover may surface legacy links if any redirect rule is missed.

Suspected ref locations (must verify):
- `api/by-archive.json` — `href` / `url` fields per record (raw archive pages or per-case PDFs may use legacy paths).
- `api/pages-index.json` — sitemap-style listing; likely has `.html` extensions on site-pages (`/about.html`, `/timeline.html`, etc.).
- `api/all.json` — currently 0-records placeholder (see follow-up TODO on `build-api.py` paths) but once regenerated will inherit whatever paths the generator emits.
- `feeds/*.xml` — Atom/RSS `<link>` + `<id>` elements. Per-archive feeds + `feeds/all.xml`. Likely point to `/aaro/details.html` etc.

## Solution

TBD. Likely approach:

1. **Inventory** — grep `api/` + `feeds/` for `\.html(?:[^a-z]|$)` patterns; classify each match by ref type (case story, site page, archive index, external).
2. **Mapping** — apply same rewrite rules used in `8b053c0`:
   - `/<archive>/<case>.html` → `/stories/<case>/` (verify slug exists in `src/data/stories.json`)
   - `/<site-page>.html` → `/<site-page>/` for the 6 site-page slugs (about/foia/glossary/map/timeline/whatsnew)
   - Keep `/<archive>/` archive-index URLs as-is (legacy copy-script still ships them)
3. **Patch generators** — update `scripts/build-api.py`, `scripts/build-feeds.py` so future regen emits new format (mirrors the `build-geo.py` patch in `8b053c0`).
4. **Verify** — `pnpm build` + grep dist for residual `\.html"` refs in JSON/XML payloads. Acceptance: zero matches except external `https://*.html` links.

Out-of-scope: regenerating `api/all.json` with real record count — separate TODO blocks that (needs `build-api.py` MANIFEST update to source from `legacy/<slug>/` instead of pre-04.1 root paths).

## Related

- `8b053c0` — geo.json case-href rewrite (the precedent fix)
- `.planning/debug/site-pages-broken-round2.md` — earlier round of API-related fallout
- CLAUDE.md §13 — Phase 4 carve-outs (`build-api.py`, `build-feeds.py` still alive until scrape.yml rewrite)
