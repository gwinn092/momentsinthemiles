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

## Display advertising (policy set Aug 12 2026 — Jesse's call)
Display ads are a **separate policy from affiliate/sponsorship above**, and the
scopes are deliberately different. Do not merge the two rules.

- **Affiliate + sponsorship**: `/guides/` and `/itineraries/` only. Unchanged.
- **Display ads**: allowed **sitewide**, essays included. The reasoning is that
  story content converts affiliate clicks badly but accumulates the pageviews an
  ad network actually pays for, so confining ads to the guides would monetize
  only the pages that already earn and leave the traffic earning nothing.

**Never carry ads**, whatever the config says:
- `/reduce-friction/` — the quiz and the $27 Kit sales page. An ad there competes
  with the product. Enforced by `excludeSections` in `hugo.toml`.
- `/privacy/`, `/terms/` — legal pages. Enforced by `ads: false` front matter.
- `/work-with-us/` — an ad on the sponsorship pitch page undercuts the pitch.
  Enforced by `ads: false` front matter.

**How it works.** Nothing renders until `enabled = true` under `[params.ads]`.
The slots exist now because reserving the space is what is expensive to retrofit,
not the ad tag.
- `partials/ads-allowed.html` — the single source of truth for "may this page
  carry an ad". Both other partials ask it. Do not re-implement the check.
- `partials/ad-slot.html` — one reserved slot. Keep the `min-height`; an ad
  loading into an unreserved box shifts the text under it, which is a CLS
  penalty and the thing that makes a site feel cheap.
- `partials/article-body.html` — weaves in-content slots into `.Content` at
  top-level paragraph boundaries, scaled to article length. Tuning lives in
  `[params.ads]`, not in the template.
- `preview = true` (or `HUGO_PARAMS_ADS_PREVIEW=true`) draws the reserved space
  locally. **Never ship it true.**

⚠️ **Ads off must stay byte-identical to no-ads output.** That was verified when
this shipped; if a change to these partials starts emitting stray whitespace into
every article, that is a regression, not cosmetic.

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

## Hosting
The site is built and deployed by **Netlify** (`netlify.toml`), not GitHub Pages.
CAVL is on Netlify too, so both sites live in one dashboard — but their DNS
values are completely different and must never be copied across.

`.github/workflows/hugo.yml` no longer deploys anything. It is a pure CI check:
publishing from there as well would put a second copy of the site on
`gwinn092.github.io` with its own canonical URLs, which is duplicate content
rather than a backup.

`baseURL` is passed as `-b $URL` at build time rather than trusted from
`hugo.toml`, so a build is correct wherever it is served — production domain,
`*.netlify.app`, or a deploy preview. `static/CNAME` is now inert; it is left in
place only because it costs nothing.

## What CI will reject
Four gates. The first three also run inside the Netlify build command, so a
failing check fails the deploy and the previous version stays up; the fourth
runs only in GitHub Actions. Run them before pushing rather than finding out
from a red deploy:
- `python3 scripts/check_links.py public <base_url>` — dead internal links.
- `python3 scripts/check_invariants.py public` — one tag spelled two ways,
  `shuffle` in a template, photos in `data/photo_dates.yaml` with no `alt` or
  listed twice under different names, root-relative paths in templates,
  `[params.ads] preview = true`, and leftover `gwinn092.github.io` references.
- `python3 scripts/check_content.py` — prose that no longer matches the data
  under it: a stated count in an itinerary summary that disagrees with the stop
  list, a country inked on the world map with neither a story in
  `map_stories.yaml` nor a `data-note`, one hero `image:` on two published
  pages, and a section `_index.md` using a photo that is also one of its own
  post cards. Takes no arguments — it reads source, not `public/`.
  Canada and Mexico are inked with no story yet and sit in that script's
  `KNOWN_SILENT` set, which keeps the gate green while printing the debt on
  every run. **Delete a name from that set the moment its story lands** — the
  gate fails on a stale entry as well as on a new silent country.
- **The build must be reproducible.** Two builds of one commit are diffed and
  must be byte-identical. Nothing in a template may roll dice at build time —
  on a static site that never varies what a reader sees, it just rewrites pages
  every deploy and hides real diffs.
