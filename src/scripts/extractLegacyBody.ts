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

  // 8. Legacy site-page link rewrite (Phase 04.1 hotfix 2026-06-02).
  //    Pre-04.1 site pages lived at root with `.html` extension
  //    (/about.html, /timeline.html, …). After 04.1 the canonical URL is
  //    /<slug>/ with trailing slash. Production redirects (`_redirects`
  //    via Plan 04.1-06) handle the 301 on Cloudflare Pages, but the
  //    dev server (python http.server / wrangler pages dev) does NOT
  //    honour _redirects — so legacy `<a href="/timeline.html">` 404s
  //    during local UAT.
  //
  //    Rewrite anchor `href`s and `src`s for the 6 site pages to the
  //    new trailing-slash form. Verbatim text content is untouched
  //    (CLAUDE.md §9 trust boundary — only URLs change, never prose).
  const SITE_PAGE_SLUGS = ['about', 'foia', 'glossary', 'map', 'timeline', 'whatsnew'];
  for (const slug of SITE_PAGE_SLUGS) {
    out = out.replace(
      new RegExp(`(href|src)=(["'])/${slug}\\.html\\2`, 'gi'),
      `$1=$2/${slug}/$2`,
    );
  }

  return out;
}
