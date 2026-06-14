---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
last_updated: "2026-06-01T19:17:17.617Z"
progress:
  total_phases: 7
  completed_phases: 4
  total_plans: 44
  completed_plans: 33
  percent: 57
---

# STATE: realufo.org — SSG Migration Milestone

**Last updated:** 2026-05-25 (initialization)

---

## Project Reference

- **Project:** realufo.org — offline-first archive of every official government UAP source
- **Core value:** Every official government UAP release is preserved and viewable offline-first, with content matching the official source verbatim — durable, free, resistant to source-site takedowns.
- **Current milestone:** SSG migration (brownfield big-bang from plain HTML + Python build scripts to Astro 5 / Cloudflare Pages / Workers cron)
- **Repo:** `hectorchanht/gov-ufo-archive` (local folder name `war-gov-ufo-release` is historical)
- **Live site:** <https://realufo.org>
- **Source-of-truth docs:**
  - `CLAUDE.md` — design system, storage layout, JS invariants
  - `.planning/PROJECT.md` — core value, constraints, decisions
  - `.planning/REQUIREMENTS.md` — v1 requirements (56) with traceability
  - `.planning/ROADMAP.md` — 6-phase plan
  - `.planning/research/{STACK,ARCHITECTURE,FEATURES,PITFALLS}.md` — researched context
  - `.planning/codebase/CONCERNS.md` — existing fragility points

## Current Position

Phase: 04.1 (legacy-reorg-stories-site-pages-nav-surface) — EXECUTING
Plan: 1 of 7

- **Phase:** None (roadmap just created; awaiting `/gsd:plan-phase 1`)
- **Plan:** None
- **Status:** Executing Phase 04.1
- **Progress:** 0 / 6 phases complete (0 / 56 requirements implemented)

```
[          ] 0%
```

## Performance Metrics

| Metric | Baseline (today on `main`) | Target (post-Phase 6) |
|--------|----------------------------|------------------------|
| Largest per-archive HTML | 3.3 MB (GEIPAN inline JSON) | ≤ 500 KB |
| Cross-archive index | 4.6 MB `/api/all.json` (Lunr) | Pagefind sharded WASM, initial < 30 KB |
| SW registration coverage | 12 / ~32 pages | 15 / 15 archive pages (every page via `BaseHead.astro`) |
| Scrape → release-upload | Local-only, manual | CI-automated via Workers cron + GH Actions hybrid |
| Hosting | GitHub Pages | Cloudflare Pages |
| Lighthouse mobile LCP @ 4× CPU | Not budgeted | ≤ 2.5 s with HTML+inline ≤ 500 KB |

## Accumulated Context

### Roadmap Evolution

- Phase 04.1 inserted after Phase 4: Legacy reorg + stories/site-pages nav surface (URGENT)

### Key Decisions

