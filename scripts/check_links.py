#!/usr/bin/env python3
"""Check that every internal link and asset reference in the built site
resolves to a real file, so link rot fails the build instead of shipping.

Usage: python3 scripts/check_links.py <public_dir> <base_url>
Only stdlib; external URLs (other hosts, mailto:, etc.) are not checked.
"""
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, unquote


class RefCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if value is None:
                continue
            if name in ("href", "src", "poster", "data-src"):
                self.refs.append(value)
            elif name in ("srcset", "data-srcset"):
                for part in value.split(","):
                    url = part.strip().split()[0] if part.strip() else ""
                    if url:
                        self.refs.append(url)


def main():
    public = Path(sys.argv[1])
    base = sys.argv[2] if len(sys.argv) > 2 else "/"
    base_path = urlparse(base).path or "/"
    if not base_path.endswith("/"):
        base_path += "/"
    base_host = urlparse(base).netloc

    missing = []
    checked = 0
    for page in public.rglob("*.html"):
        parser = RefCollector()
        parser.feed(page.read_text(encoding="utf-8", errors="replace"))
        for ref in parser.refs:
            parsed = urlparse(ref)
            if parsed.scheme in ("mailto", "tel", "data", "javascript"):
                continue
            if parsed.scheme in ("http", "https") and parsed.netloc != base_host:
                continue  # external
            path = unquote(parsed.path)
            if not path:
                continue  # pure fragment
            if path.startswith("/"):
                if not path.startswith(base_path) and base_path != "/":
                    missing.append((page.relative_to(public), ref, "outside base path"))
                    continue
                rel = path[len(base_path):] if base_path != "/" else path.lstrip("/")
                target = public / rel
            else:
                target = page.parent / path
            checked += 1
            if target.is_dir():
                target = target / "index.html"
            if not (target.exists() or Path(str(target) + "/index.html").exists()):
                missing.append((page.relative_to(public), ref, "missing file"))

    if missing:
        unique = sorted(set(missing))
        print(f"BROKEN INTERNAL LINKS ({len(unique)}):")
        for page, ref, why in unique:
            print(f"  {page}: {ref}  [{why}]")
        sys.exit(1)
    print(f"Link check passed: {checked} internal references resolved.")


if __name__ == "__main__":
    main()
