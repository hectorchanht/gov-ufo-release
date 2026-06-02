---
created: 2026-06-02
title: Decide fate of orphan partial-port pages (aaro/pages/ + nara/pages/)
area: legacy
files:
  - dist/aaro/pages/*.html (12 stub files)
  - dist/nara/pages/*.html (9 stub files)
  - legacy/aaro/pages/*.html
  - legacy/nara/pages/*.html
  - scripts/copy-legacy-archives.sh (currently copies them unconditionally)
---

## Problem

Surfaced during `/gsd:debug link-asset-seo-audit`. The audit crawler found 21 HTML files with **zero inbound links** from anywhere on the active surface (Nav, Footer, story pages, search):

```
dist/aaro/pages/{congressional-press-products,efoia-reading-room,faq,home,
                 leaders,mission-vision,official-uap-imagery,resources,
                 submit-a-report,uap-case-resolution-reports,uap-records,
                 uap-reporting-trends}.html      (12 files)
dist/nara/pages/{blogs-and-articles,faqs,federal-agency,moving-images-and-sound,
                 photographs,presidential-libraries,rg-615,
                 textual-and-microfilm,topic}.html  (9 files)
```

These are Wayback Machine snapshots of the corresponding agency pages (e.g. `https://www.aaro.mil/FAQ/`) with all Wayback chrome (`__wm.init`, banner-styles.css from `https://web-static.archive.org/`) intact. Together they contribute **~1,264 broken internal refs** to the link audit (links to agency-internal paths like `/research/topics/uaps`, `/contact`, `/includes/javascript/sortable/tablesort.js` that realufo.org doesn't host).

## Three options

1. **Link them.** Add an "Agency Reference" rail to /aaro/ and /nara/ archive index pages linking to each stub. Pro: orphans resolved. Con: surfaces low-quality Wayback snapshots into the curated SEO surface; the ~1264 broken refs they carry would then appear in active-surface link audits.

2. **Retire them.** Delete `legacy/aaro/pages/` + `legacy/nara/pages/`; add `_redirects` entries `/aaro/pages/* /aaro/ 301` and `/nara/pages/* /nara/ 301`. Pro: cleans the audit; removes ~1264 broken refs. Con: loses the historical Wayback partial-port (small content loss).

3. **Leave as direct-URL-only.** Status quo. Pages ship to `dist/`, no nav link, no sitemap entry. Direct URLs work (e.g. `https://realufo.org/aaro/pages/faq.html`). Pro: zero work. Con: SEO impact (orphans get crawled and counted as low-quality pages).

## Recommendation

Option 2 — retire. The Wayback Internet Archive itself hosts these snapshots at canonical timestamps; realufo.org doesn't need to re-host them. The 301 redirect to the archive index preserves any external inbound links that may exist.

## Related

- `/gsd:debug link-asset-seo-audit` (2026-06-02) — surfaced this
- CLAUDE.md §2 status table — defines "partial-port" pages
- `scripts/copy-legacy-archives.sh` — currently includes these via `git ls-files "legacy/aaro/"`
