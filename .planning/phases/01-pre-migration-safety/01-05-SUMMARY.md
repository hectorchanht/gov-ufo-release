---
phase: 01-pre-migration-safety
plan: 05
subsystem: infra
tags: [service-worker, kill-switch, sw-deregister, updateViaCache, cache-poisoning, gh-pages, ssg-migration]

# Dependency graph
requires:
  - phase: 01-pre-migration-safety
    provides: "URL-CONTRACT.txt on main (01-02) — baseline URL surface against which any post-kill-switch-deploy anomaly can be diffed"
  - phase: 01-pre-migration-safety
    provides: "Planning context (01-CONTEXT.md decisions D-05..D-08 — full-nuke behaviour, replace in-place, no self-disable timer, 14-day deploy-anchored gate)"
provides:
  - "sw.js as kill-switch: install→skipWaiting, activate→unregister+caches.delete(all)+postMessage+claim, no fetch handler, no message handler"
  - "scripts/build-sw.py adapted to stamp the kill-switch (cache-prefix realufo-killswitch-) + warns if the kill-switch identity is removed"
  - "scripts/patch-sw-registration.py — idempotent stdlib-only patcher; rewrites bare register('/sw.js') to register('/sw.js', { updateViaCache: 'none' })"
  - "58 tracked HTML files now register the SW with updateViaCache:'none' so the browser cannot HTTP-cache /sw.js"
affects: [01-cutover-deploy, 06-cutover, ssg-migration, sw-real-rebuild, sw-cache-naming]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Kill-switch service worker pattern: install=skipWaiting, activate=unregister+full-cache-nuke+postMessage+claim, no fetch handler"
    - "Idempotent HTML patcher walking `git ls-files '*.html'` with literal string substitution + GUARD-substring skip-check"
    - "Cache-name prefix as collision-avoidance contract between two SW builds at the same /sw.js URL (realufo-killswitch- vs the future Phase 6 prefix)"

key-files:
  created:
    - scripts/patch-sw-registration.py
  modified:
    - sw.js
    - scripts/build-sw.py
    - 58 tracked *.html files (single-line registration-options addition)

key-decisions:
  - "Kept the docstring's __SW_VERSION__ placeholder literal — the build-sw.py regex only matches the `const VERSION = '...';` source line, so the documentation mention of the placeholder name stays verbatim while the live VERSION is stamped on deploy"
  - "Wrapped each activate-handler step (unregister / caches.delete / postMessage / claim) in independent try/catch so one failing step does not abort the others — a best-effort full-nuke is strictly better than an all-or-nothing one in the deregistration context"
  - "Plan's example BEFORE/AFTER used double-quoted /sw.js — verified in the codebase via `git grep` that all 58 tracked registrations match the exact double-quoted form; the patcher does not need to handle the single-quote variant"
  - "Patcher prints a single-line summary (`patched=N already_ok=M no_register=K total=T`) instead of per-file output — keeps CI logs scannable and gives the idempotency invariant a stable substring to grep"

patterns-established:
  - "Kill-switch SW carries a DevTools-identifiable cache-name prefix even though it maintains no caches — `realufo-killswitch-<sha>-<date>` so a developer reading Application → Cache Storage can name the build that ran"
  - "Banner comment in load-bearing project artifacts (sw.js) must contain literal `DO NOT REMOVE` so future tree-walks / refactors / regenerators preserve the intent"
  - "HTML registration-options modifier (`updateViaCache: 'none'`) is host-agnostic — embeds the fix in source HTML so it survives any host migration (GH Pages → CF Pages today; anywhere else later)"

requirements-completed: [PMS-02]

# Metrics
duration: ~6min
completed: 2026-05-25
---

# Phase 01 Plan 05: SW Kill-Switch + updateViaCache Patcher Summary

**Replaced the live realufo.org service worker with a one-shot kill-switch (install→skipWaiting, activate→unregister + caches.delete(all) + postMessage + claim, no fetch handler) AND patched every one of the 58 tracked HTML files' inline SW registrations to carry `updateViaCache: 'none'` so the browser cannot HTTP-cache /sw.js and defeat the kill-switch's 14-day Phase 6 countdown.**

## Performance

- **Duration:** ~6 min (executor wall-time; on-disk edits only — Task 3 deploy + DevTools verification still pending operator)
- **Started:** 2026-05-25T04:30:00Z
- **Completed (Tasks 1+2 on-disk):** 2026-05-25T04:33:29Z
- **Tasks committed:** 2 of 3 (Task 3 is `checkpoint:human-verify`)
- **Files modified:** 61 (sw.js + scripts/build-sw.py + scripts/patch-sw-registration.py + 58 HTML)

