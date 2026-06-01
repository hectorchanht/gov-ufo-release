# Roadmap: realufo.org — SSG Migration Milestone

**Created:** 2026-05-25
**Granularity:** standard
**Project mode:** Horizontal Layers (brownfield, big-bang migration)
**Core Value:** Every official government UAP release is preserved and viewable offline-first, with content matching the official source verbatim — durable, free, resistant to source-site takedowns.

This roadmap derives 6 phases from the v1 REQUIREMENTS.md categories (PMS / INF / SSG / SRC / SW / HOST / SCRP / PERF). Each phase is a horizontal technical layer that builds on the previous one; ordering reflects the hard pre-cutover sequencing constraints from research/PITFALLS.md (SW kill-switch on old origin T-14d, URL-CONTRACT.txt snapshot from `main` before any SSG code lands, Akamai egress spike before scrape architecture finalises, DNS TTL drop before cutover).

---

## Phases

- [ ] **Phase 1: Pre-Migration Safety** — Snapshot the current contract and remove production tripwires before SSG code lands
- [ ] **Phase 2: Infrastructure & CI Scaffolding** — Stand up Cloudflare Pages, Workers paid, and verification gates against current `main` baselines
- [x] **Phase 3: SSG Foundation** — Bring up Astro 5.x alongside the existing build, port the smallest archive end-to-end as a proof (completed 2026-05-27)
- [x] **Phase 4: Full Migration, Search, Offline, Performance** — Port the remaining 14 archives, wire Pagefind + injectManifest SW + per-page weight budget (completed 2026-05-28)
- [ ] **Phase 5: Scrape Automation** — Move source ingestion to Cloudflare Workers cron with hybrid Akamai fallback and idempotent GH Releases upload
- [ ] **Phase 6: Hosting & Cutover** — Stabilise preview deploy, swap DNS off GitHub Pages, monitor 7-day window, archive the legacy workflow

---

## Phase Details

### Phase 1: Pre-Migration Safety

**Goal**: Capture an immutable snapshot of the current contract (URLs, source-fetch viability, latent FIX bugs) and ship the kill-switch to the OLD origin before any SSG code can land — so a botched cutover can never serve a stale shell.

**Depends on**: Nothing (first phase, runs against current `main`)

**Requirements**: PMS-01, PMS-02, PMS-03, PMS-04, PMS-05, PMS-06

**Success Criteria** (what must be TRUE):

  1. `URL-CONTRACT.txt` exists on `main` listing every public route + `#card-<id>` anchor served by today's GitHub Pages deployment. (The CI gate that fails PRs dropping/renaming URLs is Phase 2 work per CONTEXT.md D-04 / INF-02 — not Phase 1's deliverable.)
  2. A SW kill-switch (`unregister()` + `caches.delete(all)`) is deployed to the live GitHub Pages origin and verified in DevTools on a returning-user profile — returning visitors self-deregister, and the gate against the Phase 6 cutover window is the `≥ 14 days since kill-switch deploy` counter.
  3. A documented 1-day Akamai egress spike (Workers vs GH Actions runners against war.gov + aaro.mil) determines the Phase 5 scrape architecture; the decision is recorded in `.planning/decisions/akamai-spike.md` before Phase 5 code is written.
  4. DNS TTL on `realufo.org` is dropped to 300 s and verified via `dig +noall +answer realufo.org` (gate against Phase 6 cutover: TTL must read 300 s for ≥ 7 consecutive days before DNS swap).
  5. Two latent FIX bugs are closed: `scripts/sync.sh:144` resolves to a real path (PMS-05), and `CLAUDE.md §5.1` reflects the actual remote `hectorchanht/gov-ufo-archive` (PMS-06).

**Plans**: 5 plans

Plans:
**Wave 1**

- [ ] 01-01-PLAN.md — Close PMS-05 (sync.sh:144 broken download.py path) + PMS-06 (CLAUDE.md §5.1 verification)
- [ ] 01-02-PLAN.md — PMS-01: generate scripts/snapshot-urls.py + commit URL-CONTRACT.txt from main
- [ ] 01-03-PLAN.md — PMS-03: bilateral Akamai egress spike (Workers vs Actions) + write .planning/decisions/akamai-spike.md
- [ ] 01-04-PLAN.md — PMS-04: discover DNS provider for realufo.org, drop TTL to 300 s, verify via dig

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 01-05-PLAN.md — PMS-02: replace sw.js with kill-switch SW, deploy to GH Pages, verify on returning-user profile

