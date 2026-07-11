# Codebase Concerns

**Analysis Date:** 2026-07-11

> Full-repo refresh of the 2026-05-25 audit (198 commits stale, pre-migration).
> The project has since executed a big-bang Astro 5 / Cloudflare Pages
> migration (Phases 1–4 + 4.1 complete; Phase 5 "scrape automation" ~30%
> done and stalled). Most of the 2026-05-25 findings targeted the retired
> plain-HTML + Python build pipeline and are now **RESOLVED BY MIGRATION**.
> New concerns have emerged from the migration itself (dual build system,
> disabled CI gates, broken cron pipeline). Every item below is verified
> against the current tree at commit `e731163` (branch
> `quick/260615-3e3-wargov-release-03`, 5 commits ahead of `main`, unmerged).

---

## At a Glance — Severity Ranking

| # | Concern | Severity | Status |
|---|---------|----------|--------|
| 1 | `scripts/update_all.sh` calls 5 deleted Python builders — hard-broken | **HIGH** | NEW (post-migration regression) |
| 2 | `quality-gates.yml` auto-trigger disabled since 2026-05-29 — visual-regression / fidelity / tone-colours / js-off HARD-fail / mobile Lighthouse budget do not run on any push or PR | **HIGH** | NEW (accepted risk, undocumented expiry) |
| 3 | `scrape.yml` weekly cron hard-fails every run — references 5 deleted Python builders | **HIGH** | KNOWN — documented accepted risk (ADR), deferred to Phase 5 |
| 4 | Release-03: 2 large AARO/DOD videos (2.99 GiB + 1.19 GiB) never reached R2 — 2 AUD cards play → 404 | **HIGH** | LIVE, open ~1 month |
| 5 | Mobile Lighthouse HARD budget (LCP ≤2.5s, ≤500KB) is not the config actually gating CI — the live `lighthouse.yml` gate is desktop + soft-warn | **MEDIUM-HIGH** | NEW (documentation vs. reality drift) |
| 6 | `r2-sync.yml` push-trigger paths match gitignored binary globs — CI job structurally cannot sync in the common case | **MEDIUM** | NEW (design gap, real uploads are manual) |
| 7 | Dual build system: 4 Astro archives vs. 11 dormant legacy HTML via `copy-legacy-archives.sh` | **MEDIUM** | KNOWN — intentional interim state, retirement debt |
| 8 | 4 active-archive `index.astro` pages (600–870 lines each) duplicate filter/sort/pagination/stats markup with no shared layout | **MEDIUM** | NEW (same shape as old Python-builder duplication) |
| 9 | Playwright test suite (1,145 lines, 7 specs) exists but only runs via manual `workflow_dispatch` — not a merge-time safety net | **MEDIUM** | PARTIALLY RESOLVED (built, not wired) |
| 10 | CSP header deferred to Phase 6 — no Content-Security-Policy in production today | **LOW-MEDIUM** | KNOWN — tracked (D-07) |
| 11 | Stale duplicate `_headers` (repo root) vs. `public/_headers` (the one actually shipped) | **LOW** | NEW (dead config) |
| 12 | CF Pages 25 MiB per-file deploy limit | **LOW** | RESOLVED — self-healing guard added |
| 13 | Service worker registered on all pages / shell precache gap | **LOW** | RESOLVED by migration |
| 14 | Zero test coverage | **N/A** | RESOLVED — see #9 for the residual wiring gap |
| 15 | Inline-JSON multi-MB manifest anti-pattern (old GEIPAN 3.3 MB page) | **LOW** (for active surface) | RESOLVED for the 4 active archives; unchanged for dormant |

---

## Resolved Since Last Audit (2026-05-25)

These 2026-05-25 findings targeted the plain-HTML + Python build pipeline
that Phase 4 retired. Verified fixed on the current active surface
(wargov, aaro, nasa, nara):

- **Per-page inline-JSON bloat** — `index.html` (479 KB), `geipan/index.html`
  (3.3 MB) inline manifests. Active archives now ship sharded JSON
  (`data/wargov-shard-{2..6}.json`, `data/aaro-shard-1.json`,
  `data/nara-shard-1.json`) fetched progressively; `dist/index.html` is
  222 KB, `dist/aaro/index.html` 258 KB, `dist/nara/index.html` 216 KB,
  `dist/nasa/index.html` 98 KB. Still above the 500 KB *target* only for
  none of them — all four are under budget. GEIPAN/UK/etc. (dormant)
  remain unchanged at their old sizes since they ship as static legacy
  HTML (acceptable — dormant, not in the active-surface budget).
- **SW registered on only 12/~32 pages** — `src/layouts/BaseHead.astro`
  registers `/sw.js` structurally on every Astro-built page (100%
  coverage for the 4 active archives + all site/story pages). Dormant
  legacy HTML: 57 of 68 tracked pages already carry the registration
  (via the retired `patch-sw-registration.py`); residual gap is
  low-priority (dormant surface).
