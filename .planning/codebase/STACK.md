# Technology Stack

**Analysis Date:** 2026-07-11

> **This document supersedes the 2026-05-25 STACK.md**, which described the
> pre-migration pure-HTML/Python stack (198+ commits stale). realufo.org has
> since migrated to Astro 5 + Cloudflare Pages (CLAUDE.md §13; Phase 4 closed
> 2026-05-28). This rewrite verifies everything against `package.json`,
> `astro.config.mjs`, `src/`, `scripts/`, and git as checked out on branch
> `quick/260615-3e3-wargov-release-03` (forked from `main` post-Phase-4).

## Languages

**Primary:**
- **TypeScript `~5`** (strict) — `tsconfig.json` extends
  `astro/tsconfigs/strict`; covers content-collection schema
  (`src/content.config.ts`), service worker (`src/sw.ts`), client-side
  helper modules (`src/scripts/*.ts`).
- **Astro component syntax** (`.astro` — TS + HTML + scoped CSS) —
  `src/pages/**/*.astro`, `src/components/*.astro`, `src/layouts/*.astro`.

**Secondary:**
- **Python 3.11** (CI-pinned via `actions/setup-python@v5`) — build-time
  normalisers (`scripts/normalize-{csv,aaro,nara,nasa,nz,uruguay}.py`),
  downloaders (`scripts/download-war.gov.py`, `scripts/dl-*.sh`
  companions), DVIDS-ID resolvers (`scripts/resolve-dvids-{r01,r03}.py`),
  verification utilities (`scripts/verify-fidelity.py`,
  `scripts/verify-lighthouse-budgets.py`), and the legacy build/scrape
  scripts still consumed by `scrape.yml` for the 11 dormant archives
  (`scripts/build-{brazil,chile,geipan,uk,api,cases,feeds,geo,og,
  pages-index,stories,sw}.py`, `scripts/build_batch3.py`). No
  `requirements.txt` / `pyproject.toml` — the sole non-stdlib dependency
  (`curl_cffi`, for Akamai TLS-impersonation) is `pip install`-ed ad hoc in
  CI steps and locally; convention is documented inline as "stdlib-only
  except curl_cffi" (`scripts/_archive_common.py`, `scripts/normalize-
  csv.py`, `scripts/snapshot-urls.py` docstrings).
- **Bash** — `scripts/sync.sh`, `scripts/dl-*.sh`, `scripts/copy-legacy-
  archives.sh` (postbuild), `scripts/verify-redirects.sh`,
  `scripts/verify-python-retired.sh`.

**Active-surface Python build retirement (Plan 04-20):** `scripts/build-
wargov.py`, `build-details.py`, `sync-nav.py`, `sync-footer.py`, `parse-
aaro.py`, `extract-evidence.py`, `build-aaro.py`, `build-nasa.py`, `build-
nara.py`, `build-{nz,uruguay,argentina,italy,canada,peru,spain}.py` are all
**confirmed deleted** (verified directly — `ls scripts/` does not contain
any of them). `scripts/verify-python-retired.sh` CI-asserts they stay
deleted and that the whitelisted survivors (`spider.py`, `build-
redirects.py`, the `scrape.yml`-consumed builders, `copy-legacy-
archives.sh`) stay present. The 4 active archives (wargov, aaro, nasa,
nara) are 100% Astro + content collections — no Python generates their
HTML.

## Runtime

**Environment:**
- **Node.js `>=22 <23`** (`package.json#engines.node`) — single major line
  pinned, not just a floor.
- `.nvmrc` pins `22` exactly. Cloudflare Pages auto-detects this.

**Package Manager:**
- **pnpm `9.15.9`** — pinned via `package.json#packageManager`. CI
  workflows use `pnpm/action-setup@v4` with the `version:` input
  deliberately omitted (setting both the action input and
  `packageManager` throws `ERR_PNPM_BAD_PM_VERSION`; `packageManager`
  alone drives the resolved version).
