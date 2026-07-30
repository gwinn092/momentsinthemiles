# Moments in the Miles — Project Rules

These layer on top of the global rules in `~/.claude/CLAUDE.md`.

## Monetization (policy changed July 30 2026 — Jesse's call)
MitM now carries affiliate links and sponsorship. The old "no monetization in the
story" hard line is retired. The model is Salt in Our Hair: soft, contextual,
useful. Not pushy is the whole point, so the boundaries below are firm.

**Where money is allowed**
- Guides (`/guides/`) and itineraries (`/itineraries/`). These are the pages
  people read with a trip to plan, so a booking link is a service, not an ad.
- The Leave Anyway Kit and Reduce Friction, as before. Keep Reduce Friction in
  the nav; it is the only route to the Kit.
- Sponsorship, via `/work-with-us/`.

**Where money is NOT allowed — this part is still a hard line**
- Essays, Van Life, About, Start Here, The Map, Places, Gallery, The Years.
  Those pages are the trust engine, and the trust is what makes a guide convert
  at all. No booking links, no sponsored blocks, no product placement there.
- No product roundups, comparison tables, or "best X of 2026" pages anywhere on
  MitM. That format lives on CAVL (`../affiliation.vansite`) and stays there.
- Never more than one booking block per section of a guide, and never above the
  first real paragraph of the page.

**Rules for every affiliate link**
- Use the `{{< book >}}` shortcode or `partials/booking-link.html`. Never write a
  raw affiliate URL into content — partner IDs live in `hugo.toml` so they can be
  changed in one place, and the markup carries `rel="sponsored nofollow noopener"`.
- Every page with an affiliate link on it must show `{{< affiliate-note >}}`.
  This is an FTC requirement, not a preference.
- **Never invent a hotel, restaurant, or business they stayed at or used.** If a
  specific place is not already named in the content or in project memory, link
  the city search instead — an honest "find a place in Hanoi" beats a fabricated
  recommendation. Ask Jesse for real names; do not fill the gap.

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
