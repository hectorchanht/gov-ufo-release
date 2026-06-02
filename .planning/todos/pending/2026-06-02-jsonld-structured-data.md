---
created: 2026-06-02
title: Emit JSON-LD structured data on key landing pages
area: seo
files:
  - src/layouts/RootLayout.astro
  - src/layouts/BaseHead.astro (already has `<slot name="head-extra" />`)
  - src/pages/index.astro
  - src/pages/stories/index.astro
  - src/pages/stories/[slug].astro
---

## Problem

Surfaced during `/gsd:debug link-asset-seo-audit`. SEO inventory found that no Astro-served page emits JSON-LD structured data. `BaseHead.astro` even has a `<slot name="head-extra" />` slot ready for this (per Plan 03-05 wargov Dataset schema TODO comment), but no caller fills it.

Missing schema types:
- **Homepage** (`/`) — `WebSite` + `SearchAction` (advertises Pagefind search to Google).
- **`/stories/`** — `CollectionPage` listing all stories.
- **`/stories/{slug}/`** — `Article` (or `NewsArticle`) with headline, datePublished, author/publisher, image.
- **`/aaro/`, `/nasa/`, `/nara/`** — `Dataset` (per CLAUDE.md §13 "Plan 03-05's wargov index.astro will emit Dataset schema.org structured data here when it consumes RootLayout").

## Solution

Add a small `src/components/StructuredData.astro` component that takes a schema type + payload and emits `<script type="application/ld+json">`. Slot into each route via `<Fragment slot="head-extra">`.

Acceptance:
1. `/` emits `WebSite` + `SearchAction` (with `https://realufo.org/search/?q={search_term_string}` as the target).
2. Story pages emit `Article` with headline=`entry.title`, datePublished=`entry.incidentDate || ''`, publisher=`realufo.org`, image=`og:image`.
3. `/stories/` emits `CollectionPage` with `hasPart` listing every story slug.
4. Active archive indexes emit `Dataset` per CLAUDE.md §13 expectation.
5. Google's Rich Results Test passes for at least one story page.

## Related

- `/gsd:debug link-asset-seo-audit` (2026-06-02) — surfaced this
- BaseHead.astro line 87 — pre-existing `<slot name="head-extra" />` ready to consume
- CLAUDE.md §13 — references "Plan 03-05's wargov index.astro will emit Dataset schema.org"