- **Shell precache excludes archive roots** — superseded by
  `@vite-pwa/astro` `injectManifest` (`src/sw.ts`); Workbox
  `precacheAndRoute(self.__WB_MANIFEST)` is driven by
  `injectManifest.globPatterns` in `astro.config.mjs`, not a hand-maintained
  SHELL array.
- **`sync.sh:144` `download.py` path mismatch** — `scripts/sync.sh` no
  longer shells out to per-archive Python downloaders for the rebuild
  step; it now delegates to `pnpm build` (`scripts/sync.sh:213-215`).
- **Manual nav/footer sync across 15+ archives** — `Nav.astro` and
  `Footer.astro` are now the single source of truth for the 4 active
  archives; `scripts/sync-nav.py` / `sync-footer.py` and their CI drift
  gates are deleted (Plan 04-20).
- **Hardcoded release-repo mismatch** (`build-details.py:42`) —
  `build-details.py` itself is deleted; per-archive R2 URLs are now
  generated by `normalize-*.py` from a single `assets.realufo.org` base.
- **Zero unit/E2E tests** — `tests/` now has 7 Playwright specs
  (1,145 lines): `visual-regression`, `verify-fidelity.py`
  (fidelity samples), `tone-colours`, `js-off` (hard-fail architecture
  guarantee), Lighthouse budget, `pagination`, `lightbox`, `search`,
  `sw`, `r2-urls`. See concern #9 below for the residual "not wired to
  CI trigger" gap — the tests exist, but are not yet a merge gate.
- **Images lacking `loading="lazy"` on hero carousel** — superseded;
  `src/components/HeroCarousel.astro` is a fresh Astro component, not
  audited here in detail but not flagged by the Lighthouse/visual gates
  when they do run.
- **`api/all.json` / `api/by-archive.json` both 4.6 MB (Lunr)** —
  Lunr search deleted entirely; replaced by Pagefind (`dist/pagefind/`,
  1.0 MB total for the 4-archive index) — commit `374265a`.

---

## Known Live Issues (explicitly tracked, verify-each)

### 1. Release-03: 2 large videos pending R2 upload — 2 AUD cards 404 [HIGH, LIVE]

**Files:** `data/wargov-shard-6.json:112,116`, `scripts/dvids2dod-r03.json:8-9`

Two DVIDS→DOD mappings resolved and wired into cards, but the source
binaries were never uploaded to R2:

- `DOD_111764796.mp4` (2.99 GiB, DVIDS `1010319`) — card `r278` (NASA-UAP-D024)
- `DOD_111764902.mp4` (1.19 GiB, DVIDS `1010336`) — card `r279` (NASA-UAP-D025)

Both card templates in `data/wargov-shard-6.json` point their `Open`
and `Download` buttons at
`https://assets.realufo.org/videos/wargov/DOD_111764796.mp4` and
`…DOD_111764902.mp4` — URLs that 404 until uploaded. Root cause:
wrangler's `r2 object put` caps single-PUT uploads at 300 MiB; these
two files exceed the cap by 10× and 4×. Per
`.planning/quick/260615-3e3-fetch-third-war-gov-ufo-release-and-upda/260615-3e3-SUMMARY.md`,
an S3-multipart path (aws-cli or rclone against R2's S3-compat
endpoint, using R2 S3 API keys) is required. Source files staged at
operator machine `/Users/laichan/UFO/AARO061226/` per STATE.md TODOs
— **not** in this repo, not in git.

**Verified still open:** no commit since `e731163` (2026-06-15)
mentions these DVIDS IDs, "multipart", or touches
`data/wargov-shard-6.json`. `git log --all --grep` for both IDs
returns only the original resolve/upload commits. The branch this
work landed on (`quick/260615-3e3-wargov-release-03`) is 5 commits
ahead of `main` and **still unmerged** — this fix, and everything else
in Release 03 (72 rows, R2 mirror, Pagefind reindex), has not reached
`main` at all as of 2026-07-11, nearly a month after the quick-task
summary was written.

**Fix:** (a) operator runs the S3-multipart upload for the 2 files,
(b) merge `quick/260615-3e3-wargov-release-03` → `main` to ship
Release 03 (72 new records) to production at all.

### 2. CF Pages 25 MiB per-file deploy limit [LOW, RESOLVED with caveat]

**Files:** `scripts/copy-legacy-archives.sh:36-40` (`MAX_BYTES`,
`copy_one()`)

Commit `15e0233` (2026-05-29) fixed the immediate incident (two
geipan mp4s, 40 MiB + 4.4 MiB, broke `deploy-cf-pages.yml`) by
deleting the files. Since then, `copy_one()` in
`copy-legacy-archives.sh` was hardened to **skip** (not fail) any
tracked file over 25 MiB with a stderr warning, rather than letting
the whole CF Pages upload abort. Largest currently-tracked file is
`legacy/chile/pdfs/DGAC-CEFAA-Publicacion-Web-2019.pdf` at 4.7 MB —
comfortably under the cap.

