#!/usr/bin/env python3
"""Publish an AvGrav blog post from a JSON spec, or check every post.

  python3 tools/avgrav-blog/new_post.py tools/avgrav-blog/posts/<slug>.json
  python3 tools/avgrav-blog/new_post.py --check

Publishing writes avgrav-blog/<slug>.html, with the head, nav, footer, CTA,
and disclaimer copied from TEMPLATE so every post matches the site. It also
puts the post at the top of avgrav-blog/index.html (NEW for 7 days, then
LIVE), adds it to sitemap.xml, and marks its topic published in topics.json.
--check validates every post in avgrav-blog/. Run either from anywhere;
paths are relative to the repository. README.md here has the writing rules.
"""
import datetime
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
BLOG = os.path.join(ROOT, "avgrav-blog")
TEMPLATE = os.path.join(BLOG, "fuel-delivery-api-gravity-check.html")
INDEX = os.path.join(BLOG, "index.html")
SITEMAP = os.path.join(ROOT, "sitemap.xml")
TOPICS = os.path.join(HERE, "topics.json")
BASE = "https://avclockapp.com/avgrav-blog/"
ICON = "https://avclockapp.com/images/avgrav-icon.png"
NEW_DAYS = 7
DASHES = ("—", "&mdash;", "&#8212;", " -- ")

ROW = '''{ind}<a class="blog-row" href="{slug}">
{ind}  <span class="tag">{tag}</span>
{ind}  <span class="row-main">
{ind}    <span class="row-title">{title}</span>
{ind}    <span class="row-excerpt">{excerpt}</span>
{ind}  </span>
{ind}  <span class="row-status live">{status}</span>
{ind}</a>
'''


def fail(msg):
    sys.exit("new_post.py: " + msg)


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def write(p, s):
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)


def plain(s):
    """Visible text of an HTML fragment, entities decoded."""
    return html.unescape(re.sub(r"<[^>]+>", " ", s))


# ---------------------------------------------------------------- spec

def load_spec(path):
    spec = json.loads(read(path))
    need = ["slug", "title", "description", "date", "eyebrow", "tag", "excerpt", "minutes", "body", "faq"]
    missing = [k for k in need if k not in spec]
    if missing:
        fail("spec is missing " + ", ".join(missing))
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", spec["slug"]):
        fail("slug must be lowercase words joined by hyphens: " + spec["slug"])
    datetime.date.fromisoformat(spec["date"])
    if not re.fullmatch(r"[A-Z0-9]{2,5}", spec["tag"]):
        fail("tag must be 2 to 5 capital letters or digits: " + spec["tag"])
    if isinstance(spec["body"], list):
        spec["body"] = "\n".join(spec["body"])
    if not (2 <= len(spec["faq"]) <= 5) or any(len(qa) != 2 for qa in spec["faq"]):
        fail("faq needs 2 to 5 [question, answer] pairs")
    for k in ("title", "description", "excerpt"):
        if re.search(r"&[#a-zA-Z0-9]+;|<[a-z/]", spec[k]):
            fail("%s is plain text: type the real character (°, ³) instead of an entity or tag" % k)
    for q, _ in spec["faq"]:
        if re.search(r"<[a-z/]", q):
            fail("FAQ questions are plain text: " + q)
    return spec


def problems(spec):
    """(errors, warnings) for the spec's text against the house rules."""
    errors, warnings = [], []
    fields = {"title": spec["title"], "description": spec["description"], "excerpt": spec["excerpt"],
              "eyebrow": spec["eyebrow"], "body": spec["body"],
              "faq": " ".join(q + " " + a for q, a in spec["faq"])}
    for name, text in fields.items():
        for d in DASHES:
            if d in text:
                errors.append("%s has an em dash (%r); use a period, colon, or comma" % (name, d.strip()))
        if "!" in plain(text):
            warnings.append(name + " has an exclamation point")
    body = plain(spec["body"])
    words = len(body.split())
    if words < 450:
        errors.append("body is %d words; write at least 450 (aim for 600 to 1,000)" % words)
    for crutch in ("simply", "just "):
        n = body.lower().count(crutch)
        if n > 2:
            warnings.append("body uses %r %d times" % (crutch.strip(), n))
    if "AvGrav" not in body:
        errors.append("body never mentions AvGrav; every post has a short section on where it fits")
    if 'href="../avgrav"' not in spec["body"]:
        warnings.append("body doesn't link the AvGrav page (../avgrav)")
    if len(spec["title"]) > 70:
        warnings.append("title is %d characters; search results cut off around 60 to 70" % len(spec["title"]))
    if not 70 <= len(spec["description"]) <= 165:
        warnings.append("description is %d characters; aim for 120 to 160" % len(spec["description"]))
    if spec["body"].count("<h2>") < 3:
        warnings.append("body has fewer than three <h2> sections")
    return errors, warnings


