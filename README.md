# AvClock Website

Plain static site (no build step) — homepage, blog, support, credits,
privacy, and terms. Built to deploy free on Cloudflare Pages.

## What's in here

```
index.html                        Homepage
blog/index.html                   Blog listing
blog/how-to-read-metar-taf-reports.html   First post (live)
support.html                      Support / FAQ (from SUPPORT.md)
credits.html                      Data source credits (from ATTRIBUTION.md)
privacy.html                      Privacy Policy
terms.html                        Terms of Use
css/style.css                     Shared styles
images/app-icon.png               Real app icon (from Assets.xcassets)
js/track.js                       First-party analytics beacon (every page)
functions/api/track.js            Cloudflare Pages Function — logs events (public)
functions/api/stats.js            Cloudflare Pages Function — reads aggregates (should be gated)
analytics.html                    Private live-stats dashboard (should be gated, see below)
```

## A privacy note on the legal pages

Per your request, `privacy.html` and `terms.html` say **"AvClock"**
wherever the in-app version (`LegalText.swift`) names you personally —
your name is not published anywhere on this site. This is a wording
difference between the app's Terms and the website's Terms, done
deliberately for your privacy. It's a common, generally accepted
approach for a sole proprietor operating under a product name, but
since the terms doc's own header already says "not legal advice, have
an attorney review" — worth a quick sanity check with whoever
eventually reviews these, specifically on using "AvClock" as the named
party throughout.

**Separately, unrelated to this site:** the root `TERMS_OF_USE.md` in
your app repo still says Premium is "an auto-renewing subscription."
That's wrong — it's a one-time purchase, and `LegalText.swift` (the
in-app copy, dated July 19) already has this correct. This website's
`terms.html` uses the correct, up-to-date `LegalText.swift` version.
Worth fixing or deleting that stale root file so it doesn't get
mistaken for current later.

## Screenshots

**Fully local now** — no hotlinks to Apple's CDN anymore. Your real
App Store Connect renders (10 iPhone, 10 iPad, 5 Mac, 8 Apple Watch)
live in `images/screenshots/{iphone,ipad,mac,watch}/`, resized for web
(originals were 1–4.5MB each; these are ~20–500KB). Source renders:
- `AppScreens-Screenshots-*.render/apple/English (en-US)/iPhones  6.5/`
- `AppScreens-AvClock-iPadOS-*.render/apple/English (en-US)/iPad  13/`
- `AppScreens-AvClock-MacOS-*.render/apple/English (en-US)/Mac OS/`
- `AvClockWatchAppScreenshots/AppStoreReady/Ultra3-422x514/` — the
  same exact-size, alpha-flattened JPEGs used for the Apple Watch App
  Store screenshot slot, reused here at display size.

One combined **Screenshots** section (`index.html`, replacing what
used to be 3 scattered single-image slots plus a separate placeholder
device-tabs section) shows all of them in a scroll-snap filmstrip,
switchable by device tab (iPhone / iPad / Mac / Apple Watch).

To add a new screenshot later: drop the resized PNG into the right
`images/screenshots/{device}/` folder, then add an `<img>` to the
matching `.shot-gallery` block in `index.html` (same pattern as the
existing ones — file path + a real, specific `alt` description).

**On embedding the live App Store page directly** (asked about, so
noting the answer here too): not possible. Apple sends
`X-Frame-Options: DENY` and `frame-ancestors 'none'` on that page —
verified directly against the response headers. No browser will render
it in an iframe on any site, by design, no workaround.

## App Store badges

