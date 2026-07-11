# Coding Conventions

**Analysis Date:** 2026-07-11

This document reflects the codebase after the Astro 5 / Cloudflare Pages
migration (Phase 4 closed 2026-05-28; Phase 04.1 nav-surface work merged
through 2026-06-02, plus quick-task `260615-3e3` Release-03 work). It
supersedes the 2026-05-25 version of this file, which described the
pre-migration static-HTML-per-archive world (no `src/`, no build step,
inline `<script>`/`<style>` per page). `CLAUDE.md` (§3 design system, §7
JS invariants, §8 mobile-first, §9 content rules, §11 don'ts) is the
canonical spec — this file explains **how those rules manifest in
actual files** so a future agent can write conforming code without
re-deriving the rules from scratch.

---

## 0. The two build surfaces — know which one you're editing

The repo ships **4 ACTIVE archives** (`wargov` at `/`, `aaro`, `nasa`,
`nara`) via Astro 5 + content collections (`src/`), and **11 DORMANT
archives** (`geipan`, `uk`, `brazil`, `chile`, `argentina`, `canada`,
`italy`, `nz`, `peru`, `spain`, `uruguay`) via a legacy static-HTML
postbuild copy (`scripts/copy-legacy-archives.sh`, wired as `pnpm`'s
`postbuild` script). Only `nz` and `uruguay` among the dormant set have
Astro page templates (`src/pages/nz/index.astro`, `src/pages/uruguay/
index.astro`) — the rest are pre-rendered HTML snapshots under
`legacy/<slug>/`.

**Rule of thumb:** if you are touching card markup, lightbox behaviour,
nav, footer, or anything under `src/`, you are on the Astro surface and
every convention below applies. If you are touching `scripts/build-<
brazil|chile|geipan|uk>.py`, `scripts/build_batch3.py`, or the other
`scripts/build-{api,cases,feeds,geo,og,pages-index,stories,sw}.py`
files, you are on the legacy Python surface consumed by
`.github/workflows/scrape.yml` (Phase 5 SCRP scope) — `scripts/verify-
python-retired.sh` whitelists these files explicitly; **do not delete
them**, and do not expect Astro's fidelity/Zod rules to apply there.

---

## 1. Design system — LOCKED (CLAUDE.md §3)

These tokens and colours are **frozen**. Never introduce a new colour,
font, or spacing scale outside this set. Any new archive gets ONE new
row added to the tone-colour table below — nothing else changes.

### 1.1 Tone colours (`--caution`) per archive

Defined in exactly two places that MUST stay byte-identical:
- `src/layouts/RootLayout.astro` — the `TONE` map (lines ~75-91)
- `tests/tone-colours-fixture.json` — the CI fixture `tests/tone-
  colours.spec.ts` asserts against via `getComputedStyle`

```ts
// src/layouts/RootLayout.astro
const TONE: Record<ArchiveSlug, { caution: string; sealStart: string; sealMid: string; sealEnd: string }> = {
  wargov:    { caution: '#d4a017', sealStart: '#b91c1c', sealMid: '#6b1010', sealEnd: '#2a0606' },
  aaro:      { caution: '#4a9eff', sealStart: '#1e3a8a', sealMid: '#102560', sealEnd: '#061238' },
  nasa:      { caution: '#fc3d21', sealStart: '#fc3d21', sealMid: '#a01818', sealEnd: '#400606' },
  nara:      { caution: '#cbd5e1', sealStart: '#9ca3af', sealMid: '#4b5563', sealEnd: '#1f2937' },
  // ...11 more dormant-archive entries, preserved verbatim for direct-URL rendering
};
```

`--caution` is injected as an inline CSS custom property on `<html>` by
`RootLayout.astro` (`style={rootStyle}`), NOT hard-coded per archive
stylesheet:
```ts
const tone = TONE[archiveSlug] ?? TONE.wargov;
const sealGradient = `radial-gradient(circle at center, ${tone.sealStart} 0%, ${tone.sealMid} 50%, ${tone.sealEnd} 100%)`;
const rootStyle = `--caution: ${tone.caution}; --seal-gradient: ${sealGradient};`;
```
`src/styles/global.css` and every `src/styles/<slug>.css` file consume
`var(--caution)` — never a literal hex value in component CSS. If
`TONE[archiveSlug]` misses (typo, or a dormant slug arriving from
loosely-typed JSON), the lookup falls back to `TONE.wargov` — **always
defend with `?? TONE.wargov`, never let the lookup return `undefined`
into a `style` string** (this is the T-03-11 tampering mitigation).

### 1.2 Shared palette (`src/styles/global.css` `:root`)

```css
:root {
  --bg:          #0a0a0c;
  --bg-2:        #111114;
  --panel:       #15151a;
  --ink:         #e8e3d8;
  --ink-dim:     #a8a298;
  --ink-faint:   #6b665d;
  --rule:        rgba(232, 227, 216, 0.12);
  --rule-strong: rgba(232, 227, 216, 0.28);
  --stamp:       #b91c1c;
  --warm:        #d4a017;
  --classified:  #c9362c;
  --serif:       "Source Serif 4", "Iowan Old Style", Georgia, serif;
  --mono:        "JetBrains Mono", "SF Mono", Consolas, ui-monospace, monospace;
  --caution: var(--warm);        /* overridden per-archive by RootLayout inline style */
  --seal-gradient: radial-gradient(circle at center, #b91c1c 0%, #6b1010 50%, #2a0606 100%);
}
```

`src/styles/global.css:1` reads: `/* Shared design system per CLAUDE.md
§3.2 — DO NOT EDIT without updating CLAUDE.md */`. Treat that literally
— a PR that changes a hex value here without a corresponding CLAUDE.md
§3.1/§3.2 edit is a drift bug, not a style tweak.

### 1.3 Typography (CLAUDE.md §3.3)

- Serif (`var(--serif)`) for prose, hero titles, card titles.
- Mono (`var(--mono)`) for nav, metadata labels, badges, counters.
- Body: `font-size: 16px` desktop (`src/styles/global.css:40`), `15px`
  mobile via `@media (max-width: 720px) { html { font-size: 15px; } }`
  (`src/styles/global.css:47-49`).
- No third font. Fonts are self-hosted via `@fontsource/source-serif-4`
  and `@fontsource/jetbrains-mono` npm packages, imported in
  `src/layouts/BaseHead.astro` — **not** Google Fonts (that regressed
  offline-first per Phase 4 SW-07: woff2 files now ship from
  `dist/_astro/` and are precached by the service worker so fonts work
  fully offline).

### 1.4 Favicon (CLAUDE.md §3.4)

One shared SVG at `/assets/favicon.svg`, referenced identically from
`src/layouts/BaseHead.astro`:
```astro
<link rel="icon" type="image/svg+xml" href="/assets/favicon.svg" />
<link rel="apple-touch-icon" href="/assets/favicon.svg" />
```
Never add a per-archive favicon variant. Per-archive identity lives in
the seal (`.seal` element in `src/components/Nav.astro`, coloured via
`--seal-gradient`), not the favicon.

---

## 2. Astro component conventions

### 2.1 No client-side hydration, ever

Every `.astro` file in `src/components/` and `src/layouts/` carries a
comment reiterating: **NO `client:*` directives, NO framework imports
(React/Vue/Svelte)**. Interactivity ships as plain `<script is:inline>`
blocks, either inline in the component (`src/components/Nav.astro`
dropdown controller, `src/components/HeroCarousel.astro` autoplay) or
via the shared `src/scripts/invariants.ts` string injected once at the
bottom of `<body>` by `src/layouts/RootLayout.astro`:

```astro
<script is:inline set:html={INVARIANTS_JS}></script>
```

This is a **hard architectural constraint** (PROJECT.md: "pre-rendered
cards, no hydration") enforced by the `js-off` CI gate — cards must
render meaningfully with JavaScript disabled (see TESTING.md).

### 2.2 `src/scripts/invariants.ts` is a string template, not runtime code

`src/scripts/invariants.ts` exports `INVARIANTS_JS: string` built with a
`String.raw` template literal containing **plain ES2020**, not
TypeScript. The file is never imported as executable JS — Astro reads
the string at build time and inlines it verbatim via `set:html`. Rules
when editing it:
- No TypeScript syntax inside the backticks (`as` casts, type
  annotations) — they would ship to the browser and throw a parse
  error that silently breaks every subsequent handler in the same
  script block.
- No literal backtick inside the template — it would close the outer
  `String.raw` early (a real regression caught 2026-05-29, documented
  inline at `src/scripts/invariants.ts:304-309`).
- Every numbered behaviour block (1)-(8) maps 1:1 to a CLAUDE.md §7
  invariant; if you add new behaviour, update CLAUDE.md §7 first, then
  add a matching numbered comment here.

### 2.3 Card markup is a cross-language contract

`src/components/Card.astro` (wargov-only, CSV-keyed row shape) and
`src/components/CatalogCard.astro` (generic, used by the 13 non-wargov
archives with the abbreviated `catalogAssetSchema` shape) are **markup
contracts**, not just components:

- `Card.astro`'s compiled output must byte-match `scripts/normalize-
  csv.py`'s `render_card_html()` Python function — same class names,
  same attribute names, same attribute *order* — because the first 50
  wargov rows render via Astro SSR while the remaining rows render via
  Python-pre-rendered HTML strings fetched as lazy-loaded shards
  (`data/wargov-shard-N.json`) and inserted with `insertAdjacentHTML`.
  See `src/components/Card.astro:1-11`.
- `CatalogCard.astro` is reused unchanged across 13 archive port plans
  (04-06..04-18) — **never add archive-specific logic to this file.**
  Archive-specific behaviour belongs in the per-archive page
  (`src/pages/<slug>/index.astro`) or per-archive CSS
  (`src/styles/<slug>.css`).

Every card `<article>` carries this fixed `data-*` contract (both
components emit identically-named attributes):

```astro
<article
  class="arch-card"
  id={`card-${slug}`}
  data-id={rowId}
  data-row-id={rowId}
  data-idx={idx}
  data-action="open"
  data-type={rtype}
  data-agency={agency}
  data-date={date}
  data-desc={desc}
  data-region={region}
  data-category={rtype}
  data-src={source}
  data-pagefind-filter={`archive:<slug>,type:${rtype},agency:${agency}`}
  data-pagefind-meta={`title:${title},agency:${agency},date:${date}`}
>
```

`rowId` is always `r` + 1-based index zero-padded to 3 digits
(`r${String(idx + 1).padStart(3, '0')}` — `r001`, `r042`, `r222`). This
is how the lightbox looks up which card is open (`openAt(rowId)` in
`src/scripts/invariants.ts:242-264`) — **never switch this to a raw
numeric index without updating the lightbox lookup.**

### 2.4 Field aliasing — never read raw CSV/JSON keys past the frontmatter boundary

Both card components destructure verbose source keys (`row['PDF |
Image Link']`, `asset.ti`) into short local variables (`url`, `title`)
at the top of the frontmatter, with `?? ''` defaults on every field:

```ts
const title = row.Title ?? '';
const desc = row['Description Blurb'] ?? '';
```

Reasoning documented in `src/components/CatalogCard.astro:106-108`:
Astro coerces `undefined` interpolated into an attribute to the literal
string `"undefined"`, which corrupts the `data-*` contract silently.
Always default falsy-but-required string fields to `''`.

### 2.5 Never transform fidelity-sensitive text

Per CLAUDE.md §9 + the fidelity CI gate (see TESTING.md), NO
`.trim()`, `.replace()`, `.replaceAll()`, smartypants, or Unicode
normalisation on any title/description/date field, in either Astro
components or `src/content.config.ts` Zod schemas. `astro.config.mjs`
explicitly disables markdown smartypants:

```js
markdown: {
  smartypants: false,
  remarkPlugins: [],
  rehypePlugins: [],
},
```

Astro's automatic `{expr}` HTML-escaping is the ONLY transform applied
to card text — it is reversible (entity-encodes `&<>"'` only) and is
the sole XSS mitigation (no manual escaping needed in `.astro` files;
`html.escape(value, quote=True)` is the Python-side equivalent in
`scripts/normalize-csv.py`).

### 2.6 `is:global` styles — only for runtime-injected DOM

`src/components/Lightbox.astro`'s `<style is:global>` block is
required (not a stylistic choice) because `src/scripts/invariants.ts`
injects lightbox content (`<iframe>`, `<dl>`, `<img>`, `<video>`) via
`.innerHTML` at runtime — those elements never receive Astro's
`data-astro-cid-*` scope attribute, so scoped CSS would never match
them. Every selector in that global block is still prefixed with
`.lightbox` or `.lb-*` to avoid leaking into unrelated DOM (documented
at `src/components/Lightbox.astro:76-86`). Default to scoped `<style>`
everywhere else; only reach for `is:global` when the DOM you're styling
is injected outside Astro's render pass.

### 2.7 `class:list` for conditional classes

Astro's `class:list` directive is the house pattern for conditional
class application — not template-string concatenation:

```astro
<a class:list={[a.slug === archiveSlug && 'active']}>{a.name}</a>
```
(`src/components/Nav.astro:135`)

### 2.8 Props interfaces are always named and colocated

Every component declares an `interface Props { ... }` immediately above
`const { ... } = Astro.props;` in the frontmatter, with JSDoc-style
`/** ... */` comments on non-obvious fields (see `src/components/
Card.astro:30-57`, `src/components/CatalogCard.astro:61-98`). Do not
inline anonymous prop types.

### 2.9 Build-time invariant gates inside `.astro` frontmatter

`src/components/Nav.astro:42-65` demonstrates the house pattern for
data-integrity checks that must fail the *build*, not silently degrade
at runtime: read the JSON at module scope, validate an invariant
(featured-story count/order), and `throw new Error(...)` with a
descriptive message if it fails:

```ts
if (!ok) {
  throw new Error(
    `[Nav.astro] Featured-story W-3 gate failed: expected 8 featured stories with unique order 1..8, got ${FEATURED_STORIES.length} entries with orders ${JSON.stringify(orders)}`,
  );
}
```

Prefer this over a runtime `console.warn` — Astro's static-site model
means a bad build is cheap to catch and a bad deploy is expensive to
fix.

### 2.10 Type unions must stay on one line in `.astro` frontmatter

`export type ArchiveSlug = 'wargov' | 'aaro' | ... ;` in `src/layouts/
RootLayout.astro:31` and `export type PageType = 'archive' | 'story' |
'site-page';` at line 41 are each forced onto a single line, with an
explicit comment explaining why: `@astrojs/compiler 2.13.1` mis-compiles
multi-line `export type` declarations in `.astro` frontmatter, splicing
the `$$createComponent` block in between union members and producing an
`Unexpected "|"` esbuild error. If you need to add a slug to
`ArchiveSlug`, edit the single line — do not reformat it to multi-line
for readability.

---

## 3. Content collection schema patterns (`src/content.config.ts`)

- One `defineCollection` per archive slug (15 total, even though only 4
  render pages) — `getCollection('wargov')`, `getCollection('aaro')`,
  etc. Never introduce a monolithic union schema across archives.
- Two schema shapes only:
  - `catalogEnvelopeSchema` — the 14 non-wargov archives, abbreviated
    keys (`t`, `ti`, `de`, `ag`, `cat`, `date`, `region`, `l`, `u`, `s`,
    `th`) matching `scripts/templates/archive.py` output byte-for-byte.
    `catalogAssetSchema` is `.strict()` — unknown fields are a build
    error, not silently dropped (drift signal per D-02/SSG-02).
  - `wargovEnvelopeSchema` — CSV-header-keyed shape with literal spaces
    in keys (`'Release Date'`, `'PDF | Image Link'`) — never rename
    these keys for ergonomics; the Phase 5 scrape pipeline reads the
    same CSV headers verbatim.
- **No `z.transform()` or `z.preprocess()` on any text field** — this is
  the single most load-bearing rule in the file (see the "Fidelity
  guard" docblock at `src/content.config.ts:16-24`). A transform here
  is a fidelity bug even if it looks like an improvement (e.g. trimming
  whitespace, normalising smart quotes).
- Loader is always Astro 5's `file()` loader over `data/<slug>.json`,
  entries-object form with a single `"v1"` key:
  ```json
  { "v1": { "schemaVersion": 1, "slug": "<slug>", "assets": [], "stats": {} } }
  ```
- `data/<slug>.json` files are **committed, never gitignored** — `pnpm
  prebuild` (→ `python3 scripts/normalize-csv.py`) regenerates
  `data/wargov.json` from `uap-data.csv` / `uap-release001.csv`, and the
  per-archive `scripts/normalize-<slug>.py` scripts regenerate the rest.

---

## 4. JS invariants — CLAUDE.md §7 (source of truth: `src/scripts/invariants.ts`)

Every behaviour below is numbered in the source file; keep the numbers
in sync if you add a ninth invariant.

1. **Hamburger toggle** — `#nav-toggle` ↔ `#primary-nav`. Guarded by
   `navToggle.dataset.wired` so both `Nav.astro`'s own copy (component-
   isolation contexts) and the global `invariants.ts` copy can run
   without double-binding.
2. **Unified lightbox** — `openAt(rowIdOrIdx)`, `navLb(delta)`,
   `closeLb()`. Prefers stable `data-row-id` lookup over numeric index
   (`lbList.findIndex(x => x.rowId === rowIdOrIdx)`), wraps via modulo.
   Arrow keys (`←`/`→`), `Escape`, and touch swipe (> 50 px horizontal,
   < 800 ms) all route through `navLb`/`closeLb`.
3. **Image fallback** — `<img data-fallback="...">` swaps `src` on
   `error` event (capture-phase delegated listener, `WeakSet`-guarded
   against re-firing). Astro components emit `onerror="this.onerror=
   null;this.src=this.dataset.fallback||''"` as belt-and-braces on top
   of the delegated listener.
4. **Video dual-source** — `<video>` gets TWO `<source>` children (local
   + remote) whenever both exist. **Never add `crossorigin="anonymous"`
   ** — it breaks CloudFront/R2 playback (CLAUDE.md §11 don't). A
   runtime sanity pass in `invariants.ts` injects a missing second
   `<source>` from `data-remote` if a page forgets the rule.
5. **PDF lightbox** — iframe for local files AND R2-hosted PDFs
   (`assets.realufo.org` — Phase 4 D-01 moved PDFs to R2, which is
   iframable); true cross-origin remote PDFs (e.g. GitHub Release URLs
   with `Content-Disposition: attachment`) open in a new tab instead.
6. **Card open delegate** — `data-action="open"` on both the `<a
   class="btn-open">` and the parent `<article>`; a single delegated
   click listener intercepts `a[data-action="open"]` first, falls back
   to `article[data-action="open"]` for archives whose cards have no
   thumbnail/anchor (PDF/VID-only cards). Button clicks
   (`.btn-download`, `.btn-source`, `.btn-open`) are excluded from the
   article-level delegate so they keep native anchor behaviour.
7. **`/` focuses search** — global `keydown` listener; bails if the
   user is already typing in an `input`/`textarea`/`contenteditable`.
   Selector union: `input[type="search"], input[name="q"], #q,
   #arch-search`.
8. **`?q=` persistence** — on load, reads `?q=` and populates + fires an
   `input` event on the matched search field; on `input`, debounces
   180 ms then `history.replaceState`s the encoded query into the URL.
   No-ops gracefully when no search input exists on the page (e.g.
   wargov, which has no cross-archive search input by design).

A ninth, undocumented-in-CLAUDE.md-but-load-bearing behaviour lives in
the same file: the **arch-controls-bar scroll-direction reveal**
(`src/scripts/invariants.ts:509-566`) — hides the sticky filter bar on
scroll-down, shows it on scroll-up, gated on the `.arch-grid` element
existing and the lightbox being closed.

---

## 5. Mobile-first specifics — CLAUDE.md §8

- **360 px is the canonical first viewport.** Every layout rule in
  `src/styles/global.css` is written mobile-first (base rule = mobile;
  `@media (min-width: 720px)` widens, not the inverse) — see
  `src/styles/global.css:371` for the one `min-width` breakpoint vs. the
  many `max-width: 720px` narrowing rules.
- **Hamburger below 720 px**, inline nav above. Breakpoint constant
  appears as `(max-width: 719.98px)` in `src/components/Nav.astro:259`
  and `src/styles/global.css:330` — use `719.98px`, not `720px`, to
  avoid a 1px double-match with the `min-width: 720px` rule.
- **44×44 px touch targets** — grep `src/styles/global.css` for `/*
  CLAUDE.md §8 — 44px touch target */` comments (11 call sites as of
  this analysis: nav links via `padding: 12px 0`, lightbox nav buttons,
  carousel arrows, filter controls). Any new interactive element needs
  either `min-height: 44px` + `min-width: 44px` or padding that achieves
  the same rendered hit area.
- **Lightbox nav buttons**: 52×52 desktop, 40×40 mobile
  (`@media (max-width: 720px)` in `src/components/Lightbox.astro:311-
  319`), edge-pinned via `left/right: 8px`.
- **`overflow-wrap: anywhere`** on long titles — `src/components/
  Lightbox.astro:237` (`.lb-meta-panel dd`), applied anywhere a title or
  free-text field could overflow its container.
- **`body { overflow-x: hidden; }`** as the last-resort guard rail
  (`src/styles/global.css:42`) — never remove this even if a specific
  overflow bug gets fixed at the source; it's defence-in-depth.
- **Tab strips wrap, never horizontal-scroll.** No `.arch-controls-bar`
  or `.tabs` rule anywhere uses `overflow-x: auto` / `overflow-x:
  scroll` — verify this holds before adding a new filter UI.

---

## 6. Content rules — CLAUDE.md §9

- **No filler descriptions.** `{desc && <p class="card-desc">{desc}
  </p>}` — the paragraph is omitted entirely when `desc` is empty
  (`src/components/Card.astro:132`, `src/components/
  CatalogCard.astro:155`). Never substitute a placeholder string like
  "Click to play" or "View file". The same rule governs the lightbox
  meta panel (`renderMeta()` in `src/scripts/invariants.ts:98-111` only
  emits a `<p>` when `a.desc` is truthy) and `.lb-meta-panel:empty {
  display: none; }` (`src/components/Lightbox.astro:202-204`).
- **Verbatim official text** for hero ledes, sub-heads, FAQ answers,
  license footers. This is CI-enforced — see `scripts/verify-
  fidelity.py` in TESTING.md. Never run text through `.strip()` beyond
  leading/trailing whitespace, never fold smart quotes, never
  re-encode.
- **Public-domain attribution per jurisdiction** — `src/components/
  Footer.astro`'s `LICENSE` map is the single source (15-wide, though
  only the US-jurisdiction 4 active archives surface): all of `wargov`,
  `aaro`, `nasa`, `nara` share `'17 U.S.C. § 105'`. Every string in that
  map is a direct copy from CLAUDE.md §9 — do not paraphrase when
  adding a new archive's license string.
- **Header vs footer `↗` rule (ties into §11 below):** internal
  archive-to-archive links in `Nav.astro` never carry `↗`; external
  official-source links in `Footer.astro`'s Source column always do
  (`{primarySource.name} ↗`). `src/components/Nav.astro:18-22`
  documents the distinction explicitly, including the one exception —
  the internal "All stories →" uses a different glyph (U+2192, single
  right arrow) which is NOT the forbidden external marker (U+2197).

---

## 7. House-style don'ts — CLAUDE.md §11 (verified against current code)

| Don't | Where it's enforced / verified |
|---|---|
| Inline `↗` inside header nav links | `src/components/Nav.astro` never emits `↗`; only `Footer.astro`'s Source column does |
| "OFFLINE MIRROR" banner | Absent from `RootLayout.astro` / `Nav.astro` — removed by design |
| `crossorigin="anonymous"` on `<video>` | Absent from `src/scripts/invariants.ts`'s video-render branch (kills CloudFront/R2 playback) |
| Single-`<source>` `<video>` when both local + remote exist | Invariant (4) in `src/scripts/invariants.ts:182-192` always emits both when available, plus a runtime sanity-check pass |
| Filler description sentences | `{desc && <p>}` guards throughout `Card.astro` / `CatalogCard.astro` / `renderMeta()` |
| `gh release upload` from main without checking the previous upload finished | Operational rule — no code enforcement; respect manually |
| Skipping mobile testing (360 px canonical) | `tests/visual-regression.spec.ts` VIEWPORTS array puts `[360, 800]` first |
| Force-pushes to main | Operational rule — no code enforcement; respect manually |
| Touching `uap-release001.csv` / `uap-data.csv` | `scripts/normalize-csv.py` opens both **read-only** and runs `_assert_csv_unchanged()` after every write, exiting 1 on any diff |
| Calling archive pages "mirrors" in user-facing copy | `Footer.astro`'s About column says "archive", never "mirror" |

---

## 8. Naming patterns

**Astro/TS files (`src/`):**
- Components: `PascalCase.astro` (`Card.astro`, `CatalogCard.astro`,
  `HeroCarousel.astro`, `StructuredData.astro`).
- Layouts: `PascalCase.astro` under `src/layouts/`.
- Pages: `kebab-case` or archive-slug directories mirroring the URL
  (`src/pages/aaro/index.astro` → `/aaro/`, `src/pages/stories/
  [slug].astro` → `/stories/<slug>/`).
- Scripts (non-component logic): `camelCase.ts` under `src/scripts/`
  (`invariants.ts`, `jsonldSchemas.ts`, `extractLegacyBody.ts`).
- CSS: `<slug>.css` per archive under `src/styles/`, plus `global.css`
  (shared) and `site-pages.css` / `stories.css` (cross-archive
  informational pages).

**Python scripts (`scripts/`):**
- `normalize-<slug>.py` — CSV/JSON → content-collection JSON
  normalisers (the Phase 3/4 SSG data pipeline; `normalize-csv.py` is
  wargov's, `normalize-aaro.py` / `normalize-nara.py` / `normalize-
  nasa.py` / `normalize-nz.py` / `normalize-uruguay.py` are per-archive).
- `build-<slug>.py` — legacy dormant-archive builders, retired from the
  active surface but preserved for `.github/workflows/scrape.yml`
  (Phase 5 SCRP) — see `scripts/verify-python-retired.sh` for the exact
  whitelist (`build-brazil.py`, `build-chile.py`, `build-geipan.py`,
  `build-uk.py`, `build_batch3.py`, plus `build-{api,cases,feeds,geo,
  og,pages-index,stories,sw}.py`).
- `verify-*.py` / `verify-*.sh` — CI gate scripts (stdlib-only Python;
  see TESTING.md).
- `_archive_common.py`, `_mirror_shared.py`, `_release_manifest.py`,
  `_site_template.py` — underscore-prefixed shared helper modules,
  imported by the `build-*`/`normalize-*` scripts.
- `dl-<slug>.sh` — per-archive idempotent downloader shell scripts.

**Data attributes:** always `data-kebab-case` (`data-row-id`, `data-
pagefind-filter`), never `data-camelCase` — matches HTML5 convention and
keeps Astro's dataset access (`el.dataset.rowId`) predictable.

**Row/card IDs:** `r` + 1-based zero-padded 3-digit index (`r001`..
`r222` for wargov's 222 rows). Never introduce a second ID scheme for
the same card set.

---

## 9. Comments and documentation style

- Every non-trivial file opens with a block comment naming: (a) what
  the file is, (b) which CLAUDE.md section or Decision ID (`D-NN`) it
  implements, and (c) any cross-file contract it must stay in sync
  with. See the top of `src/components/Card.astro`, `src/scripts/
  invariants.ts`, `scripts/normalize-csv.py` for the pattern.
- Inline comments cite the CLAUDE.md section number directly (`/*
  CLAUDE.md §8 — 44px touch target */`) rather than paraphrasing the
  rule — this makes `grep -rn "CLAUDE.md §"` a working audit tool across
  the codebase.
- Decision IDs (`D-12`, `D-27`, etc.) and Threat IDs (`T-03-11`) appear
  throughout comments, referencing `.planning/phases/*/CONTEXT.md` and
  `.planning/research/PITFALLS.md`. When editing code that carries one
  of these tags, check whether the referenced decision doc needs a
  matching update.
- Python docstrings (module-level, triple-quoted) follow a fixed shape:
  one-line summary, blank line, prose description, then `###`-headed
  subsections (`Invariants`, `Threat mitigations`, `CLI`, `Exit codes`).
  See `scripts/normalize-csv.py:1-108` and `scripts/verify-fidelity.py:
  1-48` as reference templates for any new verification/build script.

---

## 10. Error handling

- **Astro build-time:** throw `Error` with a descriptive message from
  frontmatter code when an invariant can't hold (`src/components/
  Nav.astro:58-64`'s featured-story gate). Zod schema violations in
  `src/content.config.ts` propagate as hard `ZodError` build failures
  — no silent drop-on-validation-failure (D-03).
- **Client-side JS (`invariants.ts`):** defensive `if (!el) return;`
  guards before every DOM operation; `try { } catch (_) { /* ignore */
  }` around browser APIs that may be unavailable (Fullscreen API,
  `history.replaceState`) rather than feature-detection branches.
- **Python scripts:** `argparse` + explicit exit codes documented in
  each script's module docstring (0 = success, 1 = drift/violation, 2 =
  missing input/fetch error) — never a bare `sys.exit(1)` without a
  documented meaning. `verify-fidelity.py`, `verify-lighthouse-
  budgets.py`, and `normalize-csv.py --check` all follow this 0/1/2
  convention.
- **Shell scripts:** `set -euo pipefail` (or `set -uo pipefail` when a
  script needs to continue past a failed `curl` to count failures, e.g.
  `scripts/verify-redirects.sh:29`) at the top of every `.sh` file.

---

## 11. Module design / where to add new code

- **New archive:** add one `TONE` entry (`RootLayout.astro`), one
  `LICENSE` + `SOURCE_URLS` entry (`Footer.astro`), one `ARCHIVES`/
  `BRAND` entry (`Nav.astro`) if activating it in the nav, one
  `defineCollection` entry (`src/content.config.ts`), one `data/<slug>
  .json`, and a `scripts/normalize-<slug>.py`. Re-use `CatalogCard.astro`
  unmodified; write a new `src/pages/<slug>/index.astro` page.
- **New page-level content type** (like Phase 04.1's Stories / Site
  Pages): add a JSON data file under `src/data/`, a Zod-free plain
  import (not a content collection — `src/data/stories.json` and
  `src/data/site-pages.json` are consumed as raw JSON imports, not
  Astro content collections), and wire `pageType` through
  `RootLayout.astro` if the new content needs to bypass the
  active/dormant Pagefind gate.
- **New shared UI behaviour:** add to `src/scripts/invariants.ts` as a
  new numbered block, document it in CLAUDE.md §7 first.
- **New CI verification:** stdlib-only Python (`argparse`, `json`,
  `pathlib`, `re`, `sys`) matching the `verify-*.py` convention, OR a
  new Playwright spec under `tests/*.spec.ts` matching the existing
  `test.describe.parallel(...)` + independent-test-per-assertion
  pattern (see TESTING.md).

---

*Convention analysis: 2026-07-11*
