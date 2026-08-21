#!/usr/bin/env python3
"""Assert the things about this site that are easy to break and hard to notice.

check_links.py already catches dead links. These are the other classes of bug
that shipped, or nearly shipped, without anyone seeing them:

  - A tag written two ways ("Van Life" and "van-life") slugs to one term, and
    Hugo races to decide its title — the chip rendered "Van-Life" on about half
    of all builds.
  - shuffle() in a template makes every build rewrite the same pages, which
    hides real diffs in the noise.
  - Photos in the archive with no alt: the homepage showed no caption and a
    generic "A photo from Michigan" roughly half the time.
  - Two names for one image file, so a place gallery shows the same photo twice.
  - A hardcoded "/essays/" in a template: fine on the custom domain, 404 on the
    old project-pages subpath, and invisible until the base URL moves.
  - [params.ads] preview left on, which ships placeholder ad boxes to readers.
  - A class a template emits that no CSS defines: .article-hero-wrap left 19
    live pages with an unframed hero flush against the left edge, and every
    other gate passed while it did.

Usage: python3 scripts/check_invariants.py [public_dir] [base_url]
Only stdlib. Exits non-zero with a report, so CI fails instead of deploying.
"""
import hashlib
import os
import re
import sys
from collections import Counter, defaultdict
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
failures = []
notes = []


def fail(check, detail):
    failures.append((check, detail))


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8", errors="replace") as fh:
        return fh.read()


def walk(rel, exts):
    base = os.path.join(ROOT, rel)
    for dirpath, _, names in os.walk(base):
        for n in names:
            if n.endswith(exts):
                yield os.path.join(dirpath, n)


# --- 1. Tag spellings that collide on one slug -----------------------------
def check_tag_slugs():
    seen = defaultdict(set)
    for path in walk("content", (".md",)):
        text = open(path, encoding="utf-8", errors="replace").read()
        fm = re.match(r"^---\n(.*?)\n---", text, re.S)
        if not fm:
            continue
        m = re.search(r"^tags:\s*(\[.*?\]|\n(?:\s*-\s*.*\n?)+)", fm.group(1), re.M)
        if not m:
            continue
        for a, b, c in re.findall(r'"([^"]+)"|\'([^\']+)\'|-\s*([^\n\[\],]+)', m.group(1)):
            v = (a or b or c).strip().strip('",')
            if v:
                seen[v.lower().replace(" ", "-")].add(v)
    for slug, spellings in sorted(seen.items()):
        if len(spellings) > 1:
            fail("tag-slug-collision",
                 f"/tags/{slug}/ is written {len(spellings)} ways {sorted(spellings)} — "
                 "Hugo picks the term title nondeterministically. Use one spelling.")


# --- 2. Nondeterministic template helpers ----------------------------------
def check_determinism():
    for path in walk("themes", (".html",)):
        body = open(path, encoding="utf-8", errors="replace").read()
        # `| shuffle` or `(shuffle $x)` — but not the word inside a comment.
        stripped = re.sub(r"\{\{/\*.*?\*/\}\}", "", body, flags=re.S)
        if re.search(r"\bshuffle\b", stripped):
            fail("nondeterministic-build",
                 f"{os.path.relpath(path, ROOT)} calls shuffle. On a static site it "
                 "re-rolls per BUILD, not per visitor, so it never varies what a reader "
                 "sees and rewrites the page every deploy. Rotate by index instead.")


# --- 3. The dated photo archive --------------------------------------------
def check_photo_archive():
    rel = "data/photo_dates.yaml"
    if not os.path.exists(os.path.join(ROOT, rel)):
        return
    blocks = re.split(r"\n  - ", read(rel))[1:]
    hashes, srcs = defaultdict(list), []
    for b in blocks:
        m = re.search(r'src:\s*"([^"]+)"', b)
        if not m:
            continue
        src = m.group(1)
        srcs.append(src)
        disk = os.path.join(ROOT, "static", src)
        if not os.path.exists(disk):
            fail("photo-archive", f"{src} is listed but not on disk")
            continue
        if "alt:" not in b:
            fail("photo-archive",
                 f"{src} has no alt — the homepage 'On This Day' block renders it "
                 "with no caption and a generic alt")
        if "date:" not in b:
            fail("photo-archive", f"{src} has no date, so it can never be picked")
        with open(disk, "rb") as fh:
            hashes[hashlib.md5(fh.read()).hexdigest()].append(src)

    for dup, names in ((s, c) for s, c in Counter(srcs).items() if c > 1):
        fail("photo-archive", f"{dup} is listed {names} times")
    for _, names in hashes.items():
        if len(names) > 1:
            fail("photo-archive",
                 f"same image under {len(names)} names {names} — a place gallery will "
                 "show it twice. Keep one entry; the files can stay.")