# ---------------------------------------------------------------- index

ROW_RE = re.compile(r'( *)<a class="blog-row" href="([^"]+)">\s*<span class="tag">(.*?)</span>\s*'
                    r'<span class="row-main">\s*<span class="row-title">(.*?)</span>\s*'
                    r'<span class="row-excerpt">(.*?)</span>\s*</span>\s*'
                    r'<span class="row-status live">(.*?)</span>\s*</a>\n', re.S)


def index_rows():
    """[(slug, tag, title, excerpt)] in the index's order, newest first."""
    return [(m.group(2), m.group(3), m.group(4), m.group(5)) for m in ROW_RE.finditer(read(INDEX))]


def post_date(slug):
    m = re.search(r'"datePublished":\s*"(\d{4}-\d{2}-\d{2})"', read(os.path.join(BLOG, slug + ".html")))
    return datetime.date.fromisoformat(m.group(1)) if m else None


def update_index(spec):
    s = read(INDEX)
    first = ROW_RE.search(s)
    if not first:
        fail("couldn't find the post list in avgrav-blog/index.html")
    ind = first.group(1)
    s = s[:first.start()] + ROW.format(ind=ind, slug=spec["slug"], tag=spec["tag"], title=spec["title_html"],
                                        excerpt=spec["excerpt_html"], status="NEW") + s[first.start():]
    today = datetime.date.fromisoformat(spec["date"])

    def status(m):
        d = post_date(m.group(2))
        label = "NEW" if d and (today - d).days < NEW_DAYS else "LIVE"
        return m.group(0).replace('<span class="row-status live">%s</span>' % m.group(6),
                                  '<span class="row-status live">%s</span>' % label)
    write(INDEX, ROW_RE.sub(status, s))


def refresh_row(spec):
    """A rewritten post (--force) keeps its place and status; its tag, title, and excerpt follow the spec."""
    s = read(INDEX)

    def fix(m):
        if m.group(2) != spec["slug"]:
            return m.group(0)
        return ROW.format(ind=m.group(1), slug=spec["slug"], tag=spec["tag"], title=spec["title_html"],
                          excerpt=spec["excerpt_html"], status=m.group(6))
    write(INDEX, ROW_RE.sub(fix, s))


# ---------------------------------------------------------------- sitemap

def update_sitemap(spec):
    s = read(SITEMAP)
    url = BASE + spec["slug"]
    if "<loc>%s</loc>" % url in s:
        return
    blocks = list(re.finditer(r"  <url>\s*<loc>(%s[^<]+)</loc>.*?</url>\n" % re.escape(BASE), s, re.S))
    if not blocks:
        fail("no avgrav-blog entries in sitemap.xml to add after")
    entry = "  <url>\n    <loc>%s</loc>\n    <lastmod>%s</lastmod>\n    <priority>0.7</priority>\n  </url>\n" % (url, spec["date"])
    end = blocks[-1].end()
    s = s[:end] + entry + s[end:]
    s = re.sub(r"(<loc>%s</loc>\s*<lastmod>)[^<]+" % re.escape(BASE), lambda m: m.group(1) + spec["date"], s, count=1)
    write(SITEMAP, s)


# ---------------------------------------------------------------- the page

