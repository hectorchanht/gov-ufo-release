/**
 * Astro Content Collections schema — 15 archives.
 *
 * Defines one Content Collection per government UAP archive (per CLAUDE.md §2),
 * with Zod validation + Astro's official `file()` loader reading `data/<slug>.json`.
 *
 * ### Decisions
 * - **D-02:** All 15 archives have a collection in Phase 3, even though only
 *   wargov ships rendered pages. Schema is the single source of truth Phase 4
 *   SSG-06 will consume byte-for-byte from `scripts/build-<slug>.py` output.
 * - **D-03:** Zod throws `ZodError` → Astro propagates as a hard build error.
 *   No silent drop-on-validation-failure.
 * - **D-04:** `data/<slug>.json` is committed, never gitignored. `pnpm prebuild`
 *   normalises CSV/scrape inputs into these files.
 *
 * ### Fidelity guard (D-26..D-28; PITFALLS.md #6)
 * - NO `z.transform()`, NO `z.preprocess()` on text fields. Smart quotes,
 *   em-dashes, accents, zero-width chars round-trip byte-exact through the
 *   schema. Any Zod transform on `ti`, `de`, `Title`, `Description Blurb`,
 *   `Release Date`, `Incident Date`, `Incident Location`, etc. is a fidelity bug.
 * - `catalogAssetSchema` uses `.strict()` so unknown fields in `assets[]` are
 *   caught as drift signals. The envelope schemas are lenient (extra top-level
 *   fields allowed for forward-compat).
 *
 * ### Schema variants (no monolithic union)
 * - `catalogEnvelopeSchema` — 14 catalog-style archives (AARO, NASA, NARA,
 *   GEIPAN, UK, Brazil, Chile, Argentina, Canada, Italy, NZ, Peru, Spain,
 *   Uruguay). `{ assets: [...], stats: {...} }`.
 * - `wargovEnvelopeSchema` — wargov only. `{ rows: [...], shards: [...] }`
 *   keyed by the CSV column names verbatim (literal spaces in keys are
 *   intentional — CSV-format drift is a build-time error per D-02).
 *
 * ### Loader shape (Astro 5 `file()` — entries-object form)
 * - Each `data/<slug>.json` contains a top-level object whose keys are entry
 *   IDs and whose values are the validated payload. Phase 3 uses a single
 *   entry id of `"v1"` per archive. The shape:
 *   ```
 *   { "v1": { "schemaVersion": 1, "slug": "<slug>", "assets": [], "stats": {...} } }
 *   ```
 *   See `data/README.md` for envelope-shape documentation.
 *
 * Source-of-truth: scripts/templates/archive.py docstring (catalog shape) +
 * index.html's `<script id="archive-manifest">` (wargov CSV-keyed shape).
 */

import { defineCollection, z } from 'astro:content';
import { file } from 'astro/loaders';

// -----------------------------------------------------------------------------
// Catalog-style archives (AARO, NASA, NARA, GEIPAN, UK, Brazil, Chile,
// Argentina, Canada, Italy, NZ, Peru, Spain, Uruguay).
// -----------------------------------------------------------------------------

/**
 * Asset card schema — abbreviated field names match the existing Python
 * output (`scripts/templates/archive.py`) byte-for-byte. Phase 4 SSG-06
 * will reuse this schema unchanged.
 *
 * `.strict()` rejects unknown fields. If a scrape pipeline starts emitting
 * a new column, the build fails loudly and the new field gets a documented
 * home in this schema (drift signal per D-02 / SSG-02).
 */
const catalogAssetSchema = z
  .object({
    // Type — enum extended to cover CASE / PAGE found in existing arch-data
    // (grep -rhoE '"t": *"[A-Z]+"' across the repo).
    t: z.enum(['PDF', 'VID', 'IMG', 'CATALOG', 'AUDIO', 'CASE', 'PAGE']),
    // Title — verbatim official title (CLAUDE.md §4.2). NO transform.
    ti: z.string().min(1),
    // Description — substantive context OR empty (CLAUDE.md §9). NO transform.
    de: z.string().default(''),
    // Agency — primary releasing body.
    ag: z.string().default(''),
    // Category — Document / Imagery / Video / Catalog / etc.
    cat: z.string().default(''),
    // Date — incident date OR release date. Free-form string per current
    // Python output (YYYY-MM-DD or MM/DD/YY); validated upstream by the
    // normaliser, not here.
    date: z.string().default(''),
    // Region — geographic context (optional).
    region: z.string().default(''),
    // Local path — '' if not committed; otherwise repo-relative path.
    l: z.string().default(''),
    // Download URL — release URL, local repo-rooted path, or external.
    // Lenient string (URL validation deferred to upstream normaliser).
    u: z.string().default(''),
    // Source page URL (official site) — optional.
    s: z.string().optional(),
    // Thumbnail relative path — optional.
    th: z.string().default(''),
  })
  .strict();

