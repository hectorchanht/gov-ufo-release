---
slug: archive-filter-lightbox
status: resolved
trigger: |
  the archive filter should filter content as the ui imply. and the lightbox next page will also be filtered. after click rotate button in lightbox, hide desc box
created: 2026-06-04
updated: 2026-06-04
resolved: 2026-06-04
---

# Debug Session: archive-filter-lightbox

## Symptoms

**Bug 1 — Archive filter doesn't filter content (as expected):**
- UI shows tabs (All / Documents / Imagery / Video / Audio) + Agency select +
  (Release select for wargov) + Per-page select.
- Filter handler exists (each archive index ships its own `applyFilters()`
  inline script) and DOES toggle `c.style.display = show ? '' : 'none'`.
- But `style.display` is ALSO controlled by the pagination handler
  (`renderPage`) which windows cards 0..PAGE_SIZE-1 → none, etc.
- Pagination + filter are in separate `<script is:inline>` IIFEs and
  do NOT coordinate. Result: race condition on `style.display`. On filter
  change, applyFilters flips display:'' across ALL pages → matching cards
  from page 5 appear on page 1. On pagination click, renderPage ignores
  filter → non-matching cards reappear.

**Bug 2 — Lightbox prev/next ignores filter:**
- `refreshLbList()` intentionally walked ALL `.arch-card` (per the inline
  "Pitfall #6" comment from Plan 04-04). User wants the opposite: lightbox
  prev/next traverses the filtered subset only.

**Bug 3 — Lightbox rotate leaves desc box visible:**
- `invariants.ts:317-323` rotate handler only toggles `lb-rotated` class.
- `Lightbox.astro` had no CSS rule hiding `.lb-meta-panel` /
  `.lb-counter` / `.lb-actions` in rotated state (only `:fullscreen`
  hid them).

## Affected files

- `src/components/Lightbox.astro` — `:lb-rotated` chrome-hide CSS rule
- `src/pages/index.astro` (wargov) — filter + pagination coordination
- `src/pages/aaro/index.astro` — same pattern
- `src/pages/nasa/index.astro` — same pattern
- `src/pages/nara/index.astro` — same pattern

## Current Focus

(closed — see Resolution)

## Evidence

- timestamp: 2026-06-04T18:00:00Z
  finding: |
    `src/scripts/invariants.ts:317-323` — rotate handler does
    `lb.classList.toggle('lb-rotated')` only. No DOM update to hide meta.
- timestamp: 2026-06-04T18:00:00Z
  finding: |
    `src/components/Lightbox.astro:338-344` — `.lightbox.lb-rotated`
    only rotates `.lightbox-inner img,video`. `.lb-meta-panel` not
    targeted. (`:fullscreen` rule at line 352-358 DOES hide meta —
    rotate needs an equivalent rule.)
- timestamp: 2026-06-04T18:00:00Z
  finding: |
    `src/pages/index.astro:514-516` (pagination renderPage) sets
    `cards[i].style.display = i >= start && i < end ? '' : 'none'`.
    `src/pages/index.astro:647-667` (applyFilters) sets
    `c.style.display = show ? '' : 'none'`. Both write the same property
    without coordination.
- timestamp: 2026-06-04T18:00:00Z
  finding: |
    `src/pages/index.astro:739-744` comment "Pitfall #6 — walk ALL
    .arch-card (including display:none from filter tabs OR ?page=N
    windowing); the lightbox prev/next must traverse the full set so
    users can arrow across hidden cards." — Plan 04-04 locked this
    invariant; this fix flips it to "filter-aware lbList" per user
    request while preserving cross-PAGE traversal.
- timestamp: 2026-06-04T18:00:00Z
  finding: |
    Same handler shape across `aaro/index.astro` (lines 463-588),
    `nasa/index.astro` (lines 453-578), `nara/index.astro` (lines 448-579).
    All four patched identically.
- timestamp: 2026-06-04T18:15:00Z
  finding: |
    Build (`pnpm build`) succeeds post-patch with no Astro / TypeScript
    errors. dist/ regenerates cleanly.