# --- 4. Paths that only work on one base URL -------------------------------
def check_template_paths():
    for path in walk("themes", (".html",)):
        rel = os.path.relpath(path, ROOT)
        for i, line in enumerate(open(path, encoding="utf-8", errors="replace"), 1):
            if re.search(r'(?:href|src|action)="/(?!/)', line):
                fail("subpath-unsafe",
                     f"{rel}:{i} hardcodes a root-relative path. Use "
                     "{{ .Site.Home.RelPermalink }} + no leading slash (CLAUDE.md).")
            if "absURL" in line and not re.search(r"og:|twitter:|schema|canonical|\$shareImg", line):
                notes.append(f"{rel}:{i} uses absURL — correct only for absolute "
                             "share/canonical URLs.")


# --- 5. Ad slots must ship dormant -----------------------------------------
def check_ads():
    if not os.path.exists(os.path.join(ROOT, "hugo.toml")):
        return
    block = re.search(r"\[params\.ads\](.*?)(?=\n\[|\Z)", read("hugo.toml"), re.S)
    if not block:
        return
    for key in ("preview", "enabled"):
        m = re.search(rf"^\s*{key}\s*=\s*(\w+)", block.group(1), re.M)
        if m and m.group(1) == "true" and key == "preview":
            fail("ads", "[params.ads] preview = true would ship placeholder ad boxes "
                        "to readers. It is a local-only switch.")


# --- 6. Built output --------------------------------------------------------
class ImgAlt(HTMLParser):
    def __init__(self):
        super().__init__()
        self.missing = 0

    def handle_starttag(self, tag, attrs):
        if tag == "img" and not any(k == "alt" for k, _ in attrs):
            self.missing += 1


def site_hosts():
    """Every host this site is known by: the custom domain and the Pages one."""
    hosts = set()
    cname = os.path.join(ROOT, "static", "CNAME")
    if os.path.exists(cname):
        v = open(cname, encoding="utf-8").read().strip()
        if v:
            hosts.add(v)
    m = re.search(r'baseURL\s*=\s*"https?://([^/"]+)', read("hugo.toml")) \
        if os.path.exists(os.path.join(ROOT, "hugo.toml")) else None
    if m:
        hosts.add(m.group(1))
    return hosts


def affiliates_live():
    """True once any partner ID under [params.affiliates] is non-empty.

    The disclosure partial suppresses itself while every ID is blank, because
    the links are then plain public URLs that earn nothing. So the built-output
    check below only means something once money is actually switched on — and
    it must start meaning something on that exact day, without anyone
    remembering to enable it."""
    block = re.search(r"\[params\.affiliates\](.*?)(?:\n\[|\Z)",
                      read("hugo.toml"), re.S)
    if not block:
        return False
    return any(v.strip() for v in re.findall(r'^\s*\w+\s*=\s*"([^"]*)"',
                                             block.group(1), re.M))


