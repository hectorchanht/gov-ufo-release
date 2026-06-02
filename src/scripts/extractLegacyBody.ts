// extractLegacyBody.ts — Phase 04.1 legacy HTML extractor + chrome scrubber.
//
// Consumed by src/pages/stories/[slug].astro (Plan 04.1-03 Task 2) and the
// site-pages route in Plan 04.1-04 Task 2 at build time. The two
// exported functions are pure, dependency-free, and operate on raw HTML
// strings via regex — no DOM library, no node:fs (callers supply the
// already-read file contents).
//
// Selector contract: see
//   .planning/phases/04.1-legacy-reorg-stories-site-pages-nav-surface/
//   04.1-legacy-html-structure-audit.md
// for the per-file disposition table. The CASCADE constant below is the
// AUTHORITATIVE implementation of that audit's "Selector cascade" §.
//
// Two B-fixes from 04.1-PLAN-CHECK enforced here:
//   B-3 — no raw «body» fallback. The cascade ends with a thrown error so
//         the build fails fast on any unrecognised shape; silent body
//         fallback would double-render legacy Nav/Footer/scanlines.
//   B-4 — single-pass chrome scrub. Strips every category of legacy
//         chrome (style/link/script/header/footer/scanlines/inline-style)
//         in one pass; the prior "v1 with style leakage" two-pass design
//         is eliminated.

