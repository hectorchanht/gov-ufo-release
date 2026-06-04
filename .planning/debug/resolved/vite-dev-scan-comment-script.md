---
slug: vite-dev-scan-comment-script
status: resolved
trigger: |
  `npm run dev` (astro dev v5.18.2) crashes during Vite dep pre-bundling.
  Vite "Failed to scan for dependencies from entries" with esbuild errors
  on ~20 .astro files. Errors point at script tag content like:
    `here is <script is:inline>. NO client:*.`
    `injected at the end of <body> from`
    `(D-23 hydration-free).`
    `HeroCarousel requires ≥4 slides per CLAUDE.md §4 (got ${sl...`
created: 2026-06-04
updated: 2026-06-04
resolved: 2026-06-04
---

# Debug Session: vite-dev-scan-comment-script

## Symptoms

- `npm run dev` / `pnpm dev` fails immediately after Astro ready banner with
  esbuild `Expected ";"` / `Unexpected "—"` errors.
- Each error path is `script:<file>?id=<N>:<line>:<col>` — i.e. Vite's
  dep-scanner is extracting `<script>` blocks from .astro files and feeding
  them to esbuild.
- The offending "script body" content matches text that ONLY appears inside
  `// ...` frontmatter comments or `{/* ... */}` template comments —
  e.g. `src/pages/aaro/index.astro:39`:
    `//   - D-21..D-23: every <script> here is <script is:inline>. NO client:*.`
- HeroCarousel.astro line 29 error (`HeroCarousel requires ≥4 slides per
  CLAUDE.md §4 (got ${sl...`) is INSIDE the frontmatter `if (!slides ||
  slides.length < 4)` throw — caught in the dep-scanner's slice because the
  upstream comment-leak shifted the slice boundary.
- `pnpm build` clean — build doesn't run Vite dep pre-bundling the same way.
- Failure only manifests on **cold** `node_modules/.vite` cache. Warm cache
  hides it because the scan already succeeded once.

## Known context

- Project uses **pnpm** (`packageManager: pnpm@9.15.9`, only `pnpm-lock.yaml`).
- Astro pinned `~5.18.0` per CLAUDE.md §13.
- Vite 6.4.2, esbuild 0.25.12.
- Astro registers `optimizeDeps.entries = ['src/**/*.{...,astro}']` in
  `astro/dist/core/create-vite.js:106`.
- Vite's `scriptRE` regex (vite/dist/node/chunks/dep-*.js):
    `/(<script(?:\s+[a-z_:][-\w:]*(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^"'<>=\s]+))?)*\s*>)(.*?)<\/script>/gis`
  — matches literal `<script>` and `<script is:inline>` substrings without
  parsing JS comments or `{/* */}` Astro-template comments.

## Affected files (from error log)

src/components/{Card,CatalogCard,Footer,HeroCarousel,Lightbox,Nav,StructuredData}.astro
src/layouts/{BaseHead,RootLayout}.astro
src/pages/{about,foia,glossary,index,map,search,timeline,whatsnew}.astro
src/pages/{aaro,nara,nasa,nz,uruguay}/index.astro
src/pages/stories/{index,[slug]}.astro

## Hypotheses (ranked)

1. ~~Prior `archive-filter-lightbox` fix introduced an unclosed template
   literal or stray `</script>`.~~ **ELIMINATED** — `git stash` of those
   5 files left the failure intact on cold cache.
2. Vite's esbuild dep-scanner regex-matches literal `<script>` substrings
   inside `// ...` frontmatter comments and `{/* ... */}` Astro template
   comments, treating intervening text as a JS body. Triggered only on
   cold `node_modules/.vite` cache. **CONFIRMED.**
3. ~~npm-vs-pnpm wrapper installed a stale dep tree.~~ Not relevant — both
   wrappers dispatch the same `astro dev` against the same node_modules.

## Current Focus

(resolved — see Resolution below)

## Evidence

- timestamp: 2026-06-04 18:21
  observation: `pnpm build` passed in the prior session immediately before
  these dev errors — build does NOT exercise Vite's dep pre-bundling
  scanner the same way `astro dev` does. Consistent with the scanner-
  specific hypothesis.

- timestamp: 2026-06-04 18:25
  observation: `git stash` of the 5 files from the prior
  `archive-filter-lightbox` session — dev started CLEAN on warm cache.
  Restoring the stash and starting dev WARM also worked. Initial impression:
  prior fix is at fault.

- timestamp: 2026-06-04 18:29
  observation: `rm -rf node_modules/.vite node_modules/.astro && npm run dev`
  reproduces the failure with ALL 5 prior-fix files restored. Error log
  cites trigger text from `nz/index.astro`, `uruguay/index.astro`,
  `search.astro`, `map.astro`, `HeroCarousel.astro`, `Nav.astro`, etc. —
  files the prior session did NOT touch. Pre-existing bug surfaced by a
  cold cache.

- timestamp: 2026-06-04 18:33
  observation: re-stashed the 5 prior-fix files, cleared
  `node_modules/.vite`, ran `pnpm dev` — SAME failures, SAME files cited.
  Prior fix definitively NOT the trigger. Hypothesis 1 eliminated.