**Residual risk:** the skip is silent-ish (stderr only, no CI
assertion that `skipped_count == 0`). A future scrape that
re-introduces an oversized dormant-archive binary would silently drop
it from `dist/` rather than failing the build — a content gap that's
easy to miss. **Fix approach:** assert `skipped_count == 0` at the
end of `copy-legacy-archives.sh` for a hard CI signal, or explicitly
allowlist expected skips.

### 3. Dual build system: 4 Astro archives vs. 11 dormant legacy HTML [MEDIUM, KNOWN/INTENTIONAL]

**Files:** `scripts/copy-legacy-archives.sh`, `legacy/` (28 dirs),
`.planning/decisions/python-build-retired.md`

By design per CLAUDE.md §2/§13: wargov/aaro/nasa/nara are owned by
Astro (`src/pages/**`); the 11 dormant archives (geipan, uk, brazil,
chile, argentina, canada, italy, nz, peru, spain, uruguay — plus
partial-port sub-pages for aaro/nara/nasa/nz/uruguay) ship as
git-tracked static HTML copied wholesale into `dist/` by
`copy-legacy-archives.sh` at postbuild. This is an accepted
interim state (ADR `python-build-retired.md` "Neutral" section),
not a bug — but it means:

- Two completely different rendering/JS-invariant implementations
  coexist (Astro components + `invariants.ts` for active; hand-rolled
  inline JS baked into 2026-05-era HTML for dormant).
- Any future CLAUDE.md §7 JS-invariant change must be applied twice —
  once in `invariants.ts`, once by hand-patching legacy HTML (no
  automated sync exists for the dormant surface; `sync-nav.py` /
  `sync-footer.py`, the old drift-gate tooling, are deleted).
- The 11 dormant `build-<slug>.py` scripts are dead code from the
  active-surface point of view but kept alive only because `scrape.yml`
  still calls them (see concern below) — a genuinely circular
  dependency: `scrape.yml` is broken *and* is the only reason these
  scripts survive deletion.

**Fix approach:** either (a) hard-delete the 11 dormant archives + their
Python build/scrape/normalize scripts in a future milestone (tracked
in CLAUDE.md §2 as a documented future decision), or (b) rewrite
`scrape.yml` end-to-end in Phase 5 and re-evaluate which dormant
builders survive.

### 4. Surviving Python under `scripts/` still referenced by `scrape.yml` [HIGH, KNOWN — but now provably worse than the ADR describes]

**Files:** `.github/workflows/scrape.yml:41-51`,
`.planning/decisions/python-build-retired.md`

The ADR accepts as a documented risk that `scrape.yml` "is presently
broken in main: it references already-deleted `build-{aaro,nasa,nara}.py`."
Verified against the current tree — the breakage is **worse** than a
soft warning:

```yaml
- name: Rebuild all archive HTML
  run: |
    python3 scripts/build-nasa.py && \
    python3 scripts/build-nara.py && \
    python3 scripts/build-aaro.py && \
    python3 scripts/build-geipan.py && \
    ...
    python3 scripts/build-details.py && \
    python3 scripts/build-wargov.py
```

This step has **no** `|| true` (unlike every other step in the same
workflow) and chains with `&&`. `scripts/build-nasa.py` (first in the
chain) does not exist —confirmed via `ls`: `build-wargov.py`,
`build-details.py`, `build-nara.py`, `build-nasa.py`, `build-aaro.py`
are all absent (deleted by Plan 04-20, commit `f3b40df`). The job
fails outright at this step on every Monday 06:00 UTC cron tick and on
every manual `workflow_dispatch`. Corroborating evidence: `git log
--all --grep="chore: weekly auto-rebuild"` returns **zero commits** —
the auto-commit step (which comes after the broken rebuild step) has
never once run since this workflow was authored.

**Impact:** the entire weekly scrape → rebuild → recommit pipeline for
the 11 dormant archives + `api/`, `feeds/`, `sitemap.xml`, `sw.js`
version stamp, and `CHANGELOG.md` auto-append has been silently dead
since 2026-05-28. Nobody depends on it today (Phase 5 scrape
automation supersedes it once built), but any content staleness on
dormant archives will go undetected indefinitely, and GitHub Actions
almost certainly emails scheduled-workflow-failure notifications to
watchers every week that get ignored.

**Fix:** Phase 5 (see `.planning/phases/05-scrape-automation/`) is
the planned replacement; Plans 05-03..05-07 are unstarted (only 05-01
and 05-02 have SUMMARY.md, both partial/blocked-on-operator). Until
Phase 5 lands, either fix the 5 missing script references (regenerate
minimal versions or point at the dormant-archive equivalents) or
disable the cron trigger to stop the weekly noise.

### 5. Akamai egress / scrape automation — stalled at Phase 5 Wave 1 [MEDIUM, OPEN]

**Files:** `workers/akamai-spike/`,
`.planning/phases/05-scrape-automation/05-02-SUMMARY.md`

