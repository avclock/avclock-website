#!/usr/bin/env python3
"""
Writes the airport local time pages, airport-time/<iata>.html, and their
index, airport-time/index.html, from data/airports.json (the app's own
airport list). One page per airport in AIRPORTS below: the busiest
airports in the world plus the main U.S. hubs, the searches people
actually make ("time at Heathrow", "JFK time zone").

Each page has the live local time, Zulu, and sunrise/sunset (js/airport-
time.js, same math as the homepage's Try any airport), and, in the HTML
itself so search engines read it without running anything, the time
zone, its UTC offsets, and every clock change from today through the end
of next year, worked out with Python's own time zone database.

    python3 tools/airport-time/make_pages.py           write the pages
    python3 tools/airport-time/make_pages.py --check   only check them

Run it again at least once a year (the clock change dates run out), and
after adding an airport. It also updates sitemap.xml. tools/ isn't served.
"""
import datetime as dt
import html
import json
import re
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "airport-time"
SITE = "https://avclockapp.com"
APP_URL = "https://apps.apple.com/us/app/avclock-global-airport-times/id6780675251"

# (IATA, the name people use) in the order the index lists them.
AIRPORTS = [
    ("ATL", "Atlanta Hartsfield-Jackson"), ("DFW", "Dallas/Fort Worth"), ("DEN", "Denver"),
    ("ORD", "Chicago O'Hare"), ("LAX", "Los Angeles"), ("JFK", "New York JFK"),
    ("LAS", "Las Vegas Harry Reid"), ("MCO", "Orlando"), ("MIA", "Miami"),
    ("CLT", "Charlotte Douglas"), ("SEA", "Seattle-Tacoma"), ("PHX", "Phoenix Sky Harbor"),
    ("EWR", "Newark Liberty"), ("SFO", "San Francisco"), ("IAH", "Houston George Bush"),
    ("BOS", "Boston Logan"), ("FLL", "Fort Lauderdale"), ("MSP", "Minneapolis-St. Paul"),
    ("LGA", "New York LaGuardia"), ("DTW", "Detroit Metro"), ("PHL", "Philadelphia"),
    ("SLC", "Salt Lake City"), ("BWI", "Baltimore/Washington"), ("DCA", "Washington Reagan National"),
    ("IAD", "Washington Dulles"), ("SAN", "San Diego"), ("TPA", "Tampa"),
    ("BNA", "Nashville"), ("AUS", "Austin-Bergstrom"), ("HNL", "Honolulu"),
    ("ANC", "Anchorage"), ("YYZ", "Toronto Pearson"), ("YVR", "Vancouver"),
    ("MEX", "Mexico City"), ("CUN", "Cancún"), ("LHR", "London Heathrow"),
    ("LGW", "London Gatwick"), ("CDG", "Paris Charles de Gaulle"), ("AMS", "Amsterdam Schiphol"),
    ("FRA", "Frankfurt"), ("MUC", "Munich"), ("MAD", "Madrid-Barajas"),
    ("BCN", "Barcelona"), ("FCO", "Rome Fiumicino"), ("ZRH", "Zurich"),
    ("DUB", "Dublin"), ("IST", "Istanbul"), ("DXB", "Dubai"),
    ("DOH", "Doha Hamad"), ("DEL", "Delhi"), ("BOM", "Mumbai"),
    ("SIN", "Singapore Changi"), ("HKG", "Hong Kong"), ("BKK", "Bangkok Suvarnabhumi"),
    ("KUL", "Kuala Lumpur"), ("ICN", "Seoul Incheon"), ("HND", "Tokyo Haneda"),
    ("NRT", "Tokyo Narita"), ("PEK", "Beijing Capital"), ("PVG", "Shanghai Pudong"),
    ("SYD", "Sydney"), ("MEL", "Melbourne"), ("AKL", "Auckland"),
    ("GRU", "São Paulo Guarulhos"), ("JNB", "Johannesburg O.R. Tambo"),
]