- Lockfile `pnpm-lock.yaml` (310 KB) committed; CI always runs `pnpm
  install --frozen-lockfile`.

## Frameworks

**Core:**
- **Astro `~5.18.0`** (tilde-pinned; lockfile resolves `5.18.2`) — static
  site generator, `output: 'static'` in `astro.config.mjs`, no SSR.
  **Do not bump to Astro 6.x** without reading
  `.planning/decisions/astro-version-pin.md` first — the pin persists past
  the original trigger (astro#15684, a Cloudflare-adapter prerender
  regression, closed 2026-03-11) because a 6.x jump also requires a
  coordinated Zod 3→4 migration, a Content Layer API surface re-verify,
  and an `@astrojs/cloudflare` 12.x→13.x adapter jump — deferred to a
  single ADR-gated transition at a future phase close, not done
  piecemeal.
- **`@astrojs/cloudflare` `^12.6.0`** — Cloudflare Pages adapter;
  peerDependency `astro: ^5.7.0` transitively locks it to the same 5.x
  family as the tilde pin. No SSR / Worker bindings used.
- **No client-side hydration framework** — zero React/Vue/Svelte/Solid.
  All interactivity is `<script is:inline>` vanilla JS following CLAUDE.md
  §7 (lightbox, hamburger nav, `/`-focuses-search, filter/sort, `?q=`
  persistence).

**Content collections:**
- `src/content.config.ts` defines one Astro Content Collection per archive
  slug — all 15 per CLAUDE.md §2 — each using Astro's `file()` loader
  against `data/<slug>.json`. Two schema shapes:
  - `wargovEnvelopeSchema` — CSV-column-keyed with **literal spaces in
    keys** (`'Release Date'`, `'DVIDS Video ID'`, `'PDF | Image Link'`,
    etc.) — intentional fidelity contract with `uap-data.csv`'s header row.
  - `catalogEnvelopeSchema` — abbreviated-key shape (`t`, `ti`, `de`, `ag`,
    `cat`, `date`, `region`, `l`, `u`, `s`, `th`) shared by the other 14
    archives, matching the historical Python `scripts/templates/
    archive.py` output byte-for-byte.
  Validated with **Zod 3** (`z` re-exported from `astro:content`).
  `.strict()` on both the wargov row schema and the catalog asset schema —
  any unknown field is a hard Astro build failure (drift signal, not a
  silent drop). **No `z.transform()` / `z.preprocess()` anywhere** — this
  is a deliberate content-fidelity guard so smart quotes, em-dashes, and
  accented characters round-trip byte-exact.
- Only **4 of the 15 collections are consumed by a rendered page**
  (`wargov`, `aaro`, `nasa`, `nara`). The other 11 (`geipan`, `uk`,
  `brazil`, `chile`, `argentina`, `canada`, `italy`, `nz`, `peru`, `spain`,
  `uruguay`) are schema-valid but currently backed by data files with
  empty `assets: []` — scaffolding for a future re-activation per
  CLAUDE.md §2, not dead weight to clean up. Two of them (`nz`,
  `uruguay`) already have Astro page templates at `src/pages/nz/
  index.astro` and `src/pages/uruguay/index.astro`, unused while the
  archive stays dormant.
- Sharded data files exist for pagination beyond the primary entry:
  `data/wargov-shard-{2..6}.json`, `data/aaro-shard-1.json`, `data/nara-
  shard-1.json`. `data/README.md` documents the envelope shape.

**Build-time data pipeline:**
- `pnpm prebuild` → `python3 scripts/normalize-csv.py` — parses
  `uap-data.csv` (source of truth per CLAUDE.md §11 — never hand-edited),
  rewrites PDF/video URLs to Cloudflare R2 via `scripts/_archive_common.py
  rewrite_to_r2()`, emits `data/wargov.json` + shards.
