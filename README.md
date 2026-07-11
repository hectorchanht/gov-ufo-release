# realufo.org — every official UAP archive, in one place

**Live at [realufo.org](https://realufo.org/)** · official government UAP
releases preserved side-by-side — offline-first, mobile-first, verbatim.

Built with **Astro 5** (static output) and deployed on **Cloudflare Pages**.
Binary payloads (PDFs, videos) live on **GitHub Releases** + **Cloudflare R2**;
search is **Pagefind**; every page ships a **service worker** so the archive
keeps working with no network.

---

## Archives

**4 ACTIVE** — rendered by Astro, wired into nav, footer, and search:

| # | Archive | Source | Route |
| --: | --- | --- | --- |
| 1 | **PURSUE — Department of War / Release 01–03** | <https://www.war.gov/UFO/> | [`/`](https://realufo.org/) |
| 2 | **AARO — All-domain Anomaly Resolution Office** | <https://www.aaro.mil/> | [`/aaro/`](https://realufo.org/aaro/) |
| 3 | **NASA UAP Independent Study Team** | <https://science.nasa.gov/uap/> | [`/nasa/`](https://realufo.org/nasa/) |
| 4 | **NARA — Project Blue Book + JFK + UAP** | <https://catalog.archives.gov/> | [`/nara/`](https://realufo.org/nara/) |

**11 DORMANT** — full code + data + content-collection entries preserved in the
repo; not linked from nav/footer/search yet, but direct-URL access still works.
`nz` + `uruguay` are Astro-ported; the other 9 ship as git-tracked legacy HTML.

| Archive | Source | Route |
| --- | --- | --- |
| France — GEIPAN (CNES) | <https://www.cnes-geipan.fr/> | `/geipan/` |
| UK — National Archives MoD files | <https://discovery.nationalarchives.gov.uk/> | `/uk/` |
| Brazil — Força Aérea Brasileira | <https://www.fab.mil.br/> | `/brazil/` |
| Chile — CEFAA / SEFAA (DGAC) | <https://www.sefaa.cl/> | `/chile/` |
| Argentina — CEFAe | <https://www.argentina.gob.ar/fuerzaaerea/cefae> | `/argentina/` |
| Canada — LAC / Project Magnet | <https://www.bac-lac.gc.ca/> | `/canada/` |
| Italy — Aeronautica Militare | <https://www.aeronautica.difesa.it/> | `/italy/` |
| NZ — NZ Defence Force | <https://www.nzdf.mil.nz/> | `/nz/` |
| Peru — OIFAA (Fuerza Aérea) | <https://www.gob.pe/fap> | `/peru/` |
| Spain — Ejército del Aire | <https://ejercitodelaire.defensa.gob.es/> | `/spain/` |
| Uruguay — CRIDOVNI | <https://www.fau.mil.uy/> | `/uruguay/` |

Cross-archive search lives at [`/search/`](https://realufo.org/search/).
Re-activating a dormant archive is a 3-line edit (its slug into `Nav.astro`,
`Footer.astro`, and `RootLayout.astro`).

Every archive shares the same visual language and control logic — a cinematic
hero carousel of real declassified imagery, a headlines strip, and a
filterable, sortable, paginated **evidence browser** that surfaces every
artifact with full context (agency, location, incident date, VIRIN / DVIDS ID,
redaction status, case status). Files served from the archive when present,
falling back to the official source URL otherwise.

---

## What's in the box

```
.
├── src/                        # Astro source — the 4 ACTIVE archives + shared chrome
│   ├── pages/                  # file-based routes
│   │   ├── index.astro         # wargov (/) — War.gov/PURSUE
│   │   ├── aaro|nasa|nara/index.astro
│   │   ├── nz|uruguay/index.astro          # dormant, but Astro-owned
│   │   ├── stories/index.astro, [slug].astro   # curated cases (legacy-HTML extraction)
│   │   ├── search.astro                    # /search/ — Pagefind UI
│   │   └── about|foia|glossary|map|timeline|whatsnew.astro   # 6 site-pages
│   ├── layouts/                # RootLayout.astro (shell + tone map), BaseHead.astro (head + SW reg)
│   ├── components/             # Card, CatalogCard, Nav, Footer, HeroCarousel, Lightbox, StructuredData
│   ├── scripts/                # invariants.ts, extractLegacyBody.ts, jsonldSchemas.ts
│   ├── styles/                 # global.css + per-archive css
│   ├── data/                   # stories.json, site-pages.json — nav/route manifests
│   ├── content.config.ts       # Content Collections schema (15 archives)
│   └── sw.ts                   # Workbox injectManifest source → dist/sw.js
│
├── data/                       # Content-collection payloads — data/<slug>.json (+ shards)
├── public/                     # static passthrough → dist/ root (favicon, _headers, robots, runtime data mirror)
├── legacy/                     # git-tracked pre-Astro HTML — 11 dormant archives + site-page sources
├── scripts/                    # normalise / scrape / verify (Python + bash) — see below
├── tests/                      # Playwright specs + visual baselines + fidelity samples
├── slideshow/ slideshow-2/ 3/  # hero-carousel imagery for Release 01 / 02 / 03 (git-tracked)
├── bundles/                    # PDF/zip source bundles (mostly gitignored; restored via sync.sh)
│
├── uap-data.csv                # ⭐ source-of-truth manifest (never hand-edit — CLAUDE.md §11)
├── uap-release001.csv          # original Release 01 manifest (158 records)
├── astro.config.mjs            # Astro 5 + Cloudflare adapter + AstroPWA (injectManifest) + swRelocator
├── package.json                # prebuild / build / postbuild pnpm scripts
├── URL-CONTRACT.txt + _redirects   # canonical routes (drift-gated in CI)
└── CLAUDE.md                   # master spec — read before changing anything
```

> **Note:** the root-level per-archive directories (`aaro/`, `geipan/`, `uk/`, …)
> are **local-only gitignored download caches** — zero git-tracked files, never
> deployed. The shipped HTML for dormant archives lives in `legacy/<slug>/`.

---

## Quick start

```bash
git clone https://github.com/hectorchanht/gov-ufo-archive
cd gov-ufo-archive          # local folder may be named war-gov-ufo-release (historical)

pnpm install                # Node 22.x + pnpm 9.15.9 (both version-pinned)
pnpm dev                    # http://localhost:4321 — Astro dev server, hot reload
```

Build the full deploy artifact locally:

```bash
pnpm build                  # prebuild → astro build → postbuild
pnpm preview                # serve dist/ exactly as Cloudflare Pages will
```

`pnpm build` runs three stages:

1. **`prebuild`** — `python3 scripts/normalize-csv.py` parses `uap-data.csv`
   (source of truth), rewrites PDF/video URLs to Cloudflare R2, emits
   `data/wargov.json` + shards.
2. **`astro build`** — renders the 4 active archives from content collections
   into `dist/` (`output: 'static'`, no SSR).
3. **`postbuild`** — `bash scripts/copy-legacy-archives.sh` runs Pagefind over
   `dist/`, copies the 11 dormant archives' git-tracked legacy HTML into
   `dist/<slug>/` (via `git ls-files`, so gitignored PDFs/videos are never
   copied), and builds the sitemap. Enforces the CF Pages 25 MiB/file limit.

### Populate the bulky local mirror (optional)

Binary payloads are excluded from Git and served from GitHub Releases + R2 in
production. To pull a full local copy of PDFs/videos:

```bash
pip install curl_cffi        # only non-stdlib dependency (Akamai TLS impersonation)
./scripts/sync.sh            # interactive picker; idempotent — skips what's on disk
```

Selective flags:

```bash
./scripts/sync.sh --all          # full run
./scripts/sync.sh --aaro-only    # one archive only (replace slug)
./scripts/sync.sh --no-videos    # skip the multi-gig videos
./scripts/sync.sh --no-build     # download only
```

---

## How it works

**Static site, no hydration framework.** Zero React/Vue/Svelte. All
interactivity is `<script is:inline>` vanilla JS following the CLAUDE.md §7
invariants (lightbox, hamburger nav, `/`-focuses-search, filter/sort, `?q=`
persistence). Cards are pre-rendered — the archive stays viewable with JS
disabled and offline.

### Data pipeline

```
uap-data.csv ──(prebuild)──► scripts/normalize-csv.py ──► data/wargov.json (+shards)
                                                          │
per-archive JSON  ◄──(normalize-<slug>.py)               │
                                                          ▼
                                    src/content.config.ts  (Zod-strict schema, 15 collections)
                                                          │
                                    astro build ──► dist/  (4 active archives rendered)
                                                          │
                              copy-legacy-archives.sh ──► dist/<slug>/  (11 dormant, from legacy/)
                                                          │
                              pagefind --site dist ──► dist/pagefind/  (search index)
                                                          ▼
                                    wrangler pages deploy dist/  ──►  Cloudflare Pages
```

- **Content collections** (`src/content.config.ts`) define one collection per
  archive slug. `.strict()` Zod schemas — an unknown field is a hard build
  failure, not a silent drop. **No `z.transform()`/`z.preprocess()`** anywhere,
  so smart quotes / em-dashes / accents round-trip byte-exact (content-fidelity
  guard, verified by a 115-sample test).
- **Search** — Pagefind indexes only pages carrying `data-pagefind-body` (the 4
  active archives); dormant pages emit `data-pagefind-ignore`.
- **Offline** — `@vite-pwa/astro` with `injectManifest` compiles `src/sw.ts`
  (Workbox 7, 5 runtime-cache tiers). Registration is hand-rolled in
  `BaseHead.astro` with `updateViaCache: 'none'` (kill-switch invariant).

### `scripts/` inventory

Surviving (Astro-era): `normalize-*.py` (content-collection writers),
`copy-legacy-archives.sh` (postbuild), `build-redirects.py` (URL-contract drift
gate), `dl-*.sh` + `scrape-*.py` + `spider.py` (local sync / Phase 5 scrape),
`verify-*.{py,sh}` (CI gates), `sync.sh` (interactive sync entry).

Retired by Plan 04-20 (CI-enforced absent via `scripts/verify-python-retired.sh`):
the old `build-wargov.py`, `build-details.py`, `sync-nav.py`, `sync-footer.py`,
`parse-aaro.py`, and the per-archive `build-*.py` HTML generators — Astro +
content collections replaced them. See
`.planning/decisions/python-build-retired.md`.

---

## Continuous integration (`.github/workflows/`)

| Workflow | Trigger | Job |
| --- | --- | --- |
| `deploy-cf-pages.yml` | push to `main`, manual | `pnpm build` → `wrangler pages deploy dist/` (fallback deploy path). |
| `lighthouse.yml` | push / PR on site paths | Lighthouse CI Core Web Vitals + a11y + SEO. Config `.lighthouserc.json`. |
| `links.yml` | push, PR, weekly | [lychee] broken-link check. Ignored hosts in `.lycheeignore`. |
| `quality-gates.yml` | (matrix; `deployment_status` trigger currently disabled) | fidelity / tone-colours / redirects / mobile-Lighthouse budget gates. |
| `r2-sync.yml` | manual / path-scoped | mirror binaries to Cloudflare R2 (`assets.realufo.org`). |
| `scrape.yml` | weekly + manual | re-scrape dormant sources (Phase 5 scope — pending rewrite). |

Secrets used in CI: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`,
`CLOUDFLARE_R2_ACCESS_KEY`, `CLOUDFLARE_R2_SECRET_KEY`, `LHCI_GITHUB_APP_TOKEN`.

---

## Hosting

**Cloudflare Pages** (project `realufo`, production branch `main`). Build
command `pnpm build`, output `dist/`. Custom domain `realufo.org`; per-deploy
previews at `https://<sha>.realufo.pages.dev/`.

**Binary CDN.** Committed images stay in Git (small, frequently shown). PDFs and
videos are excluded (`.gitignore` §5.2: any file > 100 MB, all PDF dirs, all
video dirs) and served from:

- **GitHub Releases** — `videos-v1` (mp4), `pdfs-v1` (PDFs), plus per-archive
  tags. URL pattern:
  `https://github.com/hectorchanht/gov-ufo-archive/releases/download/<tag>/<file>`.
- **Cloudflare R2** — bucket `realufo`, served via `assets.realufo.org`. Used
  for the 4 active archives' binaries and >2 GB overflow.

Any asset not present locally renders with a `SOURCE` badge linking to the
official URL. Images use `<img onerror>` to fall back automatically; video uses
two `<source>` children (local + remote). The HTML never has to change — the
manifest is regenerated from current disk/R2 state on every build.

---

## Why two scrape strategies?

| Source | Why it's hard | What we use |
| --- | --- | --- |
| `www.war.gov`, `www.aaro.mil` | Akamai TLS fingerprinting blocks `curl`/`wget`/`requests`. | `curl_cffi` (Chrome TLS impersonation), Wayback fallback. |
| `cdn.dvidshub.net`, AARO cloudfront | Public CDN. | Direct `curl`. |
| `discovery.nationalarchives.gov.uk` | Official Discovery JSON API. | Direct paged JSON. |
| `cnes-geipan.fr`, `sefaa.cl`, `fab.mil.br`, … | Plain HTML, sometimes Cloudflare-fronted. | `spider.py` (BFS crawl + rate limit). |

If `curl_cffi` still gets 403 from war.gov you're probably on a known
data-center / VPN IP that Akamai blocks — run from a residential connection.

---

## Page features (every archive)

- **Cinematic hero carousel** rotating through declassified imagery and videos.
- **Headlines strip** — the mission distilled into 4–6 cards.
- **Evidence browser** — type tabs, sort by status/title/date/agency, filter by
  region/agency/case-status/redaction, full-text search, 12/24/48/96 per page,
  paginated.
- **Full context per asset** — agency, incident date & location, release date,
  VIRIN, DVIDS ID, PDF/video pairings, alt text, case-status badge.
- **Click-to-preview lightbox** — images, videos, audio, PDFs open in-place;
  `Esc` closes, ←/→ navigate, swipe on mobile.
- **`LOCAL` / `SOURCE` badges** so it's always clear whether a file is on the
  archive or links to the official URL.
- **Cross-archive search** at `/search/` with `?q=` deep links and `/` hotkey.

---

## Notes & limits

- **Public-domain attribution per jurisdiction** — US 17 U.S.C. § 105, UK OGL
  v3, France Loi 78-753, Brazil LAI 12.527/2011, Chile 20.285, Argentina
  27.275, Italy D.lgs. 33/2013, Spain 19/2013, Uruguay 18.381. Content
  reproduced verbatim from the original publications.
- **Release 03** (war.gov, 12 Jun 2026) added 72 rows. Most assets are live on
  R2; two large AARO videos (`DOD_111764796.mp4` ≈ 2.99 GiB, `DOD_111764902.mp4`
  ≈ 1.19 GiB) exceed wrangler's 300 MiB single-request cap and await an
  S3-multipart upload path — until then their two AUD cards click through to a
  404. Tracked in `.planning/STATE.md`.
- Some AARO PDFs/images were never archived by the Wayback Machine and no longer
  resolve from aaro.mil directly (Akamai) — they show a `SOURCE` badge; the
  click-through may 403.

---

## License

Code in `scripts/` and `src/`: MIT.
Archived content: each source's national public-domain regime (see above).
