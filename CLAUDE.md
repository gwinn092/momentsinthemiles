# Moments in the Miles — Project Rules

These layer on top of the global rules in `~/.claude/CLAUDE.md`.

## Monetization (loosened Aug 19 2026 — Jesse's call; supersedes July 30 2026)
MitM carries affiliate links and sponsorship. The model is still Salt in Our
Hair: soft, contextual, useful. What changed on Aug 19 is the **scope**: the old
section whitelist (`/guides/` and `/itineraries/` only) is retired. Jesse's
instruction was to loosen it and use judgement.

**The judgement rule, which replaces the whitelist**
A booking or affiliate link belongs wherever a reader could plausibly act on it
*right there* — the page names a real place, and someone reading it might want to
go. That now includes Van Life posts, essays, `/places/` and Start Here, which
were previously off limits. Ask "would a reader be glad this link was here, or
would they notice they were being sold to?" If it is the second, leave it out.
When it is genuinely a close call, leave it out — the trust is what makes any of
this convert, and one restrained page costs far less than one page that reads as
an ad.

**What is still firm — do not treat these as loosened**
- **Legal and honesty lines are absolute** and are covered below: FTC disclosure
  on every page carrying a link, and never inventing a business they used.
- **No product roundups, comparison tables, or "best X of 2026" pages anywhere on
  MitM.** That format lives on CAVL (`../affiliation.vansite`) and stays there.
  This is a cross-site boundary, not a tone preference.
- **Nothing above the first real paragraph of a page.** A reader gets the writing
  before they get an offer, always.
- **No monetization at all** on `/about/`, `/work-with-us/`, `/privacy/`,
  `/terms/`, or the Reduce Friction quiz and Kit pages. The first two are
  credentials, the next two are legal, and the last two are already selling the
  $27 Kit — a booking link there competes with the product.
- **Restraint over density.** One booking block per section of a page remains the
  ceiling, and most sections should have none.
- **The closing `{{< planning >}}` block is for LONG pillar guides and
  itineraries only** (Jesse, Aug 20 2026). Never the short guides: on a
  ~1,500-word guide that already has a `{{< stay >}}` block, a closing block is
  the second ask in a short space and reads as a pitch. It is live on the SE
  Asia guide, which carries it only because the page is enormous and each inline
  block sits in its own country section.
  Pass `disclosure="false"` when the page already shows `{{< affiliate-note >}}`
  near the top — but never on a page with no disclosure anywhere else.
- Keep Reduce Friction in the nav; it is the only route to the Kit.
- Sponsorship still routes through `/work-with-us/`.

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

- **Affiliate + sponsorship**: judgement-based sitewide as of Aug 19 2026, with
  the firm exclusions listed above. No longer a section whitelist.
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

## Cross-site linking to CAVL (approved Aug 20 2026 — Jesse's call)
MitM is story/philosophy; CAVL (`../affiliation.vansite`,
https://www.createavanlife.com) is technical/affiliate. **Content still never
merges** — but cross-*linking* is approved and deliberate, because it sends each
site's traffic to the one that can act on that intent.

- **Contextual only.** The link earns its place when the MitM page has already
  raised the thing the CAVL page answers — the solar paragraph, the Yeti-to-
  Bluetti switch, the ninety-degrees-at-midnight question. A bare "visit our
  other site" is not a cross-link.
- **Keep it few.** Reciprocal linking at volume between two sites one person
  owns reads as a link scheme. Three or four contextual links per side is the
  working ceiling; today MitM has three plus two standing handoff links
  (`guides/gear-we-love.md`, `van-life/_index.md`).
- Plain markdown links, no `nofollow` — these are editorial links to a site
  Jesse owns, not sponsored ones.
- ⛔ **CAVL-side edits belong in the CAVL repo and its own Claude thread.**
- The roundup/comparison-table ban above is a separate rule and is unaffected.

## Internal links and image paths
- Every internal link and image `src` in a template must use the
  `{{ .Site.Home.RelPermalink }}` prefix followed by a path with **no leading
  slash**. Menu `.URL` entries are exempt.
- Never use `absURL` or a hardcoded root-relative path like `/essays/` — the site
  is served from a GitHub Pages subpath and those 404 in production.

## Photos
- ⛔ **Do NOT crop source photos to landscape** (Jesse, Aug 20 2026 — he has told
  Karlee to stop). The frame adapts to the photograph instead:
  `partials/frame-shape.html` reads each source's aspect ratio at build time and
  picks 2:1, 3:2 or a narrow 4:5 portrait. Most of their photos are 4:3 phone
  shots and eleven heroes are portrait — that is a feature, because phone-shaped
  photos read as someone actually being there. Never "fix" a portrait hero by
  re-cropping it, and never ask for landscape reshoots.
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

**The live site is `https://www.momentsinthemiles.com`.** The bare apex
`momentsinthemiles.com` 301-redirects to it. This matches CAVL and is Netlify's
own recommendation: `www` is a CNAME to the netlify.app host, so it follows
Netlify automatically, whereas an apex can only use a hardcoded A record
(`75.2.60.5`) that would need a manual edit if Netlify ever moved it.

Decided on launch day, Aug 18 2026, deliberately before announcing the URL —
switching primary domains is close to free while nothing has been indexed and
gets progressively more expensive afterwards.

`baseURL` is passed as `-b $URL` at build time rather than trusted from
`hugo.toml`, so a build is correct wherever it is served — production domain,
`*.netlify.app`, or a deploy preview. `hugo.toml` and the CI `BASE_URL` are
still kept in sync with the real primary domain so nothing in the repo
disagrees with what is actually served. `static/CNAME` is now inert (it names
`www` and GitHub Pages is disabled); it is left in place only because it costs
nothing.

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