COUNTRIES = {
    "US": "the United States", "CA": "Canada", "MX": "Mexico", "GB": "the United Kingdom",
    "FR": "France", "NL": "the Netherlands", "DE": "Germany", "ES": "Spain", "IT": "Italy",
    "CH": "Switzerland", "IE": "Ireland", "TR": "Türkiye", "AE": "the United Arab Emirates",
    "QA": "Qatar", "IN": "India", "SG": "Singapore", "HK": "Hong Kong", "TH": "Thailand",
    "MY": "Malaysia", "KR": "South Korea", "JP": "Japan", "CN": "China", "AU": "Australia",
    "NZ": "New Zealand", "BR": "Brazil", "ZA": "South Africa",
}

# A friendlier name for a zone than its IANA id, where there's a common one.
ZONE_NAMES = {
    "America/New_York": "Eastern Time", "America/Detroit": "Eastern Time",
    "America/Toronto": "Eastern Time", "America/Chicago": "Central Time",
    "America/Denver": "Mountain Time", "America/Phoenix": "Mountain Standard Time",
    "America/Los_Angeles": "Pacific Time", "America/Vancouver": "Pacific Time",
    "America/Anchorage": "Alaska Time", "Pacific/Honolulu": "Hawaii-Aleutian Standard Time",
    "Europe/London": "UK time", "Europe/Dublin": "Irish time",
    "Europe/Paris": "Central European Time", "Europe/Amsterdam": "Central European Time",
    "Europe/Berlin": "Central European Time", "Europe/Madrid": "Central European Time",
    "Europe/Rome": "Central European Time", "Europe/Zurich": "Central European Time",
    "Europe/Istanbul": "Türkiye Time", "Asia/Dubai": "Gulf Standard Time",
    "Asia/Qatar": "Arabia Standard Time", "Asia/Kolkata": "India Standard Time",
    "Asia/Calcutta": "India Standard Time", "Asia/Singapore": "Singapore Time",
    "Asia/Hong_Kong": "Hong Kong Time", "Asia/Bangkok": "Indochina Time",
    "Asia/Kuala_Lumpur": "Malaysia Time", "Asia/Seoul": "Korea Standard Time",
    "Asia/Tokyo": "Japan Standard Time", "Asia/Shanghai": "China Standard Time",
    "Australia/Sydney": "Australian Eastern Time", "Australia/Melbourne": "Australian Eastern Time",
    "Pacific/Auckland": "New Zealand Time", "America/Sao_Paulo": "Brasília Time",
    "Africa/Johannesburg": "South Africa Standard Time", "America/Mexico_City": "Central Standard Time (Mexico)",
    "America/Cancun": "Eastern Standard Time",
}


def esc(s):
    return html.escape(s, quote=True)


def offset_text(minutes):
    sign = "+" if minutes >= 0 else "−"
    a = abs(minutes)
    h, m = divmod(a, 60)
    return f"UTC{sign}{h}" + (f":{m:02d}" if m else "")


def hours_text(minutes):
    a = abs(minutes)
    h, m = divmod(a, 60)
    if m == 0:
        return f"{h} hour" + ("" if h == 1 else "s")
    return f"{h} hours {m} minutes" if h else f"{m} minutes"


def abbr(tz, when):
    name = when.astimezone(tz).tzname() or ""
    return name if re.fullmatch(r"[A-Z]{2,5}", name) else ""