def check_built(public, base_url):
    """base_url is the host this build was made for. Anything absolute pointing
    at one of the site's OTHER hosts is stale — which is the failure mode of the
    domain move, in either direction. Without a base URL we cannot tell which
    host is correct, so the check is skipped rather than guessed."""
    if not public or not os.path.isdir(public):
        return
    base_host = ""
    if base_url:
        m = re.match(r"https?://([^/]+)", base_url)
        base_host = m.group(1) if m else ""

    others = {h for h in site_hosts() | {"gwinn092.github.io"} if h and h != base_host}
    # Match a host only where it actually IS the host of a URL: right after the
    # "//" of a scheme, and ending at a real delimiter. A plain substring test
    # reports every "www.example.com" as a stale "example.com", because one
    # contains the other — that false positive failed 83 pages of a real deploy.
    host_res = {h: re.compile(r"(?<=//)" + re.escape(h) + r"(?=[/\"'\s:<>?#\\]|$)")
                for h in others}
    stale = defaultdict(list)
    missing_alt = 0
    # Hugo's contextual autoescaping percent-encodes the separators of a query
    # string built with querify inside an href, turning ?a=1&b=2 into
    # ?a%3d1%26b%3d2 — one garbled parameter name with no value. It broke every
    # share button on the site silently, because nobody clicks their own share
    # links. safeURL on the whole URL is the fix; this is the tripwire.
    mangled_qs = re.compile(r'href="[^"]*\?[^"]*%3[dD][^"]*"')
    mangled = []
    # The same failure from the other direction. A partial that RENDERS a URL
    # has its output escaped once inside the partial and again when the caller
    # drops it into an href, so "&cid=" ships as "&amp;amp;cid=" — which a
    # browser parses as a parameter called "amp;cid". The affiliate ID is
    # silently dropped and every commission is lost. Only visible once a partner
    # ID is set, which is exactly when it costs money. `return` in the partial
    # is the fix; this is the tripwire. Tolerates --minify stripping quotes.
    double_amp = re.compile(r'href="?[^"\s>]*&amp;amp;')
    doubled = []
    # FTC: a page that earns a commission must say so. Only meaningful once a
    # partner ID exists — see affiliates_live().
    money_on = affiliates_live()
    undisclosed = []
    for dirpath, _, names in os.walk(public):
        for n in names:
            if not n.endswith(".html"):
                continue
            p = os.path.join(dirpath, n)
            text = open(p, encoding="utf-8", errors="replace").read()
            if base_host:
                for h, rx in host_res.items():
                    if rx.search(text):
                        stale[h].append(os.path.relpath(p, public))
            if mangled_qs.search(text):
                mangled.append(os.path.relpath(p, public))
            if double_amp.search(text):
                doubled.append(os.path.relpath(p, public))
            # Both patterns must tolerate --minify, which strips attribute
            # quotes: class="affiliate-note" ships as class=affiliate-note.
            if money_on and re.search(r'rel="?sponsored', text) \
                    and not re.search(r'class="?affiliate-note', text):
                undisclosed.append(os.path.relpath(p, public))
            parser = ImgAlt()
            parser.feed(text)
            missing_alt += parser.missing

    if not base_host:
        notes.append("no base URL given, so the stale-host check was skipped")
    for h, pages in stale.items():
        fail("stale-host",
             f"{len(pages)} page(s) point at {h} but this build is for "
             f"{base_host}, e.g. {pages[:3]}")
    if undisclosed:
        fail("affiliate-disclosure",
             f"{len(undisclosed)} page(s) carry an affiliate link with no "
             f"disclosure rendered on them, e.g. {undisclosed[:3]} — FTC "
             f"requirement; add {{{{< affiliate-note >}}}} or set "
             f"affiliate: true in front matter")
    elif not money_on:
        notes.append("no affiliate partner IDs are set, so the disclosure "
                     "check on built pages is dormant")
    if mangled:
        fail("escaped-query",
             f"{len(mangled)} page(s) have an href whose query string is "
             f"percent-encoded (%3d for =), which makes the link inert — pipe "
             f"the whole URL through safeURL, e.g. {mangled[:3]}")
    if doubled:
        fail("double-escaped-query",
             f"{len(doubled)} page(s) have an href containing &amp;amp; — the "
             f"URL was escaped twice, so the parameter after it is read as "
             f"\"amp;<name>\" and its value is discarded. On an affiliate link "
             f"that silently loses the commission. Have the partial `return` "
             f"the URL instead of rendering it, e.g. {doubled[:3]}")
    if missing_alt:
        fail("a11y", f"{missing_alt} <img> tag(s) have no alt attribute at all "
                     "(alt=\"\" is fine for decorative images; a missing attribute is not)")