- timestamp: 2026-06-04 18:34
  observation: located Vite's `scriptRE` regex in
  `node_modules/.pnpm/vite@*/node_modules/vite/dist/node/chunks/dep-*.js`.
  Regex matches `<script>` (no attrs) and `<script is:inline>` (one attr)
  substrings — the exact strings inside the trigger comments. Vite has
  no concept of Astro frontmatter / template comments — the regex runs
  over raw file bytes.

- timestamp: 2026-06-04 18:36
  observation: applied minimal text rewrites to 13 .astro files —
  replaced literal `<script>` and `<script is:inline>` substrings inside
  author-only `//` / `{/* */}` comments with prose equivalents
  ("script tag", "is:inline script"). Cleared `node_modules/.vite`,
  ran `pnpm dev` cold → ready in 947 ms, all 9 affected pages
  (/, /aaro/, /nasa/, /nara/, /nz/, /uruguay/, /search, /map, /timeline)
  return HTTP 200, no esbuild errors. `pnpm build` also clean
  (4268 URLs rewritten, 185 legacy files copied, Pagefind 57 pages indexed).

## Eliminated

- **Hypothesis 1** (prior fix introduced the corruption): cold-cache
  failure reproduces with the 5 prior-fix files reverted via `git stash`.
  The prior `archive-filter-lightbox` fix is INNOCENT.

- **npm vs pnpm wrapper**: both wrappers dispatch the same `astro dev`;
  trigger is the cold dep-scan, not the package manager.

## Resolution

**Root cause:** Vite's dep pre-bundling stage runs esbuild's HTML extractor
over every `.astro` file matched by `optimizeDeps.entries` (set to
`src/**/*.{...,astro}` by Astro core in `create-vite.js:106`). The extractor
uses a regex (`scriptRE` in vite's `dep-*.js` chunk) that matches `<script>`
and `<script is:inline>` substrings without parsing Astro's `---` frontmatter
fences or `{/* */}` template comments. Author-only comments that mentioned
those literal substrings (e.g. `// D-21..D-23: every <script> here is
<script is:inline>. NO client:*.`) tricked the scanner into slicing prose
as JS, and esbuild rejected it. The failure only surfaces on cold
`node_modules/.vite` cache — once dep-scan succeeds, the cache short-
circuits subsequent dev starts.

**Fix:** rewrote 13 `.astro` files to remove literal `<script>` /
`<script is:inline>` / `<script id=...>` substrings from internal-only
comments (both `// ...` frontmatter and `{/* ... */}` template comments).
The user-facing content rules (CLAUDE.md §9 verbatim official text) are
not affected — these comments are author notes, not user-visible copy.
Real script tags in template bodies remain unchanged.

Files modified (13):
- `src/components/HeroCarousel.astro` — frontmatter line 9 (backtick mention)
- `src/components/Lightbox.astro` — frontmatter line 6 (backtick mention)
- `src/components/Nav.astro` — frontmatter line 30 + template line 218
- `src/layouts/RootLayout.astro` — frontmatter line 9 + template line 162
- `src/pages/index.astro` — frontmatter line 18
- `src/pages/aaro/index.astro` — frontmatter line 39 + template lines 265/290
- `src/pages/nasa/index.astro` — frontmatter line 29 + template lines 257/282
- `src/pages/nara/index.astro` — frontmatter line 31 + template lines 262/286-287
- `src/pages/nz/index.astro` — frontmatter line 22 + template lines 209/234
- `src/pages/uruguay/index.astro` — frontmatter line 22 + template lines 212/238
- `src/pages/search.astro` — frontmatter lines 14, 33 + template line 72
- `src/pages/map.astro` — frontmatter lines 14, 26, 30
- `src/pages/timeline.astro` — frontmatter line 14

**Verification:**
- `rm -rf node_modules/.vite node_modules/.astro && pnpm dev` — astro
  ready in 947 ms, no errors, no warnings.
- `curl` against /, /aaro/, /nasa/, /nara/, /nz/, /uruguay/, /search,
  /map, /timeline — all HTTP 200.
- `pnpm build` — clean run; 4268 URLs rewritten by build-redirects.py;
  185 legacy files copied by copy-legacy-archives.sh; Pagefind indexed
  57 pages; sitemap emits 67 URLs; manifest.webmanifest fallback written.
- The prior `archive-filter-lightbox` filter/rotate/lightbox fix
  (5 files, 496 diff lines) is preserved verbatim — none of its logic
  was touched by this fix.

**Followup TODOs (optional, not blocking):**
- Consider opening an upstream issue with Astro: their `optimizeDeps.entries`
  setting feeds `.astro` files to Vite's dep-scanner which doesn't understand
  Astro syntax. A defensive option is to pre-strip frontmatter and template
  comments before the dep-scan, or to register a custom esbuild plugin in
  `optimizeDeps.esbuildOptions` that pre-processes `.astro` content.
- Add a lint rule (e.g. ESLint custom rule or pre-commit grep) that flags
  literal `<script` substrings inside `//` and `{/* */}` comments in
  `.astro` files. Pattern:
    `grep -E '(//|\\*).*<script' src/**/*.astro`
  This catches regressions before they hit a cold `pnpm dev`.
