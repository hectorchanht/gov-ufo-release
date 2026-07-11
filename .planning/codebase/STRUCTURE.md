<!-- refreshed: 2026-07-11 -->
# Codebase Structure

**Analysis Date:** 2026-07-11

**Stale-doc warning:** the previous version of this file (2026-05-25)
predates the SSG migration + the Phase 04.1 legacy reorg. Root-level
per-archive directories (`aaro/`, `geipan/`, `uk/`, etc.) no longer hold the
site's HTML — that content moved to `legacy/<slug>/`. This rewrite is
verified against `git ls-files` and the live directory tree as of 2026-07-11.

## Directory Layout

```
war-gov-ufo-release/                  (remote canonical repo name: gov-ufo-archive)
├── src/                              # Astro source — the 4 ACTIVE archives + shared chrome
│   ├── pages/                        # File-based routes
│   │   ├── index.astro               # wargov (/) — War.gov/PURSUE
│   │   ├── aaro/index.astro          # /aaro/
│   │   ├── nasa/index.astro          # /nasa/
│   │   ├── nara/index.astro          # /nara/
│   │   ├── nz/index.astro            # /nz/ (dormant, but Astro-owned)
│   │   ├── uruguay/index.astro       # /uruguay/ (dormant, but Astro-owned)
│   │   ├── stories/index.astro       # /stories/ — curated case index
│   │   ├── stories/[slug].astro      # /stories/<slug>/ — legacy-HTML extraction route
│   │   ├── search.astro              # /search/ — Pagefind UI mount
│   │   ├── about.astro, foia.astro, glossary.astro,
│   │   │   map.astro, timeline.astro, whatsnew.astro   # 6 site-pages (legacy-HTML extraction)
│   ├── layouts/
│   │   ├── RootLayout.astro          # page shell, TONE map, ArchiveSlug/PageType types
│   │   └── BaseHead.astro            # shared <head>, fonts, SW registration
│   ├── components/                   # Card, CatalogCard, Nav, Footer, HeroCarousel, Lightbox, StructuredData
│   ├── scripts/                      # invariants.ts, extractLegacyBody.ts, jsonldSchemas.ts (non-.astro TS helpers)
│   ├── styles/                       # global.css + per-archive css (wargov/aaro/nara/nasa/nz/uruguay/stories/site-pages)
│   ├── data/                         # stories.json, site-pages.json — build-time nav/route manifests
│   ├── content.config.ts             # Content Collections schema/registry (15 archives)
│   └── sw.ts                         # Workbox injectManifest source → dist/sw.js
├── data/                             # Content-collection JSON payloads — data/<slug>.json (15 files)
│                                      # + data/wargov-shard-N.json (build-time source, read via import.meta.glob)
├── public/                           # Astro static passthrough → copied verbatim to dist/ root
│   ├── data/                         # RUNTIME mirror of shard/catalog JSON (fetched client-side; see ARCHITECTURE.md constraint)
│   ├── assets/favicon.svg
│   └── _headers, robots.txt, .well-known/security.txt
├── legacy/                           # Git-tracked pre-Astro HTML — 11 dormant archives + partial-port sub-pages + informational pages
│   ├── <dormant-slug>/                # geipan, uk, brazil, chile, argentina, canada, italy, nz, peru, spain, uruguay
│   │   ├── index.html                 # (nz/uruguay: NOT copied to dist — Astro owns those routes)
│   │   ├── assets/, story.html, pdfs/ (pdfs/ dirs are gitignored inside legacy/ too — see chile, geipan, uk)
│   ├── aaro/, nara/, nasa/            # partial-port: sub-pages only (index.html NOT copied — Astro owns it)
│   ├── about.html, foia.html, glossary.html, map.html, timeline.html, whatsnew.html   # site-page sources
│   └── 404.html, donate.html, embed.html, compare.html, stats.html                    # parked / 410-redirected pages
├── scripts/                          # Build, normalise, scrape, and CI-verification scripts (Python + bash)
│   ├── normalize-csv.py              # prebuild — CSV → data/wargov*.json (SURVIVING)
│   ├── normalize-{aaro,nara,nasa,nz,uruguay}.py   # per-archive normalisers (SURVIVING)
│   ├── copy-legacy-archives.sh       # postbuild — ships legacy/ → dist/, runs Pagefind + sitemap (SURVIVING)
│   ├── build-redirects.py            # URL-CONTRACT.txt → _redirects (quality-gates.yml drift gate) (SURVIVING)
│   ├── dl-<slug>.sh                  # per-archive idempotent downloader (SURVIVING, local dev only)
│   ├── scrape-<slug>.py, spider.py   # Phase 5 SCRP scrape-automation scope (SURVIVING)
│   ├── verify-*.{py,sh}              # CI verification gates (SURVIVING)
│   ├── build-{brazil,chile,geipan,uk,api,cases,feeds,geo,og,pages-index,stories,sw}.py,
│   │   build_batch3.py               # scrape.yml consumers — retired when scrape.yml is rewritten in Phase 5 (SURVIVING for now)
│   └── (build-wargov.py, build-details.py, sync-nav.py, sync-footer.py,
│        build-{aaro,nasa,nara,nz,uruguay,argentina,italy,canada,peru,spain}.py,
│        parse-aaro.py, extract-evidence.py)         # RETIRED — Plan 04-20; must NOT reappear (see scripts/verify-python-retired.sh)
├── tests/                            # Playwright specs + visual baselines + fixtures
├── .planning/                        # GSD planning docs (this map lives at .planning/codebase/)
├── .github/workflows/                # deploy-cf-pages.yml, lighthouse.yml, links.yml, quality-gates.yml, r2-sync.yml, scrape.yml
├── workers/akamai-spike/             # standalone Cloudflare Worker experiment (Phase 5 scrape spike) — NOT part of the site build
├── bundles/                          # PDF/zip source bundles — mostly gitignored (>100 MB rule); restored via sync.sh
├── slideshow/, slideshow-2/, slideshow-3/   # hero-carousel + VID-thumbnail imagery, git-tracked (small, frequently shown)
├── assets/                           # shared favicon.svg + misc images (root-level, tracked)
├── api/, feeds/                      # legacy JSON/XML endpoints consumed by /whatsnew/, /timeline/, /map/ (copied by postbuild)
├── aaro/, nasa/, nara/, nz/, uruguay/,
│   brazil/, chile/, geipan/, uk/, argentina/,
│   canada/, italy/, peru/, spain/    # LOCAL-ONLY gitignored download caches (pdfs/, videos/, .cache/) — ZERO git-tracked files, NOT shipped
├── dist/                             # build output (gitignored) — deploy artifact for Cloudflare Pages
├── astro.config.mjs                  # Astro 5 config: cloudflare adapter, AstroPWA injectManifest, sw-relocator integration
├── src/content.config.ts             # (see src/ above)
├── package.json                      # prebuild/build/postbuild pnpm scripts
├── uap-data.csv, uap-release001.csv  # source-of-truth CSVs — NEVER edit programmatically (CLAUDE.md §11)
├── URL-CONTRACT.txt                  # canonical route snapshot — drift-gated by quality-gates.yml
├── _redirects, _headers              # Cloudflare Pages routing/headers config (generated / hand-maintained)
└── CLAUDE.md                         # master spec — read before changing anything
```

