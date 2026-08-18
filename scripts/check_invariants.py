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
            parser = ImgAlt()
            parser.feed(text)
            missing_alt += parser.missing

    if not base_host:
        notes.append("no base URL given, so the stale-host check was skipped")
    for h, pages in stale.items():
        fail("stale-host",
             f"{len(pages)} page(s) point at {h} but this build is for "
             f"{base_host}, e.g. {pages[:3]}")
    if missing_alt:
        fail("a11y", f"{missing_alt} <img> tag(s) have no alt attribute at all "
                     "(alt=\"\" is fine for decorative images; a missing attribute is not)")


def main():
    public = sys.argv[1] if len(sys.argv) > 1 else "public"
    public = public if os.path.isabs(public) else os.path.join(ROOT, public)
    base_url = sys.argv[2] if len(sys.argv) > 2 else ""

    check_tag_slugs()
    check_determinism()
    check_photo_archive()
    check_template_paths()
    check_ads()
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
