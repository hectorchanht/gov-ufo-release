---
slug: site-pages-broken-round2
status: resolved
trigger: "map page still empty content, whatsnew page all link should be working but some is not. glossary input on the q should filter the content"
created: 2026-06-02
updated: 2026-06-02
phase: 04.1-legacy-reorg-stories-site-pages-nav-surface
prior_session: site-pages-broken
related_commits:
  - 49906bc fix(04.1): map height + glossary filter css + dev-link rewrite + ship api/feeds
---

# Debug Session: site-pages-broken-round2

Continuation of `site-pages-broken`. Prior fix (`118c4fa`) preserved scripts + injected `<base href="/">`. Bugs persist due to stripped legacy CSS + missing dist assets + stale legacy links.

## Symptoms

| Bug | Page | Surface |
|-----|------|---------|
| 1 | /map/ | Section#map renders 0-height (no Leaflet visual) |
| 2 | /whatsnew/ | Some links / fetch targets 404 |
| 3 | /glossary/ | `#g-q` input event fires but content stays unfiltered |

## Root causes

### Bug 1 — `#map` height stripped by scrubChrome

Legacy CSS: `#map { flex:1; width:100%; background:#0a0a0c }`. Lived inside legacy `<style>` block. `scrubChrome` strips all `<style>` tags. Without height, `<section id="map">` collapses to 0px. Leaflet renders into 0-height container → invisible.

### Bug 2 — Whatsnew broken links + missing dist assets

Legacy whatsnew has:
- `<a href="/timeline.html">` → 404 on dev server (works on CF Pages via `_redirects` 301 → `/timeline/`)
- `fetch('/api/all.json')` → 404. `api/` exists at repo root (`api/{by-archive,geo,pages-index,stats}.json`) but `api/all.json` not generated, AND nothing copies `api/` to `dist/`
- `<a href="/feeds/all.xml">` + per-archive feeds → 404. `feeds/` exists at repo root with 16 XML files but never copied to `dist/`

### Bug 3 — Glossary `.entry.hidden { display: none }` stripped

Legacy CSS: `.entry.hidden { display: none }`. Stripped by `scrubChrome`. JS toggles `.hidden` class on `<li class="entry">` per query, but no CSS rule → entries stay visible → filter appears dead.

## Fix plan

1. **`src/styles/site-pages.css`**: add targeted rules for `#map`, `.entry.hidden`, `.gsec`, plus minimum prose typography for glossary entries.
2. **`scripts/copy-legacy-archives.sh`**: copy `api/` + `feeds/` to `dist/`.
3. **One-time**: run `python3 scripts/build-api.py` to generate `api/all.json` from per-archive manifests.
4. **`src/scripts/extractLegacyBody.ts`**: add `rewriteSitePageLinks` step — rewrite `/(about|foia|glossary|map|timeline|whatsnew).html` → `/$1/` in extracted body so dev-server clicks work without `_redirects`.

## Status: applying inline.
