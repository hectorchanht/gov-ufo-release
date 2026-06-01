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
// Each regex captures the INNER HTML of the matching element. The `\b`
// after the tag name prevents `<maintenance>`/`<articulated>` etc. from
// matching (paranoid, but cheap).
const CASCADE: ReadonlyArray<{ re: RegExp; name: string }> = [
  // Cascade-1 (audit §) — 55 of 89 legacy files. Every project-authored
  // story HTML + 6 site pages.
  { re: /<main\b[^>]*>([\s\S]*?)<\/main>/i, name: '<main>' },
  // Cascade-2 (audit §) — 10 dormant-archive `<slug>/index.html` files.
  // Only used for files NOT enumerated in stories.json/site-pages.json
  // today (those files are routed via legacy 301 in Plan 04.1-06), but
  // kept here so a future re-add doesn't need an extractor change.
  { re: /<article\b[^>]*>([\s\S]*?)<\/article>/i, name: '<article>' },
  // Cascade-3 is not implemented as a generic selector. The single file
  // that needs a custom selector (legacy/aaro/details.html — uses
  // `<div class="container">`) is intentionally NOT in stories.json for
  // Plan 04.1-03 — the `/stories/aaro-overview/` slot is filled by
  // legacy/aaro/story.html which has a `<main>` anchor. If a future
  // plan re-introduces details.html, this CASCADE gains a per-file
  // entry guarded by filePath, NOT a generic <div.container> rule that
  // would catch Nav/Footer chrome divs.
];

/**
 * Extract the structural body anchor from a raw legacy HTML string.
 *
 * Strategy: walk the CASCADE list in order; return the inner HTML of the
 * first matching element. If NONE match, THROW with the file path so the
 * build fails fast and the operator can extend the audit + cascade.
 *
 * @param html      — full HTML text read from the legacy file
 * @param filePath  — repo-relative legacy path (used only for the error msg)
 * @returns inner HTML of the matched anchor (NOT yet scrubbed)
 * @throws Error if no cascade selector matches
 */
export function extractMain(html: string, filePath: string): string {
  for (const { re } of CASCADE) {
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
  // 3. <script>…</script> — unconditionally stripped for stories.
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
  return out;
}