def transitions(tz, start, end):
    """Every clock change between start and end (UTC datetimes): the UTC
    moment, the offset before, and the offset after, in minutes."""
    out = []
    t = start
    prev = int(t.astimezone(tz).utcoffset().total_seconds() // 60)
    step = dt.timedelta(hours=1)
    while t < end:
        n = t + step
        off = int(n.astimezone(tz).utcoffset().total_seconds() // 60)
        if off != prev:
            # narrow to the minute
            lo, hi = t, n
            while hi - lo > dt.timedelta(minutes=1):
                mid = lo + (hi - lo) / 2
                if int(mid.astimezone(tz).utcoffset().total_seconds() // 60) == prev:
                    lo = mid
                else:
                    hi = mid
            out.append((hi.replace(second=0, microsecond=0), prev, off))
            prev = off
        t = n
    return out


def nice_date(d):
    return d.strftime("%A, %B ") + str(d.day) + d.strftime(", %Y")


def nice_time(d):
    return d.strftime("%I:%M %p").lstrip("0").replace("AM", "a.m.").replace("PM", "p.m.")


def load_airports():
    rows = json.loads((ROOT / "data" / "airports.json").read_text())
    by_code = {r[0]: r for r in rows}
    out = []
    for code, short in AIRPORTS:
        r = by_code.get(code)
        if not r:
            sys.exit(f"{code} isn't in data/airports.json")
        iata, icao, name, lat, lon, tzid, country, city = (r + [""] * 8)[:8]
        if country not in COUNTRIES:
            sys.exit(f"Add a country name for {country} ({code})")
        out.append(dict(code=iata, icao=icao, name=name, short=short, lat=lat, lon=lon,
                        tz=tzid, country=country, city=city or short))
    return out


def facts(a, today):
    tz = ZoneInfo(a["tz"])
    start = dt.datetime(today.year, today.month, today.day, tzinfo=dt.timezone.utc)
    end = dt.datetime(today.year + 2, 1, 1, tzinfo=dt.timezone.utc)
    ch = transitions(tz, start, end)
    jan = dt.datetime(today.year, 1, 15, 12, tzinfo=dt.timezone.utc)
    jul = dt.datetime(today.year, 7, 15, 12, tzinfo=dt.timezone.utc)
    offs = sorted({int(x.astimezone(tz).utcoffset().total_seconds() // 60) for x in (jan, jul)})
    std = offs[0]
    dst = offs[1] if len(offs) > 1 else None
    std_abbr = abbr(tz, jan if int(jan.astimezone(tz).utcoffset().total_seconds() // 60) == std else jul)
    dst_abbr = ""
    if dst is not None:
        dst_abbr = abbr(tz, jan if int(jan.astimezone(tz).utcoffset().total_seconds() // 60) == dst else jul)
    return dict(changes=ch, std=std, dst=dst, std_abbr=std_abbr, dst_abbr=dst_abbr)


def zone_label(a):
    return ZONE_NAMES.get(a["tz"], a["tz"].split("/")[-1].replace("_", " ") + " time")


def page(a, f, all_airports, today):
    code, short = a["code"], a["short"]
    tz = ZoneInfo(a["tz"])
    zl = zone_label(a)
    country = COUNTRIES[a["country"]]
    std_t = offset_text(f["std"]) + (f" ({f['std_abbr']})" if f["std_abbr"] else "")
    if f["dst"] is not None:
        dst_t = offset_text(f["dst"]) + (f" ({f['dst_abbr']})" if f["dst_abbr"] else "")
        offset_sentence = f"{short} ({code}) is on {zl}: {std_t} in standard time and {dst_t} while daylight saving time is on."
    else:
        offset_sentence = f"{short} ({code}) is on {zl}, {std_t} all year. Its clocks don't change for daylight saving time."

    title = f"Time at {short} Airport ({code}): Local Time and Zulu"
    if len(title) > 65:
        title = f"Time at {short} ({code}): Local Time and Zulu"
    desc = (f"The current local time at {short} Airport ({code}, {a['icao']}), live, with Zulu time, "
            f"the time zone ({offset_text(f['std'])}"
            + (f" / {offset_text(f['dst'])}" if f["dst"] is not None else "")
            + "), sunrise, and sunset.")

    # Clock changes
    rows = []
    for when_utc, before, after in f["changes"]:
        local_before = (when_utc + dt.timedelta(minutes=before)).replace(tzinfo=None)
        direction = "forward" if after > before else "back"
        rows.append(
            f"<tr><td>{esc(nice_date(local_before))}</td><td>{nice_time(local_before)}</td>"
            f"<td>Clocks go {direction} {hours_text(after - before)}</td>"
            f"<td class=\"num\">{offset_text(after)}</td></tr>")
    if rows:
        changes_html = (
            "<h2>When the Clocks Change</h2>\n"
            f"      <p>Every daylight saving change at {esc(code)} from now through {today.year + 1}, in local time. "
            "These come from the same international time zone database phones and computers use.</p>\n"
            "      <div class=\"table-wrap\"><table>\n"
            "        <thead><tr><th>Date</th><th>Local time</th><th>Change</th><th class=\"num\">New offset</th></tr></thead>\n"
            "        <tbody>\n          " + "\n          ".join(rows) + "\n        </tbody>\n      </table></div>")
        transitions_attr = ",".join(str(int(w.timestamp())) for w, _, _ in f["changes"])
    else:
        changes_html = (
            "<h2>Daylight Saving Time</h2>\n"
            f"      <p>{esc(short)} doesn't use daylight saving time, so the offset from Zulu stays at "
            f"{offset_text(f['std'])} all year. When other places change their clocks, the difference between "
            f"{esc(code)} and those places changes by an hour instead.</p>")
        transitions_attr = ""

    # Zulu conversion
    def conv(off):
        if off == 0:
            return "Local time and Zulu are the same"
        word = "add" if off > 0 else "subtract"
        return f"To get local time from Zulu, {word} {hours_text(off)}"

    if f["dst"] is not None:
        zulu_html = (f"<p>{conv(f['std'])} in standard time. With daylight saving time on, "
                     f"{conv(f['dst'])[0].lower() + conv(f['dst'])[1:]}. Going the other way, from local time to Zulu, "
                     "do the opposite.</p>")
        z_example_off = f["std"]
    else:
        zulu_html = f"<p>{conv(f['std'])}, all year. Going the other way, from local time to Zulu, do the opposite.</p>"
        z_example_off = f["std"]
    ex_local = (dt.datetime(2026, 1, 15, 15, 0) + dt.timedelta(minutes=z_example_off))
    zulu_html += (f"\n      <p>For example, a METAR or flight plan time of <code>1500Z</code> is "
                  f"{nice_time(ex_local)} local at {esc(code)}"
                  + (" in standard time" if f["dst"] is not None else "")
                  + (", the next day" if ex_local.day != 15 and ex_local > dt.datetime(2026, 1, 15, 15) else "")
                  + (", the day before" if ex_local.day != 15 and ex_local < dt.datetime(2026, 1, 15, 15) else "")
                  + ".</p>")

    # Same zone, other airports on the list
    same = [b for b in all_airports if b["tz"] == a["tz"] and b["code"] != code]
    same_off = [b for b in all_airports if b["tz"] != a["tz"] and b["code"] != code
                and facts_cache[b["code"]]["std"] == f["std"] and facts_cache[b["code"]]["dst"] == f["dst"]]
    near = (same + same_off)[:6]
    if near:
        links = ", ".join(f"<a href=\"{b['code'].lower()}\">{esc(b['short'])} ({b['code']})</a>" for b in near)
        same_html = f"<p>Other airports on the same clock: {links}.</p>"
    else:
        same_html = ""

    faq = [
        (f"What time zone is {code} airport in?",
         f"{short} Airport ({code}) uses the {a['tz']} time zone, {zl}. "
         + (f"That's {offset_text(f['std'])} in standard time and {offset_text(f['dst'])} in daylight saving time."
            if f["dst"] is not None else f"That's {offset_text(f['std'])} all year.")),
        (f"Does {code} change its clocks for daylight saving time?",
         (f"Yes. " + (f"The next change is on {nice_date((f['changes'][0][0] + dt.timedelta(minutes=f['changes'][0][1])).replace(tzinfo=None))}." if f["changes"] else ""))
         if f["dst"] is not None else
         f"No. {short} stays at {offset_text(f['std'])} all year."),
        (f"How do I convert Zulu time to local time at {code}?",
         re.sub(r"<[^>]+>", "", zulu_html.split("</p>")[0]).strip()),
    ]
    faq_html = "\n".join(
        f"        <details class=\"faq-item\"><summary>{esc(q)}</summary><p>{esc(ans)}</p></details>" for q, ans in faq)
    faq_ld = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": ans}} for q, ans in faq],
    }
    place_ld = {
        "@context": "https://schema.org", "@type": "Airport", "name": a["name"],
        "iataCode": code, "icaoCode": a["icao"],
        "geo": {"@type": "GeoCoordinates", "latitude": a["lat"], "longitude": a["lon"]},
        "address": {"@type": "PostalAddress", "addressLocality": a["city"], "addressCountry": a["country"]},
    }
    crumbs_ld = {
        "@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Airport local times", "item": f"{SITE}/airport-time/"},
            {"@type": "ListItem", "position": 2, "name": f"{short} ({code})", "item": f"{SITE}/airport-time/{code.lower()}"},
        ]}
    url = f"{SITE}/airport-time/{code.lower()}"
    ld = "\n".join(f"<script type=\"application/ld+json\">\n{json.dumps(x, ensure_ascii=False, indent=2)}\n</script>"
                   for x in (place_ld, crumbs_ld, faq_ld))
    big_now = offset_text(f["std"]) + (f" / {offset_text(f['dst'])[3:]}" if f["dst"] is not None else "")
    static_now = f"{zl}, {offset_text(f['std'])}" + (f" / {offset_text(f['dst'])}" if f["dst"] is not None else "")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="apple-itunes-app" content="app-id=6780675251">

<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">

<meta property="og:type" content="website">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}/images/og-avclock.png">
<meta name="twitter:card" content="summary_large_image">

<link rel="icon" type="image/png" href="../images/app-icon.png">
<link rel="shortcut icon" href="../favicon.ico">
<link rel="apple-touch-icon" href="../images/app-icon.png">
<link rel="stylesheet" href="../css/style.css">

{ld}
</head>
<body>

<nav class="site-nav">
  <div class="container">
    <a class="brand" href="../">
      <img src="../images/icons/avclock-64.webp" alt="AvClock app icon">
      AvClock
    </a>
    <div class="nav-links">
      <a href="../#free">Free</a>
      <a href="../#premium">Premium</a>
      <a href="../blog/">Blog</a>
      <a href="./">Airport times</a>
      <a href="../support">Support</a>
    </div>
    <button class="nav-toggle" aria-label="Menu" aria-expanded="false"><span></span><span></span><span></span></button>
  </div>
</nav>

<section>
  <div class="container">
    <article class="post">
      <p><a href="./">&larr; All airport times</a></p>
      <div class="label-caps" style="color:var(--amber);margin-bottom:14px;">AIRPORT TIME &middot; {esc(code)} &middot; {esc(a['icao'])}</div>
      <h1>What Time Is It at {esc(short)} Airport ({esc(code)})?</h1>

      <div class="apt-clock try-card" data-tz="{esc(a['tz'])}" data-lat="{a['lat']}" data-lon="{a['lon']}" data-changes="{transitions_attr}" aria-live="off">
        <div class="try-head">
          <span class="try-code">{esc(code)} &middot; {esc(a['icao'])}</span>
          <span class="try-name">{esc(a['name'])}, {esc(a['city'])}</span>
        </div>
        <div class="try-time" data-f="time">{esc(big_now)}</div>
        <div class="try-date" data-f="date">Local time, {esc(a['tz'])}</div>
        <dl class="try-facts">
          <div><dt>Time zone now</dt><dd data-f="utc">{esc(static_now)}</dd></div>
          <div><dt>Zulu now</dt><dd data-f="zulu">UTC</dd></div>
          <div><dt>From you</dt><dd data-f="diff">&nbsp;</dd></div>
          <div><dt>Sunrise / sunset</dt><dd data-f="sun">&nbsp;</dd></div>
          <div><dt>Next clock change</dt><dd data-f="next">{"None, no daylight saving" if not f["changes"] else "&nbsp;"}</dd></div>
          <div><dt>Location</dt><dd>{a['lat']:.3f}, {a['lon']:.3f}</dd></div>
        </dl>
      </div>

      <p>{esc(offset_sentence)} The airport is in {esc(a['city'])}, {esc(country)}. Its codes are <strong>{esc(code)}</strong> (IATA, the one on your boarding pass) and <strong>{esc(a['icao'])}</strong> (ICAO, the one pilots and air traffic control use).</p>
      {same_html}

      <h2>Zulu Time and {esc(code)}</h2>
      {zulu_html}

      {changes_html}

      <div class="callout">
        <p style="margin:0;">AvClock keeps {esc(code)} on your clock next to LOCAL and Zulu, with sunrise, sunset, weather, and airport details for any airport in the world. Free on iPhone, iPad, Mac, and Apple Watch.</p>
      </div>

      <h2>Common Questions</h2>
      <div class="faq-list">
{faq_html}
      </div>

      <div style="text-align:center;margin:40px 0;">
        <div class="label-caps" style="margin-bottom:14px;">Keep {esc(code)} on your clock</div>
        <div class="badge-row" style="justify-content:center;">
          <a class="store-badge" href="{APP_URL}" target="_blank" rel="noopener" data-track="outbound">
            <svg viewBox="0 0 384 512" fill="currentColor"><path d="M318.7 268.7c-.2-36.7 16.4-64.4 50-84.8-18.8-26.9-47.2-41.7-84.7-44.6-35.5-2.8-74.3 20.7-88.5 20.7-15 0-49.4-19.7-76.4-19.7C63.3 141.2 4 184.8 4 273.5q0 39.3 14.4 81.2c12.8 36.7 59 126.7 107.2 125.2 25.2-.6 43-17.9 75.8-17.9 31.8 0 48.3 17.9 76.4 17.9 48.6-.7 90.4-82.5 102.6-119.3-65.2-30.7-61.7-90-61.7-91.9zm-56.6-164.2c27.3-32.4 24.8-61.9 24-72.5-24.1 1.4-52 16.4-67.9 34.9-17.5 19.8-27.8 44.3-25.6 71.9 26.1 2 49.9-11.4 69.5-34.3z"/></svg>
            Download AvClock, free
          </a>
        </div>
      </div>

      <p class="disclaimer">Times here come from your browser's clock and the international time zone database. Sunrise and sunset are estimates, good to a few minutes. AvClock is for reference only, not for navigation or flight planning.</p>

      <div class="more-posts">
        <div class="label-caps">More from AvClock</div>
        <div class="blog-board">
          <a class="blog-row" href="../blog/zulu-time-explained">
            <span class="tag">ZULU</span>
            <span class="row-main">
              <span class="row-title">Zulu Time Explained</span>
              <span class="row-excerpt">Why aviation runs on UTC, and how to read a Zulu timestamp.</span>
            </span>
            <span class="row-status live">LIVE</span>
          </a>
          <a class="blog-row" href="../blog/icao-vs-iata-codes">
            <span class="tag">ICAO</span>
            <span class="row-main">
              <span class="row-title">ICAO vs IATA Airport Codes</span>
              <span class="row-excerpt">Why {esc(code)} and {esc(a['icao'])} are the same airport.</span>
            </span>
            <span class="row-status live">LIVE</span>
          </a>
          <a class="blog-row" href="./">
            <span class="tag">ALL</span>
            <span class="row-main">
              <span class="row-title">Local time at {len(all_airports)} busy airports</span>
              <span class="row-excerpt">Every airport on one live board.</span>
            </span>
            <span class="row-status live">&rarr;</span>
          </a>
        </div>
      </div>
    </article>
  </div>
</section>

{FOOTER}

<script src="../js/nav.js" defer></script>
<script src="../js/track.js" defer></script>
<script src="../js/airport-time.js" defer></script>
</body>
</html>
"""


FOOTER = """<footer>
  <div class="container">
    <div class="footer-grid">
      <a class="brand" href="../">
        <img src="../images/icons/avclock-64.webp" alt="AvClock app icon">
        AvClock
      </a>
      <div class="footer-links">
        <a href="../blog/">Blog</a>
        <a href="./">Airport times</a>
        <a href="../support">Support</a>
        <a href="../credits">Credits</a>
        <a href="../privacy">Privacy Policy</a>
        <a href="../terms">Terms of Use</a>
        <a href="mailto:avclock@protonmail.com">Contact</a>
      </div>
    </div>
    <p class="footer-note">AvClock is for reference only, not for navigation, pilotage, or flight planning. Data and weather may be inaccurate or delayed; always confirm with official sources before any aviation decision.</p>
  </div>
</footer>"""


def index_page(airports):
    rows = []
    for a in airports:
        f = facts_cache[a["code"]]
        off = offset_text(f["std"]) + (f" / {offset_text(f['dst'])}" if f["dst"] is not None else "")
        rows.append(
            f"          <a class=\"blog-row apt-row\" href=\"{a['code'].lower()}\" data-tz=\"{esc(a['tz'])}\">\n"
            f"            <span class=\"tag\">{a['code']}</span>\n"
            f"            <span class=\"row-main\">\n"
            f"              <span class=\"row-title\">{esc(a['short'])}</span>\n"
            f"              <span class=\"row-excerpt\">{esc(a['city'])}, {esc(COUNTRIES[a['country']])} &middot; {esc(off)}</span>\n"
            f"            </span>\n"
            f"            <span class=\"row-status live\" data-f=\"time\">{a['icao']}</span>\n"
            f"          </a>")
    title = "Airport Local Times: Live Clocks for the Busiest Airports"
    desc = (f"The current local time and Zulu time at {len(airports)} of the busiest airports in the world, live, "
            "with each airport's time zone and daylight saving dates.")
    item_ld = {
        "@context": "https://schema.org", "@type": "ItemList", "name": "Airport local times",
        "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f"{SITE}/airport-time/{a['code'].lower()}",
                             "name": f"{a['short']} ({a['code']})"} for i, a in enumerate(airports)],
    }
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="apple-itunes-app" content="app-id=6780675251">

<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{SITE}/airport-time/">

<meta property="og:type" content="website">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{SITE}/airport-time/">
<meta property="og:image" content="{SITE}/images/og-avclock.png">
<meta name="twitter:card" content="summary_large_image">

<link rel="icon" type="image/png" href="../images/app-icon.png">
<link rel="shortcut icon" href="../favicon.ico">
<link rel="apple-touch-icon" href="../images/app-icon.png">
<link rel="stylesheet" href="../css/style.css">

<script type="application/ld+json">
{json.dumps(item_ld, ensure_ascii=False, indent=2)}
</script>
</head>
<body>

<nav class="site-nav">
  <div class="container">
    <a class="brand" href="../">
      <img src="../images/icons/avclock-64.webp" alt="AvClock app icon">
      AvClock
    </a>
    <div class="nav-links">
      <a href="../#free">Free</a>
      <a href="../#premium">Premium</a>
      <a href="../blog/">Blog</a>
      <a href="./">Airport times</a>
      <a href="../support">Support</a>
    </div>
    <button class="nav-toggle" aria-label="Menu" aria-expanded="false"><span></span><span></span><span></span></button>
  </div>
</nav>

<section>
  <div class="container">
    <article class="post">
      <div class="label-caps" style="color:var(--amber);margin-bottom:14px;">AIRPORT TIME &middot; LIVE</div>
      <h1>Local Time at the World's Busiest Airports</h1>
      <p>The time right now at {len(airports)} of the busiest airports in the world, with Zulu time at the top. Tap an airport for its time zone, its daylight saving dates, sunrise and sunset, and how to convert Zulu to local time there.</p>
      <div class="apt-zulu" aria-live="off"><span class="label-caps">Zulu now</span> <strong data-f="zulu">UTC</strong></div>
      <div class="blog-board apt-board">
{chr(10).join(rows)}
      </div>
      <div class="callout" style="margin-top:28px;">
        <p style="margin:0;">Need an airport that isn't here? The homepage's <a href="../#try">Try any airport</a> covers more than 8,000, and AvClock keeps your own list on your iPhone, iPad, Mac, and Apple Watch for free.</p>
      </div>
      <p class="disclaimer">Times come from your browser's clock and the international time zone database. AvClock is for reference only, not for navigation or flight planning.</p>
    </article>
  </div>
</section>

{FOOTER}

<script src="../js/nav.js" defer></script>
<script src="../js/track.js" defer></script>
<script src="../js/airport-time.js" defer></script>
</body>
</html>
"""


def update_sitemap(airports, today):
    sm = ROOT / "sitemap.xml"
    text = sm.read_text()
    text = re.sub(r"\s*<url>\s*<loc>https://avclockapp\.com/airport-time/[^<]*</loc>.*?</url>", "", text, flags=re.S)
    urls = [f"{SITE}/airport-time/"] + [f"{SITE}/airport-time/{a['code'].lower()}" for a in airports]
    block = "".join(
        f"\n  <url>\n    <loc>{u}</loc>\n    <lastmod>{today.isoformat()}</lastmod>\n    <priority>{'0.7' if u.endswith('/') else '0.6'}</priority>\n  </url>"
        for u in urls)
    text = text.replace("\n</urlset>", block + "\n</urlset>")
    sm.write_text(text)


def check(airports):
    errors = []
    names = {p.name for p in OUT.glob("*.html")}
    want = {"index.html"} | {a["code"].lower() + ".html" for a in airports}
    if names != want:
        errors.append(f"airport-time/ has {sorted(names ^ want)} out of step")
    sm = (ROOT / "sitemap.xml").read_text()
    for p in sorted(OUT.glob("*.html")):
        t = p.read_text()
        if "—" in t or "&mdash;" in t:
            errors.append(f"{p.name}: em dash")
        if t.count("<div") != t.count("</div>"):
            errors.append(f"{p.name}: div balance {t.count('<div')} vs {t.count('</div>')}")
        for m in re.finditer(r'<script type="application/ld\+json">\n(.*?)\n</script>', t, re.S):
            try:
                json.loads(m.group(1))
            except ValueError as e:
                errors.append(f"{p.name}: bad JSON-LD ({e})")
        canon = re.search(r'<link rel="canonical" href="([^"]+)"', t).group(1)
        if f"<loc>{canon}</loc>" not in sm:
            errors.append(f"{p.name}: {canon} not in sitemap.xml")
        title = re.search(r"<title>(.*?)</title>", t).group(1)
        if len(html.unescape(title)) > 70:
            errors.append(f"{p.name}: title is {len(title)} characters")
        for href in re.findall(r'href="([^"#:]+)"', t):
            if href.startswith(("http", "mailto")):
                continue
            target = (p.parent / href).resolve()
            if not (target.exists() or target.with_suffix(".html").exists() or (target / "index.html").exists()):
                errors.append(f"{p.name}: broken link {href}")
    return errors


facts_cache = {}


def main(argv):
    today = dt.date.today()
    airports = load_airports()
    for a in airports:
        facts_cache[a["code"]] = facts(a, today)
    if "--check" not in argv:
        OUT.mkdir(exist_ok=True)
        for a in airports:
            (OUT / f"{a['code'].lower()}.html").write_text(page(a, facts_cache[a["code"]], airports, today))
        (OUT / "index.html").write_text(index_page(airports))
        update_sitemap(airports, today)
        print(f"Wrote {len(airports)} airport pages and the index.")
    errors = check(airports)
    for e in errors:
        print("ERROR:", e)
    print("Check:", "OK" if not errors else f"{len(errors)} problem(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
