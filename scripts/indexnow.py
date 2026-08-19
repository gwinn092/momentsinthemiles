#!/usr/bin/env python3
"""Tell IndexNow (Bing, Yandex) about new or changed pages right away, instead
of waiting for a crawler to notice.

    python3 scripts/indexnow.py https://HOST/essays/a-new-post/ [more URLs...]
    python3 scripts/indexnow.py --all      # every URL in the live sitemap
    python3 scripts/indexnow.py --dry-run --all

Why this is a script you run and not a build step: IndexNow is for URLs that are
NEW or CHANGED. Firing all of them on every deploy is exactly the pattern that
gets a host ignored or throttled, and a static site rebuilds every page whether
or not its content moved. So this runs when you publish something, by hand.

--all is for the first submission on a site the engines have not seen. Do not
make a habit of it.

The key is discovered from static/<key>.txt rather than written here twice, so
the key we send and the file that proves we own the host cannot drift apart.
"""

import glob
import json
import os
import re
import sys
import urllib.request
import urllib.error

HOST = "www.momentsinthemiles.com"
ENDPOINT = "https://api.indexnow.org/indexnow"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def find_key():
    """The key file is named <key>.txt and contains exactly <key>."""
    for path in glob.glob(os.path.join(ROOT, "static", "*.txt")):
        stem = os.path.splitext(os.path.basename(path))[0]
        if not re.fullmatch(r"[A-Za-z0-9-]{8,128}", stem):
            continue
        with open(path) as f:
            if f.read().strip() == stem:
                return stem
    sys.exit("No IndexNow key file found in static/ (expected <key>.txt "
             "containing exactly <key>).")


def sitemap_urls():
    with urllib.request.urlopen(f"https://{HOST}/sitemap.xml", timeout=30) as r:
        return re.findall(r"<loc>([^<]+)</loc>", r.read().decode("utf-8"))


def main():
    args = [a for a in sys.argv[1:]]
    dry = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]

    if not args:
        sys.exit(__doc__)
    urls = sitemap_urls() if args == ["--all"] else args

    bad = [u for u in urls if not u.startswith(f"https://{HOST}/")]
    if bad:
        sys.exit(f"Refusing to submit URLs that are not on {HOST}: {bad[:3]}")

    key = find_key()
    payload = {
        "host": HOST,
        "key": key,
        "keyLocation": f"https://{HOST}/{key}.txt",
        "urlList": urls,
    }

    print(f"{len(urls)} URL(s) -> {ENDPOINT} as {HOST}")
    for u in urls[:5]:
        print(f"  {u}")
    if len(urls) > 5:
        print(f"  ... and {len(urls) - 5} more")
    if dry:
        print("\n--dry-run: nothing sent.")
        return

    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            # 200 accepted, 202 accepted but key still being validated.
            print(f"\nHTTP {r.status} — {'accepted' if r.status in (200, 202) else r.reason}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:400]
        sys.exit(f"\nHTTP {e.code} — {e.reason}\n{body}")


if __name__ == "__main__":
    main()