- `pnpm postbuild` → `bash scripts/copy-legacy-archives.sh` — does two
  jobs despite the filename: (1) runs `pnpm exec pagefind --site dist` to
  build the search index; (2) copies the 11 dormant archives' git-tracked
  legacy HTML (relocated under `legacy/<slug>/` in Phase 04.1) into
  `dist/<slug>/` via `git ls-files` enumeration — so gitignored PDFs/
  videos are never copied — stripping the `legacy/` prefix so
  `URL-CONTRACT.txt` routes stay stable. Enforces the CF Pages 25 MiB/file
  limit per copy.

**Search:**
- **Pagefind `^1.5`** (lockfile: `1.5.2`) — replaces the pre-migration
  Lunr `api/all.json` (4.6 MB blob). Invoked via `pnpm exec pagefind
  --site dist` inside `copy-legacy-archives.sh`, not a standalone build
  step. Indexes only pages carrying `data-pagefind-body` (set by
  `RootLayout.astro` for the 4 active archives); dormant pages emit
  `data-pagefind-ignore` on `<main>` so Pagefind skips them. Query UI:
  `src/pages/search.astro`.

**Offline / Service Worker:**
- **`@vite-pwa/astro` `^1.2.0`**, `strategies: 'injectManifest'` (NOT
  `generateSW`) — configured in `astro.config.mjs`, compiles `src/sw.ts`
  and injects the Workbox precache manifest into `self.__WB_MANIFEST`.
  - `registerType: 'autoUpdate'`, `injectRegister: false` —
    registration is hand-rolled in `src/layouts/BaseHead.astro`
    (`<script is:inline>`) with `updateViaCache: 'none'` explicitly set —
    a non-negotiable kill-switch invariant carried over from Phase 1.
  - **Workbox 7** (`workbox-precaching`, `workbox-routing`, `workbox-
    strategies`, `workbox-cacheable-response`, `workbox-expiration`, all
    `^7.4.1`) imported directly in `src/sw.ts` — full manual control, not
    plugin-auto-wired.
  - `astro.config.mjs` includes an inline custom Astro integration
    (`swRelocator`) that works around the CF adapter forcing
    `output==='server'` internally: `@vite-pwa/astro` would otherwise
    emit the SW to `dist/_worker.js/sw.js` (unreachable as a static
    asset). `swRelocator` copies it to `dist/sw.js` and deletes the
    worker-bundle copy at the `astro:build:done` hook.
  - `injectManifest.globDirectory` explicitly pinned to `dist/` (root),
    overriding the CF-adapter-induced default. `globPatterns`: HTML/CSS/
    JS/SVG/webp/png/jpg/jpeg/woff2/ico + `pagefind/pagefind*.{js,css}`
    (core only). `globIgnores`: PDFs/videos/audio/zip, `sw.js` itself,
    `workbox-*.js`, `_worker.js/**`, `_routes.json`, Pagefind index/
    fragment shards (lazy-loaded on query, not precached).
    `maximumFileSizeToCacheInBytes: 5 MiB`.
  - **Runtime caching** (`src/sw.ts`, 5 tiers): HTML navigation →
    `NetworkFirst` (3s timeout, denylist `/admin`, `/_`, `/api`); JSON +
    Pagefind meta/index shards → `StaleWhileRevalidate`; images+fonts
    (same-origin + `https://assets.realufo.org`) → `CacheFirst` (allows
    opaque status-0 responses via `CacheableResponsePlugin` for
    cross-origin R2); PDFs/videos/audio/zip → explicit `NetworkOnly`
    (never precached or runtime-cached — size-prohibitive); `/admin`,
    `/_`, `/api` → explicit `NetworkOnly` denylist route.
  - Cache name templated `realufo-v<COMMIT_SHA[:7]>` via Vite `define` at
    build time (`'dev'` fallback locally); stale-prefix caches purged on
    `activate` before `clients.claim()`.
  - `ALLOW_SKIP_WAITING` hardcoded `false` in `src/sw.ts` — Phase 4 deploy
    state; a later cutover phase is expected to flip this once users have
    transitioned off the Phase-1 kill-switch SW.

