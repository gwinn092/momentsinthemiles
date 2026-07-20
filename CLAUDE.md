# Moments in the Miles — Project Rules

These layer on top of the global rules in `~/.claude/CLAUDE.md`.

## Hard line: no monetization in the story
- **Never add gear recommendations, affiliate links, product roundups, or
  comparison tables to this site.** MitM is story and philosophy. The technical
  and affiliate content lives in the separate CAVL site
  (`../affiliation.vansite`) and never crosses over.
- The only commercial path here is Reduce Friction → the $27 Leave Anyway Kit.
  Keep Reduce Friction in the nav; it is the only route to the Kit.

## Internal links and image paths
- Every internal link and image `src` in a template must use the
  `{{ .Site.Home.RelPermalink }}` prefix followed by a path with **no leading
  slash**. Menu `.URL` entries are exempt.
- Never use `absURL` or a hardcoded root-relative path like `/essays/` — the site
  is served from a GitHub Pages subpath and those 404 in production.

## Photos
- Strip metadata from every photo before it enters the repo:
  `magick "$SRC" -resize 1400x1400\> -quality 82 -strip "$DST"`
- Blur or patch anything identifying that ends up in frame — license plates,
  street addresses, mail. Check before committing, not after.

## Voice
- "We" for shared content; "I" only in Karlee's individual essays.
- **Never invent a fact about Jesse, Karlee, the van, the mileage, the years, or
  where they have been.** Site canon is deliberate and Jesse's call. If a number
  or a place is not already in the content or in project memory, ask — do not
  fill the gap with something plausible.

## Local dev
- `hugo server`, no flags.