## Accomplishments

- **`sw.js` rewritten as the kill-switch** per `.planning/phases/01-pre-migration-safety/01-CONTEXT.md` decisions D-05..D-08:
  - `install` → `self.skipWaiting()`
  - `activate` → `self.registration.unregister()` + `caches.keys()` → `caches.delete(name)` for every cache + `clients.matchAll({type:'window'})` → `postMessage({type:'sw-killswitch-reload', tag: KILLSWITCH_TAG})` + `self.clients.claim()`. Each step wrapped in its own try/catch so a failure in one does not abort the rest.
  - No `fetch` handler (kill-switch must stop intercepting requests).
  - No `message` handler (kill-switch is one-shot).
- **`scripts/build-sw.py`** docstring updated to describe the kill-switch as Phase 1's `sw.js` and to note the cache-prefix `realufo-killswitch-`. The VERSION-stamping regex is unchanged, so one invocation continues to stamp the file (verified: ran once, stamped `__SW_VERSION__` → `915157a-20260525`). Added a defensive warning if the kill-switch tag goes missing from a hand-edited copy.
- **`scripts/patch-sw-registration.py`** created — stdlib-only (subprocess, pathlib, sys), idempotent, walks `git ls-files '*.html'`, replaces `navigator.serviceWorker.register("/sw.js")` with `navigator.serviceWorker.register("/sw.js", { updateViaCache: 'none' })`. Prints a single-line summary; the `patched=0` substring on second run is the idempotency invariant.
- **58 HTML files patched** with `updateViaCache: 'none'`. Git diff shows the surgical one-line change per file; no collateral edits, no indentation churn.
- **Idempotency verified:** Second run output `patched=0 already_ok=58 no_register=37 total=95`. The 37 unregistered pages are AARO case-detail pages + utility pages that intentionally do not register the SW; out of scope for this patch.
- **Banner contract met:** `sw.js` contains the literal string `DO NOT REMOVE`, mentions the `.planning/ROADMAP.md` phase pointer, and notes the SW is replaced by the real SW on cutover.

## Task Commits

Each task committed atomically on the worktree branch `worktree-agent-a2e5310d712e6d003`:

1. **Task 1: Replace sw.js with kill-switch + adapt build-sw.py** — `856cafe` (feat)
2. **Task 2a: Create scripts/patch-sw-registration.py** — `1140850` (feat)
3. **Task 2b: Bulk HTML patch (58 files)** — `136b912` (fix)
4. **Task 3: Deploy + DevTools verify** — **PENDING OPERATOR** (`checkpoint:human-verify` — see "Next Phase Readiness" below)

_Plan-metadata commit will be handled by the orchestrator on merge-back per parallel-executor protocol._

## Files Created/Modified

- `sw.js` — Now ~90 lines (down from 132); the kill-switch is intentionally tiny. Banner block carries `DO NOT REMOVE` + the migration phase pointer + the placeholder/stamped VERSION semantics. `KILLSWITCH_TAG = 'realufo-killswitch-' + VERSION` is the only cache-name constant; no caches are populated. Activate-handler nukes every cache returned by `caches.keys()`, posts `{type:'sw-killswitch-reload', tag: KILLSWITCH_TAG}` to every window client, and `claim()`s.
- `scripts/build-sw.py` — Docstring expanded to describe the Phase-1 kill-switch role + the `realufo-killswitch-` prefix invariant. Added a defensive `warn:` print if `realufo-killswitch-` is missing from the stamped file (catches accidental kill-switch removal during a hand-edit).
- `scripts/patch-sw-registration.py` (NEW, 94 lines, +x) — Stdlib-only idempotent HTML patcher; `subprocess.run(['git', 'ls-files', '*.html'])` for traversal, literal string `replace()` for substitution, GUARD-substring (`updateViaCache`) to skip already-patched files.
- 58 HTML files (one-line edit each) — Inline `<script>` block now reads `navigator.serviceWorker.register("/sw.js", { updateViaCache: 'none' }).catch(function(){});`.

## Decisions Made