**Fonts:**
- **`@fontsource/source-serif-4` `^5.2.9`** + **`@fontsource/jetbrains-
  mono` `^5.2.8`** — self-hosted (imported directly in `BaseHead.astro`),
  replacing the pre-migration Google Fonts CDN preconnect. Woff2 ships
  from `dist/_astro/` and is precached by the SW. CLAUDE.md §3.3 — no
  third font family permitted.

**Testing (dev dependencies):**
- **Playwright `1.49.0`** (+ `@playwright/test` `1.49.0`) — visual
  regression vs 60 PNG baselines, tone-colour `getComputedStyle`
  assertions, JS-off rendering hard-gate, SW invariant grep-assertions.
- **`@lhci/cli` `0.14.0`** — Lighthouse CI; mobile perf budget gate,
  **HARD-fail since Phase 4 close** (`scripts/verify-lighthouse-
  budgets.py --hard-fail` parses LHCI JSON output in CI).

**Build/Dev:**
- Standard `astro dev` / `astro build` / `astro preview` — no custom Vite
  plugins beyond the inline `swRelocator` integration noted above.
- Markdown pipeline explicitly hardened in `astro.config.mjs`:
  `smartypants: false`, `remarkPlugins: []`, `rehypePlugins: []` — defends
  content-fidelity byte-equality (Astro's default smartypants would
  otherwise silently rewrite quotes/dashes/ellipses in archive card text,
  breaking the 115-sample fidelity test).

## Key Dependencies

**Critical:**
- `astro` `~5.18.0` — rendering pipeline for the 4 active archives.
- `@astrojs/cloudflare` `^12.6.0` — Cloudflare Pages deploy adapter.
- `zod` `^3` — content-collection schema validation; hard gate against
  silent data drift.
- `pagefind` `^1.5` — cross-archive + per-archive search index/query.
- `@vite-pwa/astro` `^1.2.0` + 5× `workbox-*` `^7.4.1` — offline-first
  service worker.

**Infrastructure:**
- `papaparse` `^5` + `@types/papaparse` `^5` — installed in
  `dependencies`/`devDependencies` but **no usage found anywhere under
  `src/`** (verified by repo-wide grep for `papaparse`/`Papa\.`). CSV
  parsing for `uap-data.csv` happens entirely in Python
  (`scripts/normalize-csv.py`, stdlib `csv`), not via this JS library.
  Likely a leftover install from an earlier plan iteration — harmless,
  but a candidate for pruning in any future dependency-audit pass.
- `@fontsource/source-serif-4`, `@fontsource/jetbrains-mono` — self-hosted
  font assets (see Fonts above).

## Configuration

