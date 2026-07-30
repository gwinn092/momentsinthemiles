#!/usr/bin/env python3
"""Rebuild data/photo_dates.yaml — the date + place behind each photo on the site.

The photos in static/images/ were stripped of metadata before they entered the
repo (see the photo rules in CLAUDE.md), so their dates live only in the
originals on the Desktop. This script matches each site photo back to its
original by perceptual hash, then reads DateTimeOriginal and GPS off the
original and resolves the GPS to a state or country.

Nothing here runs in CI — it needs the photo archive, which is not in the repo.
Run it locally whenever photos are added, then commit the regenerated YAML.

    python3 scripts/build_photo_dates.py

Requires: ImageMagick (`magick`), exiftool, and the archive at ARCHIVE below.
"""
import json
import re
import subprocess
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = Path.home() / "Desktop" / "mitmfolder"
SITE_IMAGES = ROOT / "static" / "images"
OUT = ROOT / "data" / "photo_dates.yaml"
STATES_URL = "https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json"
WORLD_URL = "https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson"
CACHE_DIR = ROOT / ".cache"

# A 16x16 average hash tolerates the resize + re-encode the site copies went
# through. Real pairs land at distance 0-8; the nearest false match seen was 19.
HASH_MAX_DISTANCE = 8

# Country names as the site writes them, where they differ from the dataset.
COUNTRY_NAMES = {
    "Lao People's Democratic Republic": "Laos",
    "Viet Nam": "Vietnam",
    "United States Virgin Islands": "U.S. Virgin Islands",
    "United States of America": None,  # US points resolve to a state instead
}


def ahash(path):
    """16x16 grayscale average hash, as an int. None if the file won't decode."""
    try:
        txt = subprocess.run(
            ["magick", str(path), "-colorspace", "Gray", "-resize", "16x16!",
             "-depth", "8", "txt:-"],
            capture_output=True, text=True, timeout=60).stdout
    except (subprocess.SubprocessError, OSError):
        return None
    vals = []
    for line in txt.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 2:
            continue
        vals.append(int(parts[1].strip("()").split(",")[0]))
    if not vals:
        return None
    mean = sum(vals) / len(vals)
    bits = 0
    for v in vals:
        bits = (bits << 1) | (1 if v > mean else 0)
    return bits


def hash_all(paths, label):
    with ThreadPoolExecutor(max_workers=8) as pool:
        hashes = list(pool.map(ahash, paths))
    pairs = [(h, p) for h, p in zip(hashes, paths) if h is not None]
    print(f"  hashed {len(pairs)} {label}", file=sys.stderr)
    return pairs


def load_geo(url, filename, label):
    cache = CACHE_DIR / filename
    if not cache.exists():
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        print(f"  downloading {label}", file=sys.stderr)
        with urllib.request.urlopen(url, timeout=90) as r:
            cache.write_bytes(r.read())
    return json.loads(cache.read_text())


def point_in_ring(lon, lat, ring):
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def containing(lat, lon, collection):
    for feature in collection["features"]:
        geom = feature["geometry"]
        polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
        for poly in polys:
            if point_in_ring(lon, lat, poly[0]):
                return feature["properties"]["name"]
    return None


def nearest(lat, lon, collection, max_degrees=0.6):
    """Closest feature whose outline passes within max_degrees of the point.

    The country dataset drops small islands — Nusa Lembongan sits in open water
    as far as its polygons are concerned, about 12km off Bali. Rather than
    hardcode the places they have been, fall back to whatever coastline is
    genuinely nearest, and only within a tight radius.
    """
    best_d, best_name = None, None
    for feature in collection["features"]:
        geom = feature["geometry"]
        polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
        for poly in polys:
            for x, y in poly[0]:
                d = (x - lon) ** 2 + (y - lat) ** 2
                if best_d is None or d < best_d:
                    best_d, best_name = d, feature["properties"]["name"]
    if best_d is None or best_d ** 0.5 > max_degrees:
        return None
    return best_name


def place_of(lat, lon, states, world):
    """US points resolve to their state; everything else to its country.

    Real polygons, not bounding boxes — boxes put the Mekong photos in Thailand
    when they were taken across the river in Laos.
    """
    state = containing(lat, lon, states)
    if state:
        return state
    country = containing(lat, lon, world)
    if country is None:
        country = nearest(lat, lon, world)
    if country is None:
        return None
    if country == "United States of America":
        return nearest(lat, lon, states) or COUNTRY_NAMES.get(country)
    return COUNTRY_NAMES.get(country, country)