const catalogStatsSchema = z.object({
  total: z.number(),
  local_total: z.number(),
  pdf_total: z.number(),
  catalog_total: z.number(),
});

const catalogEnvelopeSchema = z.object({
  // Discriminator for future schema migrations.
  schemaVersion: z.literal(1),
  slug: z.string(),
  assets: z.array(catalogAssetSchema),
  stats: catalogStatsSchema,
});

// -----------------------------------------------------------------------------
// wargov — CSV-keyed shape. Column names are literal `uap-release001.csv`
// header strings (with spaces). DO NOT rename keys here — fidelity over
// ergonomics (D-26..D-28). Phase 5 scrape automation reads the same CSV
// header verbatim, so any rename would silently break the round-trip.
// -----------------------------------------------------------------------------

const wargovRowSchema = z.object({
  // `Featured` — new leading column introduced with war.gov Release 03
  // (6/12/26). 'YES' flags the row as a hero/Rotator carousel pick on the
  // official site. Lenient string fall-through (D-02 drift signal): the
  // CSV gained this column verbatim, so the schema documents it rather than
  // silently passing it through the non-strict envelope.
  Featured: z.string().default(''),
  Redaction: z.string().default(''),
  'Release Date': z.string().default(''),
  Title: z.string().min(1),
  // Phase 3: lenient string fall-through so unknown future types don't trip
  // the build. Phase 4 tightens to a strict enum once the CSV stabilises.
  Type: z.string().default(''),
  'Video Pairing': z.string().default(''),
  'PDF Pairing': z.string().default(''),
  'Description Blurb': z.string().default(''),
  'DVIDS Video ID': z.string().default(''),
  'Video Title': z.string().default(''),
  Agency: z.string().default(''),
  'Incident Date': z.string().default(''),
  'Incident Location': z.string().default(''),
  'PDF | Image Link': z.string().default(''),
  'Modal Image': z.string().default(''),
  'Image Alt Text': z.string().default(''),
  'Image VIRIN': z.string().default(''),
  // `local` appears in the current inline manifest (root index.html ~L1339).
  // Tracked so the schema round-trips against the existing Python output.
  local: z.string().default(''),
});

const wargovEnvelopeSchema = z.object({
  schemaVersion: z.literal(1),
  slug: z.literal('wargov'),
  rows: z.array(wargovRowSchema),
  // Optional shard manifest for D-10 (server-side card shards). Plan 03-03
  // writes this if it splits wargov.json by 50-card boundaries.
  shards: z
    .array(
      z.object({
        index: z.number(),
        file: z.string(),
      }),
    )
    .default([]),
});

// -----------------------------------------------------------------------------
// Collection registry — 15 archives keyed by CLAUDE.md §2 slug. Each archive
// gets its own collection so consumer pages query by name (`getCollection
// ('wargov')`, `getCollection('aaro')`, ...) instead of filtering a monolith.
// -----------------------------------------------------------------------------

export const collections = {
  wargov: defineCollection({
    loader: file('data/wargov.json'),
    schema: wargovEnvelopeSchema,
  }),
  aaro: defineCollection({
    loader: file('data/aaro.json'),
    schema: catalogEnvelopeSchema,
  }),
  nasa: defineCollection({
    loader: file('data/nasa.json'),
    schema: catalogEnvelopeSchema,
  }),
  nara: defineCollection({
    loader: file('data/nara.json'),
    schema: catalogEnvelopeSchema,
  }),
  geipan: defineCollection({
    loader: file('data/geipan.json'),
    schema: catalogEnvelopeSchema,
  }),
  uk: defineCollection({
    loader: file('data/uk.json'),
    schema: catalogEnvelopeSchema,
  }),
  brazil: defineCollection({
    loader: file('data/brazil.json'),
    schema: catalogEnvelopeSchema,
  }),
  chile: defineCollection({
    loader: file('data/chile.json'),
    schema: catalogEnvelopeSchema,
  }),
  argentina: defineCollection({
    loader: file('data/argentina.json'),
    schema: catalogEnvelopeSchema,
  }),
  canada: defineCollection({
    loader: file('data/canada.json'),
    schema: catalogEnvelopeSchema,
  }),
  italy: defineCollection({
    loader: file('data/italy.json'),
    schema: catalogEnvelopeSchema,
  }),
  nz: defineCollection({
    loader: file('data/nz.json'),
    schema: catalogEnvelopeSchema,
  }),
  peru: defineCollection({
    loader: file('data/peru.json'),
    schema: catalogEnvelopeSchema,
  }),
  spain: defineCollection({
    loader: file('data/spain.json'),
    schema: catalogEnvelopeSchema,
  }),
  uruguay: defineCollection({
    loader: file('data/uruguay.json'),
    schema: catalogEnvelopeSchema,
  }),
};