Phase 5's Plan 05-02 (Akamai-blocked-source spike Worker) is
**1 of 3 tasks complete**: the `realufo-akamai-spike` Worker scaffold
exists (`workers/akamai-spike/src/index.ts`, 108 lines) but has never
been deployed or invoked — Task 2 (operator deploys + invokes) and
Task 3 (`.planning/decisions/akamai-spike.md` ADR, which does not yet
exist) are blocked on operator action against the live Cloudflare
account. Per `05-CONTEXT.md`, Plans 05-03 (Workers cron skeleton) and
05-04 (per-archive scrape lanes) cannot proceed until this ADR locks
the `AKAMAI_BLOCKED_SOURCES` constant. **Net effect:** Phase 5 has
been stalled at Wave 1 since 2026-05-28 with no forward progress
recorded in git history since (all subsequent commits are quick-tasks
or Phase 4.1 work, not Phase 5 plans).

**Fix:** operator must run the 5-command sequence documented in
`05-02-SUMMARY.md` Task 2 (`wrangler login` → `kv namespace create` →
`wrangler deploy` → `curl` invoke → capture JSON) before Phase 5 can
resume.

### 6. URL-contract / redirects drift — gate exists but doesn't run [MEDIUM]

**Files:** `URL-CONTRACT.txt`, `_redirects`, `scripts/build-redirects.py`,
`.github/workflows/quality-gates.yml` (`redirects` job)

`build-redirects.py --check` (drift gate) and `verify-redirects.sh`
(curl harness) are both implemented and would catch URL-contract drift
— but they only run inside `quality-gates.yml`, whose auto-trigger is
disabled (see concern below). `URL-CONTRACT.txt` was last regenerated
2026-06-02 (67 canonical routes) and nothing in the last ~40 commits
suggests routes have drifted since, but there is currently no
automatic gate that would catch it if they did.

---

## Tech Debt

### `scripts/update_all.sh` is hard-broken — calls 5 deleted Python builders [HIGH, NEW]

**Files:** `scripts/update_all.sh:67-73`

```bash
maybe "python3 '$ROOT/scripts/build-wargov.py'"
maybe "python3 '$ROOT/scripts/build-aaro.py'"
maybe "python3 '$ROOT/scripts/build-details.py'"
maybe "python3 '$ROOT/scripts/build-nasa.py'"
maybe "python3 '$ROOT/scripts/build-nara.py'"
```

All 5 scripts were deleted by Plan 04-20 (commit `f3b40df`,
2026-05-28); `update_all.sh` itself was last touched 2026-05-22 and
never updated to match. Unlike `scrape.yml` (whose breakage is an
explicit, documented, accepted ADR risk), this breakage is
**undocumented** anywhere except this audit. `README.md:330-331`
still tells operators `scripts/update_all.sh` "wraps the typical
subset" of the sync pipeline — a contributor following the README
today hits 5 back-to-back `python3: can't open file` errors. It also
still calls `gh release upload videos-v1 …` / `gh release upload
pdfs-v1 …` (lines 51, 62) targeting GitHub Releases tags that the
current R2-based pipeline (`assets.realufo.org`) no longer treats as
the primary asset source for active archives.

**Fix:** either delete `scripts/update_all.sh` and its README
reference (its only non-broken responsibility — release upload — is
now superseded by manual `wrangler`/`rclone` R2 uploads per the
Release-03 workflow), or rewrite it to delegate to `pnpm build` like
`sync.sh` now does.

### `quality-gates.yml` auto-trigger disabled since 2026-05-29 — 6-job hard-fail gate matrix is dormant [HIGH, NEW]

**Files:** `.github/workflows/quality-gates.yml:14-25`

```yaml
on:
  # 2026-05-29 — deployment_status trigger disabled. ...
  # deployment_status:
  workflow_dispatch:
```

This workflow implements 6 well-designed parallel gates against every
CF Pages preview deploy: `visual-regression` (Playwright vs. 60 PNG
baselines), `fidelity` (byte-diff vs. locked samples), `tone-colours`
(CLAUDE.md §3.1 fixture), `js-off` (**explicitly documented as
"HARD-FAIL UNCONDITIONALLY... softening this gate would defeat the
entire pre-rendered-cards architecture"**), `lighthouse` (mobile,
LCP ≤2.5s / ≤500KB, HARD per Plan 04-20's PERF-04 sign-off), and
`redirects` (drift + curl harness). The `deployment_status:` trigger
that would fire this matrix after every CF Pages deploy has been
commented out since commit `b4bb39d` because `verify-redirects.sh`'s
sample list still referenced Phase-2-era legacy URLs
(`belgian-wave.html`, `cash-landrum.html`, etc.) that Phase 4.1
retired, causing every single auto-run to fail immediately.

**Impact:** since 2026-05-29, none of these 6 gates has run
automatically on any of the ~44 subsequent commits to `main`
(Phase 4.1 legacy-reorg, stories/site-pages routes, nav dropdowns,
redirects rewrite, map/glossary/timeline fixes, Release-03 work).
They are reachable only via manual `workflow_dispatch` with an
explicit `preview_url` input — nobody appears to have run it since
(no `.lighthouseci/` artifact commits or workflow-run references
found post-2026-05-29). The `js-off` architectural guarantee in
particular — the single test that would catch a regression back into
client-side hydration, which PROJECT.md treats as a core constraint —
currently has no CI enforcement at all.

**Fix:** refresh `scripts/verify-redirects.sh`'s sample URL list (or
have it derive samples from the current `URL-CONTRACT.txt` instead of
a hardcoded list) and re-enable the `deployment_status:` trigger. This
is a small, well-scoped fix relative to its risk — the gate matrix
itself is intact and just needs its trigger and one input list
refreshed.