### Phase 2: Infrastructure & CI Scaffolding

**Goal**: Stand up Cloudflare Pages + Workers Paid and freeze fidelity baselines against current `main` so every later phase has objective regression gates to fail against.

**Depends on**: Phase 1 (URL-CONTRACT.txt and the kill-switch must exist before any rival origin is built)

**Requirements**: INF-01, INF-02, INF-03, INF-04, INF-05, INF-06, INF-07, INF-08

**Success Criteria** (what must be TRUE):

  1. A Cloudflare Pages project builds a long-running `ssg-migration` branch on every push, and the build product is served at a stable `*.realufo.pages.dev` preview URL.
  2. `_headers` (CSP / HSTS / MIME / `Cache-Control: no-cache` on `/sw.js`) and `_redirects` (explicit 301s for every legacy URL from `URL-CONTRACT.txt`) are committed and verified by a `scripts/verify-redirects.sh`-style curl harness against the preview.
  3. Cloudflare Workers Paid plan is active (a $5/mo line item is visible in billing), unlocking the 15-min cron CPU budget required for Phase 5.
  4. Playwright visual-regression baselines exist on disk for all 15 archives × 4 viewports (360 / 768 / 1024 / 1440), captured against the current `main` deploy, and a CI workflow fails any PR with > 0.1 % pixel diff.
  5. `scripts/verify-fidelity.py` is wired into CI: it asserts byte-equivalence on a curated sample of verbatim text (hero ledes, FAQ answers, license footers, official titles) between the snapshot of `main` and any SSG output.
  6. Tone-colour smoke test, JS-off rendering test, and Lighthouse-mobile budgets (LCP ≤ 2.5 s, transfer ≤ 500 KB @ 4× CPU throttle) are all live as CI gates against the preview deployment.

**Plans**: 8 plans

Plans:
**Wave 1**

- [ ] 02-01-PLAN.md — INF-01 + INF-02 (_headers): CF Pages project creation, ssg-migration branch, _headers (operator checkpoint inside)

**Wave 2**

- [ ] 02-02-PLAN.md — INF-03: Workers Paid plan activation (operator-only checkpoint)
- [ ] 02-03-PLAN.md — INF-04: Playwright setup + capture 60 PNG baselines against live realufo.org
- [ ] 02-04-PLAN.md — INF-05: extract-fidelity-samples.py + fidelity-samples.json + verify-fidelity.py
- [ ] 02-05-PLAN.md — INF-02 (_redirects): build-redirects.py auto-gen from URL-CONTRACT.txt

**Wave 3**

- [ ] 02-06-PLAN.md — INF-06 + INF-07: tone-colour + JS-off Playwright specs
- [ ] 02-07-PLAN.md — INF-08: Lighthouse-CI mobile budgets + verify-lighthouse-budgets.py (soft per D-28)

**Wave 4**

- [ ] 02-08-PLAN.md — wire 5 parallel CI jobs via quality-gates.yml + verify-redirects.sh curl harness

### Phase 3: SSG Foundation

**Goal**: Bring Astro 5.x up alongside the existing Python build scripts, define the Content Collections schema, and port one small archive (wargov) end-to-end as a working proof — without breaking any of the Phase 2 gates.

**Depends on**: Phase 2 (visual-regression, fidelity, tone-colour, JS-off, and perf gates must be active before any Astro page can be evaluated against the baseline)

**Requirements**: SSG-01, SSG-02, SSG-03, SSG-04, SSG-05

**Success Criteria** (what must be TRUE):

  1. An Astro 5.x scaffold builds in the repo with `astro` pinned as `~5.x.y` (NOT `^5`, to defend against accidental Astro 6 upgrades that broke the Cloudflare adapter per research/PITFALLS.md); both the old Python build and the new Astro build coexist on `ssg-migration` without one overwriting the other.
  2. Content Collections are defined for all 15 archives with a Zod schema and a `file()` loader reading from `data/<slug>.json`; a fresh clone can run `pnpm build` and the build fails loudly (not silently) on any schema-incompatible row.
  3. Shared layout components (`RootLayout.astro`, `BaseHead.astro`, `Nav.astro`, `Footer.astro`) exist and are the canonical source of nav/footer markup — `sync-nav.py` / `sync-footer.py` and their drift gates can be retired (deferred to Phase 4, but the components themselves must exist here).
  4. Cards on the ported archive are pre-rendered HTML (no client hydration of card data); progressive-enhancement JS reads `data-*` attributes for lightbox / filter / sort, and a Playwright test confirms the cards remain visible with JS disabled.
  5. The wargov archive is fully ported and passes every Phase 2 gate (visual regression at all 4 viewports, fidelity byte-match, tone colour, JS-off rendering, Lighthouse mobile budget).

