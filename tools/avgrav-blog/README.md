# AvGrav blog: the daily post

One new post a day on the AvGrav blog (`avgrav-blog/`, live at
avclockapp.com/avgrav-blog/), written for FBOs: line techs, line service
supervisors, fuel QC people, and FBO managers. Every post is useful on its
own and has one short, honest section on where AvGrav fits. That section is
the sponsor slot, and it also mentions AvClock, the same developer's
airport world clock, in a sentence or two (see "Mentioning AvClock" below).
The App Store button and the disclaimer are added automatically. `tools/` isn't served (see `.assetsignore`), so nothing in
this folder is public.

Files here:

- `new_post.py`: publishes a post from a JSON spec, and `--check` validates
  every post.
- `topics.json`: the topic list, in order. Take the first `"todo"` topic
  that is in season.
- `posts/<slug>.json`: the spec each post was published from.
- `avgrav-math.js`: AvGrav's correction math, for every fuel number.

## Publishing today's post

1. **Pick the topic.** The first entry in `topics.json` with
   `"status": "todo"` whose `season` fits today (`"winter"` is November to
   February, `"summer"` is May to August, `"any"` is always fine). Read its
   `angle`, `facts`, `avgrav`, and `avoid` notes. Skip any topic an existing
   post already covers. If fewer than 7 `todo` topics are left, add 10 new
   ones in the same style (vetted, specific, varied: fuel QC, ramp
   operations, safety, customer service, the FBO business), with their own
   notes.
2. **Check the facts.** Anything stated as fact that isn't in the notes as
   verified gets checked with a web search first. If it can't be confirmed,
   leave it out or say it in general terms. Fuel numbers (gravity, weight,
   volume, temperature) come from AvGrav's own math, never from memory:
   `avgrav-math.js` in this folder (a copy of the app's correction code,
   from avclock/AvGrav `tools/app-store-screenshots/`). From the repository
   root:

   ```
   node -e 'const M=require("./tools/avgrav-blog/avgrav-math.js").AvGravMath;const a=M.correctedAPI(46.0,85);console.log(a.toFixed(2),M.lbPerGal(a).toFixed(3),M.vcf(a,20).toFixed(5))'
   ```

   It has `correctedAPI(obs, tempF)`, `vcf(api60, tempF)` (net gallons =
   metered gallons x VCF), `lbPerGal(api60)`, `kgPerL(api60)`,
   `sg(api60)`, `density15FromAPI(api60)`, `apiFromDensity15(kgm3)`, and
   `density15C(kgm3, tempC)`. A sample Jet A the posts reuse: 46.0 API
   observed at 85°F is 43.79 at 60°F, 6.722 lb/gal, SG 0.8072, and
   806.8 kg/m³ at 15°C.
3. **Write the spec**, `posts/<slug>.json` (format below), dated today in
   U.S. Eastern time.
4. **Publish:** `python3 tools/avgrav-blog/new_post.py
   tools/avgrav-blog/posts/<slug>.json`. It writes the page, puts it at the
   top of the blog index, adds it to `sitemap.xml`, marks the topic
   published, and runs `--check`. Fix every error, and fix the warnings
   unless there's a reason not to. To redo a post, edit the spec and run
   it again with `--force`.
5. **Look at it:** serve the repository (`python3 -m http.server`) and open
   `/avgrav-blog/<slug>.html` at 390 and 1280 pixels wide (Playwright's
   Chromium is installed). Check that nothing overflows, the FAQ opens, and
   the links work.
6. **Ship it** on a branch `claude/avgrav-daily-<date>`. Commit
   `AvGrav blog: <title>` with the session's own git identity. Never use
   the owner's personal email; this site's commits must not carry it. Open
   a PR against `main` and merge it right away (squash). The owner asked
   for every change to be merged without waiting. Cloudflare deploys `main`.

## The spec

```json
{
  "slug": "words-joined-by-hyphens",
  "title": "Title Case, Under 65 Characters, Plain Text",
  "description": "One or two plain sentences for search results, 120 to 160 characters.",
  "date": "2026-10-11",
  "eyebrow": "LINE SERVICE &middot; SAFETY",
  "tag": "MISF",
  "excerpt": "One plain line for the blog index.",
  "minutes": 5,
  "related": ["slug-a", "slug-b", "slug-c"],
  "faq": [["A question people search for?", "A two or three sentence answer."]],
  "body": ["<p>...</p>", "<h2>...</h2>", "..."]
}
```

- `title`, `description`, `excerpt`, and FAQ questions are plain text:
  type real characters (°, ³), not entities. `body`, `eyebrow`, and FAQ
  answers are HTML. In the body use `&deg;` and `&sup3;` as the older
  posts do.
- `related` is optional: three slugs from the blog index for "More from
  AvGrav". It defaults to the three newest posts.
- `faq` has 2 to 4 entries. They show on the page as Common Questions and
  in the FAQ structured data, which Google requires to match.
- `tag` is 2 to 5 capitals, airport-board style (`MISF`, `DENS`, `WNTR`).
  `eyebrow` follows the existing ones: `LINE SERVICE &middot; ...`,
  `FUEL QC &middot; ...`, `FBO &middot; ...`.

## How a post reads

- **Who it's for:** someone on a ramp or running one. Talk to them as
  "you." Explain what to do and why, with real examples. No filler intros
  about "in today's fast-paced aviation industry."
- **Length:** 600 to 1,000 words. Two short opening paragraphs, three to
  six `<h2>` sections (Title Case, like the older posts), lists where steps
  or checks are listed, and a `<h2>Where AvGrav Fits</h2>` section near the
  end.