## Directory Purposes

**`src/pages/`:**
- Purpose: Astro file-based routes — the ENTIRE Astro-rendered surface of the site
- Contains: `.astro` files only; no `.ts`/`.js` route handlers (this is `output: 'static'`, no API routes)
- Key files: `src/pages/index.astro` (wargov, largest page — 867 lines), `src/pages/stories/[slug].astro` (dynamic route via `getStaticPaths()`)

**`src/layouts/`:**
- Purpose: the ONE page shell (`RootLayout.astro`) and ONE shared `<head>` (`BaseHead.astro`) every route composes
- Contains: 2 `.astro` files
- Key files: `src/layouts/RootLayout.astro` (also exports the `ArchiveSlug` / `PageType` TypeScript types consumed across `src/components/` and `src/pages/`)

**`src/components/`:**
- Purpose: reusable render units shared across archive pages
- Contains: `Card.astro` (wargov-only), `CatalogCard.astro` (generic, used by aaro/nasa/nara/nz/uruguay), `Nav.astro`, `Footer.astro`, `HeroCarousel.astro`, `Lightbox.astro`, `StructuredData.astro`
- Key files: `src/components/Nav.astro` (contains the ACTIVE-archive cross-nav array + Stories/About dropdown controller script), `src/components/Footer.astro` (contains the per-jurisdiction LICENSE map)

