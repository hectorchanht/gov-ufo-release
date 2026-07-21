#!/usr/bin/env python3
"""
PURSUE — war.gov/UFO offline mirror downloader (TLS-impersonating version).

Why this exists:
  www.war.gov is behind Akamai bot protection that fingerprints the TLS
  handshake (JA3/JA4). curl, wget, and python-requests all have detectable
  fingerprints and get 403'd no matter what headers you send.

  curl_cffi wraps curl-impersonate, which replicates a real Chrome TLS
  handshake byte-for-byte, so Akamai lets the request through.

Setup:
  pip install curl_cffi

Run:
  python3 download.py
"""

from __future__ import annotations
import os, sys, time
from pathlib import Path

try:
    from curl_cffi import requests
except ImportError:
    sys.exit(
        "\nMissing dependency. Install with:\n"
        "    pip install curl_cffi\n"
        "or, if you use pipx / a venv, install it there.\n"
    )

ROOT = Path(__file__).resolve().parent.parent   # repo root
SLIDES_DIR    = ROOT / "slideshow"
SLIDES_2_DIR  = ROOT / "slideshow-2"             # Release 02 carousel images
SLIDES_3_DIR  = ROOT / "slideshow-3"             # Release 03 carousel images
SLIDES_4_DIR  = ROOT / "slideshow-4"             # Release 04 carousel images
BUNDLES_DIR   = ROOT / "bundles"
ASSETS_DIR    = ROOT / "assets"
for d in (SLIDES_DIR, SLIDES_2_DIR, SLIDES_3_DIR, SLIDES_4_DIR, BUNDLES_DIR, ASSETS_DIR):
    d.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "Referer": "https://www.war.gov/UFO/",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
}

# Try a few Chrome versions if one gets blocked
IMPERSONATE_PROFILES = ["chrome124", "chrome120", "chrome116", "chrome110"]


def fetch(url: str, out: Path) -> bool:
    """Download url -> out. Returns True on success."""
    label = out.name
    if out.exists() and out.stat().st_size > 0:
        print(f"  → {label:<70} [skip — already {out.stat().st_size:,} B]")
        return True

    last_code = "?"
    for profile in IMPERSONATE_PROFILES:
        try:
            r = requests.get(
                url,
                headers=HEADERS,
                impersonate=profile,
                timeout=1800,
                allow_redirects=True,
            )
            last_code = r.status_code
            if r.status_code == 200 and r.content:
                out.write_bytes(r.content)
                size = len(r.content)
                size_h = (
                    f"{size/1_000_000_000:.2f} GB" if size > 1_000_000_000 else
                    f"{size/1_000_000:.1f} MB"    if size > 1_000_000 else
                    f"{size/1_000:.1f} KB"        if size > 1_000 else
                    f"{size} B"
                )
                print(f"  → {label:<70} [ok  {size_h}  via {profile}]")
                return True
        except Exception as e:
            last_code = type(e).__name__
            time.sleep(1)
            continue

    print(f"  → {label:<70} [FAIL http={last_code}]")
    return False


SLIDESHOW_BASE = "https://www.war.gov/portals/1/Interactive/2026/UFO/Slideshow/"
SLIDES = [
    "FBI-Photo-1.jpg",
    "FBI-Photo-A5.jpg",
    "FBI-Photo-B2.jpg",
    "FBI-Photo-B7-.jpg",
    "FBI-Photo-B18.jpg",
    "FBI-Photo-B20.jpg",
    "2024-04-30-Composite-Sketch.jpg",
    "NASA-UAP-VM6-Apollo-17-1972.jpg",
    "DOW-UAP-PR19-Unresolved-UAP-Report-Middle-East-May-2022.jpg",
    "DOW-UAP-PR26-Unresolved-UAP-Report-United-Arab-Emirates-October-2023.jpg",
    "DOW-UAP-PR34-Unresolved-UAP-Report-Greece-October-2023.jpg",
    "DOW-UAP-PR35-Unresolved-UAP-Report-Greece-October-2023.jpg",
    "DOW-UAP-PR38-Unresolved-UAP-Report-Middle-East-2013.jpg",
    "DOW-UAP-PR43-Unresolved-UAP-Report-Africa-2025.jpg",
    "DOW-UAP-PR45-Unresolved-UAP-Report-Middle-East-2020.jpg",
    "DOW-UAP-PR46-Unresolved-UAP-Report-INDOPACOM-2024.jpg",
    "DOW-UAP-PR49-Unresolved-UAP-Report-Department-of-the-Army-2026.jpg",
]