def related_rows(spec):
    rows = {r[0]: r for r in index_rows()}
    picks = spec.get("related") or [r[0] for r in index_rows() if r[0] != spec["slug"]][:3]
    out = []
    for slug in picks:
        if slug not in rows:
            fail("related post %r isn't in the blog index" % slug)
        _, tag, title, excerpt = rows[slug]
        out.append(ROW.format(ind="          ", slug=slug, tag=tag, title=title, excerpt=excerpt, status="LIVE"))
    return "".join(out)


def faq_html(faq, ind="      "):
    """The visible Common Questions section; Google requires FAQ markup to match visible text."""
    items = "".join('%s<details class="faq-item">\n%s  <summary>%s</summary>\n%s  <p>%s</p>\n%s</details>\n'
                    % (ind, ind, html.escape(q, quote=False), ind, a, ind) for q, a in faq)
    return "\n%s<h2>Common Questions</h2>\n%s" % (ind, items)


def render(spec):
    t = read(TEMPLATE)
    url = BASE + spec["slug"]
    attr = lambda s: html.escape(s, quote=True)
    t = re.sub(r"<title>.*?</title>", lambda m: "<title>" + html.escape(spec["title"], quote=False) + "</title>", t, count=1)
    for pat, val in ((r'(<meta name="description" content=")[^"]*', spec["description"]),
                     (r'(<meta property="og:description" content=")[^"]*', spec["description"]),
                     (r'(<meta property="og:title" content=")[^"]*', spec["title"]),
                     (r'(<link rel="canonical" href=")[^"]*', url),
                     (r'(<meta property="og:url" content=")[^"]*', url),
                     (r'(<meta property="og:image" content=")[^"]*', ICON)):
        t, n = re.subn(pat, lambda m: m.group(1) + attr(val), t, count=1)
        if n != 1:
            fail("template is missing " + pat)

    article = {"@context": "https://schema.org", "@type": "Article", "headline": spec["title"],
               "description": spec["description"], "datePublished": spec["date"],
               "publisher": {"@type": "Organization", "name": "AvGrav"}, "mainEntityOfPage": url}
    faq = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": plain(q).strip(), "acceptedAnswer": {"@type": "Answer", "text": plain(a).strip()}}
        for q, a in spec["faq"]]}
    ld = "".join('<script type="application/ld+json">\n%s\n</script>\n' % json.dumps(o, indent=2, ensure_ascii=False)
                 for o in (article, faq))
    t, n = re.subn(r'(<script type="application/ld\+json">.*?</script>\n)+', lambda m: ld, t, count=1, flags=re.S)
    if n != 1:
        fail("template has no structured data block")

    a0, a1 = t.index('<article class="post">'), t.index("</article>")
    old = t[a0:a1]
    disclaimer = re.search(r'\n      <p class="disclaimer">.*?</p>\n', old, re.S).group(0)
    cta = re.search(r'\n      <div style="text-align:center;margin:40px 0;">.*?\n      </div>\n', old, re.S).group(0)
    body = "\n".join("      " + line if line.strip() else "" for line in spec["body"].strip("\n").split("\n"))
    new = ('<article class="post">\n'
           '      <p><a href="./">&larr; Back to Blog</a></p>\n'
           '      <div class="label-caps" style="color:var(--amber);margin-bottom:14px;">%s</div>\n'
           '      <h1>%s</h1>\n'
           '      <div class="post-meta">%d min read <button class="share-btn" data-track="share">Share</button></div>\n\n'
           '%s\n%s%s%s\n'
           '      <div class="more-posts">\n'
           '        <div class="label-caps">More from AvGrav</div>\n'
           '        <div class="blog-board">\n%s'
           '        </div>\n'
           '      </div>\n    ') % (spec["eyebrow"], spec["title_html"], int(spec["minutes"]), body,
                                    faq_html(spec["faq"]), disclaimer, cta, related_rows(spec))
    return t[:a0] + new + t[a1:]


