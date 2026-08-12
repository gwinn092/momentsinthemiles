# MitM launch handoff — written 2026-08-12

Paste the block below into a new chat opened in `~/Desktop/projects/momentsinthemiles`.
Everything under it is the detail that block refers to.

---

## ► COPY-PASTE THIS INTO THE NEW CHAT

> Read `CLAUDE.md` and `notes/launch-handoff-2026-08-12.md` first.
>
> Context: Moments in the Miles goes live on **www.momentsinthemiles.com by
> Tuesday 2026-08-18**. It is currently previewing at
> `https://gwinn092.github.io/momentsinthemiles/`. The repo is clean and pushed.
>
> I want to work on the launch. In priority order:
>
> 1. **Verify link integrity for the domain flip.** `static/CNAME` already holds
>    `www.momentsinthemiles.com` and the workflow builds with GitHub Pages'
>    `base_url`, so the flip is mostly DNS/Pages settings rather than code. The
>    risk is that every internal link and image path is relative-by-convention
>    for the subpath, and the base changes underneath them. Build against the
>    final base URL and run `python3 scripts/check_links.py public <base_url>`
>    before and after.
> 2. **Decide the ad layout before launch, not after.** The plan is display ads
>    as MitM's main engine long-term (story content converts affiliate clicks
>    badly but accumulates pageviews). Ad networks care about slot placement,
>    article length and sidebar structure, and retrofitting that into a finished
>    theme is painful. Designing for it now is nearly free.
> 3. **Pinterest.** MitM is a much better Pinterest fit than CAVL's spec
>    content. Worth planning boards and the first pins around launch.
> 4. **The MitM → CAVL cross-link**, once, at launch.
>
> Do not touch CAVL. Ask me before publishing anything outward-facing.

---

## Why each of those, and what I already checked

### 1. The domain flip is a link-integrity event

This is the one that can actually break the site, and it is worth doing carefully
because CAVL learned it the hard way — a stray `--baseURL` there once baked a
localhost address into every asset URL.

What is **already correct** in this repo, verified 2026-08-12:

- `static/CNAME` contains `www.momentsinthemiles.com`.
- `hugo.toml` `baseURL` is `https://www.momentsinthemiles.com/`.
- `.github/workflows/hugo.yml` builds with
  `--baseURL "${{ steps.pages.outputs.base_url }}/"`, so the deployed base comes
  from GitHub Pages at build time rather than from a hardcoded value. With a
  CNAME present, Pages reports the custom domain.
- `scripts/check_links.py public <base_url>` already runs in CI.

So the flip is mostly a DNS and Pages-settings action. **The check that matters
is running the link checker against the post-flip base URL**, because
`CLAUDE.md` mandates `{{ .Site.Home.RelPermalink }}` + no leading slash
specifically to survive a subpath, and the subpath is what disappears.

⚠️ Watch for anything that slipped past that convention: a hardcoded `/essays/`,
an `absURL`, or an image `src` starting with `/`. Those work on one base and
404 on the other.

### 2. Ads before launch

Monetization policy was already settled 2026-07-30 in `CLAUDE.md` — the Salt in
Our Hair model, soft and contextual, with money allowed in `/guides/` and
`/itineraries/` and forbidden in essays, Van Life, About, Start Here, The Map,
Places, Gallery and The Years. **That is decided; do not reopen it.**

What is *not* yet decided is display advertising, and that is the piece worth
thinking about while the theme is still soft. The reasoning:

- Story and reflective content converts affiliate clicks poorly. Nobody finishes
  an essay and books a hotel.
- The same content accumulates pageviews, which is what ad networks pay for.
- Salt in Our Hair runs Mediavine alongside its affiliates for exactly this
  reason.

**Be realistic about the timeline.** Ad networks need real traffic — Salt in Our
Hair has 583 guides and 10+ years behind it. MitM has 47 pages. This is a 2027
income line that you make cheap *now* by leaving room for it, not a launch-week
revenue plan.

Their other lesson worth stealing eventually: **their own digital products.**
They sell curated Google Maps location packs at €17–19 — near-zero marginal
cost, no network approval, and it monetizes readers who never click an affiliate
link. Eight years of real van park-ups across all 48 states is the raw material
for something equivalent. Park it until after launch.

### 3. Pinterest

Pinterest's audience is roughly 70% women platform-wide, and the content that
earns *saves* is planning material — itineraries, guides, "what I wish I'd
known" — not specification tables. That is MitM's native format, and it is
exactly what CAVL has been struggling to produce (CAVL's pins get clicks and
almost zero saves).

So MitM is likely the better Pinterest engine of the two sites. Worth setting up
boards and the first pins around launch rather than months later.

### 4. The cross-link

CAVL already links here **three times** from `/about/`, and those links go live
the moment the domain resolves. The reciprocal MitM → CAVL link should go in at
launch.

Set expectations honestly: two fresh sites owned by the same LLC cross-linking
is a crawl path, not authority. It helps discovery. It will not move rankings.
Real lift needs third-party links.

## Boundaries — do not cross these

- **CAVL is a separate brand.** Never move posts, photos or voice between the
  two sites. CAVL is technical and affiliate; MitM is story and philosophy.
  No product roundups, comparison tables or "best X of 2026" pages on MitM ever
  — that format lives on CAVL.
- **Never invent a fact** about Jesse, Karlee, the van, the mileage, the years,
  or where they have been. Same rule as CAVL, and it is the reason both sites
  are worth reading. If a number or a place is not already in the content or in
  memory, ask.
- **Never invent a hotel, restaurant or business** they stayed at or used. Link
  a city search instead. `CLAUDE.md` is explicit about this.

## One thing competing for attention

CAVL has a hard deadline that launch week should not swallow: its Amazon
Associates account needs **3 qualifying sales by ~2026-11-17** and none have
happened yet. A qualifying sale is anyone clicking a CAVL link and buying
anything on Amazon within 24 hours, so a few friends shopping normally covers
it. It is a fifteen-minute task, and it is the only affiliate income either site
currently has. Worth clearing before launch week starts.

⛔ Never through Jesse's own link — self-purchases do not count and are a
bannable violation.

## State of the repo, 2026-08-12

- Clean tree, 0 ahead of origin, last commit `73693a8` *"Adopt soft affiliate +
  sponsorship: booking machinery, itineraries, Work With Us."*
- 47 content pages across `essays`, `guides`, `itineraries`, `places`,
  `van-life`, `reduce-friction`, `start-here`, plus `about`, `gallery`, `map`,
  `years`, `work-with-us`.
- Local dev is `hugo server`, no flags.