Both "Download on the App Store" and "Download on the Mac App Store"
buttons point at your real, live listing
(`apps.apple.com/us/app/avclock-global-airport-times/id6780675251`) —
one URL correctly serves both platforms since it's a single universal
listing. Optional: swap the current text-styled buttons for Apple's
official badge artwork from [Apple's marketing guidelines
page](https://developer.apple.com/app-store/marketing/guidelines/#app-store-badges)
if you want pixel-identical badges — not required, the current ones
are on-brand.

## A real typo on your live App Store screenshots

Two of your uploaded screenshots (the VFR/MVFR badges one and the
widget one) say "not for pilotage or **naviagtion**" — should be
"navigation." Worth fixing next time you update screenshots in App
Store Connect. Unrelated to this website; just noticed it while
pulling the URLs above.

## Deploying to Cloudflare Pages (free)

You already have an empty GitHub repo wired up as a git remote here
(`origin` → `github.com/avclock/avclock-website`), so you have two
options. **Option A is simplest if you just want it live today; Option
B is better long-term** (push to GitHub → auto-deploys, no manual
re-upload every time you add a blog post).

### Option A — Direct Upload (fastest, no GitHub needed)
1. Go to [dash.cloudflare.com](https://dash.cloudflare.com) and create a free account (no card required).
2. **Workers & Pages** → **Create** → **Pages** → **Upload assets**.
3. Drag this whole folder in, give the project a name (e.g. `avclock`).
4. You'll get a live URL like `avclock.pages.dev` within a minute or two.

### Option B — Connect the GitHub repo (recommended once you're ready)
1. Push this folder to the `avclock/avclock-website` repo you already have:
   ```
   git add .
   git commit -m "Initial site"
   git push -u origin main
   ```
   *(This step is yours to run — I won't push to GitHub on your behalf.)*
2. In Cloudflare dashboard: **Workers & Pages** → **Create** → **Pages** → **Connect to Git**, authorize GitHub, pick `avclock-website`.
3. Build settings: leave the build command **empty** and the output directory as `/` — this is a plain static site, nothing to build.
4. Every future `git push` auto-deploys. This is the easiest way to publish new blog posts later.

## Live analytics — private stats dashboard

Every page (including all blog posts) quietly logs pageviews, scroll
depth (25/50/75/100%), outbound/backlink clicks, and post shares via
`js/track.js`, a small first-party beacon with no cookies and no third
party involved. Two Cloudflare Pages Functions handle the server side:
`functions/api/track.js` (logs events, public — every visitor's
browser needs to reach it) and `functions/api/stats.js` (reads
aggregated totals — this one should be private, see below).
**`analytics.html`** is the dashboard itself: live tiles, per-page
breakdowns, and a rolling activity feed, polling `/api/stats` every 10
seconds. It's not linked anywhere in the site's nav, but that alone is
**not real privacy** — anyone who guesses or finds the URL can open it
until you gate it (next step).

**This only works once deployed on Cloudflare Pages** — the plain
local `python3 -m http.server` preview has no Functions runtime, so
`analytics.html` will just show "couldn't reach /api/stats" locally.
That's expected, not a bug.

### 1. Connect a KV namespace (required — this is where the data lives)
1. Cloudflare dashboard → **Workers & Pages** → **KV** → **Create a namespace** (e.g. name it `avclock-analytics`).
2. Back in your Pages project → **Settings → Functions → KV namespace bindings** → **Add binding**.
3. Variable name: **exactly** `ANALYTICS_KV` (the Functions code reads `env.ANALYTICS_KV`) → bind it to the namespace you just created.
4. Redeploy (or it takes effect on the next deploy) — after that, `analytics.html` will start showing real numbers as people visit the site.

### 2. Gate the dashboard behind Cloudflare Access (strongly recommended)
Same free Cloudflare Access setup already covered under [Optional: a
real login for publishing](#optional-a-real-login-for-publishing-cloudflare-access)
below — just point it at different paths this time:
- Application domain/path: `avclockapp.com/analytics.html`
- Also add a second Access application for `avclockapp.com/api/stats*` (the read endpoint) — otherwise someone could skip the dashboard UI and hit that URL directly to read raw totals.
- **Don't** gate `/api/track` — that one has to stay public, or every visitor's pageviews silently stop logging.

### A heads-up on scale
This is a lightweight, good-enough-for-a-personal-blog setup, not
built for high traffic — Cloudflare KV counters can slightly undercount
if many events hit the exact same counter at the exact same instant
(KV is eventually consistent, not built for atomic increments). For
the traffic this site is actually expecting, that's a non-issue; if
this blog ever gets genuinely heavy simultaneous traffic, a real
analytics service (Cloudflare Web Analytics, Plausible) would be the
more correct tool.

## Connecting a real domain later

Whenever you buy a domain (e.g. from Cloudflare Registrar, Namecheap,
or similar — typically ~$10–15/year):
1. Cloudflare Pages project → **Custom domains** → **Set up a domain**.
2. If the domain's DNS is already on Cloudflare, this is one click. If
   registered elsewhere, Cloudflare gives you a CNAME record to add at
   your registrar — takes a few minutes, propagates within an hour or so.
3. Once connected, update the `<link rel="canonical">` and Open Graph
   `og:image`/`og:url` tags across the HTML files from
   `avclockapp.com` to your real domain (simple find-and-replace).

## After it's live

Submit the site to [Google Search Console](https://search.google.com/search-console)
(free, just needs a Google account) — this is what actually gets you
indexed and shows real search data. Takes about 5 minutes, worth doing
on day one per the SEO notes.

## Adding future blog posts

`blog/index.html` already lists the 5 planned topics from the design
brief as grayed-out "Coming soon" stub cards. To publish one:
1. Copy `blog/how-to-read-metar-taf-reports.html` as a starting template.
2. Write the post, update the `<title>`/meta description/canonical URL.
3. Drop in real components (METAR blocks, category chips, the "more
   posts" footer, etc.) from **`blog/COMPONENTS.md`** — copy/paste
   snippets using classes that already exist in `css/style.css`, no new
   CSS needed.
4. In `blog/index.html`, replace that topic's `.post-card.stub` div with
   a real `<a class="post-card" href="...">` link (same pattern as the
   METAR/TAF post above it).

There's no CMS and no "dev login" baked into the site itself — this is
a static site with no backend, so any login built in plain JS/HTML
would just be a UI gate anyone could bypass from dev tools, not real
security. The template-and-push workflow above is the actual publishing
path; see the Cloudflare Access section below if you want real,
server-enforced login for editing on the go.

## Optional: a real login for publishing (Cloudflare Access)

If you want to be able to publish from your phone or any browser
without pushing through git, **Cloudflare Access** (part of Cloudflare
Zero Trust, free for individual use) gives you a genuine, server-side
login gate — not client-side JS. It checks your email via a one-time
login link, enforced by Cloudflare's edge before your page ever loads,
so it can't be bypassed from the browser.

This requires no changes to any file in this repo — it's configured
entirely in the Cloudflare dashboard, on your account:
1. Cloudflare dashboard → **Zero Trust** → **Access** → **Applications** → **Add an application** → **Self-hosted**.
2. Set the application domain to a specific path on your site, e.g.
   `avclockapp.com/admin*` (pick a path prefix you'll actually use).
3. Under **Policies**, add a rule: "Allow" if **Email** equals your own
   email address.
4. Save. Now visiting `avclockapp.com/admin/...` prompts a real login
   (a code sent to your email) before Cloudflare's edge will serve
   anything under that path — everything else on the site stays public
   and untouched.

Note this only gates *access to a path* — it's not a CMS with an
editor UI. You'd still hand-write the HTML (using the snippets above)
and either upload it through that gated path or push via git; Access
just makes sure only you can reach whatever you put there. Since this
step happens in your own Cloudflare account, it's something you'll
need to click through yourself — I can't log into your dashboard for
you.