LOGOS = [
    ("https://www.war.gov/Portals/1/Images/DOD-Icon-Header.png", "DOD-Icon-Header.png"),
    ("https://www.war.gov/Portals/1/Images/DOW-Icon-Header.png", "DOW-Icon-Header.png"),
]

# Release 02 (2026-05-22) — second tranche of records under PURSUE.
# Lives under a different Portals path (Slideshow-2/) and has its own
# document bundle + 5.6 GB video archive on Cloudfront.
SLIDESHOW_2_BASE = "https://www.war.gov/portals/1/Interactive/2026/UFO/Slideshow-2/"
SLIDES_2 = [
    "CIA-UAP-D001_Intelligence_Information_Report_USSR_1973.jpg",
    "DOE-UAP-D001_PANTEX_Image.jpg",
    "DOW-UAP-D017_General_Correspondence_Of_Sandia.jpg",
    "DOW-UAP-PR050_4UAP_Formation_Iran_26_Aug_2022.jpg",
    "DOW-UAP-PR051.jpg",
    "DOW-UAP-PR052.jpg",
    "DOW-UAP-PR071_USAF-ANG F-16C_callsign_CALLSIGN_Shoots_Down_UAP.jpg",
    "DOW-UAP-PR086-UAP_from_Dec_2019_East_Coast.jpg",
    "NASA-UAP-D008_Apollo12_Medical_Debriefing.jpg",
    "ODNI-UAP-D001_USPER_Narrative_Senior_USIC.jpg",
]

# Release 03 (2026-06-12) — third tranche under PURSUE. 72 records
# (53 PDF, 10 IMG, 6 VID, 3 AUD). The hero/carousel imagery lives under a
# new /061226/Rotator/ path (NOT a Slideshow-3/ dir), and ships its own
# document bundle + a ~5 GB Cloudfront video archive. Filenames discovered
# verbatim from the live www.war.gov/UFO/ page markup.
SLIDESHOW_3_BASE = "https://www.war.gov/portals/1/Interactive/2026/UFO/061226/Rotator/"
SLIDES_3 = [
    "CIA-UAP-017_Placement_on_High_Alert_Due_to_Perceived_Aggressive_Foreign_Posturing.jpg",
    "DOW-UAP-D084_USArmy-Flying-Saucer-Study_1949_.jpg",
    "FBI-UAP-D002_FD-1057_Unresolved-UAP-Report_ColoradoSprings_2022.jpg",
    "FBI-UAP-D003_Digital-Rendering_Unresolved-UAP-Report_ColoradoSprings_2022.jpg",
    "FBI-UAP-D009_FD-302-67_Northeastern-Orb-Sighting_2026.jpg",
    "FBI-UAP-D010_FD-302-71_Northeastern-Orb-Sighting_2026.jpg",
    "FBI-UAP-D011_DFBI-Correspondence-Referral_1949.jpg",
    "FBI-UAP-PR003_Orbs-Over-the-Pond_2024.jpg",
    "FBI-UAP-PR004_Northeastern-Orb-Sighting_2025.jpg",
    "ICA-UAP-D001_Analysis_Colorado-Springs-UAP-Incident.jpg",
]

