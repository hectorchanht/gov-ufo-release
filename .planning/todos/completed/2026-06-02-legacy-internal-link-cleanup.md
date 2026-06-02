---
created: 2026-06-02
title: Rewrite legacy internal links in dormant archive HTML at copy time
area: legacy
files:
  - scripts/copy-legacy-archives.sh
  - legacy/{aaro,nara,brazil,chile,nz,uk,spain,canada,argentina,italy,peru,uruguay,geipan}/*.html
---

## Problem

Surfaced during `/gsd:debug link-asset-seo-audit`. The dormant archive story HTML files (e.g. `dist/aaro/belgian-wave.html`, `dist/nara/roswell.html`, ~80 files total) contain ~425 internal links that work via `_redirects` 301 chains but not via direct file resolution. Examples:

- `<a href="../search.html">` → 301 → `/search/`
- `<a href="../about.html">` → 301 → `/about/`
- `<a href="../aaro/tic-tac.html">` → 301 → `/stories/tic-tac/`
- `<a href="../uk/rendlesham.html">` → 301 → `/stories/rendlesham/`

Production CF Pages handles every link correctly via the legacy 301 block (Plan 04.1-06). But:

1. Dev preview servers (`wrangler pages dev`, `python -m http.server dist`) don't honor `_redirects` → silent 404 during local UAT.
2. Crawlers + LLM scrapers hit every link with a redirect hop → wasted bandwidth + SEO equity dilution.
3. Cache invalidation on the 301 target requires browser knowledge of the redirect (HTTP 301 caching is per-implementation messy).

## Solution

Two viable approaches:

### Option A — postbuild HTML rewrite

Extend `scripts/copy-legacy-archives.sh` with a Python postpass that walks every copied legacy HTML file in `dist/` and applies the same rewrite rules as `rewriteLegacyLinks()` in `src/scripts/extractLegacyBody.ts` (factor the map out into a shared JSON config consumed by both).

Pros: idempotent; one source of truth shared between Astro extractor and legacy copy.
Cons: extra postbuild step; touches verbatim legacy HTML (CLAUDE.md §9 conservatism — but only URL attribute values, not text).

### Option B — repo-side rewrite

Pre-rewrite the legacy HTML files in `legacy/<archive>/*.html` once (commit) and remove the legacy 301 block from `_redirects`. Then the legacy URLs are direct hits.

Pros: zero postbuild work; cleaner _redirects file.
Cons: breaks any external inbound links that referenced the legacy paths; harder to roll back; CLAUDE.md §11 don't list "don't touch verbatim official text" but URL paths aren't official text.

## Recommendation

Option A — postbuild HTML rewrite. Preserves the legacy 301 safety net for external inbound links while eliminating the redirect chain on internal nav. Factor the rewrite map (currently duplicated between `rewriteLegacyLinks` in TS + the existing `_stories.json` cross-refs in Python builders) into `src/data/legacy-link-rewrites.json` and consume from both.

## Related

- `/gsd:debug link-asset-seo-audit` (2026-06-02) — surfaced this
- `src/scripts/extractLegacyBody.ts` — `rewriteLegacyLinks()` (the rule-set to port)
- Plan 04.1-06 — `_redirects` legacy 301 block
- `.planning/debug/site-pages-broken-round2.md` — earlier related round
