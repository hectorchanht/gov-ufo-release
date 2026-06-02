---
created: 2026-06-02
title: Add /.well-known/security.txt OR remove the dangling reference
area: seo
files:
  - legacy/about.html (line 271 — `<a href="/.well-known/security.txt">`)
  - public/.well-known/security.txt (proposed)
---

## Problem

Surfaced during `/gsd:debug link-asset-seo-audit`. The about page (built from `legacy/about.html`) has:

```html
<li>Security finding? <a href="/.well-known/security.txt">/.well-known/security.txt</a></li>
```

But `dist/.well-known/security.txt` doesn't exist → 404 on production. RFC 9116 (`/.well-known/security.txt`) is a soft convention for vulnerability-disclosure contact, expected by some security scanners + GitHub's automated reporters.

## Two options

1. **Add it.** Create `public/.well-known/security.txt` with `Contact: mailto:realufo@flowtheroom.com`, expires date, optional PGP key reference. Astro auto-copies `public/` to `dist/`.
2. **Remove the link.** Edit `legacy/about.html` to drop the line, OR rewrite the about page in Astro Markdown to skip it.

Recommendation: option 1. Setting up a tiny security.txt costs nothing and is the right answer if anyone IS looking.

## Suggested file

```
Contact: mailto:realufo@flowtheroom.com
Expires: 2027-06-30T00:00:00.000Z
Preferred-Languages: en
Canonical: https://realufo.org/.well-known/security.txt
```

## Related

- RFC 9116 (security.txt spec)
- `/gsd:debug link-asset-seo-audit` (2026-06-02) — surfaced this