### Two Lighthouse configs, only the weaker one is actually live [MEDIUM-HIGH, NEW]

**Files:** `.lighthouserc.json` (used by `.github/workflows/lighthouse.yml`,
live on every push+PR), `.lighthouserc.cf.json` (used by the disabled
`quality-gates.yml` `lighthouse` job)

Plan 04-20's ADR (`python-build-retired.md`) and STATE.md both record
"Lighthouse HARD-flip — warn → error (PERF-04)" as a **closed** Phase
4 milestone. That HARD, mobile-throttled, 2.5s-LCP/500KB-budget config
lives in `.lighthouserc.cf.json` — but that file is only consumed by
`quality-gates.yml`, which per the concern above does not run
automatically. The workflow that *does* run on every push and PR
(`lighthouse.yml`) uses `.lighthouserc.json`, which is:
- **desktop** preset, not mobile (`"preset": "desktop"` —
  contradicts CLAUDE.md §8 mobile-first / the 360px baseline used
  everywhere else in the project's own test fixtures)
- **`"warn"`**-level assertions on category scores only
  (performance/accessibility/best-practices/seo), not the LCP/byte
  budget assertions at all
- uploads to `temporary-public-storage` (ephemeral, no artifact
  retention)

`.lighthouserc.cf.json` also carries a self-contradictory ownership
comment: `"owner": "ssg-migration branch; do NOT merge into main —
legacy .lighthouserc.json owns the main branch gate (D-32)"` — yet
the file is committed on `main` today and is the one actually
implementing the "HARD" PERF-04 requirement. Net effect: the
performance guarantee the project's own documentation considers
signed-off and enforced is not the one actually gating merges.

**Fix:** decide which config is canonical, delete or clearly
re-scope the other, and correct the stale ownership comment. If the
mobile/hard budget is the intended gate, it needs a live trigger
(ties into the `quality-gates.yml` re-enable fix above).

### `r2-sync.yml` push-trigger paths target gitignored binaries [MEDIUM, NEW]

**Files:** `.github/workflows/r2-sync.yml:29-40`, `.gitignore`

The workflow's `push:` trigger watches paths like `bundles/**/*.pdf`,
`**/videos/**/*.mp4`, `<slug>/bundles/**/*.pdf` to fire an
rclone-to-R2 sync. But every one of those path globs points at
directories `.gitignore` explicitly excludes (`bundles/Release_1/*.pdf`,
`aaro/videos/`, `nasa/pdfs/`, `nara/pdfs/`, etc. — see `.gitignore`
lines 20-38). A normal `git push` can never contain a diff matching
these paths, because the files are never committed by design (binary
CDN policy, CLAUDE.md §5.2). The `workflow_dispatch` /
`repository_dispatch` paths still work (they don't depend on a push
diff), but they too assume the binaries already exist in the runner's
**checkout** (`if [ -d "bundles/Release_1" ]` — a gitignored,
uncommitted directory that a fresh `actions/checkout@v4` will never
populate). In practice, every real upload to date (Release 01, 02, 03)
has been performed by a human running `wrangler`/`rclone` locally,
never via this CI workflow — confirmed by the Release-03 quick-task
SUMMARY describing a fully manual R2 upload with 2 files failing on
wrangler's 300 MiB cap.

**Fix:** either (a) add a fetch/download step to `r2-sync.yml` before
the rclone sync (re-running the relevant `dl-<slug>.sh` against the
runner), or (b) document explicitly that this workflow is designed
only for the `repository_dispatch` path fed by a future Worker that
stages binaries somewhere the runner *can* reach (e.g., a private R2
staging bucket, per the `05-05 per-archive promote` plan referenced in
the workflow's own comments) — and accept that the push-trigger
branch is presently dead code.

### 4 active-archive index pages duplicate filter/sort/pagination markup [MEDIUM, NEW — same shape as old Python-builder debt]

**Files:** `src/pages/index.astro` (867 lines), `src/pages/aaro/index.astro`
(618 lines), `src/pages/nara/index.astro` (608 lines),
`src/pages/nasa/index.astro` (606 lines)

The 2026-05-25 audit's top concern was that per-archive Python
builders (`build-aaro.py` at 1,360 lines) each hand-rolled their own
manifest/HTML/JS, making a 16th archive expensive to add. The
migration replaced the *JS* half of this problem cleanly — all 4
active pages share `src/scripts/invariants.ts` (572 lines, injected
once via `RootLayout.astro`) for lightbox/nav/hamburger behaviour. But
the *markup* half of the duplication persists: each of the 4 pages
independently implements its `arch-controls-bar` / `filter-bar` /
`stats-grid` structure (6 matches each via
`grep -c "arch-controls-bar\|filter-bar\|stats-grid"`) with no shared
`ArchiveLayout.astro` or `ArchivePage` component. There is no
`src/layouts/` entry besides `BaseHead.astro` and `RootLayout.astro`.

**Impact:** smaller than the old problem (4 archives, not 15+), but
the same shape — reactivating a 5th archive (e.g. NZ or Uruguay,
which already have partial Astro page templates per CLAUDE.md §2)
means copying ~600 lines of markup/filter-wiring rather than
extending a shared component.

**Fix:** extract a shared `ArchiveIndexLayout.astro` (or a
`<ArchiveControls>` + `<ArchiveGrid>` component pair) that the 4
pages compose, parameterised by content-collection name + tone
colour. Lower priority than the CI-gate issues above since the
active surface is stable at 4 archives with no near-term 5th planned.

### Stale duplicate `_headers` files [LOW, NEW]

**Files:** `_headers` (repo root), `public/_headers`

Two files exist with near-identical rules (`/sw.js` no-cache,
`Strict-Transport-Security`, `X-Content-Type-Options`, immutable
caching for `/assets/*` and `/_astro/*`). Only `public/_headers` is
actually shipped (Astro auto-copies `public/` → `dist/`); the
repo-root copy's own comment says it exists for "the legacy Python
build path" — which no longer exists post Plan 04-20. The root copy
is dead weight that must be hand-kept in sync (currently identical
except for one comment line) or it will silently drift.

**Fix:** delete the repo-root `_headers`; keep `public/_headers` as
the single source (Astro's own copy mechanism already handles
`dist/`).

### `.lycheeignore`, `.htmlvalidate.json` reference a retired workflow [LOW]

**Files:** `.htmlvalidate.json`

`html-validate.yml` was deleted by Plan 04-20 (per
`python-build-retired.md`, "redundant with quality-gates.yml"), but
`.htmlvalidate.json` (643 bytes) remains committed at repo root with
no consumer. Harmless but confusing to a contributor searching for
"how is HTML validated."

### README.md still references the pre-rename repo path [LOW]

**Files:** `README.md:88-89,396,411,434`

`README.md` clone/cron examples still use
`war-gov-ufo-release`/`git clone https://github.com/<you>/war-gov-ufo-release`
even though CLAUDE.md §5.1 documents the canonical remote as
`hectorchanht/gov-ufo-archive` (local folder name is historical).
Cosmetic, but a new contributor following the README literally will
clone into a directory name that no longer matches the on-disk
convention CLAUDE.md assumes.

---

## Known Bugs

### Release-03 AUD cards 404 on Play/Download

See "Known Live Issues #1" above — `DOD_111764796.mp4` /
`DOD_111764902.mp4` referenced by `data/wargov-shard-6.json` but not
present at `assets.realufo.org`.

### `scrape.yml` fails at "Rebuild all archive HTML" every scheduled run

See "Known Live Issues #4" above.

---

## Security Considerations

### No Content-Security-Policy header [LOW-MEDIUM, KNOWN/TRACKED]

**Files:** `_headers`, `public/_headers`

Both `_headers` files explicitly defer CSP to "Phase 6 cutover (D-07)."
`Strict-Transport-Security` and `X-Content-Type-Options: nosniff` are
present; `Content-Security-Policy` is not. This is a documented,
tracked deferral rather than an oversight — flagged here so it isn't
lost, since Phase 6 has not yet started (Phase 5 is the current,
stalled, in-progress phase).

### `esc()` / URL-scheme trust boundary carried over from the old templates

The 2026-05-25 audit flagged that the legacy `scripts/templates/archive.py`
`esc()` helper escaped HTML entities but not `javascript:` URL schemes
before `window.open(a.u, '_blank')`-style calls. The equivalent pattern
now lives in `src/scripts/invariants.ts`'s card-open handler
(reading `data-url`/`data-src` attributes rendered from Astro
content-collection frontmatter). Content sources are trusted CSV/JSON
scraped from official `.gov`/`.mil` sources and normalized by
`normalize-*.py`, so exploitability is low, but no explicit
`https:`/`http:`/`mailto:`-only allowlist exists in `invariants.ts` for
these attribute reads. Low priority given the closed, curated content
pipeline, but worth a defensive fix if the project ever ingests
less-trusted sources (e.g. a future user-submission feature).

### No leaked secrets in source [VERIFIED CLEAN]

Re-audited: `grep -rn "API_KEY\|SECRET\|TOKEN\|password"` across
`scripts/`, `.github/workflows/`, `workers/` returns only legitimate
`${{ secrets.* }}` GitHub Actions interpolations
(`CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_R2_ACCESS_KEY`,
`CLOUDFLARE_R2_SECRET_KEY`, `CLOUDFLARE_ACCOUNT_ID`,
`LHCI_GITHUB_APP_TOKEN`). `.gitignore` now explicitly lists `.env`,
`.dev.vars`, `*.pre-bounce.md` (added since the 2026-05-25 audit,
which flagged their absence — **RESOLVED**). No `.pem`/`.key`/
credential files tracked.

---

## Performance Bottlenecks

### Active-surface pages are within budget; dormant surface is not tracked

`dist/index.html` 222 KB, `dist/aaro/index.html` 258 KB,
`dist/nara/index.html` 216 KB, `dist/nasa/index.html` 98 KB — all
under the 500 KB target from STATE.md's Performance Metrics table.
`dist/pagefind/` totals 1.0 MB (sharded WASM, loads incrementally),
replacing the old 4.6 MB Lunr blob. **However**, per the "two
Lighthouse configs" concern above, there is currently no live CI gate
verifying these numbers stay under budget on every change — the
config that asserts it is wired to a disabled trigger.

### Dormant archives unchanged (out of active budget by design)

The 11 dormant archives (geipan 3.2 MB `index.html` + 3.1 MB
`cases.json`, uk, brazil, etc.) retain their pre-migration weight
since they ship as static legacy HTML, not Astro pages. Acceptable per
CLAUDE.md §2 (not user-navigable from the active surface), but direct
URL visitors to `/geipan/` still pay the full 6+ MB weight with no SW
precache coverage guarantee (dormant pages get `data-pagefind-ignore`
but the migration's SW/precache work targeted the active surface).

---

## Fragile Areas

### `scripts/copy-legacy-archives.sh` is the sole guardian of the dormant-archive URL contract

**Files:** `scripts/copy-legacy-archives.sh`

A single postbuild bash script (with a hand-maintained per-slug loop
and an explicit skip-list for partial-port archives) is now the only
thing standing between `legacy/<slug>/` and the correct `dist/<slug>/`
URL. Getting the skip-list wrong (e.g., accidentally copying a
legacy `index.html` for a partial-port slug like `aaro`) would
silently shadow the Astro-rendered route with stale static HTML — the
script has an explicit comment acknowledging this exact risk ("a 404
here would break the live site") but no automated test asserts the
skip-list matches the actual set of Astro-owned routes.

### Phase 5 (scrape automation) is ~30% done and stalled with no forward commits

**Files:** `.planning/phases/05-scrape-automation/05-0{3,4,5,6,7}-PLAN.md`
(no matching SUMMARY.md files)

Plans 05-03 through 05-07 (Workers cron skeleton, per-archive scrape
lanes, GH Actions curl_cffi runner, R2 promote pipeline, and
whatever 05-07 covers) have PLAN.md files but no SUMMARY.md — they
have not been executed. All work since 2026-05-28 has been Phase 4.1
(legacy reorg) or ad-hoc quick-tasks (Release 03), not Phase 5. The
scrape-automation milestone is open-ended until the Akamai spike
(concern above) unblocks it.

### `src/sw.ts` `ALLOW_SKIP_WAITING = false` is a manual Phase-6 flip

**Files:** `src/sw.ts:44-49`

The service worker intentionally does not `skipWaiting()` on install
(`ALLOW_SKIP_WAITING = false`, gated behind a runtime global rather
than inlined so a test can grep-assert the literal). The code comment
states "Phase 6 cutover plan flips to TRUE after users have
transitioned off the Phase 1 kill-switch SW" — this is a manual
one-line flip that must be remembered and executed at the correct
point in a future Phase 6, with no tracking issue found referencing
it besides this source comment and CLAUDE.md §13.

### Root-level `sw.js` kill-switch — stale artifact of uncertain relevance

**Files:** `sw.js` (repo root, 92 lines)

This is the Phase-1 kill-switch service worker (self-unregisters,
nukes all caches, intended for the *old* GitHub-Pages-hosted origin
during cutover). It is **not** the service worker Astro ships — the
production SW is compiled from `src/sw.ts` via `@vite-pwa/astro`
`injectManifest` and relocated to `dist/sw.js` by a custom Astro
integration in `astro.config.mjs` (`swRelocator`). Root `sw.js` is
version-stamped by `scripts/build-sw.py` and is not obviously wired
into any current build or deploy step (`copy-legacy-archives.sh` only
copies from `legacy/`, not repo-root files). Given CF Pages is the
live origin today (DNS cutover already happened per commit history),
this file appears to be inert leftover from the pre-cutover safety
plan. Not urgent, but worth an explicit decision: confirm it's truly
dead and delete it, or document why it's still needed.

---

## Scaling Limits

### GitHub Releases per-tag asset quotas (carried over, now secondary)

Still true in principle (~1000 assets/tag), but R2
(`assets.realufo.org`) is now the primary CDN for active-archive
binaries (per Release-03's URLs: `assets.realufo.org/videos/wargov/…`,
`assets.realufo.org/pdfs/wargov/…`). GitHub Releases
(`pdfs-v1`, `videos-v1`, `wargov-r02-v1`) remain as an optional
cold-storage backup per the Release-03 SUMMARY ("optional GH Releases
cold-storage backup … cards do NOT reference these") — lower priority
than before.

### R2 single-PUT 300 MiB wrangler cap

Directly caused Known Live Issue #1. Any future single-file asset over
300 MiB (this project already has 2, and AARO/DOD video releases have
historically included multi-GB files) requires an S3-multipart path
that is currently manual/undocumented as a repeatable script — no
`scripts/upload-r2-multipart.sh` or equivalent exists yet. **Fix:**
codify the multipart upload as a script (aws-cli or rclone against the
R2 S3-compat endpoint, matching the credentials/config pattern already
established in `.github/workflows/r2-sync.yml`) so this doesn't
require a bespoke operator runbook every time a release includes a
large video.

---

## Dependencies at Risk

### Astro 5.x pin — verify on every `pnpm add`/lockfile bump

**Files:** `package.json:34` (`"astro": "~5.18.0"`),
`.planning/decisions/astro-version-pin.md`

Pinned to `~5.x` (not `^5`) specifically because Astro 6 broke the
`@astrojs/cloudflare` adapter's prerender behaviour (upstream issue
#15684, per STATE.md Key Decisions). `@astrojs/cloudflare` itself is
on `^12.6.0` (caret, not pinned) — a minor/patch bump to the adapter
could reintroduce adapter-specific breakage independent of the Astro
core pin. No CI check currently asserts the Astro version stays
within the `~5.18` range beyond the lockfile itself.

### `curl_cffi` soft-installed in `scrape.yml` [carried over, now secondary]

`pip install curl_cffi || true` remains at `.github/workflows/scrape.yml`
line ~15, but since the workflow fails at a *later*, unconditional step
(`Rebuild all archive HTML`, no `|| true`) regardless of whether
`curl_cffi` installed, this particular soft-fail is currently masked by
the bigger, unconditional breakage documented above. Once `scrape.yml`
is fixed/rewritten (Phase 5), this soft-install risk becomes live again
and should be hardened at that point.

### `wrangler` version drift risk between local operator and CI

**Files:** `.github/workflows/deploy-cf-pages.yml` (pins
`wranglerVersion: '4.95.0'`), `workers/akamai-spike/package.json`
(`wrangler ^4.95.0`, caret)

The deploy workflow pins wrangler exactly; the Akamai-spike Worker's
`package.json` uses a caret range. A future `pnpm install` in
`workers/akamai-spike/` could pull a wrangler minor ahead of what's
been validated, though the spike Worker is throwaway/low-stakes by
design.

---

## Missing Critical Features

### No repeatable large-file R2 upload path

See Scaling Limits above — the 300 MiB single-PUT cap has already
blocked one release from shipping completely (Known Live Issue #1)
and will recur for any future large-video release until a scripted
multipart path exists.

### No automated "scrape.yml is red" alerting beyond GitHub's default email

Given `scrape.yml` has been failing every scheduled run since
2026-05-28 with (per the evidence above) apparently zero human
follow-up commits addressing it, GitHub's default scheduled-workflow-
failure email notifications are evidently not being acted on. No
Slack/issue-create escalation exists (this was also flagged, unfixed,
in the 2026-05-25 audit).

---

## Test Coverage Gaps

### Playwright suite exists (1,145 lines) but has no automatic trigger [MEDIUM — largest residual gap from the old "zero tests" finding]

**Files:** `tests/visual-regression.spec.ts` (59),
`tests/tone-colours.spec.ts` (67), `tests/js-off.spec.ts` (87),
`tests/search.spec.ts` (92), `tests/lightbox.spec.ts` (183),
`tests/sw.spec.ts` (191), `tests/r2-urls.spec.ts` (191),
`tests/pagination.spec.ts` (275)

This is the single biggest structural improvement since the
2026-05-25 audit (which found zero tests anywhere) — real regression
coverage now exists for exactly the areas the old audit called out as
undertested (lightbox URL routing, SW cache strategy, search). But
per the `quality-gates.yml` disabled-trigger concern above, none of
these specs run on a normal push or PR today; they require a manual
`workflow_dispatch` with a `preview_url` input. There is also no
`"test"` script in `package.json` — a contributor has no single local
command to run the suite without first standing up a preview URL and
passing `PREVIEW_URL` manually. **Fix:** re-enabling the
`quality-gates.yml` trigger (already recommended above) closes most of
this gap in one move; additionally consider a `pnpm test` script
alias for local `PREVIEW_URL=http://localhost:4321 pnpm exec
playwright test`.

### No unit tests for Python normalizers

**Files:** `scripts/normalize-aaro.py`, `normalize-csv.py`,
`normalize-nara.py`, `normalize-nasa.py`, `normalize-nz.py`,
`normalize-uruguay.py`

These are the D-10 "LOCKED contract with `Card.astro`" scripts — any
CSV/JSON→content-collection field mismatch here silently produces
malformed cards. Covered indirectly by `js-off.spec.ts` /
`visual-regression.spec.ts` (which would catch a rendering break) but
not by a focused unit test on the transform logic itself (e.g., DVIDS
ID resolution, release-batch mapping, R2 URL rewriting). The
`--check` mode flags exist for drift detection (e.g.
`normalize-csv.py --check`) but are invoked manually per the
Release-03 SUMMARY, not gated in CI.

---

*Concerns audit: 2026-07-11*