- **Single try/catch per activate-handler step** rather than wrapping the whole IIFE — best-effort full-nuke beats all-or-nothing in deregistration. If `unregister()` somehow throws on an edge browser, the cache delete + postMessage + claim still run.
- **Kept the `__SW_VERSION__` literal in the docstring lines** — only the `const VERSION = '...';` line carries the stamp; documentation references to the placeholder stay verbatim so a future reader understands what gets stamped.
- **No single-quote-variant handling in the patcher.** `git grep` against the codebase shows 58/58 SW registrations use the exact double-quoted form; adding a regex for `'/sw.js'` would be premature generalisation and create idempotency edge cases.
- **Patcher print format `patched=N already_ok=M no_register=K total=T`** — single-line, grep-friendly, gives the post-deploy `patched=0` invariant a stable substring.

## Deviations from Plan

None — plan executed exactly as written. All verification checks (Task 1 acceptance criteria, Task 2 idempotency invariant, Task 2 zero-bare-registrations invariant) passed on the first run.

## Issues Encountered

- **Worktree branched from a pre-`.planning/` commit.** This worktree's HEAD `915157a` predates the `.planning/` tree (the planning work was committed on `main` after this worktree was created). Resolution: the `.planning/STATE.md`, `01-05-PLAN.md`, `01-CONTEXT.md`, etc. were read from the main repo's path (`/Users/laichan/code/war-gov-ufo-release/.planning/`), and this SUMMARY.md is written to the same main-repo path. The orchestrator merges the worktree's code commits back to `main` separately; the SUMMARY lives only on `main`'s planning tree by design.
- **No code-related issues.** All verification commands listed in the plan's `<verify>`/`<acceptance_criteria>` blocks passed without modification: `node --check sw.js` clean, `self.registration.unregister` present, `caches.keys` present, `DO NOT REMOVE` present, `realufo-killswitch-` present, no fetch handler, no message handler, no `SHELL_CACHE`/`DATA_CACHE`/`IMG_CACHE` remnants, VERSION stamped with `<7-char-hex>-<date>`, patcher idempotent, 0 bare registrations remain, 58 HTML files carry `updateViaCache: 'none'`.

## Known Stubs

None. Tasks 1+2 ship complete on-disk artifacts; Task 3 is an explicit human checkpoint, not a stub.

## Threat Flags

No new threat surface introduced beyond the plan's `<threat_model>`:
- The kill-switch SW only does cache-delete (origin-scoped per service-worker spec — T-05-05).
- The HTML patcher only modifies tracked HTML files at known fixed positions (T-05-06).
- No package installs (T-05-SC).

## Task 3 Checkpoint — Awaiting Operator

**Task 3 is `checkpoint:human-verify` and was NOT auto-approved.** It requires a real-browser DevTools observation on a returning-user profile against the live GH Pages origin, which only the operator can perform.

### Pre-flight diff already verified by executor

- `git diff sw.js scripts/build-sw.py scripts/patch-sw-registration.py '*.html'` shows exactly:
  - Kill-switch SW rewrite (sw.js: -121, +99 lines).
  - build-sw.py docstring + warn-line additions (+26 lines).
  - patch-sw-registration.py new file (+94 lines, +x).
  - 58 HTML files: one-line registration-options addition each (+58, -58).
- `node --check sw.js` clean.
- Patcher idempotent (`patched=0` on second run).
- Bare-registration matches across the HTML tree: 0.

### Operator next steps (concrete)

1. **Merge worktree → main.** Three commits land:
   - `856cafe` feat(01-05): replace sw.js with kill-switch SW + adapt build-sw.py
   - `1140850` feat(01-05): add scripts/patch-sw-registration.py — idempotent updateViaCache patcher
   - `136b912` fix(01-05): apply updateViaCache:'none' to every HTML SW registration

2. **Push to origin.**
   ```
   git push origin main
   ```
   Record the wall-clock UTC push timestamp — **this is the Phase 6 14-day countdown anchor (D-08)**.

3. **Wait 1–2 min** for GH Pages to redeploy (Actions tab, or default auto-deploy).

4. **Verify the live `/sw.js` is the kill-switch via curl:**
   ```
   curl -s https://realufo.org/sw.js | grep -c "self.registration.unregister"
   # → 1+
   curl -s https://realufo.org/sw.js | grep -c "realufo-killswitch-"
   # → 1+
   curl -s https://realufo.org/index.html | grep -c "updateViaCache: 'none'"
   # → 1
   curl -sI https://realufo.org/sw.js | head -10
   ```