- timestamp: 2026-06-04T18:20:00Z
  finding: |
    Local-preview Playwright run:
      - `tests/lightbox.spec.ts:27,43,66,84` — 4/4 pass.
        Notably 84 ("filter Documents tab then click open opens the
        filtered card not #1") passes — exercises the filter→lightbox
        rowId resolution path.
      - `tests/pagination.spec.ts:243` — passes. Confirms cross-PAGE
        lightbox traversal preserved (lbList still includes
        pagination-hidden cards; only filter-failed cards excluded).
    Pre-existing failures (`pagination.spec.ts:57,70,94,123,156,193`
    and `lightbox.spec.ts:142`) are unchanged — all are PAGE_SIZE=20
    vs select-default=24 drift / stale-fixture issues unrelated to
    this fix.

## Eliminated

- ✗ "Filter handler missing entirely" — handlers exist + are wired.
- ✗ "data-type missing from cards" — `Card.astro:110`, `CatalogCard.astro:135`
  both emit `data-type={rtype}`.

## Resolution

### Root cause

Two independent JS IIFEs (`renderPage` for pagination, `applyFilters` for
filter/sort) write the same `style.display` property on every
`.arch-card` without coordinating, so each clobbers the other's intent.
`refreshLbList` is also out of sync: it deliberately walked ALL cards
(including filter-failed ones), so the lightbox's prev/next nav stepped
through cards the user could not see in the grid. Rotate had no CSS
rule to hide the meta-panel — only fullscreen did.

### Fix

**Single owner of `style.display`:** the pagination `renderPage` now
owns the property; the filter writes a `data-filter-hidden="1"`
attribute instead. `renderPage` reads that attribute and paginates only
the filter-passing subset, then sets `display:none` for every
filter-failed card unconditionally.

**Filter → pagination handshake:** the pagination IIFE exposes its
`renderPage` on `window.__<slug>RenderPage`. The filter IIFE calls it
(with `skipPaginate:true` during the initial-load + MutationObserver
storms — defers to pagination's own boot path; `skipPaginate:false` on
real user filter changes — resets to page 1 over the filtered subset).

**Filter-aware lbList:** `refreshLbList()` now skips cards where
`dataset.filterHidden === '1'`. Pagination-hidden cards remain in
`lbList`, so the cross-page test
(`pagination.spec.ts:243 — lightbox arrow advances across page boundary`)
still passes. Only the filter constraint is honored in lightbox
traversal.

**Rotate hides chrome:** `Lightbox.astro` gains a
`.lightbox.lb-rotated .lb-meta-panel, .lb-counter, .lb-actions {
display:none }` rule plus a frame-padding tweak so the rotated asset
gets the same full-bleed area as `:fullscreen`.

### Files changed

- `src/components/Lightbox.astro`
  - Add `.lightbox.lb-rotated .lb-meta-panel, .lb-counter, .lb-actions`
    → `display: none`
  - Add `.lightbox.lb-rotated .lb-frame { padding: 8px }`
- `src/pages/index.astro` (wargov, 5 patches)
  - `renderPage`: paginate over `allCards.filter(c =>
    c.dataset.filterHidden !== '1')`; hide filter-failed cards
    unconditionally.
  - Expose `window.__wargovRenderPage = renderPage`.
  - `applyFilters(opts)`: set/delete `c.dataset.filterHidden` instead
    of `style.display`; call `window.__wargovRenderPage(1, ...)` when
    `!opts.skipPaginate`; call `refreshLbList()` after.
  - `refreshLbList`: skip cards with `dataset.filterHidden === '1'`.
  - Initial `applyFilters({ skipPaginate: true })` + MutationObserver
    passes `{ skipPaginate: true }` to avoid materialise-loop thrash.
- `src/pages/aaro/index.astro` — same 5 patches (slug = `aaro`).
- `src/pages/nasa/index.astro` — same 5 patches (slug = `nasa`).
- `src/pages/nara/index.astro` — same 5 patches (slug = `nara`).

### Verification

- `pnpm build` — passes (Astro + postbuild + Pagefind clean).
- Playwright (against local `dist/` served on :4321):
  - `lightbox.spec.ts:27,43,66,84` — 4/4 pass (incl. filter→lightbox
    rowId resolution).
  - `pagination.spec.ts:243` — pass (cross-PAGE lightbox traversal
    preserved).
- No new test regressions vs the pre-change baseline; the 7 pre-existing
  failures (PAGE_SIZE=20 vs select-default=24 drift, stale remote-PDF
  fixture) remain unrelated to this work.
