#!/usr/bin/env python3
"""Assert that the site's prose still agrees with the site's data.

check_links.py catches dead links. check_invariants.py catches templates and
build output that drift. This one catches a third class: a sentence that was
true when it was written and quietly stopped being true when the data under it
changed. Nothing here is a broken page — every one of these ships green and
reads wrong.

Each check exists because the bug it describes actually shipped:

  - The Southeast Asia itinerary said "Seven countries and thirty-one stops"
    for five days after the Philippines was added to the stop list, making it
    eight and thirty-four. The summary is hand-written; the stops are data;
    nothing connected the two.
  - Canada and Mexico were inked as visited on the world map with no story and
    no tooltip note, so the twelve-country claim had three countries behind it
    that said nothing at all when a reader hovered or clicked.
  - Work With Us and the Leave Anyway Kit shared a hero image, so a sponsor and
    a buyer landed on what looked like the same page.
  - The Van Life landing page ran two photos as in-body fullbleeds that were
    also, further down the same page, the card heroes of two of its own posts.
  - The affiliate disclosure partial keyed off two partner IDs by name, so a
    link for any third partner would have gone out earning a real commission
    with no disclosure beside it, and nothing would have failed.

Scope note: the ink check covers the world map only. The US map inks all 48
states deliberately — most have no story and that is the point — so applying it
there would fail 36 times on purpose.

Usage: python3 scripts/check_content.py
Only stdlib, no YAML dependency. Exits non-zero with a report so CI fails
instead of deploying.
"""
import glob
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
failures = []
notes = []

# Countries knowingly inked with nothing behind them yet, because the trips are
# real but the stories have not been written with Jesse and Karlee. Listed here
# so the gate can go live green instead of sitting disabled, and so the debt is
# recorded in code rather than remembered. DELETE A NAME the moment its story or
# tooltip note lands — a stale entry here is reported below, it does not rot
# silently. Any country that goes quiet and is NOT on this list fails the build.
KNOWN_SILENT = {"Canada", "Mexico"}


def fail(check, detail):
    failures.append((check, detail))


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace") as fh:
        return fh.read()


def frontmatter(path):
    """Return (frontmatter_text, body_text) for a content file."""
    text = open(path, encoding="utf-8", errors="replace").read()
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    return (m.group(1), m.group(2)) if m else ("", text)


def is_draft(fm):
    return bool(re.search(r"^draft:\s*true\s*$", fm, re.M))


def hero_of(fm):
    m = re.search(r'^image:\s*"?([^"\n]+?)"?\s*$', fm, re.M)
    return m.group(1).strip() if m else None


# --- number words ----------------------------------------------------------
_UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19,
}
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
         "seventy": 70, "eighty": 80, "ninety": 90}


def word_to_int(word):
    """'thirty-four' -> 34. Returns None if it isn't a number word."""
    w = word.strip().lower().replace("–", "-")
    if w.isdigit():
        return int(w)
    if w in _UNITS:
        return _UNITS[w]
    if w in _TENS:
        return _TENS[w]
    if "-" in w:
        a, _, b = w.partition("-")
        if a in _TENS and b in _UNITS and _UNITS[b] < 10:
            return _TENS[a] + _UNITS[b]
    return None


_NUMWORD = r"[A-Za-z]+(?:-[A-Za-z]+)?|\d+"


def stated_count(text, noun):
    """Find '<number> <noun>' in prose. Returns (int, phrase) or (None, None)."""
    for m in re.finditer(rf"\b({_NUMWORD})\s+{noun}\b", text, re.I):
        n = word_to_int(m.group(1))
        if n is not None:
            return n, m.group(0)
    return None, None


# --- 1. itinerary prose vs the stop list ------------------------------------
def check_itinerary_counts():
    """The summary/subtitle must agree with the stops actually listed."""
    path = os.path.join(ROOT, "data", "itineraries.yaml")
    if not os.path.exists(path):
        return
    text = open(path, encoding="utf-8", errors="replace").read()

    # Split into itinerary blocks on the "- slug:" list markers.
    blocks = re.split(r"^\s*-\s+slug:\s*", text, flags=re.M)[1:]
    for blk in blocks:
        slug = blk.split("\n", 1)[0].strip().strip('"')
        # Prose fields that might carry a count.
        prose = " ".join(
            m.group(1) for m in
            re.finditer(r'^\s*(?:summary|subtitle):\s*"([^"]*)"', blk, re.M)
        )
        if not prose:
            continue
        stops = re.findall(r'^\s*-\s+place:\s*"?([^"\n]+?)"?\s*$', blk, re.M)
        countries = []
        for c in re.findall(r'^\s*country:\s*"?([^"\n]+?)"?\s*$', blk, re.M):
            if c not in countries:
                countries.append(c)

        for noun, actual in (("stops", len(stops)), ("countries", len(countries))):
            said, phrase = stated_count(prose, noun)
            if said is not None and said != actual:
                fail("itinerary-count",
                     f'{slug}: prose says "{phrase}" but the data lists '
                     f"{actual} {noun}")