5. **DevTools verification (load-bearing per ROADMAP.md Phase 1 success criterion 2):**
   - **Fresh profile (incognito):** Visit `https://realufo.org`. DevTools → Application → Service Workers should show the kill-switch installing then unregistering. Cache Storage should be empty post-activate.
   - **Returning-user profile (regular Chrome, already has prior `realufo-shell-*` / `realufo-data-*` / `realufo-img-*` caches):** Visit `https://realufo.org`. Expected sequence:
     a. Within seconds, the OLD SW fetches the new `/sw.js`, sees changed bytes (the `updateViaCache: 'none'` option forces a network round-trip; verify in DevTools → Network → /sw.js → Size column shows real bytes, NOT "(disk cache)"), and installs the kill-switch as "waiting" → "activating" (skipWaiting fires in install).
     b. Kill-switch's activate handler runs: unregister + caches.delete(all) + postMessage + claim.
     c. SW Source momentarily visible, then transitions to "deleted" / "no active service worker".
     d. Console: `navigator.serviceWorker.controller` returns `null` after one manual reload.
     e. Cache Storage: `realufo-shell-*`, `realufo-data-*`, `realufo-img-*` caches all gone. No `realufo-killswitch-*` cache entries (the kill-switch maintains none).

6. **Record deploy anchor.** Create `.planning/decisions/sw-killswitch.md` with:
   - Git commit SHA of the merged kill-switch commits (or a merge-commit SHA).
   - UTC wall-clock timestamp of `git push origin main`.
   - DevTools observation (one-paragraph confirmation of steps a–e above OR a `blocked: <observation>` note).
   - **The 14-day Phase 6 gate becomes active from this timestamp.**

7. **If DevTools shows anything other than the expected sequence:** `git revert` the three commits and surface the failure as `blocked: <observation>`. Do NOT leave a half-working kill-switch on production.

### Resume signal

The plan's `<resume-signal>` expects either:
- `killswitch-deployed-and-verified` — once steps 1–6 are complete and the deploy timestamp is recorded in `01-05-SUMMARY.md` (this file; append a `## Deploy Verified` section with the timestamp).
- `blocked: <observation>` — if anything diverges.

## Next Phase Readiness

- **Phase 6 (cutover) is unblocked from a code-prep perspective** — once Task 3 verifies on production, the 14-day countdown gate starts and Phase 6 can begin its own planning work in parallel.
- **Phase 2 (SSG migration) can proceed independently** — the patcher is a recipe Phase 2's templating layer can reuse (or, more durably, Phase 2 can bake `updateViaCache: 'none'` directly into the head-template so the option is never lost).
- **Phase 6's real SW MUST use a different cache-name prefix** than `realufo-killswitch-` per D-06; the `build-sw.py` warn-line will alert if a future build accidentally keeps the kill-switch prefix.

## Self-Check: PASSED

- ✓ `sw.js` exists on worktree, valid JavaScript (`node --check` clean).
- ✓ `sw.js` contains `self.registration.unregister` (2 occurrences — code + comment; plan requires ≥1).
- ✓ `sw.js` contains `caches.keys` (3 occurrences — code + comments; plan requires ≥1).
- ✓ `sw.js` contains literal `DO NOT REMOVE` (1 occurrence).
- ✓ `sw.js` contains `realufo-killswitch-` (2 occurrences — banner + `KILLSWITCH_TAG`).
- ✓ `sw.js` has NO `fetch` event listener.
- ✓ `sw.js` has NO `message` event listener.
- ✓ Old `SHELL_CACHE` / `DATA_CACHE` / `IMG_CACHE` constants gone.
- ✓ VERSION line stamped: `const VERSION = '915157a-20260525';` (not the `__SW_VERSION__` placeholder).
- ✓ `scripts/build-sw.py` docstring mentions `killswitch` (3 occurrences).
- ✓ `scripts/patch-sw-registration.py` exists, is +x, stdlib-only, contains `updateViaCache`.
- ✓ First-run output: `patched=58 already_ok=0 no_register=37 total=95`.
- ✓ Second-run output: `patched=0 already_ok=58 no_register=37 total=95` (idempotency invariant).
- ✓ Zero bare `register("/sw.js")` matches remaining in tracked HTML.
- ✓ 58 HTML files carry `updateViaCache: 'none'`.
- ✓ Commits `856cafe`, `1140850`, `136b912` all in `git log` on branch `worktree-agent-a2e5310d712e6d003`.

---
*Phase: 01-pre-migration-safety*
*On-disk completion: 2026-05-25 (Tasks 1+2)*
*Deploy + DevTools verification: PENDING OPERATOR (Task 3 — checkpoint:human-verify)*