# Release 04 (2026-07-10) — fourth tranche under PURSUE. 40 records
# (14 PDF, 3 IMG, 19 VID, 4 AUD). Carousel imagery lives under a
# /071026/Slideshow/ path; documents are served as individual PDFs (no
# doc-bundle zip) and a ~1.55 GB Cloudfront video archive holds the 23
# DOD_*.mp4 assets. Filenames verbatim from the live www.war.gov/UFO/ markup.
SLIDESHOW_4_BASE = "https://www.war.gov/portals/1/Interactive/2026/UFO/071026/Slideshow/"
SLIDES_4 = [
    "DOE-UAP-D004_Los-Alamos-Conference-on-Aerial-Phenomena_1949.jpg",
    "DOW-UAP-D094_Analysis-of-Flying-Object-Incidents-in-the-US_1949.jpg",
    "DOW-UAP-D097_Project-Sign-Progress-Report_1948.jpg",
    "DOW-UAP-PR104_Unresolved-UAP-Report_Yellow-Sea_2025.jpg",
    "DOW-UAP-PR105_Unresolved-UAP-Report_East-China-Sea_2025.jpg",
    "DOW-UAP-PR113_Unresolved-UAP-Report_Western-US_1996.jpg",
    "DOW-UAP-PR115_Unresolved-UAP-Report_Gulf-of-America_2019.jpg",
    "NASA-UAP-D030_STS-80-Unidentified-Object-Image1_1996.jpg",
    "NASA-UAP-D031_STS-80-Unidentified-Object-Image2_1996.jpg",
    "NASA-UAP-D032_STS-80-Unidentified-Object-Image3_1996.jpg",
]

# Release 04 individual document PDFs (14). Served directly under
# /medialink/ufo/071026/release_04/documents/ (no bundle zip). Fetched into
# BUNDLES_DIR/release_04_documents/ for the R2 pdfs/wargov/ mirror.
DOCS_4_BASE = "https://www.war.gov/medialink/ufo/071026/release_04/documents/"
DOCS_4_DIR  = BUNDLES_DIR / "release_04_documents"
DOCS_4 = [
    "DOE-UAP-D004_Los-Alamos-Conference-on-Aerial-Phenomena_1949.pdf",
    "DOW-UAP-D094_Analysis-of-Flying-Object-Incidents-in-the-US_1949.pdf",
    "DOW-UAP-D097_Project-Sign-Progress-Report_1948.pdf",
    "CIA-UAP-D020_Memorandum-on-Unconventional-Aircraft-Sightings_1955.pdf",
    "CIA-UAP-D021_Analysis-of-Unconventional-Aircraft-Sightings_1955.pdf",
    "DOE-UAP-D005_Pantex-Unidentified-Object-Incident-Report_2015.pdf",
    "DOW-UAP-D089_Range-Fouler-Debrief_Eastern-US_2020.pdf",
    "DOW-UAP-D090_Range-Fouler-Debrief_Eastern-US_2019.pdf",
    "DOW-UAP-D091_Range-Fouler-Debrief_Atlantic-Ocean_2020.pdf",
    "DOW-UAP-D092_DAF-Committee-to-Review-Project-Bluebook_1966-1967.pdf",
    "DOW-UAP-D093_Analysis-of-Flying-Object-Incidents-in-the-US_1948.pdf",
    "DOW-UAP-D095_Joint-US-Canadian-Aviation-Projects-and-UFO-Sighting-Reports_1954-1955.pdf",
    "DOW-UAP-D096_Correspondence-Relating-to-Project-Blue-Book_1955.pdf",
    "FBI-UAP-D014_Correspondence-Relating-to-UFO-Sightings_1967_1974.pdf",
]

# Master manifest. As of Release 02 (5/22/26), war.gov serves a single
# combined CSV (uap-data.csv) that includes both Release 01 and 02 rows.
# The legacy /uap-release001.csv is still served verbatim — we keep both.
MANIFESTS = [
    ("https://www.war.gov/Portals/1/Interactive/2026/UFO/uap-data.csv",
     "uap-data.csv"),
    ("https://www.war.gov/Portals/1/Interactive/2026/UFO/uap-release001.csv",
     "uap-release001.csv"),
]