// Cascade selectors in priority order. First match wins. There is NO
// raw «body» fallback — see CLAUDE.md §11 don'ts ("no force-push") AND
// the build-fail contract in extractMain() below.
//
// Each entry MAY have an optional `filePath` matcher (regex against the
// repo-relative legacyPath). When present, the entry only fires for that
// specific file — so the generic `<main>` / `<article>` cascade-1/-2
// rules remain safe, and cascade-3 (per-file custom selectors) cannot
// accidentally match files it wasn't audited for.
//
// Each regex captures the INNER HTML of the matching element. The `\b`
// after the tag name prevents `<maintenance>`/`<articulated>` etc. from
// matching (paranoid, but cheap).
const CASCADE: ReadonlyArray<{ re: RegExp; name: string; filePath?: RegExp }> = [
  // Cascade-1 (audit §) — 55 of 89 legacy files. Every project-authored
  // story HTML + 5 site pages (about, foia, glossary, timeline, whatsnew).
  { re: /<main\b[^>]*>([\s\S]*?)<\/main>/i, name: '<main>' },
  // Cascade-2 (audit §) — 10 dormant-archive `<slug>/index.html` files.
  // Only used for files NOT enumerated in stories.json/site-pages.json
  // today (those files are routed via legacy 301 in Plan 04.1-06), but
  // kept here so a future re-add doesn't need an extractor change.
  { re: /<article\b[^>]*>([\s\S]*?)<\/article>/i, name: '<article>' },
  // Cascade-3b (audit §) — legacy/map.html has NO `<main>`, NO
  // `<article>`, AND no in-file `<footer>` (the legacy map page ended
  // at `</body>` directly; the visual footer was a sibling include
  // in the pre-Phase-4 build pipeline). The audited body region is
  // the slice starting at the unambiguous `<section id="map">` marker
  // and ending at the first `<footer` boundary OR `</body>` if no
  // footer is present in-file.
  //
  // Anchoring on `<section id="map"` is safe because the audit
  // confirms there is exactly ONE `<section id="map">` in
  // legacy/map.html. Lookahead-terminator allows the regex to
  // gracefully cope with both footer-bearing and footer-less legacy
  // shapes (legacy/map.html is the latter; future re-audited files
  // with body-tail content + footer would also work).
  //
  // Scripts INSIDE this slice (the Leaflet init at lines ~181/~294)
  // are preserved by scrubChrome({ preserveScripts: true }). The
  // `<script id="nav-script-shared">` block at the tail of the slice
  // is stripped by scrubChrome's nav-script-shared cleanup pass
  // because it duplicates Astro Nav.astro's dropdown behaviour (per
  // 04.1-legacy-html-structure-audit.md §"Extractor implementation
  // hints"). W-4 fix is upheld: scripts come ONLY from the anchor
  // slice, never from legacy <head>.
  //
  // filePath guard ensures this only fires for legacy/map.html — the
  // start anchor `<section id="map"` is unambiguous globally, but
  // belt-and-braces.
  {
    filePath: /(^|\/)map\.html$/,
    re: /(<section\s+id=["']map["'][\s\S]*?)(?=<footer\b|<\/body>)/i,
    name: 'map.html cascade-3b',
  },
  // Cascade-3c (audit §"Script preservation whitelist") — legacy/
  // timeline.html. The legacy file has a `<main>` anchor (cascade-1
  // WOULD match) but the timeline init script lives AFTER `</main>`
  // in the body-tail region (audit-confirmed at line ~226 in
  // legacy/timeline.html — actually OUTSIDE `<main>` despite the
  // audit table's "inside <main>" cell, which was an authoring slip).
  // The post-`</main>` body region also contains `<footer>` (legacy
  // chrome, scrubbed by scrubChrome) and another inline script at
  // line ~494 (the data-loading IIFE — KEEP per audit). The trailing
  // `<script id="nav-script-shared">` is DROPPED per audit "Extractor
  // implementation hints" (handled in scrubChrome).
  //
  // To preserve both the <main> content AND the body-tail timeline
  // scripts, we extend the cascade slice from `<main>` open through
  // to the `<script id="nav-script-shared">` boundary (exclusive).
  // scrubChrome then strips the legacy `<footer>` content, the stray
  // `</main>` tag, and the nav-script-shared block (already stripped
  // earlier if it slips into the slice).
  //
  // filePath guard ensures cascade-1 (<main>) does NOT win first for
  // timeline.html — we want the EXTENDED slice. The guard makes the
  // generic <main> rule SKIP timeline.html implicitly by being later
  // in the cascade order ... but since cascade-1 (no guard) runs
  // FIRST, we need to ensure cascade-3c runs FIRST for timeline.html
  // specifically. Solution: add this entry BEFORE cascade-1, but
  // gate it with the timeline.html filePath. Implementation below
  // reorders.
  {
    filePath: /(^|\/)timeline\.html$/,
    re: /<main\b[^>]*>([\s\S]*?)<script\s+id=["']nav-script-shared["']/i,
    name: 'timeline.html cascade-3c (main + body-tail scripts)',
  },
  // Cascade-3d (hotfix 2026-06-02) — legacy/glossary.html and legacy/whatsnew.html
  // BOTH have <main> but all their interactive <script> blocks (filter logic,
  // archive-fetch+render logic) sit AFTER </main> in the legacy body, before
  // the nav-script-shared sentinel. Cascade-1 (<main>...</main>) would truncate
  // those scripts → broken interactivity even with preserveScripts: true.
  // Same pattern as timeline.html cascade-3c: anchor from <main> through the
  // body-tail right up to (but not including) the nav-script-shared block.
  // See .planning/debug/site-pages-broken.md for full root-cause.
  {
    filePath: /(^|\/)glossary\.html$/,
    re: /<main\b[^>]*>([\s\S]*?)<script\s+id=["']nav-script-shared["']/i,
    name: 'glossary.html cascade-3d (main + body-tail scripts)',
  },
  {
    filePath: /(^|\/)whatsnew\.html$/,
    re: /<main\b[^>]*>([\s\S]*?)<script\s+id=["']nav-script-shared["']/i,
    name: 'whatsnew.html cascade-3d (main + body-tail scripts)',
  },
  // Future per-file selectors (e.g. legacy/aaro/details.html cascade-3a
  // — `<div class="container">`) would go here with their own
  // filePath guards.
];

/**
 * Extract the structural body anchor from a raw legacy HTML string.
 *
 * Strategy: filePath-guarded cascade entries (cascade-3* per-file
 * selectors) are tried FIRST so they can override the generic
 * `<main>`/`<article>` rules for files that need a different slice
 * (e.g. legacy/timeline.html, where the body-tail timeline-init
 * script lives AFTER `</main>` and would be lost by cascade-1). If
 * no guarded entry matches OR fires, fall through to the unguarded
 * entries in declaration order. If NONE match, THROW with the file
 * path so the build fails fast and the operator can extend the audit
 * + cascade.
 *
 * @param html      — full HTML text read from the legacy file
 * @param filePath  — repo-relative legacy path (used by cascade-3 guards
 *                    AND the error message)
 * @returns inner HTML of the matched anchor (NOT yet scrubbed)
 * @throws Error if no cascade selector matches
 */
export function extractMain(html: string, filePath: string): string {
  // Pass 1 — guarded per-file cascade entries (cascade-3*).
  for (const { re, filePath: guard } of CASCADE) {
    if (!guard) continue;
    if (!guard.test(filePath)) continue;
    const m = html.match(re);
    if (m) return m[1];
  }
  // Pass 2 — unguarded generic entries (cascade-1, cascade-2).
  for (const { re, filePath: guard } of CASCADE) {
    if (guard) continue;
    const m = html.match(re);
    if (m) return m[1];
  }
  throw new Error(
    `extractMain: no recognised structural anchor in ${filePath}. ` +
      `Audit the file in .planning/phases/04.1-legacy-reorg-stories-site-pages-nav-surface/` +
      `04.1-legacy-html-structure-audit.md and add a selector to ` +
      `src/scripts/extractLegacyBody.ts CASCADE, OR remove the file from ` +
      `src/data/stories.json (Plan 04.1-03) / src/data/site-pages.json (Plan 04.1-04) ` +
      `and rely on the legacy 301 redirect (Plan 04.1-06). Raw <` + `body> ` +
      `fallback is forbidden (B-3 fix per 04.1-PLAN-CHECK.md §3).`,
  );
}

export interface ScrubOptions {
  /**
   * Stories: false (default — scripts unconditionally stripped per
   * CLAUDE.md §9 verbatim-TEXT-only trust boundary). Site-pages
   * map/timeline: true (Plan 04.1-04 — preserve in-body Leaflet +
   * timeline scripts after extractor isolates them to the anchor slice).
   */
  preserveScripts?: boolean;
  /**
   * Repo-relative source path (e.g. `legacy/aaro/belgian-wave.html`).
   * When provided, scrubChrome rewrites relative legacy URLs in the
   * extracted body to their post-04.1 canonical forms (step 9 below).
   * Without it, relative URLs are passed through unchanged — fine for
   * site-page test fixtures that don't carry cross-archive links.
   *
   * Audit-driven 2026-06-02 (link-asset-seo-audit): adding this
   * disambiguates `./tic-tac.html` (relative to source archive) from
   * the otherwise-identical sibling-story rewrite target.
   */
  sourcePath?: string;
  /**
   * Stories pages emit their own `<h1>` from the Astro hero block, so
   * the legacy body's `<h1>` would duplicate (SEO defect: two H1s per
   * page). When `stripBodyH1: true`, scrubChrome demotes the FIRST
   * `<h1>...</h1>` in the body to `<h2>...</h2>`. Subsequent H1s are
   * preserved (none observed in practice — legacy bodies have exactly
   * one).
   *
   * Audit-driven 2026-06-02 (link-asset-seo-audit).
   */
  stripBodyH1?: boolean;
}

// ============================================================
// Legacy URL rewrite tables — audit-driven 2026-06-02.
//
// Pre-04.1 legacy HTML files cross-link via paths relative to their
// source location (e.g. `../aaro/tic-tac.html`, `../search.html?q=X`,
// `./gimbal.html`). After Plan 04.1-03/04 those slugs are served by
// Astro at a NEW canonical URL — the relative paths no longer resolve
// from the new URL location.
//
// `rewriteLegacyLinks()` below is the single source of truth that
// maps every still-living legacy URL pattern to its post-04.1
// canonical form. Verbatim text content (CLAUDE.md §9 trust boundary)
// is preserved — only `href`/`src` URL values are touched.
// ============================================================

// Active archives reachable from Nav/Footer (CLAUDE.md §2 status table).
// /{archive}/ URLs survive verbatim — only the path component changes
// from relative to root-absolute.
const ACTIVE_ARCHIVES = new Set(['aaro', 'nasa', 'nara']);
// 'wargov' lives at `/` (CLAUDE.md §2) and rewrites from `../wargov/`
// or `../` accordingly.

// Dormant archives still served at /{archive}/index.html via
// scripts/copy-legacy-archives.sh. URLs survive verbatim — same
// relative-to-root-absolute rewrite as active.
const DORMANT_ARCHIVES = new Set([
  'geipan', 'uk', 'brazil', 'chile', 'argentina', 'canada',
  'italy', 'nz', 'peru', 'spain', 'uruguay',
]);

// Site-page slugs (src/data/site-pages.json). Pre-04.1 lived at root
// with `.html` (e.g. /about.html); post-04.1 canonical is /{slug}/.
const SITE_PAGE_SLUGS = ['about', 'foia', 'glossary', 'map', 'timeline', 'whatsnew'];

// Legacy `{archive}/{leaf}.html` -> canonical `/stories/{slug}/` map.
// Source: src/data/stories.json (build-time read in callers; this
// duplicate is intentional so scrubChrome stays dependency-free and
// JSON-imports don't pollute the test surface). Update both when
// adding a story.
const LEGACY_TO_STORY: ReadonlyMap<string, string> = new Map([
  ['aaro/belgian-wave.html', 'belgian-wave'],
  ['aaro/cash-landrum.html', 'cash-landrum'],
  ['aaro/coyne.html', 'coyne'],
  ['aaro/gimbal.html', 'gimbal'],
  ['aaro/jal-1628.html', 'jal-1628'],
  ['aaro/ohare-2006.html', 'ohare-2006'],
  ['aaro/phoenix-lights.html', 'phoenix-lights'],
  ['aaro/stephenville.html', 'stephenville'],
  ['aaro/story.html', 'aaro-overview'],
  ['aaro/details.html', 'aaro-overview'],  // master case index — same target as legacy 301
  ['aaro/tehran.html', 'tehran'],
  ['aaro/tic-tac.html', 'tic-tac'],
  ['aaro/travis-walton.html', 'travis-walton'],
  ['argentina/story.html', 'argentina-overview'],
  ['brazil/operacao-prato.html', 'operacao-prato'],
  ['brazil/story.html', 'brazil-overview'],
  ['brazil/trindade.html', 'trindade'],
  ['brazil/varginha.html', 'varginha'],
  ['canada/falcon-lake.html', 'falcon-lake'],
  ['canada/shag-harbour.html', 'shag-harbour'],
  ['canada/story.html', 'canada-overview'],
  ['chile/el-bosque.html', 'el-bosque'],
  ['chile/story.html', 'chile-overview'],
  ['geipan/story.html', 'geipan-overview'],
  ['geipan/trans-en-provence.html', 'trans-en-provence'],
  ['geipan/valensole.html', 'valensole'],
  ['italy/story.html', 'italy-overview'],
  ['nara/chiles-whitted.html', 'chiles-whitted'],
  ['nara/condon-committee.html', 'condon-committee'],
  ['nara/levelland.html', 'levelland'],
  ['nara/lubbock-lights.html', 'lubbock-lights'],
  ['nara/mantell.html', 'mantell'],
  ['nara/mcminnville.html', 'mcminnville'],
  ['nara/robertson-panel.html', 'robertson-panel'],
  ['nara/roswell.html', 'roswell'],
  ['nara/socorro.html', 'socorro'],
  ['nara/story.html', 'nara-overview'],
  ['nasa/story.html', 'nasa-overview'],
  ['nz/kaikoura.html', 'kaikoura'],
  ['nz/story.html', 'nz-overview'],
  ['peru/story.html', 'peru-overview'],
  ['spain/manises.html', 'manises'],
  ['spain/story.html', 'spain-overview'],
  ['uk/cosford.html', 'cosford'],
  ['uk/rendlesham.html', 'rendlesham'],
  ['uk/story.html', 'uk-overview'],
  ['uruguay/story.html', 'uruguay-overview'],
]);

// Parked utility pages (donate, embed, compare, stats). Plan 04.1-06
// 301-redirects them to /about/. Rewrite legacy refs to the same target.
const PARKED_TO_ABOUT = new Set(['donate', 'embed', 'compare', 'stats']);

/**
 * Internal: derive `{archive}` from a source path like `legacy/aaro/foo.html`.
 * Returns undefined if the path doesn't match the legacy/<archive>/ shape.
 */
function sourceArchive(sourcePath?: string): string | undefined {
  if (!sourcePath) return undefined;
  const m = sourcePath.match(/^legacy\/([a-z]+)\//);
  return m ? m[1] : undefined;
}

/**
 * Rewrite every still-living legacy URL pattern in the extracted body
 * to its post-04.1 canonical form. Idempotent — calling twice on the
 * same input yields the same output.
 *
 * Verbatim text content (CLAUDE.md §9) is preserved — only `href` and
 * `src` URL VALUES are rewritten. `<a>` link text is never touched.
 *
 * @internal — exported for unit tests; production callers go through scrubChrome.
 */
export function rewriteLegacyLinks(html: string, sourcePath?: string): string {
  let out = html;
  const archive = sourceArchive(sourcePath);

  // Rewrite href/src attribute values in one regex pass so that we
  // don't double-rewrite. The replacer inspects the URL, returns the
  // rewritten form (or the original if no rule applies).
  out = out.replace(
    /(href|src)=(["'])([^"']+)\2/gi,
    (match, attr, quote, url) => {
      const rewritten = rewriteOneUrl(url, archive);
      if (rewritten === url) return match;
      return `${attr}=${quote}${rewritten}${quote}`;
    },
  );
  return out;
}

function rewriteOneUrl(url: string, archive: string | undefined): string {
  // Pass through fragments, mailto, javascript, data URIs, external.
  if (!url) return url;
  if (url.startsWith('#') || url.startsWith('mailto:') || url.startsWith('tel:')
    || url.startsWith('javascript:') || url.startsWith('data:')
    || url.startsWith('http://') || url.startsWith('https://')
    || url.startsWith('//')) {
    return url;
  }

  // Split path | query/fragment for cleaner pattern-matching.
  const queryMatch = url.match(/^([^?#]*)([?#].*)?$/);
  if (!queryMatch) return url;
  const path = queryMatch[1];
  const tail = queryMatch[2] || '';

  // (1) /search.html (root-absolute or relative) -> /search/
  //     Catches /search.html, ./search.html, ../search.html, ../../search.html.
  if (/(^|\/)search\.html$/.test(path)) {
    return `/search/${tail}`;
  }

  // (2) /<site-page>.html (root-absolute or relative) -> /<site-page>/
  //     Catches /about.html, ../about.html, ./glossary.html etc.
  for (const slug of SITE_PAGE_SLUGS) {
    const re = new RegExp(`(^|/)${slug}\\.html$`);
    if (re.test(path)) {
      return `/${slug}/${tail}`;
    }
  }

  // (3) Parked utility pages -> /about/
  for (const slug of PARKED_TO_ABOUT) {
    const re = new RegExp(`(^|/)${slug}\\.html$`);
    if (re.test(path)) {
      return `/about/${tail}`;
    }
  }

  // (4) /manifest.webmanifest is a real artifact at dist root — leave it.
  if (path === '/manifest.webmanifest') return url;

  // (5) Cross-archive index: relative `../{archive}/` or `../{archive}/index.html`
  //     -> root-absolute `/{archive}/`.
  let m = path.match(/(^|\.\.\/)([a-z]+)\/(index\.html)?$/);
  if (m) {
    const slug = m[2];
    if (ACTIVE_ARCHIVES.has(slug) || DORMANT_ARCHIVES.has(slug) || slug === 'wargov') {
      if (slug === 'wargov') return `/${tail}`;
      return `/${slug}/${tail}`;
    }
  }

  // (6) Sibling story or cross-archive story: `./X.html`, `X.html` (bare),
  //     `../{otherArchive}/X.html`. Match leaf `{archive}/{leaf}` against
  //     LEGACY_TO_STORY.
  //
  //     6a — bare or `./` form: resolve against source archive.
  m = path.match(/^(?:\.\/)?([a-z0-9-]+\.html)$/);
  if (m && archive) {
    const key = `${archive}/${m[1]}`;
    const slug = LEGACY_TO_STORY.get(key);
    if (slug) return `/stories/${slug}/${tail}`;
  }

  //     6b — `../{otherArchive}/X.html` form.
  m = path.match(/^\.\.\/([a-z]+)\/([a-z0-9-]+\.html)$/);
  if (m) {
    const key = `${m[1]}/${m[2]}`;
    const slug = LEGACY_TO_STORY.get(key);
    if (slug) return `/stories/${slug}/${tail}`;
  }

  // (7) `../` to wargov landing -> `/`.
  if (path === '../' || path === '../index.html') {
    return `/${tail}`;
  }

  // No rewrite — pass through.
  return url;
}

/**
 * Strip legacy chrome from an extracted body anchor.
 *
 * Categories removed in one pass:
 *   1. <style>…</style>
 *   2. <link rel="stylesheet" …> (void or self-closing)
 *   3. <script>…</script> — UNLESS opts.preserveScripts === true
 *   4. <header>…</header> — competes with Nav.astro
 *   5. <footer>…</footer> — competes with Footer.astro
 *   6. <div class="scanlines" …></div> — RootLayout emits its own
 *   7. inline `style="…"` attributes on any tag — would override the
 *      CLAUDE.md §3.2 palette
 *   8. (audit 2026-06-02) <link rel="manifest"> in body — chrome leak
 *   9. (audit 2026-06-02) legacy URL rewrite — see rewriteLegacyLinks()
 *  10. (audit 2026-06-02) optional first-<h1> demotion when caller
 *      already emits a hero `<h1>` (stripBodyH1: true)
 *
 * Idempotent: scrubChrome(scrubChrome(x)) === scrubChrome(x).
 *
 * @param html — extracted anchor HTML (NOT the full document)
 * @param opts — { preserveScripts?: false } default
 * @returns scrubbed HTML ready for `set:html` injection
 */
export function scrubChrome(html: string, opts: ScrubOptions = {}): string {
  let out = html;
  // 1. <style>…</style>
  out = out.replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, '');
  // 2. <link rel="stylesheet" …> — void element or self-closing.
  out = out.replace(/<link\b[^>]*\brel=["']?stylesheet["']?[^>]*\/?>/gi, '');
  // 2b. <link rel="manifest" …> (audit 2026-06-02) — legacy chrome leak.
  //     The PWA plugin emits its own manifest reference at the page
  //     `<head>` via BaseHead/RootLayout. Embedded body manifest refs
  //     would duplicate; if the legacy points at the now-emitted
  //     /manifest.webmanifest fallback we still want it out of <body>.
  out = out.replace(/<link\b[^>]*\brel=["']?manifest["']?[^>]*\/?>/gi, '');
  // 3a. <script id="nav-script-shared">…</script> — legacy "canonical
  //     nav-dropdown wiring" block injected by the retired
  //     scripts/sync-nav.py builder. Strips ALWAYS, regardless of
  //     preserveScripts, because Astro Nav.astro now owns dropdown
  //     wiring (Plan 04.1-05) — leaving this script in would either
  //     double-bind event listeners (`.has-dropdown > details` collide
  //     with Astro Nav's own toggle wiring) or fail noisily when the
  //     selectors don't match. Per 04.1-legacy-html-structure-audit.md
  //     §"Extractor implementation hints".
  out = out.replace(
    /<script\b[^>]*\bid=["']nav-script-shared["'][^>]*>[\s\S]*?<\/script>/gi,
    '',
  );
  // 3b. <script>…</script> — unconditionally stripped for stories.
  //    Site-pages opt in via preserveScripts when their data row asks
  //    for in-body Leaflet/timeline JS (W-4 fix: callers pass only the
  //    extracted anchor slice, so head-region scripts NEVER leak).
  if (!opts.preserveScripts) {
    out = out.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, '');
  }
  // 4. <header>…</header> — legacy chrome competing with Nav.astro.
  out = out.replace(/<header\b[^>]*>[\s\S]*?<\/header>/gi, '');
  // 5. <footer>…</footer> — legacy chrome competing with Footer.astro.
  out = out.replace(/<footer\b[^>]*>[\s\S]*?<\/footer>/gi, '');
  // 5a. Stray `</main>` close tag — appears in timeline.html cascade-3c
  //     slice where the extracted region spans the </main> boundary
  //     to reach the body-tail timeline-init script. Removed so the
  //     final article body doesn't contain an unmatched closer.
  out = out.replace(/<\/main>/gi, '');
  out = out.replace(/<main\b[^>]*>/gi, '');
  // 5b. Inner content <nav> landmarks (e.g. legacy/foia.html
  //     `<nav class="toc">`, legacy/glossary.html `<nav class="az">`):
  //     rewrite the tag NAME from `nav` to `div` while preserving all
  //     attributes and inner content (anchor links to #us, #uk, etc).
  //     Astro Nav.astro is the SOLE `<nav>` landmark on the page (B-3
  //     anti-double-render: exactly ONE `<nav>` element per built
  //     HTML). The a11y `aria-label` attributes carried by these
  //     inline TOCs are preserved verbatim so screen readers still
  //     announce the section, and `role="navigation"` is added so the
  //     navigation landmark role is retained. Verbatim TEXT (CLAUDE.md
  //     §9) is preserved — only the tag NAME changes.
  out = out.replace(
    /<nav\b([^>]*)>/gi,
    (_match, attrs) => `<div role="navigation"${attrs}>`,
  );
  out = out.replace(/<\/nav>/gi, '</div>');
  // 6. <div class="…scanlines…" …>…</div> — RootLayout's own scanlines
  //    overlay already wraps the page; legacy duplicates stack visually.
  out = out.replace(
    /<div\b[^>]*\bclass=["'][^"']*\bscanlines\b[^"']*["'][^>]*>[\s\S]*?<\/div>/gi,
    '',
  );
  // 7. Inline style="…" attributes (single or double quotes, any tag).
  //    Legacy files hard-code colours that would override CLAUDE.md
  //    §3.2 palette + per-archive --caution tone.
  out = out.replace(/\s+style=["'][^"']*["']/gi, '');

  // 9. Legacy URL rewrite (audit 2026-06-02 — link-asset-seo-audit).
  //    Replaces step 8 from the previous design with a comprehensive
  //    rewrite that handles:
  //      - Relative `../search.html?q=X` -> `/search/?q=X`
  //      - Relative `../about.html` etc -> `/about/`
  //      - Root-absolute `/about.html` etc -> `/about/`
  //      - Cross-archive `../{archive}/` -> `/{archive}/`
  //      - Sibling-story `./X.html`, `X.html`, `../{archive}/X.html`
  //        -> `/stories/{slug}/` when X maps to a known story
  //      - `../donate.html` and other parked utilities -> `/about/`
  //
  //    Verbatim TEXT (CLAUDE.md §9) is preserved — only URLs change.
  out = rewriteLegacyLinks(out, opts.sourcePath);

  // 10. Optional first-<h1> demotion (audit 2026-06-02 — link-asset-seo-audit).
  //     Story routes emit a hero `<h1>` in the Astro frontmatter; the
  //     extracted body's own `<h1>` would yield two H1s per page (SEO:
  //     ambiguous topical heading; lighthouse: ~3-point structure
  //     penalty). Demote the FIRST `<h1>` (and only the first) to `<h2>`
  //     when the caller opts in.
  if (opts.stripBodyH1) {
    let replaced = false;
    out = out.replace(/<h1\b([^>]*)>([\s\S]*?)<\/h1>/i, (match, attrs, body) => {
      if (replaced) return match;
      replaced = true;
      return `<h2${attrs}>${body}</h2>`;
    });
  }

  return out;
}