def harvest_alt_text():
    """Reuse the alt text each photo already carries wherever it appears.

    Keeps the On This Day card honest: the description is one Jesse or Karlee
    already wrote for that exact image, not something invented here.
    """
    alts = {}
    sources = list((ROOT / "content").rglob("*.md")) + list((ROOT / "themes").rglob("*.html"))
    pattern = re.compile(r'src="[^"]*?/?([\w.-]+\.jpg)"[^>]*?alt="([^"]+)"')
    for f in sources:
        for name, alt in pattern.findall(f.read_text(errors="ignore")):
            alts.setdefault(name, alt.strip())
    return alts


def read_exif(originals):
    """One exiftool pass over every matched original."""
    fmt = "${Directory}/${FileName}\t$DateTimeOriginal\t$GPSLatitude#\t$GPSLongitude#"
    out = subprocess.run(
        ["exiftool", "-q", "-m", "-d", "%Y-%m-%d", "-p", fmt, "-@", "-"],
        input="\n".join(str(o) for o in originals),
        capture_output=True, text=True).stdout
    info = {}
    for line in out.splitlines():
        parts = (line.split("\t") + ["", "", ""])[:4]
        info[parts[0]] = parts[1:]
    return info


def main():
    if not ARCHIVE.exists():
        sys.exit(f"photo archive not found at {ARCHIVE}")

    print("hashing site photos...", file=sys.stderr)
    site = hash_all(sorted(SITE_IMAGES.rglob("*.jpg")), "site photos")

    print("hashing archive originals...", file=sys.stderr)
    exts = ("*.jpg", "*.jpeg", "*.heic", "*.png", "*.JPG", "*.JPEG", "*.HEIC")
    originals = sorted({p for e in exts for p in ARCHIVE.rglob(e)})
    orig = hash_all(originals, "originals")

    matched = {}
    for sh, sp in site:
        best_d, best_p = None, None
        for oh, op in orig:
            d = (sh ^ oh).bit_count()
            if best_d is None or d < best_d:
                best_d, best_p = d, op
        if best_d is not None and best_d <= HASH_MAX_DISTANCE:
            matched[sp] = best_p
    print(f"  matched {len(matched)} of {len(site)} site photos", file=sys.stderr)

    exif = read_exif(matched.values())
    states = load_geo(STATES_URL, "us-states.json", "US state polygons")
    world = load_geo(WORLD_URL, "countries.geojson", "country polygons")
    alts = harvest_alt_text()

    entries = []
    for site_path, orig_path in sorted(matched.items()):
        date, lat, lon = exif.get(str(orig_path), ["", "", ""])
        if not date:
            continue
        place = None
        if lat and lon:
            try:
                place = place_of(float(lat), float(lon), states, world)
            except ValueError:
                pass
        entries.append({
            "src": str(site_path.relative_to(ROOT / "static")).lstrip("/"),
            "date": date,
            "place": place,
            "alt": alts.get(site_path.name),
        })

    entries.sort(key=lambda e: (e["date"][5:], e["date"]))
    lines = [
        "# Date and place behind each photo on the site. GENERATED — do not hand-edit;",
        "# run scripts/build_photo_dates.py and commit the result. Dates come from the",
        "# EXIF in the unstripped originals, matched to the site copies by image hash;",
        "# place is the GPS resolved against real US state and country polygons.",
        f"# {len(entries)} photos dated, "
        f"{sum(1 for e in entries if e['place'])} with a place, "
        f"{sum(1 for e in entries if e['alt'])} with alt text. Sorted by month-day.",
        "photos:",
    ]
    for e in entries:
        lines.append(f"  - src: \"{e['src']}\"")
        lines.append(f"    date: \"{e['date']}\"")
        if e["place"]:
            lines.append(f"    place: \"{e['place']}\"")
        if e["alt"]:
            lines.append(f"    alt: \"{e['alt']}\"")
    OUT.write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(entries)} photos)", file=sys.stderr)


if __name__ == "__main__":
    main()