**Plans**: 6 plans

Plans:
**Wave 1**

- [x] 03-01-PLAN.md — SSG-01: Astro 5.18.x scaffold + @astrojs/cloudflare adapter + tsconfig + ADR
- [x] 03-02-PLAN.md — SSG-02 (schema side): src/content.config.ts Zod schema for all 15 archives + 14 skeleton data/<slug>.json files

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 03-03-PLAN.md — SSG-02 (data side, wargov): scripts/normalize-csv.py + data/wargov.json + shards + pnpm prebuild wiring
- [x] 03-04-PLAN.md — SSG-03 + SSG-04 (JS invariants): RootLayout + BaseHead + Nav + Footer + global.css + invariants.ts (CLAUDE.md §7)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 03-05-PLAN.md — SSG-04 + SSG-05 (output): src/pages/index.astro wargov port + Card.astro + Lightbox.astro + HeroCarousel.astro + wargov.css

**Wave 4** *(blocked on Wave 3 completion — operator checkpoint)*

- [x] 03-06-PLAN.md — SSG-05 acceptance: wargov port passes all 7 quality-gates.yml jobs on CF Pages preview URL

### Phase 4: Full Migration, Search, Offline, Performance

**Goal**: Port the remaining 14 archives, swap Lunr → Pagefind, wire the `injectManifest` SW so every page registers it from a single point, and hit the ≤ 500 KB-per-page weight target (currently GEIPAN is 3.3 MB).

**Depends on**: Phase 3 (the Content Collections schema and shared layouts must be proven on wargov before being applied to 14 more archives)

**Requirements**: SSG-06, SSG-07, SSG-08, SSG-09, SSG-10, SSG-11, SSG-12, SRC-01, SRC-02, SRC-03, SRC-04, SRC-05, SW-01, SW-02, SW-03, SW-04, SW-05, SW-06, SW-07, PERF-01, PERF-02, PERF-03, PERF-04

**Success Criteria** (what must be TRUE):

  1. All 15 archives (AARO, NASA, NARA, GEIPAN, UK, Brazil, Chile, Argentina, Canada, Italy, NZ, Peru, Spain, Uruguay, plus the Phase 3 wargov port) render from Astro with byte-equivalent verbatim text, correct per-archive tone colour, correct public-domain licence footer, and surviving CLAUDE.md §7 JS invariants (hamburger, lightbox prev/next + arrow keys + swipe, image/video/PDF fallback, `/` keydown focus, `?q=` persistence).
  2. Every archive page weighs ≤ 500 KB HTML+inline and renders meaningful card content with JS disabled; GEIPAN's LCP measures ≤ 2.5 s on mobile + 4× CPU throttle, with the data shard split into ≤ 3 chunks (not naive per-card atomisation).
  3. Pagefind 1.x runs at the end of the build and outputs a sharded WASM index to `dist/pagefind/`; `/search.html` returns results from Pagefind (Lunr removed), `api/all.json` 4.6 MB blob is deleted, and search result links use stable `#card-<id>` anchors.
  4. The service worker registers structurally from `BaseHead.astro` (impossible to forget on a page), precaches every HTML page + every card thumbnail, applies tiered cache strategies (network-first nav, SWR JSON, cache-first images/fonts, no-cache for PDFs/videos), and ships a versioned `realufo-v<sha>` cache name that cleans up old caches on activate.
  5. All legacy Python build scripts (`build-*.py`, `sync-nav.py`, `sync-footer.py`, `parse-aaro.py`, `extract-evidence.py`, `spider.py`) are deleted from `main` — replaced entirely by Astro components and Content Collections; their CI drift gates are removed.

**Plans**: 20 plans

