#!/usr/bin/env python3
"""Adds AvGrav's App Store screenshots to avgrav.html as a swipeable,
device-tabbed gallery (the same component as AvClock's on index.html).

Usage, from the repo root, pointing at folders of the exported App
Store screenshots (PNG or JPG, any size; they're used in file-name
order):

    python3 tools/avgrav-screenshots.py --iphone ~/Desktop/AvGrav/iPhone \\
        --ipad ~/Desktop/AvGrav/iPad --watch ~/Desktop/AvGrav/Watch

Any of the three can be left out; only devices given get a tab. Each
folder may hold a captions.txt, one line per screenshot in the same
order, used as the image's alt text (what a screen reader reads, and
what shows if an image can't load). Without it, the alt text is
"AvGrav on iPhone, screenshot 1 of 6" and so on, so write captions.txt
if you can, e.g. "Corrected API gravity at 60°F with the density row".

What it does:
  - Resizes each screenshot to the same heights AvClock's gallery uses
    (iPhone 800px, iPad 900px, Watch 514px), saves it as a JPEG to
    images/screenshots/avgrav/<device>/NN.jpg, and removes old ones.
  - Rewrites the gallery between the AVGRAV-GALLERY markers in
    avgrav.html. Running it again replaces the gallery cleanly.

Needs Pillow (pip3 install pillow) or, on a Mac without it, uses the
built-in `sips` tool instead. Then commit and push as usual.
"""
import argparse
import glob
import html
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "avgrav.html")
OUT = os.path.join(ROOT, "images", "screenshots", "avgrav")
START = "<!-- AVGRAV-GALLERY:START"
END = "<!-- AVGRAV-GALLERY:END -->"

DEVICES = [
    # key, tab label, target height, gallery class (matches style.css)
    ("iphone", "iPhone", 800, ""),
    ("ipad", "iPad", 900, ""),
    ("watch", "Apple Watch", 514, " watch"),
]


def sources(folder):
    files = []
    for ext in ("png", "jpg", "jpeg", "PNG", "JPG", "JPEG"):
        files += glob.glob(os.path.join(os.path.expanduser(folder), "*." + ext))
    return sorted(set(files))


def captions(folder, count, label):
    path = os.path.join(os.path.expanduser(folder), "captions.txt")
    lines = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
    return [
        "AvGrav " + label + ": " + lines[i] if i < len(lines)
        else "AvGrav on %s, screenshot %d of %d" % (label, i + 1, count)
        for i in range(count)
    ]


def resize(src, dst, height):
    try:
        from PIL import Image
        im = Image.open(src).convert("RGB")
        w = round(im.width * height / im.height)
        im.resize((w, height), Image.LANCZOS).save(dst, "JPEG", quality=82, optimize=True, progressive=True)
        return
    except ImportError:
        pass
    if shutil.which("sips"):
        subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "82",
                        "--resampleHeight", str(height), src, "--out", dst],
                       check=True, stdout=subprocess.DEVNULL)
        return
    sys.exit("Needs Pillow (pip3 install pillow) or macOS sips to resize images.")


def build(args):
    blocks = []
    for key, label, height, cls in DEVICES:
        folder = getattr(args, key)
        if not folder:
            continue
        files = sources(folder)
        if not files:
            sys.exit("No PNG or JPG files in %s" % folder)
        out_dir = os.path.join(OUT, key)
        os.makedirs(out_dir, exist_ok=True)
        for old in glob.glob(os.path.join(out_dir, "*.jpg")):
            os.remove(old)
        alts = captions(folder, len(files), label)
        imgs = []
        for i, src in enumerate(files, 1):
            name = "%02d.jpg" % i
            resize(src, os.path.join(out_dir, name), height)
            imgs.append('      <img src="images/screenshots/avgrav/%s/%s" alt="%s" loading="lazy" decoding="async">'
                        % (key, name, html.escape(alts[i - 1], quote=True)))
        blocks.append((key, label, cls, imgs))
        print("%s: %d screenshots" % (label, len(files)))
    if not blocks:
        sys.exit("Give at least one of --iphone, --ipad, --watch.")
    # A device left out this run loses its tab, so drop its old images.
    for key, _, _, _ in DEVICES:
        if not getattr(args, key):
            shutil.rmtree(os.path.join(OUT, key), ignore_errors=True)
    return blocks


def gallery_html(blocks):
    tabs = ""
    if len(blocks) > 1:
        tabs = '    <div class="device-tabs" role="tablist" aria-label="Choose a device">\n' + "".join(
            '      <button class="device-tab" role="tab" data-gallery-tab="%s" aria-selected="%s">%s</button>\n'
            % (key, "true" if i == 0 else "false", label)
            for i, (key, label, _, _) in enumerate(blocks)) + "    </div>\n\n"
    galleries = "".join(
        '    <div class="shot-gallery%s" data-gallery="%s"%s>\n%s\n    </div>\n\n'
        % (cls, key, " data-active" if i == 0 else "", "\n".join(imgs))
        for i, (key, _, cls, imgs) in enumerate(blocks))
    return (START + " (written by tools/avgrav-screenshots.py; rerun it, don't edit by hand) -->\n"
            '<section id="screenshots">\n'
            '  <div class="container">\n'
            '    <div class="section-head reveal">\n'
            '      <div class="section-eyebrow">Screenshots</div>\n'
            '      <h2>See it before you fuel</h2>\n'
            '      <p>Real screenshots from the App Store listing. Swipe through, or pick your device.</p>\n'
            '    </div>\n\n'
            + tabs + galleries +
            '    <p class="gallery-hint">Scroll to see more &rarr;</p>\n'
            '  </div>\n'
            '</section>\n'
            + END)


def main():
    p = argparse.ArgumentParser(description="Add AvGrav's App Store screenshots to avgrav.html.")
    p.add_argument("--iphone")
    p.add_argument("--ipad")
    p.add_argument("--watch")
    args = p.parse_args()
    blocks = build(args)
    with open(PAGE, encoding="utf-8") as f:
        page = f.read()
    a, b = page.find(START), page.find(END)
    if a == -1 or b == -1:
        sys.exit("Couldn't find the AVGRAV-GALLERY markers in avgrav.html.")
    page = page[:a] + gallery_html(blocks) + page[b + len(END):]
    with open(PAGE, "w", encoding="utf-8") as f:
        f.write(page)
    print("Updated avgrav.html. Check it locally (python3 -m http.server), then commit and push.")


if __name__ == "__main__":
    main()