# --- Editorial notes that leak into public HTML ----------------------------
def check_editorial_comments():
    """An HTML comment in a markdown file is published to readers.

    Markdown passes `<!-- ... -->` straight through to the output, so a note
    written to Jesse or Karlee inside content/ ends up in the page source of a
    live page. This has now shipped three times: the "REVIEW NUMBERS BEFORE
    PUBLISHING" markers on two guides (Aug 20 2026), and then a note to Karlee
    on the gear page plus a GA4 TODO on Work With Us.

    The fix each time is the same — move the note into front matter, which is
    never rendered. This gate exists so there is not a fourth time.

    Hugo's own `{{/* ... */}}` comments are fine and are not matched here;
    they are stripped at build time. Only raw HTML comments in content are.
    """
    for path in walk("content", (".md",)):
        body = read(path)
        # front matter is not rendered, so only look after it
        if body.startswith("---"):
            end = body.find("\n---", 3)
            body = body[end + 4:] if end != -1 else body
        if "<!--" in body:
            rel = os.path.relpath(path, ROOT)
            snippet = body[body.index("<!--"):][:70].replace("\n", " ")
            fail(
                "editorial comment in content",
                f"{rel} contains an HTML comment, which markdown publishes to "
                f"readers: {snippet}... Move it into front matter instead.",
            )


# --- 7. Classes a template emits that no CSS defines ------------------------
# The bug this exists for: itinerary.html and place.html spent the whole
# print-frame rebuild emitting .article-hero-wrap / .article-hero-img, two
# names that appear nowhere in main.css. With no rule sizing the image the
# <img> fell back to the width="1400" attribute respimg.html writes, so 19
# live pages showed an unframed hero flush against the left edge with white
# space beside it. Nothing failed: not the link check, not the build, not the
# reproducibility diff. Only looking at the page found it.
#
# Plenty of classes are unstyled on purpose — JS hooks, bare semantic
# wrappers, BEM modifiers that were never given a rule. Those are listed
# below WITH a reason. The point of the allowlist is that adding to it is a
# deliberate act; a class that turns up unlisted and unstyled fails the build.
INTENTIONALLY_UNSTYLED = {
    # JS behaviour hooks — selected by script, never painted.
    "article": "scroll/share JS selector in single.html",
    "map-progress__play-label": "label swapped by the map tour JS",
    "map-svg--us": "JS selector for the US map instance",
    # Bare wrappers: the parent grid/flex or the children carry every rule.
    # Each was measured in the browser before being listed here.
    "itin": "bare <article>; .content-container children do the layout",
    "place": "bare <article>; .content-container children do the layout",
    "itin__head": "element also carries .content-container, which is styled",
    "quiz": "bare wrapper; .quiz__start / __card / __result carry the rules",
    "quiz__result": "bare wrapper; verified it lays out at 666x534 when shown",
    "roadtrip": "bare <article>, template not live yet",
    "article-main": "sized by the .article-layout grid above it",
    "aside-newsletter": "sized by its styled parent",
    "otd__body": "sized by the homepage grid",
    "kit-who__col": "sized by the .kit-who grid",
    "first-reads__item": "<li> sized by the .first-reads grid",
    "tour-dot__num": "<span> sized by the flex dot around it",
    "map-progress__of": "inline <span>, inherits from .map-progress__readout",
    # BEM modifiers that were never given a rule. The base class IS styled, so
    # the element renders correctly; the modifier is dead but harmless.
    "map-scrolly__cue--loop": "modifier on a styled .map-scrolly__cue",
    "map-step--outro": "modifier on a styled .map-step",
    "map-step--today": "modifier on a styled .map-step",
    "map-step__note--years": "modifier on a styled .map-step__note",
    "map-marker--together": "modifier on a styled .map-marker",
    "roadtrip__badge--list": "modifier on a styled badge, not live yet",
    "roadtrip__empty": "empty state, template not live yet",
    "roadtrip__stops": "sized by its children, template not live yet",
    # Third-party.
    "formkit-alert": "ConvertKit ships its own CSS for this",
    "formkit-alert-error": "ConvertKit ships its own CSS for this",
    # Body state hook.
    "is-home": "body flag, available to CSS/JS; nothing paints it today",
}

CSS_FILE = "themes/moments/assets/css/main.css"


