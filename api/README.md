# realufo.org static API

Generated: 2026-06-02T08:00:22Z  
Total records: **0**  
Total archives: **15**

## Endpoints

| File | Shape | Use case |
| --- | --- | --- |
| [`all.json`](all.json) | `{_meta, records: [...]}` | Every record across every archive. |
| [`by-archive.json`](by-archive.json) | `{_meta, archives: {slug: [...]}}` | Group by archive. |
| [`stats.json`](stats.json) | `{_meta, perArchive: [...]}` | Counts only, low bandwidth. |

## Record schema

```json
{
  "archive": "aaro",
  "archiveLabel": "AARO",
  "archiveDir": "aaro/",
  "title": "...",
  "description": "...",
  "agency": "...",
  "category": "...",
  "classification": "...",
  "date": "...",
  "region": "...",
  "url": "https://...",
  "src": "https://...",
  "local": "pdfs/whatever.pdf",
  "thumb": "https://...",
  "type": "PDF"
}
```

## Licensing

Each record inherits the licence of its source jurisdiction
(US 17 U.S.C. §105, UK OGL v3, France Loi 78-753, Brazil LAI 12.527,
Chile 20.285, etc.). See the matching archive page for the canonical
source URL of any record.

## CORS

GitHub Pages serves these files with `Access-Control-Allow-Origin: *`.