**Environment:**
- No `.env` file drives the Astro build — all data is filesystem-sourced
  (`data/*.json` + `uap-data.csv`). Secrets live exclusively in GitHub
  Actions repo secrets: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`,
  `CLOUDFLARE_R2_ACCESS_KEY`, `CLOUDFLARE_R2_SECRET_KEY`,
  `LHCI_GITHUB_APP_TOKEN`.
- `astro.config.mjs` reads `process.env.COMMIT_SHA` at build time only
  (to template the SW cache-name prefix); falls back to `'dev'`.

**Build:**
- `astro.config.mjs` — `output: 'static'`, `site: 'https://realufo.org'`,
  `trailingSlash: 'ignore'` (accepts both `/path` and `/path/` during the
  migration coexistence window).
- `tsconfig.json` — extends `astro/tsconfigs/strict`; includes
  `.astro/types.d.ts` (generated) + `**/*`; excludes `dist`.
- **No `wrangler.toml` exists in the repo.** The Cloudflare Pages project
  (`realufo`) is configured entirely via the CF dashboard — build command
  `pnpm build`, output dir `dist/`, framework preset `Astro` (per
  `.planning/decisions/cf-pages-project.md`). `.github/workflows/deploy-
  cf-pages.yml` is a **fallback** deploy path (the native CF Pages
  GitHub-App webhook stopped firing after a repo rename from
  `war-gov-ufo-release` → `gov-ufo-archive`) that runs `pnpm build` then
  `wrangler pages deploy dist/ --project-name=realufo --branch=main`
  directly via `cloudflare/wrangler-action@v3`, pinned to
  `wranglerVersion: '4.95.0'`. A `wrangler.toml` path-filter entry exists
  in that workflow's trigger list even though no such file is tracked —
  harmless (the filter simply never matches).
- `_headers` (repo root, mirrored to `public/_headers` so it ships in
  `dist/`) — `Cache-Control: no-cache, no-store, must-revalidate` on
  `/sw.js` (kill-switch invariant), HSTS + `X-Content-Type-Options` on
  `/*`, immutable long-cache on `/assets/*` + `/_astro/*`.
- `_redirects` (~8 KB) — generated by `scripts/build-redirects.py` from
  `URL-CONTRACT.txt`; drift-gated in `quality-gates.yml`.
- `.lighthouserc.json` (local/PR profile) + `.lighthouserc.cf.json` (CF
  Pages preview profile, `__PREVIEW_URL__` templated at CI time via
  `sed`) — perf budget definitions (LCP ≤ 2.5s, total transfer ≤ 500 KB,
  HARD since Phase 4 close).
- `.htmlvalidate.json` — HTML linting config, legacy static-page era,
  still present (governs `legacy/` dormant HTML).
- `manifest.webmanifest` (repo root) — legacy PWA manifest; the
  `@vite-pwa/astro` `manifest` option in `astro.config.mjs` generates the
  Astro-era equivalent at build time (`name: 'realufo.org — Government
  UAP Archive'`, icons pointing at `/assets/favicon.svg`).

## Platform Requirements

**Development:**
- Node 22.x + pnpm 9.15.9 (both version-pinned).
- Python 3.11 for any `scripts/*.py` (normalisers, legacy scrapers/
  builders, verification utilities). No virtualenv/lockfile convention;
  `curl_cffi` is the only non-stdlib import, installed ad hoc.
- `git ls-files` (never `os.path.exists`) is the mandated check for
  whether a binary asset is actually tracked — a repo convention
  (CLAUDE.md §4.2), enforced by `copy-legacy-archives.sh`'s use of `git
  ls-files` for enumeration, not by a standalone lint script.

**Production:**
- **Cloudflare Pages** — project `realufo`, account
  `f1868a071996e836eae6da2b65f37929`. Production branch is `main`
  (Phase 4 close migrated production off the interim `ssg-migration`
  branch used through Phases 2–4; both branches still exist in the repo
  — `ssg-migration` is now historical). Custom domain `realufo.org` (see
  `CNAME`; DNS-authority/cutover state tracked in INTEGRATIONS.md — as of
  the last committed ADR, DNS migration to Cloudflare was still
  `migration-pending`, so this may be stale relative to actual production
  DNS). Per-deployment preview URLs at `https://<sha>.realufo.pages.dev/`;
  production preview at `https://realufo.pages.dev/`.
- **Cloudflare R2** — bucket `realufo`, custom domain
  `assets.realufo.org` — binary CDN for PDFs + videos on the 4 active
  archives (full detail in INTEGRATIONS.md).
- CF Pages hard limit: 25 MiB per file — enforced explicitly in
  `copy_one()` inside `scripts/copy-legacy-archives.sh`, and reflected in
  `astro.config.mjs`'s SW `maximumFileSizeToCacheInBytes` (5 MiB, more
  conservative than the CF ceiling).

---

*Stack analysis: 2026-07-11*