def mark_topic(spec):
    if not os.path.exists(TOPICS):
        return
    topics = json.loads(read(TOPICS))
    for t in topics:
        if t.get("slug") == spec["slug"]:
            t["status"] = "published"
            t["published"] = spec["date"]
            write(TOPICS, json.dumps(topics, indent=2, ensure_ascii=False) + "\n")
            return
    print("note: %s isn't in topics.json; add it there too so it isn't written twice" % spec["slug"])


def publish(path):
    spec = load_spec(path)
    out = os.path.join(BLOG, spec["slug"] + ".html")
    if os.path.exists(out) and "--force" not in sys.argv:
        fail("avgrav-blog/%s.html already exists (add --force to rewrite it)" % spec["slug"])
    errors, warnings = problems(spec)
    for w in warnings:
        print("warning: " + w)
    if errors:
        fail("\n  " + "\n  ".join(errors))
    spec["title_html"] = html.escape(spec["title"], quote=False)
    spec["excerpt_html"] = html.escape(spec["excerpt"], quote=False)
    page = render(spec)
    existed = os.path.exists(out)
    write(out, page)
    if not existed:
        update_index(spec)
    else:
        refresh_row(spec)
    update_sitemap(spec)
    mark_topic(spec)
    print("wrote avgrav-blog/%s.html (%d words)" % (spec["slug"], len(plain(spec["body"]).split())))
    print("live after merge: " + BASE + spec["slug"])
    return check()


# ---------------------------------------------------------------- check

def check():
    errors = []
    rows = {r[0] for r in index_rows()}
    sitemap = read(SITEMAP)
    for name in sorted(os.listdir(BLOG)):
        if not name.endswith(".html"):
            continue
        p = os.path.join(BLOG, name)
        s = read(p)
        slug = name[:-5]
        where = "avgrav-blog/" + name
        for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', s, re.S):
            try:
                json.loads(m.group(1))
            except ValueError as e:
                errors.append("%s: structured data doesn't parse (%s)" % (where, e))
        if s.count("<div") != s.count("</div>"):
            errors.append("%s: %d <div> vs %d </div>" % (where, s.count("<div"), s.count("</div>")))
        visible = s[s.find("<title>"):s.find("</title>")] + (s[s.find("<article"):s.find("</article>")] if "<article" in s else "")
        for d in DASHES[:3]:
            if d in visible:
                errors.append("%s: em dash in the title or article" % where)
        for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', s, re.S):
            try:
                data = json.loads(m.group(1))
            except ValueError:
                continue
            if data.get("@type") == "FAQPage":
                shown = {html.unescape(x).strip() for x in re.findall(r"<summary>(.*?)</summary>", s, re.S)}
                for q in data["mainEntity"]:
                    if q["name"].strip() not in shown:
                        errors.append("%s: FAQ question isn't shown on the page: %s" % (where, q["name"]))
        canon = re.search(r'<link rel="canonical" href="([^"]+)"', s)
        want = BASE if slug == "index" else BASE + slug
        if not canon or canon.group(1) != want:
            errors.append("%s: canonical should be %s" % (where, want))
        if slug != "index":
            if slug not in rows:
                errors.append("%s: not listed in avgrav-blog/index.html" % where)
            if "<loc>%s</loc>" % (BASE + slug) not in sitemap:
                errors.append("%s: not in sitemap.xml" % where)
        for ref in re.findall(r'(?:href|src)="([^"#:]+)(?:#[^"]*)?"', s):
            target = os.path.normpath(os.path.join(BLOG, ref))
            if ref.endswith("/") or ref in (".", "./"):
                ok = os.path.exists(os.path.join(target, "index.html"))
            else:
                ok = os.path.isfile(target) or os.path.isfile(target + ".html")
            if not ok:
                errors.append("%s: broken link %s" % (where, ref))
    for e in errors:
        print("error: " + e)
    print("checked %d pages in avgrav-blog/: %s" % (len([n for n in os.listdir(BLOG) if n.endswith(".html")]),
                                                    "no problems" if not errors else "%d problem(s)" % len(errors)))
    return 1 if errors else 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--force"]
    if args == ["--check"]:
        sys.exit(check())
    if len(args) != 1:
        sys.exit(__doc__)
    sys.exit(publish(args[0]))
