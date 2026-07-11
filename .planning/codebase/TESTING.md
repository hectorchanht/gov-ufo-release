# Testing Patterns

**Analysis Date:** 2026-07-11

This document supersedes the 2026-05-25 version, which stated "no test
framework — static HTML archive." That is no longer accurate: the
Astro migration (Phase 2 onward) added a real Playwright spec suite
(`tests/`) plus several standalone Python/shell verification scripts
wired into a dedicated `quality-gates.yml` CI workflow. **There is
still no unit-test framework** (no Jest/Vitest/pytest for isolated
function-level tests) — all verification is either (a) Playwright
end-to-end specs against a live deployed URL, or (b) CI-gate scripts
that fetch/parse a live deployment and assert structural/content
invariants. Treat "run the test suite" as "run the CI gate matrix
against a preview URL," not "run `pnpm test`" — **there is no `test`
script in `package.json`.**

---

## 1. Test framework

**Runner:** Playwright (`@playwright/test` 1.49.0, pinned identically
to the `playwright` package itself — `package.json` devDependencies).
Chromium-only (`tests/playwright.config.ts` projects array has a single
`chromium` entry using `devices['Desktop Chrome']`) — this is a
deliberate decision (D-15), not an oversight.

**Config:** `tests/playwright.config.ts`
- `testDir: '.'` — resolves relative to the config file's own
  directory, i.e. `tests/` (NOT `tests/tests/` — a documented gotcha in
  the file's header comment).
- `testMatch: '**/*.spec.ts'`
- `fullyParallel: true`, `workers: 4`
- `use.baseURL`: `process.env.PREVIEW_URL || 'https://realufo.pages.dev'`
  — **every spec runs against a live deployed URL**, not a local dev
  server. There is no `webServer` block spinning up `astro dev` /
  `astro preview` for these specs.
- `expect.toHaveScreenshot`: `maxDiffPixelRatio: 0.001`, `threshold:
  0.1`, `animations: 'disabled'` (D-16 — 0.1% pixel-diff hard-fail
  budget for visual regression).
- `snapshotPathTemplate: 'visual-baselines/{arg}{ext}'` — resolves
  screenshots to `tests/visual-baselines/<slug>-<width>.png` directly
  (not Playwright's default `*.spec.ts-snapshots/` subfolder).

**No assertion library beyond Playwright's built-in `expect`.** No
Jest/Vitest/Mocha anywhere in the repo.

**Local run commands:**
```bash
pnpm exec playwright install --with-deps chromium   # one-time browser install
PREVIEW_URL=https://<sha>.realufo.pages.dev pnpm exec playwright test tests/<name>.spec.ts --config=tests/playwright.config.ts
# omit PREVIEW_URL to hit the default production-branch preview https://realufo.pages.dev
```

---

## 2. Test file organization (`tests/`)

```
tests/
├── playwright.config.ts        # baseURL, viewport, chromium-only, snapshot path
├── fidelity-samples.json       # locked content-fidelity fixture (consumed by scripts/verify-fidelity.py, NOT a Playwright spec)
├── tone-colours-fixture.json   # locked CLAUDE.md §3.1 --caution values (consumed by tone-colours.spec.ts)
├── visual-regression.spec.ts   # 15 archives × 4 viewports = 60 screenshot comparisons
├── tone-colours.spec.ts        # 15 archives × 1 getComputedStyle assertion
├── js-off.spec.ts              # 15 archives × JS-disabled rendering assertions
├── sw.spec.ts                  # Service-worker lifecycle (6 tests)
├── search.spec.ts              # Pagefind cross-archive search (4 tests)
├── lightbox.spec.ts            # wargov lightbox behaviour (6 tests, 1 skipped)
├── pagination.spec.ts          # wargov pagination (7 tests)
├── r2-urls.spec.ts             # R2 binary CDN URL smoke (env-gated)
└── visual-baselines/
    ├── README.md                # D-17 operator-only-regen runbook
    ├── .gitkeep
    └── <slug>-<width>.png       # 60 frozen PNGs (15 archives × 360/768/1024/1440)
```

**Naming:** `<feature>.spec.ts`, one file per feature area, not one
file per component. Every spec file opens with a comment block citing
the Plan ID it was written for (`Plan 04-19`, `Plan 04-01`, `Plan
04-04`) and a numbered "coverage matrix" list of what each `test()`
block proves — follow this pattern for new specs.

**Structure convention (every spec):**
```ts
import { test, expect } from '@playwright/test';

test.describe.parallel('<feature> — <plan-id> must-haves', () => {
  test('<specific behaviour, one assertion group>', async ({ page }) => {
    await page.goto(PATH, { waitUntil: 'networkidle' });
    // ...
  });
  // more independent test() blocks — NOT one omnibus test
});
```
Rationale stated in every spec's header: independent tests give
independent RED failure messages, and `workers: 4` fully-parallel mode
means each test must reset its own state via a fresh `page.goto()` —
shared mutable state across tests would deadlock or flake.

---

## 3. CI gate matrix (`.github/workflows/quality-gates.yml`)

This is the closest thing to "run the test suite" in this repo. One
coordinator job (`preflight`) resolves the CF Pages preview URL, then 6
gate jobs fan out in parallel:

| Job | What it runs | Fail mode |
|---|---|---|
| `preflight` | Resolves `deployment_status.environment_url` or `workflow_dispatch` input; HEAD-sanity probes `/` | Hard — aborts the whole matrix if the preview 4xx/5xx's |
| `visual-regression` | `playwright test tests/visual-regression.spec.ts` | **Hard** (D-16, 0.1% pixel diff) |
| `fidelity` | `python3 scripts/verify-fidelity.py --base-url <preview> --color` | **Hard** (D-21, loud unified diff per mismatch) |
| `tone-colours` | `playwright test tests/tone-colours.spec.ts` | **Hard** (D-23) |
| `js-off` | `playwright test tests/js-off.spec.ts` | **Hard, unconditional** (D-25 + B3 — deliberately no `continue-on-error`) |
| `lighthouse` | `lhci autorun --config=.lighthouserc.cf.json` then `python3 scripts/verify-lighthouse-budgets.py --hard-fail` | **Hard as of Phase 4 close** (D-28, flipped 2026-05-28 by Plan 04-20) |
| `redirects` | `python3 scripts/build-redirects.py --check` then `bash scripts/verify-redirects.sh <preview>` | Hard (drift + curl harness) |

**Trigger note:** the `deployment_status:` trigger is currently
**commented out** in `.github/workflows/quality-gates.yml` (see the
2026-05-29 comment block at the top of the file) — the workflow no
longer auto-fires on every CF Pages deploy because `verify-
redirects.sh`'s curl samples still probe Phase-2-era legacy URLs
(`belgian-wave.html`, `cash-landrum.html`, etc.) that were retired
during the Phase 4 migration. **The workflow only runs on manual
`workflow_dispatch` today.** Re-enabling the automatic trigger requires
first refreshing the redirect curl-sample list to current Astro routes.

### 3.1 `js-off.spec.ts` — the hydration-regression tripwire

Iterates all 15 archives with `javaScriptEnabled: false` and asserts,
per archive: ≥1 `article`/`.arch-grid > *`/`.card`/`.head-card` element,
≥1 `h1`/`h2`, body text > 50 chars, and the first 100 chars of body text
do NOT match a loading/hydration placeholder regex. This directly
verifies the PROJECT.md constraint "pre-rendered cards, no hydration."
During the Phase 2/3 wargov-only migration window this gate was
*expected* to fail for not-yet-ported archives — the file's header
comment explicitly forbids softening the gate (`continue-on-error`)
even during that window; a red row means "Phase 3 SSG port is pending
for this archive," not "the gate is miscalibrated."

### 3.2 `tone-colours.spec.ts` — cross-archive drift tripwire

Reads `getComputedStyle(document.documentElement).getPropertyValue
('--caution')` per archive and diffs against `tests/tone-colours-
fixture.json` (which must stay byte-identical to CLAUDE.md §3.1 and to
`RootLayout.astro`'s `TONE` map). Catches "one `--caution` typo on
archive 14 of 15" class bugs that visual-regression alone might miss
on a busy page.

### 3.3 `visual-regression.spec.ts` — pixel contract

60 screenshots (15 archives × 4 viewports: 360×800, 768×1024,
1024×768, 1440×900 — 360 first per mobile-first). Compares against
`tests/visual-baselines/*.png`, captured from **live production
GitHub Pages** (not CF Pages preview, not local dev — see `tests/
visual-baselines/README.md` "D-12"). **These baselines are
operator-regen-only** — `grep -r 'capture-baselines' .github/
workflows/` must always return empty; CI must never invoke `scripts/
capture-baselines.py`. A baseline change requires its own commit with
an explicit rationale (D-17 in the README).

### 3.4 `sw.spec.ts` — service-worker lifecycle

6 tests against the deployed `/sw.js` + Cache Storage API: SW
registers + controls the page within 5s, precache contains ≥1 HTML
page, precache excludes PDF/video/audio/zip (`SW-04` — size-prohibitive
media never precached), cache names use the `realufo-v<sha>` prefix
(`D-22`/`SW-06`), `/sw.js` references the R2 origin
(`assets.realufo.org`) and Pagefind core glob, `ALLOW_SKIP_WAITING` is
compiled in as `false` (Pitfall #4 — flips only at Phase 6 cutover),
and `/sw.js` is served with `Cache-Control: no-cache, no-store,
must-revalidate` (the Phase 1 kill-switch invariant — without this
header the browser would cache the SW script itself and defeat the
whole update path).

### 3.5 `search.spec.ts` — Pagefind cross-archive search

4 tests against `/search`: PagefindUI mounts (`.pagefind-ui` visible),
query `"tic tac"` returns ≥1 result, the archive-filter dropdown lists
all 4 active archives (`wargov`/`aaro`/`nasa`/`nara`), and result links
carry a `#card-` fragment (SRC-04 — `src/pages/search.astro` overrides
PagefindUI's default `processResult` to append `sub_results[0].anchor
.id`).

### 3.6 `lightbox.spec.ts` / `pagination.spec.ts` — wargov-specific regressions

Both are named after the bug-fix plans that produced them (`04-01`,
`04-04`) and each test is a named regression for a specific numbered
bug (e.g. "Bug 1 — data-idx drift", "Bug 2 — local field never
propagated"). `pagination.spec.ts` also documents the wargov data
shape directly in its constants (`PAGE_SIZE = 20`, `TOTAL_CARDS = 222`
— 50 SSR + 3×50 shards + 22, per D-32) — if the wargov CSV row count
changes, these constants need a matching update.

### 3.7 `r2-urls.spec.ts` — env-gated, not run by default

Verifies `data/wargov.json` + shard files contain well-formed
`https://assets.realufo.org/{pdfs,videos}/wargov/` URLs (always runs),
plus an HTTP HEAD + CORS-echo check against a sample of 10 URLs — but
that second test is wrapped in `test.skip(!R2_MIGRATED, ...)` and only
executes when the `R2_MIGRATED` env var is `1`/`true`/`yes`. No
workflow in `.github/workflows/` currently sets this env var, so in
practice only the "manifest contains R2 URLs" sanity check runs in CI;
the HEAD-check portion is opt-in for whoever runs the bulk R2 migration
step manually.

---

## 4. Lighthouse budgets — two coexisting configs

There are **two separate Lighthouse configs that must never be merged
or cross-edited**:

**`.lighthouserc.json`** (legacy, owns `main` branch via `.github/
workflows/lighthouse.yml`):
- Desktop preset, `throttlingMethod: simulate`, `numberOfRuns: 1`.
- 9 URLs against a local `http://localhost:4321` server (`astro dev`
  build served via `pnpm build` + `python3 -m http.server 8000` from
  `dist/`).
- Category-score assertions only, all `warn` level (never blocks a
  merge): performance ≥ 0.8, accessibility ≥ 0.9, best-practices ≥
  0.85, seo ≥ 0.9.
- Triggered by `.github/workflows/lighthouse.yml` on push to `main` +
  PRs touching `src/**`/`public/**`.

**`.lighthouserc.cf.json`** (Phase 2/3/4 CF Pages preview budgets,
owns the `lighthouse` job in `quality-gates.yml`; the file's own
`_metadata` block says explicitly: *"do NOT merge into main — legacy
`.lighthouserc.json` owns the main branch gate (D-32)."*):
- Mobile preset, `cpuSlowdownMultiplier: 4`, 360×800 @ deviceScaleFactor
  2 (CLAUDE.md §8 mobile-first baseline).
- 18 URLs (all 15 archives + `/search.html` + `/about.html` +
  `/timeline.html`), each with `__PREVIEW_URL__` substituted at CI time
  via `sed` (LHCI 0.14 has no native env-var interpolation in JSON
  config — see the file's `preview_url_substitution` metadata note).
- Two metric assertions, both `error` level as of Phase 4 close (D-28,
  flipped 2026-05-28 by Plan 04-20): `largest-contentful-paint ≤ 2500
  ms`, `total-byte-weight ≤ 512000 bytes` (500 KB).

**`scripts/verify-lighthouse-budgets.py`** re-parses `lhci autorun`'s
JSON output (`assertion-results.json` primary path, falls back to
globbing `lhr-*.json`) and prints a per-URL pass/fail table. Two
run modes:
- Default (soft): always exits 0, prints `[WARN]` lines for
  violations — used during Phase 2/3.
- `--hard-fail`: exits 1 on any violation — the mode `quality-
  gates.yml`'s `lighthouse` job actually invokes today (Phase 4 close).

Run locally:
```bash
sed "s|__PREVIEW_URL__|https://your-preview.pages.dev|g" .lighthouserc.cf.json > /tmp/lhci.json
pnpm exec lhci autorun --config=/tmp/lhci.json
python3 scripts/verify-lighthouse-budgets.py --hard-fail --color
```

---

## 5. Drift/content verification scripts (stdlib-only Python + bash)

These are standalone CLI tools, not Playwright specs, but they are the
project's primary correctness net for content fidelity and routing —
treat them as first-class "tests" when reasoning about coverage.

### 5.1 `scripts/verify-fidelity.py`

Re-fetches every unique `source_path` recorded in `tests/fidelity-
samples.json` (hero ledes, hero subs, license footers, FAQ answers,
first-5 card titles per archive) from a live base URL and asserts
byte-equivalence with `expected_text` after **leading/trailing
whitespace strip ONLY** — no smart-quote folding, no accent
normalisation, no em-dash collapsing (D-20). On mismatch, prints a
`difflib.unified_diff` per failure (D-21 — loud, granular). HTML
text-extraction is done with a hand-rolled `html.parser.HTMLParser`
subclass (`_TagTextCollector`, `_FooterParagraphFinder`,
`_SectionHeadingFinder`) — **duplicated verbatim** from `scripts/
extract-fidelity-samples.py` (the script that *creates* the locked
samples) because Python filenames with hyphens aren't importable as
modules; **keep the two copies in sync** when editing either.

```bash
python3 scripts/verify-fidelity.py                                    # default: https://realufo.pages.dev
python3 scripts/verify-fidelity.py --base-url https://realufo.org     # sanity: prod should always pass
python3 scripts/verify-fidelity.py --archive aaro --kind hero-lede    # scoped local debug
```
Exit codes: `0` all matched, `1` ≥1 mismatch (diff printed), `2` fetch
error / samples file missing.

### 5.2 `scripts/verify-redirects.sh`

Parses `URL-CONTRACT.txt` (4937 lines → 95 canonical routes after
fragment-stripping + dedup) and curls each canonical route against a
preview origin, asserting `200`. Catches "CF Pages silently drops
`_redirects` rules at parse time" (Pitfall #8) — a discrepancy between
what `scripts/build-redirects.py` *intended* to ship and what CF Pages
*actually* parsed. Optional `--strict` flag additionally probes the
unslashed-form 301 leg (e.g. `/aaro` → `/aaro/`). Bails early after 10
failures so a fully-broken deploy doesn't spam hundreds of `[FAIL]`
lines.

```bash
scripts/verify-redirects.sh https://<sha>.realufo.pages.dev
scripts/verify-redirects.sh https://realufo.pages.dev --strict
```
Exit codes: `0` all match, `1` ≥1 mismatch, `2` usage/missing-file
error.

### 5.3 `scripts/build-redirects.py --check`

The drift half of the `redirects` CI job — regenerates `_redirects`
in-memory from `URL-CONTRACT.txt` and diffs against the on-disk file
(modulo the volatile sha+date stamp on line 1). A structural mismatch
means someone hand-edited `_redirects` without updating `URL-
CONTRACT.txt` (or vice versa).

### 5.4 `scripts/verify-python-retired.sh`

Phase 4 close (Plan 04-20) invariant guard: asserts the active-surface
Python build legacy (`build-wargov.py`, `build-details.py`, `sync-
nav.py`, `sync-footer.py`, `parse-aaro.py`, `extract-evidence.py`,
`build-{aaro,nasa,nara,nz,uruguay,argentina,italy,canada,peru,
spain}.py`) has NOT reappeared, while asserting the Phase-5-SCRP
whitelist (`spider.py`, `build-redirects.py`, `build-{brazil,chile,
geipan,uk}.py`, `build_batch3.py`, `copy-legacy-archives.sh`) is still
present. **This script is not currently wired into any GitHub Actions
workflow** (`grep -rn verify-python-retired .github/` returns only the
script's own self-references) — it exists as a manual invariant check
an operator or agent should run after touching anything under
`scripts/`:
```bash
bash scripts/verify-python-retired.sh
```

### 5.5 `scripts/capture-baselines.py`

**Never invoked by CI** (see §3.3 above — this is enforced by a grep
check documented in `tests/visual-baselines/README.md`, not by code).
Operator-only tool for regenerating `tests/visual-baselines/*.png`
against live production. Requires a separate Python venv with the
`playwright` **Python** bindings (distinct from the Node `@playwright/
test` package used by the actual spec suite):
```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install playwright==1.49.0 && playwright install chromium
python3 scripts/capture-baselines.py            # full 60-PNG recapture
python3 scripts/capture-baselines.py --archive aaro --viewport 360
python3 scripts/capture-baselines.py --check    # verify 60/60 present (no venv needed for --check)
```

---

## 6. Pagefind (search index) — not unit-tested, verified end-to-end

There is no isolated Pagefind-index unit test. Coverage is entirely via
`tests/search.spec.ts` (§3.5 above) running against a live, fully-built
`dist/pagefind/` index. `RootLayout.astro` controls which pages get
indexed (`data-pagefind-body` on `<main>` for the 4 active archives
plus all `story`/`site-page` page types; `data-pagefind-ignore` for
dormant archives) — if you change that gating logic, `search.spec.ts`
Test 3 (archive-filter dropdown lists exactly the active archives) is
the regression check that will catch a mis-gated page leaking into (or
disappearing from) the index.

---

## 7. What's NOT tested (gaps to know about)

- **No unit tests** for any `.ts` helper (`src/scripts/
  jsonldSchemas.ts`, `src/scripts/extractLegacyBody.ts`) or any Python
  helper module (`scripts/_archive_common.py`, `scripts/
  _release_manifest.py`) in isolation — everything is verified
  end-to-end via a live deployed URL.
- **No component-level Astro test** (no `@astrojs/test` /
  container-API rendering tests) — `Card.astro`/`CatalogCard.astro`
  markup-contract correctness is verified indirectly via `js-off.spec
  .ts` (cards render) + `lightbox.spec.ts` (cards are clickable) +
  `scripts/verify-fidelity.py` (card titles match source text), never
  by rendering the component in isolation and asserting its output
  HTML directly.
- **`verify-python-retired.sh` is not CI-wired** (see §5.4) — a
  regression here would only be caught by someone running it manually.
- **The R2 HEAD/CORS check in `r2-urls.spec.ts` doesn't run in CI**
  today (no workflow sets `R2_MIGRATED=1`) — only the offline manifest-
  shape sanity check does.
- **`quality-gates.yml`'s automatic trigger is disabled** (see §3) —
  the entire 6-job gate matrix currently only runs on manual
  `workflow_dispatch`, not on every CF Pages deploy. Confirm with
  `.planning/STATE.md` / `.planning/decisions/` whether this has been
  re-enabled before assuming the gates run automatically on a given PR.
- **No accessibility-specific spec** beyond Lighthouse's `accessibility`
  category score (soft, legacy config only) — no axe-core / Pa11y
  integration in the Playwright suite.

---

*Testing analysis: 2026-07-11*
