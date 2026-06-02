---
created: 2026-06-02
title: Add directory index pages for /api/ and /feeds/ (or fix the links pointing at them)
area: seo
files:
  - dist/api/ (no index.html — has README.md + JSON files)
  - dist/feeds/ (no index.html — has *.xml files)
  - legacy/about.html (line ~ — `<a href="/api/">`)
  - legacy/whatsnew.html (line ~ — `<a href="/feeds/">`)
---

## Problem

Surfaced during `/gsd:debug link-asset-seo-audit`. The about + whatsnew pages link to bare `/api/` and `/feeds/` directory URLs:

- `<a href="/api/">/api/</a>` (from about page — "Researchers + LLM scrapers: see the static `/api/` dump")
- `<a href="/feeds/">Per-archive feeds</a>` (from whatsnew page — "Per-archive feeds")

CF Pages returns 404 for directory URLs that have no `index.html`. The directories exist with content (`api/all.json`, `api/by-archive.json`, `api/README.md`, `feeds/aaro.xml`, etc.) — only the directory index is missing.

## Solution

Generate small `index.html` files for both directories listing the contents — equivalent to a poor-man's Apache `mod_autoindex`. Either:

1. **Postbuild script:** small Python that lists `dist/api/*` and `dist/feeds/*` and writes a `<ul>` of links. Adds two ~30-line files.
2. **Static placeholders:** check in `public/api/index.html` + `public/feeds/index.html` with hand-curated content (the file set is small + stable).

Recommendation: option 1, included in `scripts/copy-legacy-archives.sh` next to the existing api/feeds copy block. Auto-stays-in-sync as the artifact set evolves.

## Acceptance

- `dist/api/index.html` exists with `<ul>` of `<li><a href="all.json">all.json</a></li>` etc.
- `dist/feeds/index.html` exists with same shape.
- Both files include SEO meta (`<title>`, `description`, `canonical`).
- Audit re-run shows 0 broken refs from active surface to `/api/` or `/feeds/`.

## Related

- `/gsd:debug link-asset-seo-audit` (2026-06-02) — surfaced this
- `scripts/copy-legacy-archives.sh` — copies `api/*.json` + `feeds/*.xml` to dist