- **Copy rules (the owner's, for all user-facing text):** no em dashes,
  ever; use a period, colon, or comma. No exclamation points. Sentence case
  in the body. Plain words over jargon, and define jargon on first use. No
  "simply" or "just" as a crutch. No hype ("game-changer," "revolutionary,"
  "seamless").
- **Links:** two or three links to other AvGrav posts where they help, and
  `<a href="../avgrav">AvGrav</a>` and `<a href="../">AvClock</a>` in the
  AvGrav section. One or two links
  to an authoritative source (FAA, NTSB, NATA, SKYbrary, ASTM, the Energy
  Institute) are welcome, with `target="_blank" rel="noopener"`.
- **Tables** use the existing component:
  `<div class="table-wrap"><table>...</table></div>`, with `class="num"`
  on numeric `<th>` and `<td>`. Callouts: `<div class="callout"><p
  style="margin:0;">...</p></div>`, at most one.
- **Images** are optional. Only use files already in `images/` (for
  example `images/blog/` or `images/screenshots/avgrav/iphone/`) inside
  `<figure class="wide-shot">`, with a real description in `alt`.

## Accuracy (this is fuel; get it right)

- Never invent statistics, studies, quotes, accident details, tolerances,
  intervals, or regulation numbers. If a number isn't verified or computed,
  it doesn't go in.
- Limits and procedures belong to the reader's quality control manual, the
  fuel supplier, the aircraft manufacturer, and the airport. Describe the
  usual practice, and say where the real limit comes from.
- Name standards only when sure of them: A4A Specification 103 (formerly
  ATA 103), FAA Advisory Circular 150/5230-4, NFPA 407, 14 CFR 139.321,
  ASTM D1655 (Jet A, Jet A-1), ASTM D910 (100LL), API MPMS Chapter 11.1,
  API/EI 1542 (grade markings), EI/JIG standards.
- Safety-critical steps (bonding, misfueling, spills, lightning) stay
  general and point to training and the manual. Never suggest skipping a
  step.

## What AvGrav does (say only these)

- Corrects a hydrometer reading to API gravity at 60°F with the published
  API MPMS Chapter 11.1 tables (Table 6B), including the glass hydrometer
  correction, and corrects density meter readings to 15°C (Table 53B).
  Every result shows API at 60°F, specific gravity at 60°F, density at
  15°C, and pounds per gallon.
- Fuels: Jet A / Jet A-1, Avgas 100LL, Mogas, and Diesel. The result is
  colored against the typical range for the fuel picked (API at 60°F: Jet A
  36 to 51, 100LL 60 to 72, mogas 55 to 65, diesel 30 to 42); marginal is
  amber, outside the range is red.
- **Ticket API @ 60°F (optional)** or **Ticket Density @ 15°C**: shows the
  difference from the delivery ticket or certificate against a tolerance
  the user sets in Settings from their own procedures.
- **Fuel Volume** in gallons, liters, or mL: gives **Net Volume @ 60°F**
  and **Total Weight** in pounds or kilograms. **Already corrected to
  60°F** (and the Settings default **Volume already at 60°F**) is for a
  temperature-compensated meter.
- Every reading saves on its own to History with the time, the fuel, a
  **Tank or Truck** name (Settings > Tanks & Trucks), photos, and a note.
  The observed and corrected values can't be changed after saving, and
  edits to the other fields are kept in an edit history. A star protects a
  reading from deletion. **Require Volume to Save** and **Require Photo to
  Save** are in Settings.
- Export from History: today, the last 7 days, or everything, as
  **Spreadsheet (CSV)** or **Summary PDF**.
- A full calculator on Apple Watch, Home Screen widgets, Siri, and a
  Control Center button. iPhone, iPad, and Apple Watch.
- $0.99, once. No subscription, no account, no ads. Readings stay on the
  device.
- It's a reference tool, not a certified instrument, and it doesn't replace
  a QC program. Don't say it makes anyone compliant, and don't claim
  features beyond this list.

## Mentioning AvClock

Every post also mentions AvClock, in one or two sentences inside the
`Where AvGrav Fits` section (usually its last paragraph), linked as
`<a href="../">AvClock</a>`. AvGrav stays the main app in that section.
Tie AvClock to something the post is about, the way someone working a ramp
would use it: Zulu time on tickets and logs, the local time and weather at
an arriving aircraft's departure airport, FAA delays that move arrivals, or
a crew's next stop. One honest sentence beats a sales pitch, and never
suggest AvClock does anything with fuel.

What AvClock does (say only these):

- A free airport world clock: local time and UTC/Zulu for 8,700+ airports
  in 236 countries, searched by ICAO or IATA code, city, or name. Local
  weather in plain English, nearby airports (worked out on the device),
  an interactive world map, Home Screen and Lock Screen widgets, a Big
  Clock widget for StandBy, and Overlap (the hours when up to four
  airports are all awake). No account, no ads, no data collection.
- Premium, $4.99 once (not a subscription), one purchase for iPhone, iPad,
  and Mac: live METAR and TAF, color-coded VFR, MVFR, IFR, and LIFR; FAA
  ground stops, delays, and closures; weather and delay alerts; My Flights
  (log flights, calendar reminders); a Time Converter that shifts every
  clock together; heliports and hospital helipads.
- It's for reference only, not for navigation or flight planning. Weather
  and status can be delayed; official sources come first. Say so whenever
  a post leans on its weather or FAA status.

## When something's off

If a run can't publish (a check fails that it can't fix, a fact can't be
verified for any remaining topic), it opens the PR anyway as a draft, says
what's wrong in the PR description, and doesn't merge. Never publish
something unchecked to keep the streak going.
