<!-- refreshed: 2026-07-11 -->
# Architecture

**Analysis Date:** 2026-07-11

**Stale-doc warning:** the previous version of this file (2026-05-25) predates
the SSG migration (Phase 3-4), the 2026-05-28 scope pivot (4 active / 11
dormant archives), the Phase 04.1 legacy reorg (`legacy/` directory), and the
Release-03 work. This is a full rewrite verified against `src/`, `scripts/`,
`legacy/`, `astro.config.mjs`, `src/content.config.ts`, and git history.

## System Overview

```text
┌───────────────────────────────────────────────────────────────────────────┐
│                          BUILD-TIME (Astro 5, `pnpm build`)                │
├─────────────────────────────┬───────────────────────────────────────────── │
│  prebuild                   │  astro build                                 │
│  `scripts/normalize-csv.py` │  reads `src/pages/**` + Content Collections  │
│  CSV → `data/wargov*.json`  │  renders 4 ACTIVE archives + stories +       │
│                             │  site-pages + search shell → `dist/`         │
├─────────────────────────────┴───────────────────────────────────────────── │
│  postbuild `scripts/copy-legacy-archives.sh`                               │
│  copies 11 DORMANT archives + 5 partial-port sub-page sets (git-tracked   │
│  HTML under `legacy/`) into `dist/`, then runs Pagefind indexing,          │
│  sitemap.xml, manifest.webmanifest fallback                               │
└───────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                    dist/  (deployed to Cloudflare Pages)                   │
│  4 Astro-rendered pages (/, /aaro/, /nasa/, /nara/) + 2 dormant Astro     │
│  pages (/nz/, /uruguay/) + 9 dormant + partial-port legacy HTML trees +   │
│  /stories/*, /search/, /about/, /foia/, /glossary/, /map/, /timeline/,    │
│  /whatsnew/ + pagefind/ index + sw.js + data/*.json shard mirrors         │
└───────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│               RUNTIME (browser) — zero client:* hydration                  │
│  `src/scripts/invariants.ts` (is:inline, injected by RootLayout) wires:   │
│  hamburger nav, lightbox, `/`-focuses-search, `?q=` persistence, wargov   │
│  shard fetch+insertAdjacentHTML (see Data Flow §2)                        │
│  `sw.js` (Workbox, injectManifest) — 5-tier runtime cache strategy        │
└───────────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| `RootLayout` | Composes `<head>` + Nav + `<main>` + Footer + invariants script; owns the 15-archive `TONE` map, the `ACTIVE_ARCHIVES` set, and the Pagefind `data-pagefind-body`/`data-pagefind-ignore` gate | `src/layouts/RootLayout.astro` |
| `BaseHead` | `<head>` shared across every page: meta/OG tags, favicon, self-hosted fonts, SW registration script, Umami analytics, `head-extra` slot | `src/layouts/BaseHead.astro` |
| `Nav` | Sticky 64 px header: seal + brand, hamburger, 4-archive cross-nav, Stories ▾ / About ▾ dropdowns (JS-driven single-open controller) | `src/components/Nav.astro` |
| `Footer` | Source list (official URLs), per-jurisdiction license string, Pages column, Stories column, Archives column (4 active only), colophon | `src/components/Footer.astro` |
| `Card` | wargov-specific card renderer — the first 50 rows server-render via this component; the HTML string it emits must byte-match `render_card_html()` in `scripts/normalize-csv.py` (D-10 locked pair) | `src/components/Card.astro` |
| `CatalogCard` | Generic card renderer over `catalogAssetSchema` — shared by AARO/NASA/NARA/NZ/Uruguay (and any future catalog-style archive) | `src/components/CatalogCard.astro` |
| `HeroCarousel` | 16:9 autoplay carousel, ≥4 slides, dots/arrows/caption per CLAUDE.md §4 | `src/components/HeroCarousel.astro` |
| `Lightbox` | Static modal shell; open/close/nav/swipe wired by `invariants.ts`, not component-local JS | `src/components/Lightbox.astro` |
| `StructuredData` | JSON-LD helper component (schema.org) | `src/components/StructuredData.astro` |
| `extractLegacyBody` | Build-time-only HTML extractor + chrome-scrubber that turns a `legacy/*.html` file into a verbatim `<article>` body slice for Astro pages | `src/scripts/extractLegacyBody.ts` |
| `invariants.ts` | Source-of-truth for the CLAUDE.md §7 JS invariants, injected verbatim via `is:inline` + `set:html` from `RootLayout.astro` | `src/scripts/invariants.ts` |
| `content.config.ts` | Zod schema + `file()` loader registry for all 15 archive Content Collections | `src/content.config.ts` |
| `sw.ts` | Workbox `injectManifest` service-worker source — compiled to `dist/sw.js` at build time | `src/sw.ts` |

## Pattern Overview

**Overall:** Static-site generation (Astro 5, `output: 'static'`) with a
**two-tier content model**: 4 "ACTIVE" archives fully ported to Astro +
Content Collections, and 11 "DORMANT" archives shipped as git-tracked,
pre-rendered legacy HTML via a bash postbuild step. No SSR, no islands, no
`client:*` hydration anywhere — every interactive behaviour is a hand-rolled
`is:inline` script shared via `RootLayout.astro`.

**Key Characteristics:**
- **Content Collections over CMS.** Every one of the 15 archives has a Zod-validated collection (`src/content.config.ts`) reading `data/<slug>.json`, even though only 6 archives (wargov, aaro, nasa, nara, nz, uruguay) currently have Astro pages that consume them.
- **Fidelity-over-ergonomics schema design.** Field names in `catalogAssetSchema` (`ti`, `de`, `ag`, `l`, `u`, `s`, `th`) and `wargovRowSchema` (literal CSV header strings with spaces, e.g. `'Release Date'`) are chosen to byte-match the upstream Python normaliser output, NOT idiomatic naming. `smartypants: false` + zero markdown plugins in `astro.config.mjs` exist purely to protect this fidelity guarantee.
- **Build-time HTML extraction, not a CMS migration.** `/stories/{slug}/` and the 6 site-pages (`/about/`, `/foia/`, `/glossary/`, `/map/`, `/timeline/`, `/whatsnew/`) do NOT have hand-authored Astro markup for their body content — they read a raw `legacy/*.html` file at build time via `fs.readFileSync`, run it through a regex-based "cascade selector" (`extractMain`), strip chrome (`scrubChrome`), and `set:html` the result into an Astro-owned wrapper.
- **Selective Pagefind indexing via a body-marker gate.** Pagefind indexes a page only if *some* page on the site carries `data-pagefind-body` (per Pagefind's own semantics) — `RootLayout.astro`'s `pageType` prop (`'archive' | 'story' | 'site-page'`) decides whether a given `<main>` gets the marker (active archives + all stories + all site-pages) or the inverse `data-pagefind-ignore` (dormant archive pages).
- **Server-rendered-then-lazy-shard hybrid for large catalogs.** wargov (294 records) server-renders the first 50 rows as real HTML (`Card.astro`), then ships the remaining rows as pre-rendered HTML-string shards (`data/wargov-shard-N.json`, mirrored into `public/data/` so they're fetchable at `/data/wargov-shard-N.json`); a client script fetches all shards up front and does `insertAdjacentHTML` — zero client-side templating (D-10 LOCKED invariant).

## Layers

**Presentation / Routing (`src/pages/`):**
- Purpose: one Astro file per route. File-based routing — `src/pages/aaro/index.astro` → `/aaro/`, `src/pages/stories/[slug].astro` → `/stories/<slug>/` (dynamic via `getStaticPaths()`).
- Location: `src/pages/`
- Contains: `.astro` files only (no nested route logic outside this tree)
- Depends on: `src/layouts/`, `src/components/`, `astro:content` (Content Collections), `src/scripts/extractLegacyBody.ts` for extraction-based routes
- Used by: nothing (leaf layer — Astro's router)

**Layout (`src/layouts/`):**
- Purpose: shared page shell (`RootLayout.astro`) and shared `<head>` (`BaseHead.astro`)
- Location: `src/layouts/`
- Depends on: `src/components/Nav.astro`, `src/components/Footer.astro`, `src/scripts/invariants.ts`
- Used by: every page in `src/pages/`

**Components (`src/components/`):**
- Purpose: reusable render units — cards, carousel, lightbox, nav, footer, JSON-LD helper
- Location: `src/components/`
- Depends on: `src/layouts/RootLayout.astro` for the shared `ArchiveSlug` type
- Used by: `src/pages/**`

**Content Collections (`src/content.config.ts` + `data/*.json`):**
- Purpose: typed, Zod-validated data source for every archive, decoupled from how each archive's page ultimately renders it
- Location: `src/content.config.ts` (schema/registry), `data/<slug>.json` (payload)
- Contains: two schema shapes — `wargovEnvelopeSchema` (CSV-keyed, wargov only) and `catalogEnvelopeSchema` (14 other archives, abbreviated Python-parity field names)
- Depends on: `astro/loaders` `file()` loader
- Used by: `getEntry('<slug>', 'v1')` in `src/pages/index.astro`, `src/pages/aaro/index.astro`, `src/pages/nasa/index.astro`, `src/pages/nara/index.astro`, `src/pages/nz/index.astro`, `src/pages/uruguay/index.astro`

**Legacy static HTML (`legacy/`):**
- Purpose: the pre-Astro archive corpus — 9 dormant archives shipped wholesale, 5 partial-port archives' sub-pages (case narratives, per-archive `/pages/*` sections), root-level informational pages, all git-tracked
- Location: `legacy/`
- Depends on: nothing (self-contained HTML/CSS/JS files, no build step)
- Used by: `scripts/copy-legacy-archives.sh` (wholesale file copy into `dist/`), `src/scripts/extractLegacyBody.ts` (build-time body extraction for `/stories/*` and the 6 site-pages)

**Build scripts (`scripts/`):**
- Purpose: everything that runs OUTSIDE `astro build` — CSV/JSON normalisation (`pnpm prebuild`), legacy-HTML shipping + Pagefind indexing + sitemap (`pnpm postbuild`), scrape automation (Phase 5 scope), verification/CI gates
- Location: `scripts/`
- Depends on: `data/`, `legacy/`, `dist/` (postbuild only)
- Used by: `package.json` `prebuild`/`postbuild` hooks, `.github/workflows/*.yml`

## Data Flow

### Primary Request Path — wargov (`/`)

1. `pnpm prebuild` runs `scripts/normalize-csv.py`, which reads `uap-data.csv` (fallback `uap-release001.csv`) and writes `data/wargov.json` (first 50 rows + shard manifest) plus `data/wargov-shard-N.json` (pre-rendered `<article>` HTML strings, 50/shard) — mirrored into `public/data/` for client fetch (`scripts/normalize-csv.py` ~line 829).
2. `astro build` loads `data/wargov.json` through the `wargov` Content Collection (`src/content.config.ts` → `file('data/wargov.json')`), Zod-validates it against `wargovEnvelopeSchema`.
3. `src/pages/index.astro` calls `getEntry('wargov', 'v1')`, server-renders the first 50 rows via `Card.astro`, and emits the shard manifest as an inline `<script id="wargov-shards" set:html={JSON.stringify(shards)}>` (`src/pages/index.astro:372`).
4. At runtime, an `is:inline` script in `index.astro` (~line 399+) reads `#wargov-shards`, `fetch()`s every `/data/wargov-shard-N.json` in parallel (served from `dist/data/` — the `public/data/` mirror), and does `insertAdjacentHTML('beforeend', card.html)` for each card — zero client-side templating (D-10 LOCKED).
5. `pnpm postbuild` (`scripts/copy-legacy-archives.sh`) runs AFTER `astro build`: copies the 11 dormant + partial-port legacy trees into `dist/`, then invokes `pnpm exec pagefind --site dist` to build the search index over every page carrying `data-pagefind-body`.

### Dormant-Archive Request Path (e.g. `/geipan/`)

1. `legacy/geipan/index.html` (git-tracked, pre-Astro HTML with inline CSS/JS/manifest) exists on disk before any build step runs.
2. `scripts/copy-legacy-archives.sh` enumerates `git ls-files "legacy/geipan/"`, strips the `legacy/` prefix, and copies each file to `dist/geipan/...` (skipping anything > 25 MiB, the CF Pages file-size cap).
3. No Astro route owns `/geipan/` — the file lands in `dist/` purely via file copy. Astro's own build never sees it.
4. The copied `<main>` in that legacy HTML lacks `data-pagefind-body`, so Pagefind (which runs after the copy step) skips it — dormant content stays out of search by construction.

### Curated Story / Site-Page Path (e.g. `/stories/tic-tac/`, `/about/`)

1. `src/data/stories.json` (stories) or `src/data/site-pages.json` (site-pages) declares `{ slug, legacyPath, ... }` entries.
2. At build time, `getStaticPaths()` (stories) or a direct top-of-file read (site-pages) calls `readFileSync(legacyPath)`, then `extractMain(raw, legacyPath)` (`src/scripts/extractLegacyBody.ts`) — a priority-ordered regex "cascade" that matches `<main>`, `<article>`, or a handful of per-file custom anchors (e.g. `legacy/map.html` has neither `<main>` nor `<article>`, so a `filePath`-guarded cascade entry anchors on `<section id="map">` instead). No anchor match ⇒ the build throws (no silent `<body>` fallback, by design — "B-3" invariant).
3. `scrubChrome(anchor, opts)` strips `<style>`, `<link rel="stylesheet">`, `<script>` (unless `preserveScripts: true` for `map`/`timeline`/`whatsnew`/`glossary`), `<header>`, `<footer>`, the legacy scanlines div, inline `style=` attributes, and rewrites relative legacy URLs (`../aaro/tic-tac.html` → `/stories/tic-tac/`, `../about.html` → `/about/`, etc.) via `rewriteLegacyLinks()`.
4. The scrubbed HTML is injected via `<article set:html={bodyHtml}>` inside an Astro-owned page that supplies its own `<h1>`, `RootLayout`, Nav, Footer. `pageType="story"` / `pageType="site-page"` forces `data-pagefind-body` regardless of the referenced archive's active/dormant status.

**State Management:** none — every page is stateless HTML at request time. The
only "state" is URL-driven (`?page=N` pagination param, `?q=` search-query
persistence), read and written by `invariants.ts` / `search.astro`'s inline
scripts, never a client-side store.

## Key Abstractions

**`ArchiveSlug` literal union:**
- Purpose: single source of truth for the 15 valid archive slugs; exported from `RootLayout.astro` (must stay on ONE LINE — `@astrojs/compiler 2.13.1` mis-compiles multi-line `export type` in `.astro` frontmatter) and re-imported by `Nav.astro`, `Footer.astro`, `src/pages/stories/[slug].astro`
- Examples: `src/layouts/RootLayout.astro:31`
- Pattern: TypeScript literal union + a companion `Record<ArchiveSlug, T>` lookup table (TONE, LICENSE, SOURCE_URLS, PATH) in each consumer, always with a `?? TONE.wargov` / `?? BRAND.wargov!` defensive fallback

**`pageType` discriminator:**
- Purpose: decides Pagefind eligibility independent of archive active/dormant status
- Examples: `src/layouts/RootLayout.astro:41` (`'archive' | 'story' | 'site-page'`)
- Pattern: default `'archive'` preserves pre-Phase-04.1 behavior for every call site that omits the prop

**Catalog vs. wargov schema split:**
- Purpose: wargov's CSV-native shape (`rows[]` keyed by literal spaced column names) cannot be unioned with the other 14 archives' abbreviated JSON shape (`assets[]` with `t`/`ti`/`de`/... fields) without a lossy transform, so `content.config.ts` deliberately keeps two schemas rather than one monolithic union
- Examples: `src/content.config.ts` (`wargovEnvelopeSchema` vs `catalogEnvelopeSchema`)
- Pattern: `.strict()` on the leaf asset schema (unknown fields = build error = drift signal), lenient envelope wrapper (forward-compatible top-level fields)

**Legacy-HTML extraction cascade:**
- Purpose: reuse verbatim official text from 89 pre-Astro legacy files without hand-transcribing content into Astro components
- Examples: `src/scripts/extractLegacyBody.ts` `CASCADE` array
- Pattern: priority-ordered regex matchers, `filePath`-guarded entries tried first (per-file overrides), unguarded generic entries (`<main>`, `<article>`) as fallback, hard `throw` if nothing matches (no silent `<body>` fallback)

## Entry Points

**`src/pages/index.astro`:**
- Location: `src/pages/index.astro` → `dist/index.html` (site root `/`)
- Triggers: any request to `/`
- Responsibilities: wargov (War.gov/PURSUE) archive — hero carousel, headlines, 50 server-rendered cards + lazy shard loader, stats grid, tabs/sort/search/filter/pagination UI, lightbox

**`src/pages/{aaro,nasa,nara}/index.astro`:**
- Location: `src/pages/aaro/index.astro`, `src/pages/nasa/index.astro`, `src/pages/nara/index.astro`
- Triggers: `/aaro/`, `/nasa/`, `/nara/`
- Responsibilities: the other 3 ACTIVE archives; same `CatalogCard` + pagination + lightbox pattern, each with its own tone colour and legacy sub-page set preserved via `copy-legacy-archives.sh`'s partial-port block

**`src/pages/{nz,uruguay}/index.astro`:**
- Location: `src/pages/nz/index.astro`, `src/pages/uruguay/index.astro`
- Triggers: `/nz/`, `/uruguay/` (direct URL only — not linked from Nav/Footer post-scope-pivot)
- Responsibilities: DORMANT archives that nonetheless got a full Astro port in Phase 4 (04-05/04-06) before the 2026-05-28 scope pivot removed them from the active nav/search surface; `RootLayout` marks their `<main>` `data-pagefind-ignore` via the `ACTIVE_ARCHIVES` set

**`scripts/copy-legacy-archives.sh` (postbuild):**
- Location: `scripts/copy-legacy-archives.sh`, invoked by `package.json`'s `postbuild` npm-lifecycle hook
- Triggers: runs automatically after every `astro build` completes (via `pnpm build`)
- Responsibilities: ships the 9 wholesale-dormant archives (geipan, uk, brazil, chile, argentina, canada, italy, peru, spain) + 5 partial-port sub-page sets (nz, uruguay, nasa, nara, aaro) + shared `assets/`/`slideshow*/` + `api/`/`feeds/` JSON into `dist/`; then runs Pagefind indexing, `build-dir-index.py`, `rewrite-dist-legacy-links.py`, `build-sitemap.py`, and writes a `manifest.webmanifest` fallback if the PWA plugin didn't emit one

**`scripts/normalize-csv.py` (prebuild):**
- Location: `scripts/normalize-csv.py`, invoked by `package.json`'s `prebuild` npm-lifecycle hook
- Triggers: runs automatically before every `astro build` (via `pnpm build`)
- Responsibilities: sole writer of `data/wargov.json` + `data/wargov-shard-N.json` from `uap-data.csv`; the `Card.astro`-vs-`render_card_html()` HTML parity is a LOCKED build-time contract (D-10)

## Architectural Constraints

- **Threading:** single-threaded build (Node.js, Astro's static build pipeline); no worker threads in the site build. `workers/akamai-spike/` is a SEPARATE Cloudflare Worker experiment (Phase 5 scrape-automation spike), not part of the site's request path.
- **Global state:** none at runtime — every page is static HTML plus isolated `is:inline` scripts. The closest thing to global state is the Workbox service worker's Cache Storage (`src/sw.ts`, cache-name-prefixed `realufo-v<sha>`) and the `?q=`/`?page=` URL params.
- **No client:* hydration anywhere.** This is a hard invariant (D-21..D-23) carried over from the pre-migration site: no React/Vue/Svelte islands, ever. Every interactive behavior is a hand-written `is:inline` script.
- **Two parallel data copies for wargov shards:** `data/wargov-shard-N.json` (repo root — read by Astro's build-time `import.meta.glob`) and `public/data/wargov-shard-N.json` (mirrored — becomes `dist/data/wargov-shard-N.json`, fetched by the browser at runtime). Editing one without the other desyncs build-time stats from runtime card content — `scripts/normalize-csv.py` is the only script that should write either.
- **`public/data/` is a partial, stale mirror for non-wargov archives.** It contains `aaro.json`, `nasa.json`, `nara.json`, `nz.json`, `uruguay.json` (used at runtime the same way as wargov's shards would be, if those archives ever shard) but is MISSING `argentina.json`, `brazil.json`, `canada.json`, `chile.json`, `geipan.json`, `italy.json`, `peru.json`, `spain.json`, `uk.json` — those 9 dormant archives' catalog pages are legacy static HTML (not Astro + Content Collections), so they never needed a `public/data/` mirror.
- **Root-level per-archive directories (`aaro/`, `nasa/`, `nara/`, `nz/`, `uruguay/`, `brazil/`, `chile/`, `geipan/`, `uk/`, `argentina/`, `canada/`, `italy/`, `peru/`, `spain/`) are 100% gitignored local caches** — `git ls-files <dir>/` returns zero for every one of them (verified 2026-07-11). They hold only `pdfs/`, `videos/`, `.cache/` download-cache subdirectories populated by `scripts/dl-<slug>.sh`. This CONTRADICTS the CLAUDE.md §5 storage-layout diagram, which still shows these as if they hold the archive's HTML/assets — that content moved to `legacy/<slug>/` in the Phase 04.1 reorg (commits `6504f42`, `c9fe513`, `50f8596`). Treat CLAUDE.md §5 as aspirational/historical for these paths; treat this document + `legacy/` as ground truth.
- **Legacy-extraction build failure is intentional, not a bug.** `extractMain()` throws (no `<body>` fallback) if a `legacy/*.html` file doesn't match any cascade selector — this is a deliberate "fail the build, don't silently double-render chrome" invariant (B-3). Adding a new story/site-page whose legacy source has an unusual DOM shape requires extending the `CASCADE` array in `src/scripts/extractLegacyBody.ts`, not working around it.

## Anti-Patterns

### Do not add `client:*` directives

**What happens:** Astro components support `client:load`/`client:visible`/etc. hydration directives.
**Why it's wrong:** The project's offline-first + JS-disabled-viewing goals (CLAUDE.md §1, §7) require every page to be fully readable/navigable with JavaScript OFF. Hydration islands reintroduce a JS-required code path and break the `tests/js-off.spec.ts` gate.
**Do this instead:** Add a new named function to `src/scripts/invariants.ts` (or a page-local `is:inline` script for page-specific behavior) and wire it defensively (`if (!el) return;`, idempotent `dataset.wired` guards — see `Nav.astro`'s dropdown controller for the reference pattern).

### Do not add a `<body>` fallback to `extractMain()`

**What happens:** A future edit might be tempted to add a final `<body>...</body>` regex to `CASCADE` in `src/scripts/extractLegacyBody.ts` so unrecognized legacy files "just work" instead of failing the build.
**Why it's wrong:** `<body>` includes the legacy page's own `<header>`/`<nav>`/`<footer>`/`<style>`/scanlines chrome, which would double-render alongside the Astro-rendered `Nav`/`Footer`/scanlines (the B-3 defect this design explicitly prevents).
**Do this instead:** Audit the new file's DOM shape, add a `filePath`-guarded cascade entry (see the `map.html`/`timeline.html` entries for the pattern of anchoring on an unambiguous in-file marker), and update `.planning/phases/04.1-legacy-reorg-stories-site-pages-nav-surface/04.1-legacy-html-structure-audit.md`.

### Do not mutate CSV or add text transforms to normalisers

**What happens:** A normaliser (`scripts/normalize-csv.py`, `scripts/normalize-*.py`) or the Zod schema (`src/content.config.ts`) gets a `.transform()`/`.strip()`/smart-quote rewrite "cleanup" pass on a text field.
**Why it's wrong:** CLAUDE.md §9 requires verbatim official text. Any transform on `ti`, `de`, `Title`, `Description Blurb`, etc. silently breaks the fidelity gate (`tests/fidelity-samples.json` + `scripts/verify-fidelity.py`, 115 byte-exact samples).
**Do this instead:** Do only `html.escape()`-equivalent structural encoding at RENDER time (already done in `render_card_html()`), never at normalisation time. `uap-release001.csv` / `uap-data.csv` are read-only inputs — see CLAUDE.md §11 don'ts.

### Do not point a Download/Open button at a bare local path that might be empty

**What happens:** A card template renders `<a href={asset.l}>` unconditionally.
**Why it's wrong:** CLAUDE.md §4.3 — if `a.local` is empty on the deployed site, the button must fall back to the GitHub Releases URL (`a.u` / `a.url`), never to an empty/bare local path that 404s or serves an HTML error page.
**Do this instead:** Follow the existing `CatalogCard.astro` / `Card.astro` button logic: prefer `local`, fall back to `url` (release URL), never emit a button with no resolvable target.

## Error Handling

**Strategy:** Fail loudly at BUILD time for data/content defects (missing
collection entry, Zod validation error, `extractMain()` no-match, Nav.astro's
featured-story `{1..8}` gate); fail SILENTLY/gracefully at RUNTIME for
progressive-enhancement JS (defensive `if (!el) return`, `.catch(() => {})`
on the service-worker registration call).

**Patterns:**
- `src/pages/index.astro` throws with a remediation hint (`run 'pnpm prebuild'...`) if `getEntry('wargov', 'v1')` returns undefined.
- `Nav.astro` throws a descriptive `Error` at build time if the featured-stories invariant (`FEATURED_STORIES.length === 8`, unique `order` 1..8) is violated — see `src/components/Nav.astro:58-64`.
- `extractMain()` throws with a remediation pointer to the structure-audit doc + `CASCADE` array location.
- Runtime service-worker registration is wrapped in `.catch(function () {})` — a registration failure never blocks page interactivity.
- Postbuild helper scripts (`build-dir-index.py`, `rewrite-dist-legacy-links.py`) are invoked with `|| echo "...WARN...(non-fatal)"` in `copy-legacy-archives.sh` — they degrade gracefully rather than failing the whole build.

## Cross-Cutting Concerns

**Logging:** none in production (no client-side logging/telemetry beyond
Umami analytics, `<script defer src="https://cloud.umami.is/script.js">` in
`BaseHead.astro`). Build-time scripts print to stdout/stderr (bash `echo`,
Python `print`).

**Validation:** Zod schemas in `src/content.config.ts` are the sole runtime
validation gate for content data (`.strict()` on asset-leaf schemas catches
unexpected fields as a build failure). CI-side gates (`scripts/verify-*.{py,sh}`)
enforce redirect-URL parity, Lighthouse budgets, and the Python-retirement
invariant.

**Authentication:** none — this is a fully public, read-only static archive.
No login, no admin surface (the runtime service worker explicitly
NetworkOnly-denylists a hypothetical `/admin` path defensively, per D-21 SW-05,
even though no such route exists today).

---

*Architecture analysis: 2026-07-11*