# --- 2. every inked country says something ----------------------------------
def check_map_ink():
    """A country filled as visited must have a story or a tooltip note."""
    tpl = os.path.join(ROOT, "themes", "moments", "layouts", "partials",
                       "map-world.html")
    stories = os.path.join(ROOT, "data", "map_stories.yaml")
    if not (os.path.exists(tpl) and os.path.exists(stories)):
        return
    matched = set(re.findall(r'^\s*match:\s*"([^"]+)"',
                             open(stories, encoding="utf-8").read(), re.M))
    html = open(tpl, encoding="utf-8", errors="replace").read()

    silent = []
    for m in re.finditer(r"<path[^>]*>", html):
        tag = m.group(0)
        if "mp--visited" not in tag:
            continue
        name = re.search(r'data-name="([^"]+)"', tag)
        if not name:
            continue
        name = name.group(1)
        note = re.search(r'data-note="([^"]*)"', tag)
        has_note = bool(note and note.group(1).strip())
        if name not in matched and not has_note:
            silent.append(name)

    unexpected = sorted(set(silent) - KNOWN_SILENT)
    if unexpected:
        fail("map-ink",
             f"{len(unexpected)} country/countries are inked as visited but have "
             f"neither a story in map_stories.yaml nor a data-note, so hovering "
             f"shows a bare name and clicking does nothing: "
             f"{', '.join(unexpected)}")

    owed = sorted(set(silent) & KNOWN_SILENT)
    if owed:
        notes.append(f"{len(owed)} country/countries still owe a story: "
                     f"{', '.join(owed)}")

    stale = sorted(KNOWN_SILENT - set(silent))
    if stale:
        fail("map-ink",
             f"KNOWN_SILENT lists {', '.join(stale)}, but they now have a story "
             f"or a note. Remove them from the set in this script.")


# --- 3. two published pages sharing one hero --------------------------------
def check_hero_uniqueness():
    heroes = defaultdict(list)
    for path in glob.glob(os.path.join(ROOT, "content", "**", "*.md"),
                          recursive=True):
        fm, _ = frontmatter(path)
        if is_draft(fm):
            continue
        img = hero_of(fm)
        if img:
            heroes[img].append(
                os.path.relpath(path, os.path.join(ROOT, "content")))

    for img, pages in sorted(heroes.items()):
        if len(pages) > 1:
            fail("duplicate-hero",
                 f"{img} is the hero of {len(pages)} published pages "
                 f"({', '.join(sorted(pages))}) — they show the same picture "
                 f"in listings and share an OG card")


# --- 4. a section landing page reusing its own posts' heroes ----------------
def check_section_image_reuse():
    for idx in glob.glob(os.path.join(ROOT, "content", "*", "_index.md")):
        section = os.path.dirname(idx)
        _, body = frontmatter(idx)
        in_body = set(re.findall(r'src="([^"]+\.(?:jpg|jpeg|png|webp))"', body))
        if not in_body:
            continue

        kids = {}
        for path in glob.glob(os.path.join(section, "*.md")):
            if os.path.basename(path) == "_index.md":
                continue
            fm, _ = frontmatter(path)
            if is_draft(fm):
                continue
            img = hero_of(fm)
            if img:
                kids[img] = os.path.basename(path)

        name = os.path.basename(section)
        for img in sorted(in_body):
            if img in kids:
                fail("section-image-reuse",
                     f"/{name}/ uses {img} in its own copy and again as the "
                     f"card hero for {kids[img]} — the same photo twice on "
                     f"one page")


def check_affiliate_disclosure():
    """Every page carrying an affiliate link must also carry the disclosure.

    This is an FTC requirement, so it is checked at source rather than in the
    build output: the disclosure partial deliberately renders nothing while all
    partner IDs are blank, which would make a rendered-output check pass for the
    wrong reason and then start failing the day money got switched on.

    The bug this replaces: the partial tested `agodaCid` or `bookingAid` by
    name, so a link for any third partner would have shipped with no disclosure
    at all and nothing would have said so.
    """
    for path in glob.glob(os.path.join(ROOT, "content", "**", "*.md"), recursive=True):
        text = read(os.path.relpath(path, ROOT))
        has_link = "{{< book" in text or 'rel="sponsored' in text
        if has_link and "{{< affiliate-note" not in text:
            fail("affiliate-disclosure",
                 f"{os.path.relpath(path, ROOT)} has an affiliate link but no "
                 "{{< affiliate-note >}} — that is an FTC requirement, not a "
                 "preference")


