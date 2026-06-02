#!/usr/bin/env bash
# ============================================================
# postbuild: copy git-tracked legacy archive files into dist/
#
# Phase 04.1 Plan 04.1-02 rewrite — sources read from `legacy/<slug>/`
# after Plan 04.1-01 relocated every pre-SSG HTML + per-archive
# assets/pages subdirectory under `legacy/`. Destination paths in
# dist/ are unchanged (URL contract preserved) — `copy_one()` strips
# the `legacy/` prefix on write so `legacy/aaro/tic-tac.html` lands
# at `dist/aaro/tic-tac.html`, NOT `dist/legacy/aaro/tic-tac.html`.
#
# Phase 3 Plan 03-05/03-06 — option (a) per cf-pages-project.md
# §interfaces: until Phase 4 SSG-06 ports the 14 non-wargov archives
# to Astro, copy their legacy Python-built HTML into dist/<slug>/ so
# URL-CONTRACT.txt routes resolve to the correct content instead of
# being shadowed by the wargov SPA fallback.
#
# CRITICAL: uses `git ls-files` to enumerate sources so that
#   - PDFs (gitignored per CLAUDE.md §5.2) are NOT copied (binary
#     CDN via GitHub Releases per §5.1)
#   - Videos (gitignored) are NOT copied
#   - Only HTML/SVG/PNG/JPG/JSON/CSS/JS that are version-controlled
#     end up in dist/
#
# W-2 fix: prefix strip is guarded by [[ "$f" == legacy/* ]] — never mauls non-legacy paths.
#
# Skipped:
#   - wargov/ — does not exist; Astro owns / via src/pages/index.astro
#   - legacy/<slug>/index.html for partial-port slugs (aaro, nara,
#     nasa, nz, uruguay) — Astro owns those routes via
#     src/pages/<slug>/index.astro. Currently no such legacy index
#     is git-tracked, but the skip rule is kept defense-in-depth
#     (W-6 contract from 04.1-PLAN-CHECK.md).
#   - search.html / stats.html / timeline.html / whatsnew.html
#     top-level static-pages block — REMOVED in 04.1-02. search.html
#     is served by `src/pages/search.astro`; timeline + whatsnew get
#     Astro routes in Plan 04.1-04; stats is parked-410 per Plan
#     04.1-06 + CONTEXT.md decisions.
#
# CF Pages hard limit per file (25 MiB) per
#   https://developers.cloudflare.com/pages/platform/limits/
# enforced in `copy_one()`.
# ============================================================
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
DIST="$REPO/dist"

if [ ! -d "$DIST" ]; then
  echo "postbuild: $DIST does not exist; skipping (was astro build run?)" >&2
  exit 0
fi

copied_count=0
skipped_count=0
# CF Pages hard limit per file (25 MiB) per https://developers.cloudflare.com/pages/platform/limits/
MAX_BYTES=$((25 * 1024 * 1024))

