# External Integrations

**Analysis Date:** 2026-07-11

> **This document supersedes the 2026-05-25 INTEGRATIONS.md**, written
> before the Astro/Cloudflare SSG migration. The integration model has
> changed substantially: Cloudflare R2 is now the canonical binary CDN for
> the 4 active archives (superseding CLAUDE.md §5.1's original "GH Releases
> stays, R2 for >2 GB overflow only" — see `.planning/decisions/r2-setup.md`),
> hosting moved from GitHub Pages to Cloudflare Pages, and GitHub Releases
> now serves only the 11 dormant legacy archives + a read-only cold-storage
> backup role for the active ones.

## Summary — integration model

realufo.org still has **no runtime backend / auth / database**. Every
integration is one of:

1. **Build-time scrapers** — Python/Bash hit upstream government sources
   (war.gov, aaro.mil, science.nasa.gov, archives.gov, etc.) and write
   results into repo files (CSV, JSON manifests, HTML snapshots for dormant
   archives). Credential-free, public URLs only.
2. **Binary CDN, dual-system** — the 4 active archives (wargov, aaro, nasa,
   nara) serve every PDF + video from **Cloudflare R2** via the custom
   domain `assets.realufo.org`. The 11 dormant archives' legacy static HTML
   still points directly at **GitHub Releases** tags (`pdfs-v1`,
   `videos-v1`). GitHub Releases also holds a read-only cold-storage copy
   of the wargov binaries (not referenced by any live card).
3. **Hosting** — **Cloudflare Pages** (project `realufo`), replacing GitHub
   Pages. Production branch is `main`.
4. **Browser-side, no auth** — Umami analytics beacon, self-hosted fonts
   (no longer Google Fonts CDN — see STACK.md).

## APIs & External Services

### Binary CDN — Cloudflare R2 (canonical for active archives)

- **Bucket:** `realufo`, account `f1868a071996e836eae6da2b65f37929`
  (`.planning/decisions/r2-setup.md`).
- **Public URL:** custom domain `assets.realufo.org` ONLY — the `*.r2.dev`
  URL is never referenced from any card or normaliser (stability contract:
  survives bucket regeneration via DNS swap).
- **Object layout** (single bucket, prefix-based):
  ```
  https://assets.realufo.org/pdfs/<archive_slug>/<basename>
  https://assets.realufo.org/videos/<archive_slug>/<basename>
  ```
  Rewrite logic lives in `scripts/_archive_common.py::rewrite_to_r2()`
  (`R2_BASE = 'https://assets.realufo.org'`) and is consumed by
  `scripts/normalize-csv.py` for wargov. Thumbnails are explicitly
  **excluded** from R2 — `rewrite_to_r2()` short-circuits any
  `.png/.jpg/.jpeg/.gif/.webp/.svg/.avif/.bmp` extension and returns it
  unmodified, because Astro's `astro:assets` Image component only
  optimises local files (A3 decision, locked 2026-05-27).
- **PDF thumbnail URL derivation:** `scripts/_archive_common.py::
  pdf_thumb_url()` derives `https://assets.realufo.org/pdf-thumbs/<slug>/
  <basename>.jpg` from a `pdfs/` R2 URL.
- **Confirmed live in content data** (verified via grep against `data/
  *.json`): `data/wargov.json` (98 R2 URLs), `data/aaro.json` (178),
  `data/nara.json` (151), `data/nasa.json` (20). Zero GitHub Releases URLs
  remain in any of the 4 active archives' data — R2 is exclusive for them.
- **CORS** (`r2-cors.json`, applied via `wrangler r2 bucket cors set
  realufo --file ./r2-cors.json --force`): explicit origin allowlist
  (`https://realufo.org`, `https://*.realufo.pages.dev`,
  `https://realufo.pages.dev`, `http://localhost:4321`,
  `http://localhost:8788` — no wildcard `*`), `GET`+`HEAD` only (no
  mutating methods reachable from the browser), conditional-GET headers
  (`Range`, `If-Match`, `If-None-Match`, `If-Modified-Since`,
  `If-Unmodified-Since`), exposes `Content-Length`, `Content-Range`,
  `Content-Type`, `ETag`, `Last-Modified` (needed for `<video>` byte-range
  streaming + the service worker's conditional-GET path), 24h preflight
  cache.
- **Upload path:** `.github/workflows/r2-sync.yml` — GitHub Actions
  workflow using **rclone** against R2's S3-compatible endpoint
  (`https://<account>.r2.cloudflarestorage.com`), NOT the Cloudflare REST
  API (wrangler can't speak S3; rclone can't speak the CF API — see
  `r2-setup.md` for why both `CLOUDFLARE_API_TOKEN` and the
  `CLOUDFLARE_R2_ACCESS_KEY`/`SECRET_KEY` pair both exist as GH secrets,
  each for a different auth surface). Triggers: push to `main` touching
  `bundles/**/*.pdf`, `**/*.mp4`, `**/*.webm`, etc.; `workflow_dispatch`
  (`full_sync`, per-archive `archive` narrow-scope, or `asset_keys` JSON
  array); `repository_dispatch` type `scrape-promote` (Phase 5 Worker
  ingest hook, payload `{archive, asset_keys[]}`). `rclone sync --checksum`
  makes every run idempotent. `concurrency.cancel-in-progress: false` —
  never cancels an in-flight upload. R2 API token is scoped to "Object
  Read & Write" on bucket `realufo` only (no account-wide access).
- **Current bucket state (2026-07-11, per `.planning/quick/260615-3e3-.../
  260615-3e3-SUMMARY.md`):**
  - wargov Release 03: 53 PDFs → `pdfs/wargov/` all HTTP 200.
  - wargov Release 03: 7 of 9 new DVIDS/DOD videos → `videos/wargov/
    DOD_<id>.mp4` all HTTP 200.
  - **2 large videos FAILED to upload** — `wrangler r2 object put` caps at
    300 MiB; `DOD_111764796.mp4` (2.99 GiB, DVIDS 1010319) and
    `DOD_111764902.mp4` (1.19 GiB, DVIDS 1010336) exceed that cap and
    require an S3-multipart upload path (rclone or the AWS SDK against the
    R2 S3-compat endpoint) instead of the single-PUT `wrangler` path used
    for the initial attempt. **No multipart-upload script exists yet in
    `scripts/`** (verified — no file matching `*multipart*` anywhere in
    the repo). Until this is done, the 2 corresponding AUD cards (DVIDS
    1010319, 1010336) render a Play button that 404s. Source binaries for
    the retry sit at `/Users/laichan/UFO/AARO061226/` on the operator's
    machine (outside the repo). Tracked as an open TODO in `.planning/
    STATE.md`.
- **DNS/cutover status:** `.planning/decisions/r2-setup.md` records R2 as
  already live and DNS-independent of the Phase 6 cutover (`assets.
  realufo.org` resolves at Cloudflare regardless of where the apex domain
  points). See Hosting section below for the separate, still-pending apex
  DNS migration.

### Binary CDN — GitHub Releases (dormant archives + cold storage)

- **Tags:** `pdfs-v1`, `videos-v1` (primary, referenced by the 11 dormant
  archives' legacy static HTML now under `legacy/<slug>/index.html`, e.g.
  `legacy/geipan/index.html`, `legacy/uk/index.html`,
  `legacy/chile/index.html` — confirmed via grep for `releases/download/
  pdfs-v1` / `videos-v1`). Historical per-wave tags also referenced in
  older tooling: `wargov-r02-v1`, `aaro-v1`.
- **URL pattern (legacy, still live for dormant archives):**
  `https://github.com/hectorchanht/gov-ufo-archive/releases/download/
  <tag>/<basename>` — note `scripts/backfill-release.py` still hardcodes
  the **pre-rename** repo name `hectorchanht/war-gov-ufo-release` in its
  `RELEASE_BASE` constant; GitHub's repo-rename redirect makes old URLs
  still resolve, but new backfill runs should be checked against the
  canonical `gov-ufo-archive` name per CLAUDE.md §5.1.
- **Role for the 4 active archives:** cold-storage backup only, per
  `r2-setup.md` D-06 — "GH Releases tags `pdfs-v1` + `videos-v1` kept
  read-only as cold-storage backup. Cards do NOT reference them —
  `rewrite_to_r2()` emits R2 URLs exclusively." Confirmed by the zero-hit
  grep above.
- **Upload tooling:** `scripts/backfill-release.py` (`gh release upload
  <tag> --clobber <files>`), also invoked from the legacy
  `scripts/update_all.sh` (`gh release upload videos-v1 …` /
  `gh release upload pdfs-v1 …`). CLAUDE.md §11 warns against firing a
  second `gh release upload` before a prior one finishes.

### Video/audio source — DVIDS + DOD media.defense.gov

wargov (war.gov / PURSUE) VID and AUD rows are sourced from two linked
identifier spaces that must be bridged at build time:

1. The CSV's `DVIDS Video ID` column carries a **DVIDS catalog-page ID**
   (e.g. `1010319`) — the human-facing page at
   `https://www.dvidshub.net/video/<id>`.
2. The actual playable asset lives in R2 as `DOD_<asset-id>.mp4`, where
   `<asset-id>` is DVIDS's internal numeric asset ID (e.g. `111764796`) —
   a **different number**, only discoverable by scraping the DVIDS page.

**Bridge files** (`scripts/dvids2dod-{r01,r02,r03}.json`) map catalog ID →
asset ID per release wave, generated by `scripts/resolve-dvids-{r01,r03}.py`
(each hits `https://www.dvidshub.net/video/<id>` once per ID and regexes
out `DOD_(\d+)\.mp4` from the embedded asset URL). These scripts are
**dev-only, must be run manually, locally** — DVIDS blocks GitHub Actions
runner IPs (Akamai-class bot protection), so they cannot run in CI.
`scripts/normalize-csv.py`'s `_hydrate_vid_url()` / `_hydrate_thumb()`
consume all 3 JSON maps (`DVIDS_MAP_PATHS`) to patch empty CSV `PDF |
Image Link` fields at read time only — never mutating the CSV on disk. As
of the Release-03 resolve (`dvidsId2dod-r03.json`, 9 entries), all 9
Release-03 VID/AUD rows have Play buttons wired; 2 of those 9 point at R2
URLs that 404 pending the multipart upload noted above.

`Card.astro` renders a **DVIDS ↗** external-link button (routing to
`https://www.dvidshub.net/video/<DVIDS Video ID>`) whenever the CSV
column is non-empty — this button works regardless of R2 upload state,
since it points at the DVIDS catalog page, not the R2 asset.

### Build-time scrapers (per-archive, credential-free)

Every upstream archive has at least one Python scraper or `dl-<slug>.sh`
downloader. Direct-request-blocked sources fall back to the **Wayback
Machine** (`web.archive.org`).

**War.gov / PURSUE** (`scripts/download-war.gov.py`):
- Akamai bot-protected — `curl`/`wget`/`requests` all 403 on TLS/JA3
  fingerprint. Mitigation: **`curl_cffi`**, which wraps curl-impersonate to
  replicate a real Chrome TLS handshake byte-for-byte. Rotates through
  Chrome impersonation profiles `chrome124 → chrome120 → chrome116 →
  chrome110` until one succeeds.
- Fetches the CSV manifest, slideshow/Rotator images (per release wave:
  `slideshow/`, `slideshow-2/`, `slideshow-3/`), and document/video ZIP
  bundles from `war.gov` + a CloudFront host. Bundle URLs are
  **discovered from live page markup, never hardcoded/guessed** — the
  Release-03 fetch found the guessed bundle filename 404'd and had to
  re-discover the real path from the rendered page.

**AARO** (`scripts/dl-aaro.sh`, `scripts/scrape-aaro.py`):
- `https://www.aaro.mil/` (12 main pages) + a CloudFront video host.
- aaro.mil has aggressive bot protection → mirrored via the **Wayback
  Machine exclusively**: `http://archive.org/wayback/available?url=…` for
  the closest snapshot timestamp, CDX fallback at
  `https://web.archive.org/cdx/search/cdx?url=…&filter=statuscode:200`,
  then download via `https://web.archive.org/web/<ts>id_/<url>` (`im_`
  flag for images, `if_` for video/other).
- Videos download direct from CloudFront with a spoofed Chrome 131
  User-Agent, not via Wayback.

**NASA UAP, NARA, GEIPAN, UK, Brazil, Chile, and the remaining 8 dormant
archives** each have a `scripts/dl-<slug>.sh` and/or `scripts/scrape-
<slug>.py`, using direct requests (no bot protection observed in
practice) with Wayback as a generic fallback. A generic BFS crawler
(`scripts/spider.py`) covers Argentina, Canada, Italy, NZ, Peru, Spain,
and Uruguay via per-source configs (`allowed_hosts`, `link_patterns`,
`file_extensions`, `max_depth`, `max_pages`, 1s rate-limit delay each),
also falling back to Wayback on direct failure.

**Weekly automation (`scrape.yml`) is currently BROKEN / stale.** It
still invokes `python3 scripts/build-wargov.py`, `build-nasa.py`,
`build-aaro.py`, `build-nara.py`, and `build-details.py` at the "Rebuild
all archive HTML" step — **all 5 of these files are confirmed deleted**
(Plan 04-20 retired the active-surface Python builders; verified via
direct filesystem check). This workflow will fail at that step on its
next scheduled run (`cron: '0 6 * * 1'`) until Phase 5 rewrites it per
CLAUDE.md §13's carve-out note ("scrape.yml — retired in Phase 5 when
scrape.yml is rewritten"). The scraper steps upstream of that (NASA/NARA/
AARO/GEIPAN/UK/Brazil/Chile scrapers + `spider.py`) still work — they
only write JSON/HTML fetch results, not touch the retired builders.

**Akamai-vs-Workers scrape-architecture spike is unresolved.**
`.planning/spikes/01-akamai/` scaffolds a bilateral probe (5 URLs:
war.gov, aaro.mil, + 3 random dormant-archive sources) to decide whether
Phase 5's scrape automation runs on Cloudflare Workers cron or stays on
GitHub Actions runners — motivated by the concern that Cloudflare's own
edge IPs may be MORE Akamai-flagged than GH Actions runners (`.planning/
research/PITFALLS.md` Pitfall #3). `results.json` shows
`worker_lane: []`, `actions_lane: []` — **the spike has not actually been
run**; `.planning/decisions/akamai-spike.md` (the ADR meant to record the
outcome) does not exist yet in the repo despite being referenced by later
ADRs as if resolved.

### Browser-side (no auth)

- **Umami analytics** — `https://cloud.umami.is/script.js`,
  `data-website-id="9c4f36ef-30ad-4d76-947a-1724fe6acdba"`. Loaded via
  `<script defer>` (deliberately not `is:inline`, so native `defer`
  semantics apply) from `src/layouts/BaseHead.astro` on every page.
  Cookieless, no SDK beyond the tag, no user identifiers.
- **Fonts are now self-hosted** (`@fontsource/source-serif-4` +
  `@fontsource/jetbrains-mono`, see STACK.md) — the pre-migration Google
  Fonts CDN dependency (`fonts.googleapis.com`/`fonts.gstatic.com`) is
  gone. This closes an offline-first regression the old CDN caused (font
  fetches failing when offline).

## Data Storage

**Databases:** None.

**File storage:**
- **GitHub repo (`main` branch)** — committed: all Astro source (`src/`),
  content-collection data (`data/*.json` + shards), `uap-data.csv` (source
  of truth, never hand-edited per CLAUDE.md §11), the 11 dormant archives'
  legacy static HTML (`legacy/<slug>/`), thumbnails/slideshow images
  (small, tracked directly — never routed through R2 per the A3 decision).
- **Cloudflare R2** (bucket `realufo`) — PDFs + videos for the 4 active
  archives. See APIs & External Services above for full detail.
- **GitHub Releases** — PDFs + videos for the 11 dormant archives (`pdfs-
  v1`, `videos-v1` tags) + a read-only cold-storage copy of active-archive
  binaries not referenced by any live card.
- **Local cache (gitignored)** — `bundles/Release_1/*.pdf`,
  `bundles/release_02_document_bundle/*.pdf`, `bundles/uapvideos/`,
  `bundles/uap052226/`, per-archive `<slug>/pdfs/`, `<slug>/videos/`
  (aaro, geipan) directories; ~15 GB present in `bundles/` on the current
  local checkout. Rebuilt on demand by `scripts/sync.sh` / `scripts/dl-
  <slug>.sh`.

**Caching (browser-side):** See STACK.md's Service Worker section for the
5-tier Workbox runtime-caching strategy (`NetworkFirst` for HTML,
`StaleWhileRevalidate` for JSON/Pagefind meta, `CacheFirst` for images/
fonts including R2-hosted images, explicit `NetworkOnly` for PDFs/videos
and `/admin`/`/api` paths).

## Authentication & Identity

**End-user auth:** None. No login, sessions, or cookies. Umami is
cookieless.

**Developer/CI auth:**
- `gh auth login` — for manual `gh release upload` to GitHub Releases.
- **`CLOUDFLARE_API_TOKEN`** (GH secret) — Cloudflare REST API bearer
  token (project create/delete, bucket create, custom-domain bind, CORS
  apply via `wrangler`). Used by `deploy-cf-pages.yml`'s fallback
  wrangler-based deploy step.
- **`CLOUDFLARE_ACCOUNT_ID`** (GH secret) — templates the R2 S3-compat
  endpoint URL and is passed to `wrangler-action`.
- **`CLOUDFLARE_R2_ACCESS_KEY`** + **`CLOUDFLARE_R2_SECRET_KEY`** (GH
  secrets) — S3-compatible credentials for `rclone` in `r2-sync.yml`,
  scoped to "Object Read & Write" on bucket `realufo` only. Distinct auth
  surface from `CLOUDFLARE_API_TOKEN` (see r2-setup.md for why both
  exist).
- GitHub Actions `permissions: contents: write` on `scrape.yml` so the
  weekly bot can commit rebuilt artifacts (though see the "currently
  BROKEN" note above — the commit step itself never gets reached at
  present because the rebuild step fails first).

## Monitoring & Observability

**Error tracking:** None (no Sentry/Rollbar/Bugsnag).

**Analytics:** Umami (`cloud.umami.is`) — log-only page views, no
behavioural profiling.

**Logs:**
- **Build-time:** GitHub Actions UI. `scripts/check-sources.py` (via
  `scrape.yml`, currently unreachable — see above) would write `dead-
  links.json`/`dead-links.md`.
- **Runtime:** browser `console` only.
- **Lighthouse CI** (`@lhci/cli`) posts budget results as GitHub Actions
  artifacts (`.lighthouseci/`, 14-day retention) and, when
  `LHCI_GITHUB_APP_TOKEN` is set, back to the PR via the LHCI GitHub App.

**Health:**
- `lychee` (`.github/workflows/links.yml`) — broken-link check on every
  `**/*.html` file, weekly cron + push/PR. Accepts `200, 206, 301, 302,
  308, 403, 429`; allowlist in `.lycheeignore`.
- `quality-gates.yml` — 6-job CI matrix (visual regression, fidelity
  samples, tone-colour, JS-off rendering, Lighthouse budgets, `_redirects`
  drift+curl) gated on a `deployment_status` event from CF Pages, but
  **the automatic trigger is currently disabled** (commented out) because
  its `verify-redirects.sh` curl harness still probes retired Phase-2
  legacy URLs (e.g. `belgian-wave.html`) that 301 under the current Astro
  routing. Runs only via manual `workflow_dispatch` until the curl-sample
  list is refreshed.

## CI/CD & Deployment

**Hosting:**
- **Cloudflare Pages** — project `realufo`, account
  `f1868a071996e836eae6da2b65f37929`. Production branch: `main`. Build:
  `pnpm install --frozen-lockfile && pnpm build` (Astro build command
  configured via CF dashboard, per `.planning/decisions/cf-pages-
  project.md`), output dir `dist/`, framework preset `Astro`. Per-
  deployment preview: `https://<sha>.realufo.pages.dev/`; branch preview:
  `https://<branch>.realufo.pages.dev/`; production preview:
  `https://realufo.pages.dev/`.
- **Apex domain DNS status is ambiguous in committed docs.** `.planning/
  decisions/dns-ttl.md` (last updated during Phase 1) records DNS
  authority as still **Porkbun** (status `migration-pending`) with a
  planned migration to Cloudflare DNS before a TTL drop to 300s ahead of
  the Phase 6 cutover. `.planning/decisions/cf-pages-project.md` (Phase 2)
  explicitly states `realufo.org` "continues to resolve to GitHub Pages"
  through Phase 2-5. Since CLAUDE.md §13 records Phase 4 as closed and
  `main` now carries production traffic per `deploy-cf-pages.yml`'s
  `branches: [main]` trigger, **the actual current DNS target for
  `realufo.org` is not verifiable from committed docs alone** — treat as
  an open question rather than assume either GitHub Pages or Cloudflare
  Pages is currently live at the apex without checking `dig realufo.org`
  directly.
- **Native CF Pages GitHub-App git integration is broken** — stopped
  firing after the repo rename `hectorchanht/war-gov-ufo-release` →
  `hectorchanht/gov-ufo-archive`. `.github/workflows/deploy-cf-pages.yml`
  is the fallback: builds locally on the runner, then `wrangler pages
  deploy dist/ --project-name=realufo --branch=main` (wrangler `4.95.0`
  pinned via `cloudflare/wrangler-action@v3`). Triggers on push to `main`
  touching `src/**`, `public/**`, `scripts/**`, `data/**`,
  `astro.config.mjs`, `package.json`, `pnpm-lock.yaml`, `tsconfig.json`,
  `uap-data.csv`, `uap-release001.csv`, `wrangler.toml` (this last filter
  entry never matches — no such file is tracked). `concurrency:
  cancel-in-progress: false` — deploys queue rather than race.

**CI pipeline (6 workflows in `.github/workflows/`):**
- `deploy-cf-pages.yml` — fallback CF Pages deploy (see above).
- `r2-sync.yml` — R2 binary sync via rclone (see APIs section above).
- `lighthouse.yml` — Lighthouse CI on push/PR touching `src/**`,
  `public/**`, `astro.config.mjs`; serves `dist/` via `python3 -m
  http.server 8000` then runs `pnpm dlx @lhci/cli@^0.14 autorun`.
- `quality-gates.yml` — 7-job matrix (preflight + 6 parallel gates:
  visual-regression, fidelity, tone-colours, js-off, lighthouse,
  redirects), designed to run per CF-Pages-preview-deploy but currently
  `workflow_dispatch`-only (see Monitoring section above).
- `links.yml` — weekly + push/PR lychee broken-link check.
- `scrape.yml` — weekly cron (Monday 06:00 UTC) scrape + rebuild + commit
  to `main`. **Currently broken** at the HTML-rebuild step (see Build-time
  scrapers section above) — the scraper steps upstream still run and
  succeed, but the workflow will fail before reaching its
  `git commit`/`git push` step.

## Environment Configuration

**Required env vars (production runtime):** None — Astro output is fully
static.

**Required env vars (CI):**
- `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` — CF Pages fallback
  deploy + R2 endpoint templating.
- `CLOUDFLARE_R2_ACCESS_KEY`, `CLOUDFLARE_R2_SECRET_KEY` — R2 S3-compat
  rclone auth.
- `LHCI_GITHUB_APP_TOKEN` — Lighthouse CI GitHub App (optional PR
  comments).
- `GITHUB_TOKEN` — auto-provided; used by lychee.
- `COMMIT_SHA` (build-time only, not a secret) — templates the SW cache
  name prefix; read by `astro.config.mjs`'s `vite.define`.

**Required env vars (local dev):** None for read-only browsing/`astro
dev`. For binary uploads: `gh` CLI authenticated (GitHub Releases path);
`wrangler` authenticated (R2 bucket admin operations like CORS updates).

**Secrets location:** GitHub repo settings → Secrets and variables →
Actions (all 5 CI secrets above). No `.env` file exists or is expected
for the Astro build.

## Webhooks & Callbacks

**Incoming:**
- `repository_dispatch` type `scrape-promote` on `r2-sync.yml` — reserved
  for a Phase 5 Cloudflare Worker ingest pipeline (not yet built) to
  trigger narrow per-archive R2 promotion after its own fingerprint-diff
  detection against KV. Payload shape: `{archive, asset_keys[]}`.
- CF Pages `deployment_status` events — intended trigger for
  `quality-gates.yml`, currently disabled (see Monitoring section).

**Outgoing:** None beyond the repo's own `git push origin main`
(`scrape.yml`, when it reaches that step) and R2/GitHub-Releases binary
uploads. No Slack/Discord/Zapier/IFTTT, no upstream API write-backs.

## External-link integrity

- **`lychee`** (`.github/workflows/links.yml`) validates every link in
  every `**/*.html` weekly + on HTML pushes.
- **`scripts/check-sources.py`** (informational, `|| true`) would scan
  every upstream `src` URL and write `dead-links.json`/`dead-links.md` —
  currently unreachable in CI since it lives downstream of `scrape.yml`'s
  broken rebuild step (see above); still runnable manually.
- When upstream source pages rot, the **Download** button always routes
  through R2 (active archives) or GitHub Releases (dormant archives) —
  never the bare upstream URL — so it never 404s. Only the **Source ↗**
  button (pointing at the original government site) can go dead, which is
  expected/acceptable per CLAUDE.md §4.3.

---

*Integration audit: 2026-07-11*