def check_orphan_classes():
    css_path = os.path.join(ROOT, CSS_FILE)
    if not os.path.exists(css_path):
        fail("orphan-class", f"{CSS_FILE} is missing — cannot check classes.")
        return
    css = read(CSS_FILE)
    # Inline <style> blocks count as definitions too, so a template that styles
    # itself is not reported. There are none today; this keeps it true if that
    # changes.
    for path in walk("themes", (".html",)):
        for m in re.finditer(r"<style[^>]*>(.*?)</style>", read(os.path.relpath(path, ROOT)), re.S | re.I):
            css += "\n" + m.group(1)
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    defined = set(re.findall(r"\.(-?[A-Za-z_][\w-]*)", css))
    if len(defined) < 100:
        fail("orphan-class",
             f"only {len(defined)} classes parsed out of {CSS_FILE} — the "
             "parser broke; refusing to report every class as orphaned.")
        return

    seen = 0
    reported = set()
    for path in walk("themes", (".html",)):
        rel = os.path.relpath(path, ROOT)
        src = read(rel)
        # HTML comments hold markup that is deliberately not live (the About
        # page parks a socials block there until the handles exist). Skipping
        # them is what stops the check reporting code nobody has shipped.
        src = re.sub(r"<!--.*?-->", "", src, flags=re.S)
        # Grab the partial-argument form FIRST. "class" "foo" lives inside the
        # {{ partial ... }} call, so stripping template expressions below would
        # erase it — which is exactly how .article-hero-img went unnoticed on
        # the first pass at this check.
        partial_args = [(src[:m.start()].count("\n") + 1, m.group(1)) for m in
                        re.finditer(r'"class"\s+"([^"]*)"', src)]
        # Go template expressions must go BEFORE the class attribute is matched,
        # not after: class="x{{ if eq $s.status "list" }} y{{ end }}" contains
        # quotes, so an attribute regex run first stops dead in the middle of
        # the expression and reports garbage tokens like .if and .$stop.status.
        # NUL cannot appear in a class name, so it marks where a value was
        # computed — any token touching one is dynamic and cannot be checked.
        src = re.sub(r"\{\{.*?\}\}", "\x00", src, flags=re.S)
        # Two ways a class reaches the page: written as an attribute here, or
        # handed to a partial as "class" "foo" (respimg.html, ad-slot.html) and
        # written out there as class="{{ .class }}". The second form is dynamic
        # at the point it becomes an attribute, so the call site collected above
        # is the only place its real name is readable.
        spots = [(src[:m.start()].count("\n") + 1, m.group(1)) for m in
                 re.finditer(r"""class\s*=\s*["']([^"']*)["']""", src)]
        spots += partial_args
        for line, value in spots:
            for tok in value.split():
                if "\x00" in tok:
                    continue
                seen += 1
                if tok in defined or tok in INTENTIONALLY_UNSTYLED:
                    continue
                key = (rel, tok)
                if key in reported:
                    continue
                reported.add(key)
                fail("orphan-class",
                     f"{rel}:{line} emits .{tok}, which no CSS rule defines. "
                     "Either style it, or add it to INTENTIONALLY_UNSTYLED in "
                     "this script with the reason it needs no rule.")
    # A scan that silently matched nothing would pass and mean nothing.
    if seen < 200:
        fail("orphan-class",
             f"only {seen} static class tokens found across templates — the "
             "scan broke, so a pass here would be meaningless.")


def main():
    public = sys.argv[1] if len(sys.argv) > 1 else "public"
    public = public if os.path.isabs(public) else os.path.join(ROOT, public)
    base_url = sys.argv[2] if len(sys.argv) > 2 else ""

    check_tag_slugs()
    check_determinism()
    check_photo_archive()
    check_template_paths()
    check_editorial_comments()
    check_ads()
    check_orphan_classes()
    check_built(public, base_url)

    for n in notes:
        print(f"note: {n}")
    if failures:
        print(f"\nINVARIANT CHECK FAILED ({len(failures)}):")
        for check, detail in failures:
            print(f"  [{check}] {detail}")
        sys.exit(1)
    print("Invariant check passed.")


if __name__ == "__main__":
    main()