# --- 6. road-trip stops: the honesty rules, enforced ------------------------
def check_road_trip_stops():
    """A stop we have never been to must say so, and must never earn money.

    data/road_trips.yaml publishes an invented ROUTE built from real STOPS. The
    whole thing rests on one promise: `status: list` means we have not been
    there, it is labelled as such on the page, and it carries no booking link.
    That promise is one careless edit away from breaking silently, so it is
    checked here rather than remembered.

    Parsed with regex on purpose — this script has no YAML dependency.
    """
    path = os.path.join(ROOT, "data", "road_trips.yaml")
    if not os.path.exists(path):
        return
    text = open(path, encoding="utf-8").read()

    body = text.split("\nstops:", 1)
    if len(body) < 2:
        return
    regions = set(re.findall(r'^\s*-\s*id:\s*([A-Za-z0-9_-]+)', body[0], re.M))
    story_ids = set()
    ms = os.path.join(ROOT, "data", "map_stories.yaml")
    if os.path.exists(ms):
        story_ids = set(re.findall(r'^\s*-\s*id:\s*([A-Za-z0-9_-]+)',
                                   open(ms, encoding="utf-8").read(), re.M))

    spines = defaultdict(list)
    for block in re.split(r'\n  - id:', body[1])[1:]:
        sid = block.split("\n", 1)[0].strip()

        def field(name):
            m = re.search(rf'^\s{{4}}{name}:\s*(.*?)\s*$', block, re.M)
            if not m:
                return ""
            raw = m.group(1)
            quoted = re.match(r'"([^"]*)"', raw)
            if quoted:
                return quoted.group(1).strip()
            # A bare value ends at an inline comment: `status: been  # note`.
            return raw.split("#", 1)[0].strip()

        if field("example") == "true":
            continue

        status = field("status")
        if status not in ("been", "list"):
            fail("road-trip-stop",
                 f"stop '{sid}' has status '{status or "(none)"}' — must be "
                 f"'been' or 'list'. Without it the page cannot tell a reader "
                 f"whether we have actually been there.")

        if status == "list" and not field("why_listed"):
            fail("road-trip-stop",
                 f"stop '{sid}' is marked 'list' (never been) with no "
                 f"why_listed. A stop we have not visited must say who told us "
                 f"or what we drove past, or it is filler.")

        if status == "list" and re.search(r'^\s+\w*(book|affiliate)\w*:', block,
                                          re.M | re.I):
            fail("road-trip-stop",
                 f"stop '{sid}' has never been visited but carries a booking or "
                 f"affiliate field. We do not earn a commission on a place we "
                 f"have not been — it is the one thing that would make every "
                 f"other recommendation untrustworthy.")

        region = field("region")
        if regions and region not in regions:
            fail("road-trip-stop",
                 f"stop '{sid}' names region '{region}', which is not defined "
                 f"in the regions list.")

        story = field("story_id")
        if story and story_ids and story not in story_ids:
            fail("road-trip-stop",
                 f"stop '{sid}' points at story_id '{story}', which does not "
                 f"exist in map_stories.yaml — its photo and prose would be "
                 f"silently missing.")

        spine = field("spine")
        if spine:
            spines[region].append((spine, sid))

    for region, entries in spines.items():
        seen = defaultdict(list)
        for spine, sid in entries:
            seen[spine].append(sid)
        for spine, ids in seen.items():
            if len(ids) > 1:
                fail("road-trip-stop",
                     f"region '{region}' has {len(ids)} stops sharing spine "
                     f"{spine} ({', '.join(ids)}) — the driving order between "
                     f"them is undefined and would flip between builds.")


def main():
    check_itinerary_counts()
    check_map_ink()
    check_hero_uniqueness()
    check_section_image_reuse()
    check_affiliate_disclosure()
    check_road_trip_stops()

    for n in notes:
        print(f"note: {n}")
    if failures:
        print(f"\nCONTENT CHECK FAILED ({len(failures)}):")
        for check, detail in failures:
            print(f"  [{check}] {detail}")
        sys.exit(1)
    print("Content check passed.")


if __name__ == "__main__":
    main()