| Decision | Rationale | Source |
|----------|-----------|--------|
| Astro 5.x (pin `~5.x.y`, NOT `^5`) | Astro 6 broke the Cloudflare adapter prerender (issue #15684) | research/STACK.md |
| Cloudflare Pages over Netlify / GitHub Pages | Free unlimited bandwidth + Workers cron + R2 escape hatch | PROJECT.md |
| Workers Paid ($5/mo) required | Free 10 ms CPU cap unusable for HTML parsing on cron | research/STACK.md |
| `injectManifest` SW strategy, not `generateSW` | Preserves hand-rolled 2xx-only nav-caching from commit `dcbc0d7` | research/ARCHITECTURE.md |
| GH Releases stays the binary CDN | Durable public-domain mirror semantics; R2 used only for > 2 GB overflow | PROJECT.md |
| Big-bang migration, NOT strangler | 15-way drift between archives is the pain — running two systems in parallel makes it worse | PROJECT.md |
| Pagefind 1.x replaces Lunr | Sharded WASM index loads < 30 KB initial, vs 4.6 MB Lunr blob | research/ARCHITECTURE.md |
| Per-archive release tags from day one | Avoid the 1000-asset/tag ceiling on shared `pdfs-v1` / `videos-v1` | research/PITFALLS.md |
| Pre-rendered cards, no hydration | Preserves offline-first + JS-disabled archival viewing | PROJECT.md constraints |
| SW kill-switch deployed to OLD origin T-14d before cutover | Prevents stale-shell serving of new origin after DNS swap | research/PITFALLS.md §1 |
| URL-CONTRACT.txt snapshot from `main` BEFORE any SSG code | Prevents silent URL drift across 95 HTML files | research/PITFALLS.md §2 |
| Akamai egress spike BEFORE finalizing scrape architecture | Workers IPs may be MORE flagged than GH Actions for some sources | research/PITFALLS.md §3 |
| DNS TTL drop to 300 s ≥ 7 days BEFORE cutover | Prevents split-brain traffic during DNS propagation | research/PITFALLS.md §15 |

### Open Questions

- Cutover strategy detail (branch+preview vs side-by-side vs hot-swap) — deferred to Phase 6 plan
- Whether to keep `uap-release001.csv` committed alongside `uap-data.csv` — deferred (PROJECT.md note)
- Final Pagefind scoping UX: per-archive default vs all-archives default — deferred to Phase 4 plan
- R2 bucket layout (`realufo-staging` private + `realufo-overflow` public?) — to be decided in Phase 5 plan

### Blockers

None at roadmap-creation time.

### Quick Tasks Completed

| # | Description | Date | Commit | Status | Directory |
|---|-------------|------|--------|--------|-----------|
| 260615-3e3 | Fetch war.gov Release 03 (6/12/26, +72 rows) + wire site + upload to R2 | 2026-06-15 | 4dc5255 | Mostly complete — 53 PDFs + 7/9 videos live on R2; 2 large videos (>300 MiB) pending S3 upload | [260615-3e3](./quick/260615-3e3-fetch-third-war-gov-ufo-release-and-upda/) |

### TODOs

- **wargov R03**: upload 2 large videos to R2 via S3 multipath — `DOD_111764796.mp4` (2.99 GiB) + `DOD_111764902.mp4` (1.19 GiB) exceed wrangler's 300 MiB cap. Source: `/Users/laichan/UFO/AARO061226/`. Until done, 2 AUD cards (DVIDS 1010319, 1010336) play → 404.
- Run `/gsd:plan-phase 1` to decompose Phase 1 into executable plans
- Confirm with user that 6-phase structure matches their mental model
- Confirm with user whether v2 social/curation features (SOCL-*, FED-*, A11Y-*) are correctly deferred

## Session Continuity

### Last Action

Roadmap drafted from `.planning/REQUIREMENTS.md` (56 v1 reqs) + `.planning/research/{STACK,ARCHITECTURE,FEATURES,PITFALLS}.md` + `.planning/codebase/CONCERNS.md`. 6-phase horizontal-layers structure aligned with research's recommended migration path. 100 % requirement coverage validated (see `REQUIREMENTS.md` traceability table).

### Next Action

`/gsd:plan-phase 1` to decompose Phase 1 (Pre-Migration Safety) into executable plans. Per the Phase 1 success criteria, the first plans will likely cover:

- `URL-CONTRACT.txt` generation script + CI gate
- SW kill-switch implementation + GH Pages deploy
- Akamai egress spike experiment
- DNS TTL drop + verification
- `scripts/sync.sh:144` and `CLAUDE.md §5.1` fixes

### Restart Hint

If returning to this session cold:

1. Read this STATE.md
2. Read `.planning/ROADMAP.md` to recall the 6-phase structure
3. Read `.planning/REQUIREMENTS.md` traceability table to see what's done
4. Run `/gsd:next` to get the recommended next action

---

*State initialised: 2026-05-25*