copy_one() {
  local f="$1"
  local size dest
  size=$(stat -f %z "$f" 2>/dev/null || stat -c %s "$f" 2>/dev/null || echo 0)
  if [ "${size:-0}" -gt "$MAX_BYTES" ]; then
    echo "postbuild: SKIP $f (${size} bytes > 25 MiB CF Pages limit; belongs in GitHub Releases per CLAUDE.md §5.1)" >&2
    skipped_count=$((skipped_count + 1))
    return
  fi
  # W-2 guard: only strip `legacy/` when the path actually starts with
  # the literal `legacy/` segment. Paths like `assets/legacy-fonts/foo.woff`
  # or a hypothetical future `legacy-snapshot/foo.html` would otherwise
  # get their prefix mangled by a bare `${f#legacy/}` parameter expansion
  # (in those cases the expansion is a no-op TODAY, but the explicit test
  # makes the contract audit-visible and future-proof — see
  # 04.1-PLAN-CHECK.md §4 W-2).
  if [[ "$f" == legacy/* ]]; then
    dest="${f#legacy/}"
  else
    dest="$f"
  fi
  mkdir -p "$DIST/$(dirname "$dest")"
  cp "$f" "$DIST/$dest"
  copied_count=$((copied_count + 1))
}

# --- dormant archive directories (9 slugs — wholesale copy from legacy/<slug>/) ---
# Plans 04-05/04-06 (D-09): the New Zealand + Uruguay archive index pages
# are now served by src/pages/[archive]/index.astro. As subsequent Wave 3+
# ports complete (04-07..04-18), drop each slug from this list. When the
# list is empty, this script can be deleted entirely.
#
# After Plan 04.1-01 every dormant slug lives under `legacy/<slug>/` —
# `copy_one()`'s guarded prefix-strip rewrites `legacy/geipan/index.html`
# → `dist/geipan/index.html`, preserving the existing /<slug>/ URL
# contract (CLAUDE.md §2 dormant-archive status table).
for slug in geipan uk brazil chile argentina canada italy peru spain; do
  if [ -d "legacy/$slug" ]; then
    while IFS= read -r f; do
      copy_one "$f"
    done < <(git ls-files "legacy/$slug/")
  fi
done

# --- partial-port archives (5 slugs — story sub-pages only, skip <slug>/index.html) ---
# Plans 04-05/04-06 (D-09): the [archive]/ index page was ported to Astro
# but legacy story sub-pages remain (story.html, case-specific narratives).
# Copy ONLY the sub-pages, NEVER the legacy index.html — Astro now owns
# the index route and the legacy HTML would shadow it. Cross-archive
# links policed by scripts/sync-nav.py + sync-footer.py still target
# these sub-pages, so a 404 here would break the live site.
#
# After Plan 04.1-01 every partial-port slug's sub-pages live under
# `legacy/<slug>/` — the `case "$f" in legacy/<slug>/index.html) continue ;;`
# skip rule was rewritten to match the new path (W-6 contract).
if [ -d "legacy/nz" ]; then
  while IFS= read -r f; do
    case "$f" in
      legacy/nz/index.html) continue ;;  # Astro owns /nz/ — never copy
      *) copy_one "$f" ;;
    esac
  done < <(git ls-files "legacy/nz/")
fi
if [ -d "legacy/uruguay" ]; then
  while IFS= read -r f; do
    case "$f" in
      legacy/uruguay/index.html) continue ;;  # Astro owns /uruguay/ — never copy
      *) copy_one "$f" ;;
    esac
  done < <(git ls-files "legacy/uruguay/")
fi
if [ -d "legacy/nasa" ]; then
  # Plan 04-16 partial-port: Astro owns /nasa/ (src/pages/nasa/index.astro)
  # but NASA has a legacy long-form sub-page (legacy/nasa/story.html — full
  # narrative of the UAP Independent Study Team's work) plus
  # legacy/nasa/assets/* (favicon.svg, og.svg, images/uap-meeting-2023.jpeg,
  # images/uap-report-cover.png). All are policed by
  # scripts/sync-footer.py STORY_META + URL-CONTRACT.txt; missing them
  # would 404 cross-archive nav links. Copy everything EXCEPT
  # legacy/nasa/index.html (which Astro owns).
  while IFS= read -r f; do
    case "$f" in
      legacy/nasa/index.html) continue ;;  # Astro owns /nasa/ — never copy
      *) copy_one "$f" ;;
    esac
  done < <(git ls-files "legacy/nasa/")
fi
if [ -d "legacy/nara" ]; then
  # Plan 04-15 partial-port: Astro owns /nara/ (src/pages/nara/index.astro)
  # but NARA has many legacy sub-pages — case-specific narratives
  # (chiles-whitted, condon-committee, levelland, lubbock-lights,
  # mantell, mcminnville, robertson-panel, roswell, socorro, story) and
  # a legacy/nara/pages/* directory (blogs-and-articles, faqs,
  # federal-agency, moving-images-and-sound, photographs,
  # presidential-libraries, rg-615, textual-and-microfilm, topic). All
  # are policed by scripts/sync-footer.py STORY_META and URL-CONTRACT.txt;
  # missing them would 404 cross-archive nav links. Copy everything
  # EXCEPT legacy/nara/index.html (which Astro owns).
  while IFS= read -r f; do
    case "$f" in
      legacy/nara/index.html) continue ;;  # Astro owns /nara/ — never copy
      *) copy_one "$f" ;;
    esac
  done < <(git ls-files "legacy/nara/")
fi
if [ -d "legacy/aaro" ]; then
  # Plan 04-17 partial-port: Astro owns /aaro/ (src/pages/aaro/index.astro)
  # but AARO has the LARGEST legacy sub-page set of any partial-port
  # archive — 14 case-specific narratives (belgian-wave, cash-landrum,
  # coyne, gimbal, jal-1628, ohare-2006, phoenix-lights, stephenville,
  # story, tehran, tic-tac, travis-walton + details.html master index)
  # plus the legacy/aaro/pages/* directory (congressional-press-products,
  # efoia-reading-room, faq, home, leaders, mission-vision,
  # official-uap-imagery, resources, submit-a-report,
  # uap-case-resolution-reports, uap-records, uap-reporting-trends)
  # plus legacy/aaro/assets/* (favicon.svg, og.svg, images/*). All are
  # policed by scripts/sync-footer.py STORY_META + URL-CONTRACT.txt;
  # missing them would 404 cross-archive nav links. Copy everything
  # EXCEPT legacy/aaro/index.html (which Astro owns).
  while IFS= read -r f; do
    case "$f" in
      legacy/aaro/index.html) continue ;;  # Astro owns /aaro/ — never copy
      *) copy_one "$f" ;;
    esac
  done < <(git ls-files "legacy/aaro/")
fi

# --- top-level static pages block REMOVED in Plan 04.1-02 ---
# The previous version copied search.html, stats.html, timeline.html,
# whatsnew.html from the repo root into dist/. Plan 04.1-02 drops it:
#   - search.html is served by `src/pages/search.astro` (Astro).
#   - timeline.html + whatsnew.html get Astro routes in Plan 04.1-04
#     (`src/pages/timeline/index.astro`, `src/pages/whatsnew/index.astro`).
#   - stats.html is parked-410 per Plan 04.1-06 + CONTEXT.md decisions
#     ("Park (not migrated, redirect to 410-gone or `/about/`)").
# All four legacy files now live under `legacy/` (Plan 04.1-01) and are
# referenced from `_redirects` once Plan 04.1-06 lands.

# --- shared root-level assets + slideshow + slideshow-2 ---
# These directories are explicitly NOT under legacy/ per CONTEXT.md
# decisions ("KEEP at root: assets/, slideshow/, slideshow-2/, bundles/.
# They are NOT legacy."). `copy_one()`'s guarded prefix-strip leaves
# their `dest` untouched (the else-branch is a no-op), so URLs land at
# /assets/..., /slideshow/..., /slideshow-2/... unchanged.
#
# slideshow-2/ holds R02 imagery referenced from src/pages/index.astro's
# hero carousel (PR050, CIA-D01) AND from VID card thumbnails populated
# by normalize-csv.py's _hydrate_thumb() (2026-05-29 — VID hydration
# patch). Without copying, the hydrated `Modal Image` paths
# `/slideshow-2/*.jpg` would 404 on the deployed site.
for dir in assets slideshow slideshow-2; do
  if [ -d "$dir" ]; then
    while IFS= read -r f; do
      copy_one "$f"
    done < <(git ls-files "$dir/")
  fi
done

# --- api/ + feeds/ (Phase 04.1 hotfix 2026-06-02) -------------------------
# Legacy interactive pages (/whatsnew/, /timeline/, /map/) consume
# /api/*.json + /feeds/*.xml. Both directories live at repo root and
# were previously surfaced by GitHub Pages deploys directly. The Astro/CF
# Pages build only ships dist/, so without this copy the dev server +
# CF Pages preview both 404 those URLs.
#
# Uses `find` (not `git ls-files`) so build-api.py / build-feeds.py
# regenerated artifacts (e.g. api/all.json) ship even when untracked.
# Per CLAUDE.md §5.2 the 100 MB rule plus copy_one's MAX_BYTES guard
# stops anything oversized from sneaking in. See
# .planning/debug/site-pages-broken-round2.md for repro.
for dir in api feeds; do
  if [ -d "$dir" ]; then
    while IFS= read -r f; do
      copy_one "$f"
    done < <(find "$dir" -type f \( -name '*.json' -o -name '*.xml' -o -name '*.md' \))
  fi
done

# Emit directory-index pages for /api/ + /feeds/ so the bare directory
# URLs (linked from about + whatsnew) don't 404 on CF Pages. Surfaced by
# /gsd:debug link-asset-seo-audit (2026-06-02).
python3 "$REPO/scripts/build-dir-index.py" || \
  echo "postbuild: WARN build-dir-index.py failed (non-fatal)" >&2

# Rewrite legacy `.html` cross-refs in copied dormant + partial-port HTML
# so dev/preview servers don't 404 on internal nav (production CF Pages
# already handles via _redirects 301s, but the chain costs a hop).
# Surfaced by /gsd:debug link-asset-seo-audit (2026-06-02).
python3 "$REPO/scripts/rewrite-dist-legacy-links.py" || \
  echo "postbuild: WARN rewrite-dist-legacy-links.py failed (non-fatal)" >&2

echo "postbuild: copied $copied_count legacy files into dist/; skipped $skipped_count oversized files"

# ============================================================
# Plan 04-19 (D-12..D-17) — Pagefind cross-archive search index.
#
# MUST run AFTER the legacy copy step so that any legacy HTML that *did*
# carry data-pagefind-body would also be indexed. In current 4-active-
# archive scope (CLAUDE.md §2 status table) ONLY the Astro-rendered
# active pages emit data-pagefind-body via RootLayout.astro, so Pagefind
# skips every legacy /aaro/<story>.html, /nasa/story.html, /geipan/*.html
# etc. by design. The full corpus walked: dist/{,/aaro/, /nasa/, /nara/}
# index.html (4 pages with data-pagefind-body) + per-card facets.
#
# pnpm exec is used (NOT npx -y) so the build is hermetic — pagefind is
# pinned in devDependencies per RESEARCH §2 + version pin guidance.
# ============================================================
echo "[postbuild] pagefind: indexing dist/ ..."
pnpm exec pagefind --site dist

# ============================================================
# SEO infra (audit-driven 2026-06-02) — sitemap.xml + PWA manifest.
#
# build-sitemap.py reads URL-CONTRACT.txt (single source of truth) and
# emits dist/sitemap.xml listing every canonical realufo.org route.
# robots.txt ships from public/robots.txt (Astro auto-copies that dir
# to dist/ at build time — no postbuild work required).
#
# manifest.webmanifest fallback: 46 legacy AARO pages reference
# `/manifest.webmanifest` in their `<link rel="manifest">`. Until those
# legacy pages are rewritten (or retired), emit a minimal manifest so
# the link resolves with 200 instead of 404. Mirrors the PWA plugin's
# astro.config.mjs `manifest` block.
# ============================================================
python3 scripts/build-sitemap.py

if [ ! -f "$DIST/manifest.webmanifest" ]; then
  cat > "$DIST/manifest.webmanifest" << 'MANIFEST'
{
  "name": "realufo.org — Government UAP Archive",
  "short_name": "realufo",
  "description": "Offline-first archive of every official government UAP source",
  "start_url": "/",
  "display": "standalone",
  "theme_color": "#0a0a0c",
  "background_color": "#0a0a0c",
  "icons": [
    { "src": "/assets/favicon.svg", "sizes": "any", "type": "image/svg+xml" }
  ]
}
MANIFEST
  echo "[postbuild] wrote dist/manifest.webmanifest fallback"
fi