BUNDLES = [
    # Release 01
    ("https://www.war.gov/medialink/ufo/bundle/Release_1.zip", "Release_1.zip"),
    ("https://cdn.dvidshub.net/press/uapvideos.zip",           "uapvideos.zip"),
    # Release 02 (5/22/26) — 6 PDFs + 57 mp4 (51 video + 7 audio-as-mp4)
    ("https://www.war.gov/medialink/ufo/052226/release_02/release_02_document_bundle.zip",
     "release_02_document_bundle.zip"),
    ("https://d34w7g4gy10iej.cloudfront.net/uap052226.zip",
     "uap052226.zip"),
    # Release 03 (6/12/26) — 53 PDFs + IMG renderings (~866 MB docs bundle)
    # + ~4.96 GB cloudfront video archive. URLs verbatim from war.gov/UFO/.
    ("https://www.war.gov/medialink/ufo/061226/release_03/release_03_documents.zip",
     "release_03_documents.zip"),
    ("https://d34w7g4gy10iej.cloudfront.net/release_03/uap_videos_061226.zip",
     "uap_videos_061226.zip"),
    # Release 04 (7/10/26) — 14 individual PDFs (see DOCS_4) + a ~1.55 GB
    # cloudfront video archive (23 DOD_*.mp4). URL verbatim from war.gov/UFO/.
    ("https://d34w7g4gy10iej.cloudfront.net/release_04/uap_release04_videos_071026.zip",
     "uap_release04_videos_071026.zip"),
]


def main():
    print("\n=== Slideshow images — Release 01 (17) ===")
    ok = sum(fetch(SLIDESHOW_BASE + f, SLIDES_DIR / f) for f in SLIDES)
    print(f"  ({ok}/{len(SLIDES)} ok)")

    print("\n=== Slideshow images — Release 02 (10) ===")
    ok = sum(fetch(SLIDESHOW_2_BASE + f.replace(" ", "%20"), SLIDES_2_DIR / f)
             for f in SLIDES_2)
    print(f"  ({ok}/{len(SLIDES_2)} ok)")

    print("\n=== Slideshow images — Release 03 (10) ===")
    ok = sum(fetch(SLIDESHOW_3_BASE + f.replace(" ", "%20"), SLIDES_3_DIR / f)
             for f in SLIDES_3)
    print(f"  ({ok}/{len(SLIDES_3)} ok)")

    print("\n=== Slideshow images — Release 04 (10) ===")
    ok = sum(fetch(SLIDESHOW_4_BASE + f.replace(" ", "%20"), SLIDES_4_DIR / f)
             for f in SLIDES_4)
    print(f"  ({ok}/{len(SLIDES_4)} ok)")

    print("\n=== Release 04 document PDFs (14) ===")
    DOCS_4_DIR.mkdir(parents=True, exist_ok=True)
    ok = sum(fetch(DOCS_4_BASE + f.replace(" ", "%20"), DOCS_4_DIR / f)
             for f in DOCS_4)
    print(f"  ({ok}/{len(DOCS_4)} ok)")

    print("\n=== Site chrome (logos) ===")
    for url, name in LOGOS:
        fetch(url, ASSETS_DIR / name)

    print("\n=== File manifests ===")
    for url, name in MANIFESTS:
        fetch(url, ROOT / name)

    print("\n=== Bundles ===")
    print("  Release 01: Release_1.zip (~1.2 GB docs+imgs), uapvideos.zip (~1.3 GB)")
    print("  Release 02: release_02_document_bundle.zip (~70 MB), uap052226.zip (~5.6 GB)")
    print("  Release 03: release_03_documents.zip (~866 MB), uap_videos_061226.zip (~4.96 GB)")
    for url, name in BUNDLES:
        fetch(url, BUNDLES_DIR / name)

    print("\n=== Done. Tree: ===")
    for p in sorted(ROOT.rglob("*")):
        if p.is_file() and p.name != "download.py":
            rel = p.relative_to(ROOT)
            print(f"  {str(rel):<60} {p.stat().st_size:>14,} B")
    print("\nOpen index.html in a browser to view the offline page.\n")


if __name__ == "__main__":
    main()