- [x] 04-01-PLAN.md — SSG-09: lightbox-fix (root-cause + invariants.ts + Card.astro patches)
- [x] 04-02-PLAN.md — SSG-06: R2 bucket setup + assets.realufo.org custom domain + r2-sync.yml + scripts/_archive_common.py
- [x] 04-03-PLAN.md — SW-01..07 + SRC-05: @vite-pwa/astro injectManifest SW + self-hosted @fontsource + _headers verification
- [x] 04-04-PLAN.md — SSG-09: wargov re-paging (50/page → 20/page client-side ?page=N + pagination handler)
- [x] 04-05-PLAN.md — SSG-06,08-12: NZ port + ESTABLISHES src/components/CatalogCard.astro template
- [x] 04-06-PLAN.md — SSG-06,08-12: Uruguay port (small static, minimal-delta template)
- [ ] 04-07-PLAN.md — SSG-06,08-12: Peru port (small static)
- [ ] 04-08-PLAN.md — SSG-06,08-12: Spain port (small static)
- [ ] 04-09-PLAN.md — SSG-06,08-12: Argentina port (small static)
- [ ] 04-10-PLAN.md — SSG-06,08-12: Italy port (small static)
- [ ] 04-11-PLAN.md — SSG-06,08-12: Brazil port (medium catalog + D-10 tone-colour fix #009c3b)
- [ ] 04-12-PLAN.md — SSG-06,08-12: Chile port (medium catalog + D-10 tone-colour fix #d52b1e)
- [ ] 04-13-PLAN.md — SSG-06,08-12: Canada port (medium catalog)
- [ ] 04-14-PLAN.md — SSG-06,08-12: UK port (medium catalog + D-10 tone-colour fix #012169)
- [x] 04-15-PLAN.md — SSG-06,08-12: NARA port (medium catalog + Catalog ↗ button support)
- [x] 04-16-PLAN.md — SSG-06,08-12: NASA port (medium catalog)
- [x] 04-17-PLAN.md — SSG-06,08-12: AARO port (large catalog + retires parse-aaro.py + extract-evidence.py)
- [ ] 04-18-PLAN.md — SSG-06,08-12 + PERF-01..04: GEIPAN port (3.3 MB → ≤500 KB + ~60 shards + D-10 tone-colour fix #0055a4 + frozen Lighthouse baseline)
- [x] 04-19-PLAN.md — SRC-01..04 + SSG-11,12: Pagefind cross-archive index + src/pages/search.astro + delete api/all.json (4.6 MB) + search.html
- [x] 04-20-PLAN.md — PERF-04 + SSG-10: Phase 4 close (Lighthouse HARD-flip + retire copy-legacy-archives.sh + sync-nav/footer.py + CI drift gates + verify-python-retired.sh) (completed 2026-05-28)


### Phase 04.1: Legacy reorg + stories/site-pages nav surface (INSERTED)

**Goal:** Move every legacy HTML file into `legacy/`, expose curated case narratives under a new `/stories/{slug}/` URL contract and informational site pages under `/<page>/`, extend Nav with `STORIES ▾` + `ABOUT ▾` dropdowns and Footer with `Pages` + `Stories` columns, update `copy-legacy-archives.sh` so dist output is unchanged for surviving legacy URLs, and 301-redirect every legacy `.html` path to its new canonical home.

**Requirements**: SSG-08, SSG-09, SSG-10, SSG-11, SRC-01, SRC-04, INF-02, INF-08, PERF-01, PERF-02

**Depends on:** Phase 4

**Plans:** 7 plans

Plans:
**Wave 1**

- [ ] 04.1-01-legacy-reorg-PLAN.md — `git mv` all legacy HTML + dormant-archive dirs into `legacy/`

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 04.1-02-copy-script-update-PLAN.md — rewrite `scripts/copy-legacy-archives.sh` to source from `legacy/` and strip prefix on copy
- [ ] 04.1-03-stories-routes-PLAN.md — `src/data/stories.json` manifest + `/stories/` index + `/stories/[slug]/` dynamic route (verbatim body extraction)
- [ ] 04.1-04-site-pages-routes-PLAN.md — `src/data/site-pages.json` + 6 site-page Astro routes (`/about/`, `/foia/`, `/glossary/`, `/map/`, `/timeline/`, `/whatsnew/`) preserving interactive scripts for map/timeline

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 04.1-05-nav-footer-dropdowns-PLAN.md — extend `Nav.astro` with `STORIES ▾` + `ABOUT ▾` (desktop CSS hover + mobile collapsible) and `Footer.astro` with Pages + Stories columns
- [ ] 04.1-06-url-contract-redirects-PLAN.md — append new canonicals to `URL-CONTRACT.txt`, extend `scripts/build-redirects.py` to emit legacy 301 block driven by stories.json + site-pages.json, parked utilities 301→/about/

**Wave 4** *(blocked on Wave 3 completion — operator checkpoint)*

- [ ] 04.1-07-verification-smoke-PLAN.md — `pnpm build` + Pagefind queries + curl-redirect harness + Lighthouse + human-verify @ 360/720/1024 px

### Phase 5: Scrape Automation

**Goal**: Move source ingestion off GitHub Actions cron onto Cloudflare Workers cron with a hybrid Akamai fallback, and replace the manual / local-only `gh release upload` path with a CI flow that survives partial failures.

**Depends on**: Phase 3 (SSG foundation must exist before the scrape pipeline writes into `data/<slug>.json` for Astro to consume). May begin in parallel with Phase 4 once the Phase 3 schema lands — Workers/cron development does not block archive porting and vice versa. Must complete before Phase 6 cutover so the post-cutover catalog stays fresh.

**Requirements**: SCRP-01, SCRP-02, SCRP-03, SCRP-04, SCRP-05, SCRP-06, SCRP-07, SCRP-08, SCRP-09, SCRP-10

**Success Criteria** (what must be TRUE):

  1. A Cloudflare Worker cron with a KV-backed fingerprint store (last-seen ETag + content-hash per source) runs on schedule and writes to an R2 staging bucket; per-source lanes are partitioned so a single bad source cannot starve others, and a KV cron-lock prevents overlapping invocations from racing.
  2. The hybrid Akamai strategy from the PMS-03 spike is implemented: Akamai-blocked sources fall through to a GitHub Actions runner using `curl_cffi`, all others stay on Workers; the `|| true` masks on `curl_cffi` install are removed, so a failed install fails the workflow loudly.
  3. New scraped binaries land in GitHub Releases via a `scripts/release-upload.py` helper with SHA-256 idempotency, explicit delete-then-upload (never `--clobber`), serialised concurrency, and per-archive release tags (`wargov-pdfs-2026q2`-style) — avoiding the 1000-asset/tag ceiling on shared `pdfs-v1` / `videos-v1`.
  4. A Worker → GitHub `repository_dispatch` payload triggers the ingest pipeline that normalises scraped JSON, commits manifest deltas to `data/<slug>.json`, and pushes — closing the loop so a new scrape becomes a new SSG build automatically.
  5. The manual `gh workflow run scrape.yml` trigger still works for ad-hoc / back-fill use, and assets > 2 GB are routed to R2 overflow via a URL-rewrite layer so physical storage location is transparent to the SSG.

**Plans**: 7 plans

Plans:
**Wave 1**

- [x] 05-01-PLAN.md — R2 bulk seed: operator-gate Phase 4 push + rewrite r2-sync.yml (add repository_dispatch + per-archive scope) + operator workflow_dispatch bulk seed
- [ ] 05-02-PLAN.md — Akamai spike Worker + `.planning/decisions/akamai-spike.md` ADR with locked AKAMAI_BLOCKED_SOURCES constant *(Task 1 scaffolded; Tasks 2+3 blocked on operator wrangler deploy)*

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 05-03-PLAN.md — Production Workers cron skeleton (`workers/scrape-cron/`) + wrangler.toml R2 + KV bindings + KV cron-lock (SCRP-07)

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 05-04-PLAN.md — Per-archive scrape lanes for the 4 active archives + ETag fingerprint diff + repository_dispatch emission
- [ ] 05-05-PLAN.md — GH Action ingest pipeline: ingest.yml + scrape-fallback.yml + release-upload.py (SHA idempotency, SCRP-05/06/10) + r2-promote.sh

**Wave 4** *(blocked on Wave 3 completion)*

- [ ] 05-06-PLAN.md — SCRP-08 fix on legacy scrape.yml (`|| true` removal) + verify-python-retired.sh extension

**Wave 5** *(blocked on Wave 4 completion)*

- [ ] 05-07-PLAN.md — E2E smoke + VERIFICATION matrix + Phase 5 close (STATE.md + ROADMAP.md updated)

### Phase 6: Hosting & Cutover

**Goal**: Stabilise the Cloudflare Pages preview for ≥ 7 days, swap `realufo.org` DNS off GitHub Pages, monitor a 7-day post-cutover window, archive (but never delete) the legacy workflow, and bring `CLAUDE.md` back into sync with reality.

**Depends on**: All previous phases — the SW kill-switch from Phase 1 must be ≥ 14 days old, every Phase 2 gate must be green on the preview, every Phase 4 archive must be passing visual regression / fidelity, the Phase 5 scrape pipeline must be writing to `data/*.json` cleanly. DNS TTL from Phase 1 must have been at 300 s for ≥ 7 days before the swap.

**Requirements**: HOST-01, HOST-02, HOST-03, HOST-04, HOST-05, HOST-06

**Success Criteria** (what must be TRUE):

  1. Cloudflare Pages preview deploy on `ssg-migration` runs without regression for ≥ 7 consecutive days (no visual-regression breakage, no SW errors, no fidelity drift), with an optional `preview.realufo.org` alias exposed for 1–2 weeks of public staging.
  2. DNS for `realufo.org` is swapped from GitHub Pages → Cloudflare Pages during a low-traffic window; the new SW registers from `BaseHead.astro` with a new cache-name prefix (so any stale-but-not-yet-deregistered kill-switch SW from Phase 1 cannot collide) and `updateViaCache: 'none'` on registration.
  3. A 7-day post-cutover monitoring window completes with Umami traffic, Lighthouse scores, and SW error tracking all stable — no spike in 404s, no LCP regression, no user-reported "site is empty" issues.
  4. The legacy GitHub Pages deployment workflow is archived (preserved in git history, not deleted) so a worst-case rollback can re-point DNS back within one TTL window.
  5. `CLAUDE.md` is updated end-to-end — design-system status reflects post-migration components, build process documents the Astro / Pagefind / Workers stack, hosting source-of-truth points at Cloudflare Pages — so the spec and the implementation agree on day 1 of v2 planning.

**Plans**: TBD

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Pre-Migration Safety | 0/5 | Not started | - |
| 2. Infrastructure & CI Scaffolding | 0/8 | Not started | - |
| 3. SSG Foundation | 6/6 | Complete   | 2026-05-27 |
| 4. Full Migration, Search, Offline, Performance | 12/11 | Complete   | 2026-05-28 |
| 5. Scrape Automation | 2/7 | In Progress|  |
| 6. Hosting & Cutover | 0/0 | Not started | - |

---

## Cross-Phase Dependencies

Hard sequencing constraints from `research/PITFALLS.md` (these cannot be reordered without re-opening known failure modes):

1. **Phase 1 → all later phases**: `URL-CONTRACT.txt` must exist on `main` before any SSG output replaces a URL; the SW kill-switch must be live on the OLD origin ≥ 14 days before any cutover.
2. **Phase 1 → Phase 5**: The Akamai egress spike (PMS-03) decides whether Phase 5 leans on Workers, GH Actions, or a hybrid. Phase 5 architecture is undecidable without that spike result.
3. **Phase 1 → Phase 6**: DNS TTL must be at 300 s for ≥ 7 days before the Phase 6 DNS swap.
4. **Phase 2 → Phase 3+**: Visual-regression / fidelity / tone-colour / JS-off / Lighthouse gates must exist as CI workflows before any SSG output can be evaluated against current `main` — otherwise regressions ship invisibly.
5. **Phase 3 → Phase 4**: One archive (wargov) must pass every Phase 2 gate from the new SSG before the 14-archive rollout begins — proof the Content Collections + layout + SW registration pattern actually works.
6. **Phase 3 → Phase 5 (partial parallelism)**: Once the Phase 3 `data/<slug>.json` schema is committed, the Workers cron pipeline can be developed in parallel with the Phase 4 archive porting — they don't share files. Phase 5 must complete before Phase 6 cutover so the post-cutover catalog stays fresh.
7. **Phases 1–5 → Phase 6**: All gates green + scrape pipeline writing cleanly + DNS prep complete are non-negotiable preconditions for the cutover window.

---

*Roadmap created: 2026-05-25*
*Last updated: 2026-05-25 by roadmapper agent*