**`src/scripts/`:**
- Purpose: plain-TypeScript build-time or shared-runtime helpers that are NOT Astro components
- Contains: `invariants.ts` (CLAUDE.md §7 JS invariants, exported as a template-literal string `INVARIANTS_JS` and injected via `set:html`), `extractLegacyBody.ts` (legacy HTML extraction cascade + chrome scrubber + URL rewrite table), `jsonldSchemas.ts` (JSON-LD schema helpers)
- Key files: `src/scripts/extractLegacyBody.ts` — the `CASCADE` array here is the single source of truth for which legacy files can become stories/site-pages

**`src/data/`:**
- Purpose: build-time manifest JSON that drives navigation + the legacy-extraction routes
- Contains: `stories.json` (curated story entries: slug, title, archive, legacyPath, featured, order, incidentDate), `site-pages.json` (6 informational-page entries: slug, title, subtitle, legacyPath, preserveScripts)
- Key files: both files are read directly by `Nav.astro`/`Footer.astro` (stories) and by `src/pages/{about,foia,glossary,map,timeline,whatsnew}.astro` (site-pages) — editing either requires no code change to add/remove/reorder an entry, only respecting the `Nav.astro` build-time invariant (exactly 8 featured stories, unique order 1..8)

**`src/styles/`:**
- Purpose: global palette/typography (`global.css`) + one CSS file per Astro-rendered archive (scoped overrides, NOT full re-themes — tone colours come from `RootLayout`'s inline `--caution`/`--seal-gradient` CSS vars, not these files)
- Contains: `global.css`, `wargov.css`, `aaro.css`, `nara.css`, `nasa.css`, `nz.css`, `uruguay.css`, `stories.css`, `site-pages.css`

**`data/` (repo root, NOT `src/data/`):**
- Purpose: Content Collection payloads — one JSON per archive, consumed by Astro's `file()` loader at BUILD time via `src/content.config.ts`
- Contains: `wargov.json` + `wargov-shard-{2..6}.json` (sharded, large), `aaro.json` (+ `aaro-shard-1.json`), `nara.json` (+ `nara-shard-1.json`), `nasa.json`, `nz.json`, `uruguay.json`, and 9 near-empty skeleton files for the wholesale-dormant archives (`argentina.json`, `brazil.json`, `canada.json`, `chile.json`, `geipan.json`, `italy.json`, `peru.json`, `spain.json`, `uk.json` — schema-valid empty `assets: []` placeholders, Phase 5 SCRP scope to populate)
- Generated: yes, by `scripts/normalize-csv.py` (wargov) / `scripts/normalize-<slug>.py` (aaro, nara, nasa, nz, uruguay)
- Committed: yes — always committed, never gitignored (`data/README.md` documents the envelope shape + writer-responsibility table)

**`public/`:**
- Purpose: Astro's static-passthrough directory — everything here is copied byte-for-byte to `dist/` root
- Contains: `public/data/` (RUNTIME-fetched mirror of shard/catalog JSON — see ARCHITECTURE.md's "two parallel data copies" constraint), `public/assets/favicon.svg`, `public/_headers`, `public/robots.txt`, `public/.well-known/security.txt`
- Generated: partially — `public/data/*.json` is written by the same normalisers that write repo-root `data/*.json`
- Committed: yes

**`legacy/`:**
- Purpose: git-tracked home for every pre-Astro archive page — created by the Phase 04.1 reorg (commits `6504f42`, `c9fe513`, `50f8596`) to get 89 legacy HTML files + their asset subdirectories OUT of the repo root and into one predictable subtree
- Contains: per-slug subdirectories (`legacy/<slug>/`) for all 15 archives except wargov (which never had a `legacy/wargov/` — Astro owns `/` outright) — but `legacy/<slug>/index.html` is only actually SHIPPED to `dist/` for the 9 wholesale-dormant slugs; for aaro/nara/nasa/nz/uruguay the `index.html` is a fossil that `copy-legacy-archives.sh` explicitly skips (Astro owns those index routes)
- Key files: `legacy/about.html`, `legacy/foia.html`, `legacy/glossary.html`, `legacy/map.html`, `legacy/timeline.html`, `legacy/whatsnew.html` (site-page sources, extracted by `src/scripts/extractLegacyBody.ts`); `legacy/aaro/*.html` (14 case narratives + `details.html` master index — the largest partial-port sub-page set)
- Generated: no (hand-authored HTML from the pre-migration era, moved not regenerated)
- Committed: yes (117 tracked files as of 2026-07-11)

**`scripts/`:**
- Purpose: everything outside the Astro build graph — CSV/JSON normalisation, legacy shipping, scrape automation, CI verification
- See the "Scripts inventory" section below for the full surviving-vs-retired breakdown

**Root-level per-archive directories (`aaro/`, `nasa/`, `nara/`, `nz/`, `uruguay/`, `brazil/`, `chile/`, `geipan/`, `uk/`, `argentina/`, `canada/`, `italy/`, `peru/`, `spain/`):**
- Purpose: LOCAL-ONLY download caches populated by `scripts/dl-<slug>.sh` — hold `pdfs/`, `videos/`, `.cache/` subdirectories
- Contains: nothing git-tracked (`git ls-files <dir>/` returns 0 files for every one of these, verified 2026-07-11)
- Generated: yes, by `scripts/dl-<slug>.sh`, entirely gitignored
- Committed: no — do not confuse these with `legacy/<slug>/`, which holds the actual shipped HTML

**`bundles/`:**
- Purpose: source PDF/zip bundles behind the GitHub Releases binary CDN
- Contains: `Release_1/`, `release_02_document_bundle/`, `uapvideos/`, `uap052226/` + their `.zip` archives
- Generated: no (downloaded original source material)
- Committed: partially — `.zip` files and PDF subdirectories are gitignored per CLAUDE.md §5.2; only small non-PDF assets survive in git

**`slideshow/`, `slideshow-2/`, `slideshow-3/`:**
- Purpose: hero-carousel imagery for Release 01 / 02 / 03 respectively, plus VID-card thumbnail hydration targets
- Contains: `.jpg`/`.png` images, git-tracked (30 / 10 / 10 tracked files respectively)
- Generated: no
- Committed: yes (images are small — CLAUDE.md §5.2 tracks images, ignores PDFs/videos)

**`api/`, `feeds/`:**
- Purpose: legacy JSON/XML endpoints consumed by the extracted `/whatsnew/`, `/timeline/`, `/map/` site-pages' preserved in-body scripts
- Contains: `api/all.json`, `api/stats.json`, `api/by-archive.json`, `api/geo.json`, `api/pages-index.json`; `feeds/<slug>.xml` + `feeds/all.xml`
- Generated: by `scripts/build-{api,feeds,geo,pages-index}.py` (scrape.yml consumers)
- Committed: yes (small JSON/XML)

**`tests/`:**
- Purpose: Playwright specs + fixtures + visual-regression baselines
- Contains: `*.spec.ts` (js-off, lightbox, pagination, r2-urls, search, sw, tone-colours), `fidelity-samples.json` (115 byte-exact content samples), `tone-colours-fixture.json`, `visual-baselines/<slug>-<viewport>.png` (4 viewports × 15 archives)
- Key files: `tests/playwright.config.ts`

**`.planning/`:**
- Purpose: GSD milestone/phase/plan tracking — NOT part of the shipped site
- Contains: `PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md`, `codebase/` (this directory), `phases/`, `decisions/`, `research/`, `quick/`, `debug/`, `todos/`, `spikes/`
- Key files: `.planning/STATE.md` (current milestone position), `.planning/decisions/python-build-retired.md` (ADR for the scripts retirement — read before touching `scripts/`)

**`workers/akamai-spike/`:**
- Purpose: standalone Cloudflare Worker used for a Phase 1 spike experiment (egress-IP flagging test against Akamai-fronted source sites) — has its OWN `package.json`/`wrangler.toml`, entirely separate from the Astro site build
- Contains: `src/index.ts`
- Generated: no
- Committed: yes

## Key File Locations

**Entry Points:**
- `src/pages/index.astro`: wargov archive at `/` — largest and most complex page (867 lines)
- `src/pages/{aaro,nasa,nara}/index.astro`: the other 3 ACTIVE archives
- `scripts/copy-legacy-archives.sh`: postbuild entry point — ships everything NOT built by Astro
- `scripts/normalize-csv.py`: prebuild entry point — sole writer of wargov's Content Collection data

**Configuration:**
- `astro.config.mjs`: Astro 5 + Cloudflare adapter + AstroPWA (injectManifest) + custom `swRelocator` integration (works around a CF-adapter/PWA-plugin path conflict — see the inline comment block at the top of the file)
- `src/content.config.ts`: Content Collections schema — the AUTHORITATIVE field-name/type contract for every archive's data
- `package.json`: `prebuild`/`build`/`postbuild` pnpm lifecycle hooks wire the whole pipeline together
- `URL-CONTRACT.txt` + `scripts/build-redirects.py` + `_redirects`: canonical-route drift gate (CI-enforced via `quality-gates.yml`)
- `.lighthouserc.json` / `.lighthouserc.cf.json`: Lighthouse CI budget config (HARD-gated per Plan 04-20)

**Core Logic:**
- `src/scripts/extractLegacyBody.ts`: legacy-HTML → Astro-page extraction cascade (stories + site-pages)
- `src/components/Card.astro` / `scripts/normalize-csv.py`'s `render_card_html()`: LOCKED HTML-parity pair for wargov cards (D-10)
- `src/layouts/RootLayout.astro`: tone-colour map, active/dormant gate, Pagefind body-marker logic
- `src/sw.ts`: service-worker runtime caching strategy (5 tiers)

**Testing:**
- `tests/*.spec.ts`: Playwright specs
- `tests/fidelity-samples.json` + `scripts/verify-fidelity.py`: content-fidelity byte-match gate
- `scripts/verify-python-retired.sh`: CI invariant guard — fails if a retired Python builder reappears
- `scripts/verify-redirects.sh` / `scripts/verify-lighthouse-budgets.py`: additional CI gates

## Naming Conventions

**Files:**
- Astro components: PascalCase — `Card.astro`, `CatalogCard.astro`, `HeroCarousel.astro`
- Astro routes: lowercase, matches the URL path — `index.astro`, `aaro/index.astro`, `stories/[slug].astro`
- Build/normalise scripts: kebab-case with a verb prefix — `normalize-csv.py`, `build-redirects.py`, `dl-aaro.sh`, `verify-fidelity.py`
- Private/shared Python helper modules: leading underscore — `scripts/_archive_common.py`, `scripts/_release_manifest.py`, `scripts/_site_template.py`

**Directories:**
- One directory per archive slug at the ACTIVE-route level (`src/pages/aaro/`) and at the legacy level (`legacy/aaro/`) — the slug is always the CLAUDE.md §2 table's canonical slug, never a display name
- `src/scripts/` (TypeScript build-time helpers) is distinct from repo-root `scripts/` (Python/bash build pipeline) — do not conflate the two when searching for "the scripts"

## Where to Add New Code

**New Astro page/route:**
- Primary code: `src/pages/<route>.astro` or `src/pages/<slug>/index.astro` for a new archive
- If porting a dormant archive to Astro: follow the `nz`/`uruguay` pattern (`CatalogCard.astro` + pagination + Lightbox), remove the slug from `copy-legacy-archives.sh`'s dormant-copy loop, and update `RootLayout.astro`'s `ACTIVE_ARCHIVES` set only if it should also appear in Nav/Footer/search (re-activation is explicitly a 3-line edit per CLAUDE.md §2 note)

**New curated story or site-page:**
- Add an entry to `src/data/stories.json` (respecting the `{1..8}` featured-order invariant if `featured: true`) or `src/data/site-pages.json`
- If the source legacy HTML doesn't match an existing `CASCADE` selector in `src/scripts/extractLegacyBody.ts`, audit the file and add a `filePath`-guarded cascade entry — do NOT add a generic `<body>` fallback (see ARCHITECTURE.md anti-patterns)

**New reusable component:**
- Implementation: `src/components/<Name>.astro`
- If it needs the `ArchiveSlug` type, import it from `src/layouts/RootLayout.astro` (single source of truth) — do not redeclare the union

**New per-archive data:**
- Content Collection payload: `data/<slug>.json`, matching `catalogEnvelopeSchema` in `src/content.config.ts` (or extend the schema first if the archive needs new fields — expect `.strict()` to reject unknown fields until you do)
- If the page will lazy-shard content client-side, also write the runtime-fetch mirror into `public/data/<slug>.json` (or `public/data/<slug>-shard-N.json`) — see the ARCHITECTURE.md "two parallel data copies" constraint

**Utilities:**
- Shared TypeScript helpers used by `.astro` frontmatter: `src/scripts/`
- Shared Python helpers used by multiple normaliser/build scripts: `scripts/_*.py`

## Special Directories

**`dist/`:**
- Purpose: Astro build output — the actual Cloudflare Pages deploy artifact
- Generated: yes (by `pnpm build`, which runs prebuild → `astro build` → postbuild)
- Committed: no (gitignored)

**`.astro/`:**
- Purpose: Astro's type-generation cache (`.astro/types.d.ts`, referenced by `tsconfig.json`)
- Generated: yes (by `astro sync` / `astro build`)
- Committed: no (gitignored — must stay generated, per the `.gitignore` comment)

**`node_modules/`, `.wrangler/`, `.lighthouseci/`, `test-results/`, `playwright-report/`:**
- Purpose: standard tool caches/output (pnpm, Wrangler local dev, Lighthouse CI, Playwright)
- Generated: yes
- Committed: no

**`.claude/`:**
- Purpose: Claude Code project skills/config (also seen at `.claude/worktrees/agent-*` — stray git-worktree checkouts from prior agent sessions, NOT part of the site)
- Generated: mixed
- Committed: partially (working-tree state was untracked at session start per git status)

---

## Scripts Inventory (Plan 04-20 retirement — verified against `scripts/verify-python-retired.sh`)

**SURVIVING (whitelisted, present today):**
- `scripts/normalize-csv.py`, `scripts/normalize-{aaro,nara,nasa,nz,uruguay}.py` — Content Collection JSON writers
- `scripts/copy-legacy-archives.sh` — ships 11 dormant + partial-port sub-pages into `dist/`; retires only when dormant archives are hard-deleted in a future milestone
- `scripts/build-redirects.py` — `URL-CONTRACT.txt` → `_redirects` (quality-gates.yml drift gate)
- `scripts/spider.py` — Phase 5 SCRP scope (generic source-page crawler)
- `scripts/build-{brazil,chile,geipan,uk,api,cases,feeds,geo,og,pages-index,stories,sw}.py`, `scripts/build_batch3.py` — still referenced by `.github/workflows/scrape.yml`; retire when that workflow is rewritten in Phase 5
- `scripts/dl-{aaro,brazil,chile,geipan,nara,nasa,uk}.sh` — idempotent per-archive downloaders (local dev / sync.sh)
- `scripts/scrape-{aaro,brazil,chile,geipan,nara,nasa,uk}.py` — Phase 5 SCRP scope
- `scripts/verify-{fidelity,lighthouse-budgets}.py`, `scripts/verify-{redirects,python-retired}.sh` — CI verification gates
- `scripts/extract-fidelity-samples.py`, `scripts/extract-pdf-text.py` — utility extractors (explicitly whitelisted; do NOT add other `extract-*.py` files)
- `scripts/sync.sh` — master interactive sync entry point
- `scripts/resolve-dvids-r0{1,3}.py`, `scripts/dvids2dod-r0{1,2,3}.json` — DVIDS↔DOD video-ID mapping (Release 01/02/03)
- `scripts/build-{dir-index,sitemap}.py`, `scripts/rewrite-dist-legacy-links.py` — postbuild helpers invoked by `copy-legacy-archives.sh`

**RETIRED by Plan 04-20 (MUST stay absent — CI-enforced via `scripts/verify-python-retired.sh`):**
- `scripts/build-wargov.py`, `scripts/build-details.py` — Astro (`src/pages/index.astro` + `Card.astro`) is the sole wargov renderer now
- `scripts/sync-nav.py`, `scripts/sync-footer.py` — `Nav.astro`/`Footer.astro` are the sole sources now
- `scripts/parse-aaro.py`, `scripts/extract-evidence.py`, `scripts/build-aaro.py` — replaced by `src/pages/aaro/index.astro` + `normalize-aaro.py`
- `scripts/build-{nasa,nara,nz,uruguay,argentina,italy,canada,peru,spain}.py` — replaced by their Astro ports or superseded by `copy-legacy-archives.sh` for the still-dormant slugs
- Any `scripts/sync-*.py` or unwhitelisted `scripts/parse-*.py` / `scripts/extract-*.py` file reappearing is a CI failure

---

*Structure analysis: 2026-07-11*
