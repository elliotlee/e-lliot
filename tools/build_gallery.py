#!/usr/bin/env python3
"""
Build the sculpture galleries for e-lliot.com.

Drop photos into:
    assets/sculpture/clay/
    assets/sculpture/digital/

then run:
    python tools/build_gallery.py

For each photo it writes web-sized WebP copies into a _web/ subfolder, then
rewrites the gallery markup in index.html between the GALLERY markers.
Originals are left alone (they stay in the repo as masters).

GROUPING PHOTOS INTO PIECES
  Several angles of one sculpture group into a single tile with thumbnails.
  Either name the files with a trailing number:

      mouse-at-the-diner-1.jpg
      mouse-at-the-diner-2.jpg      -> one piece, two views

  or list them explicitly in captions.json (see below).

CAPTIONS
  Optional captions.json in each section folder. Every field is optional:

      {
        "bear_cup_a": {
          "title":  "Bear Cup",
          "medium": "Clay",
          "year":   "2025",
          "month":  "March",        3, "03" and "Mar" all work too
          "alt":    "Unglazed stoneware cup formed as a bear.",
          "views":  ["bear-front.jpg", "bear-side.jpg"]
        }
      }

  Without an entry, the title comes from the filename ("bear_cup_a" -> "Bear
  cup") and the medium falls back to the section default.

ORDER
  Pieces run newest to oldest. Within a year, the ones with a month come first
  in reverse month order, then the rest. Anything with no year at all keeps its
  manual "order" number and sits after the dated work.
"""

import json
import re
import shutil
import sys
from pathlib import Path

try:
    from PIL import Image, ImageOps, ImageSequence
except ImportError:
    sys.exit("Pillow is required:  pip install pillow")

# .heic support is optional; only needed if you drop iPhone photos in
try:
    import pillow_heif

    pillow_heif.register_heif_opener()
    HEIC_OK = True
except ImportError:
    HEIC_OK = False

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "index.html"

WIDTHS = [400, 800, 1600]
QUALITY = 82
SOURCE_TYPES = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".tif", ".tiff", ".gif"}

# One entry per drop folder. "key" matches the GALLERY:<key> markers in the
# page; "label"/"note" render the subhead above the tiles.
SECTIONS = [
    {
        "key": "art-physical",
        "folder": "assets/art/physical",
        "label": "Physical",
        # the section intro already lists the tools; a note here would repeat it
        "note": "",
        "default_medium": "Ceramic",
        "accent": "clay",
    },
    {
        "key": "art-digital",
        "folder": "assets/art/digital",
        "label": "Digital",
        "note": "",
        "default_medium": "Digital",
    },
]

# per-piece display options, set in captions.json
RATIOS = {"square": "piece--square", "tall": "piece--tall", "panorama": "piece--panorama"}

# tiles repeat 7 / 5 / 4 / 4 / 4 columns, so every five pieces fill two rows
SPANS = ["piece--wide", "piece--slim", "piece--third", "piece--third", "piece--third"]


def titleize(key):
    """bear cup (1) -> Bear cup     mouse-at-the-diner -> Mouse at the diner"""
    words = re.sub(r"\s*\(\d+\)\s*$", "", key)      # drop the (1)/(2) disambiguator
    words = re.sub(r"_[a-z]$", "", words)           # and the _a/_b variant marker
    words = re.sub(r"[-_]+", " ", words).strip()
    return words[:1].upper() + words[1:] if words else key


def piece_key(path):
    """Group the views of one piece.

    The trailing number counts up through a piece's photos, with or without a
    separator, so bear1/bear2, birdbath1..3 and 'bear cup (1)1..3' each collapse
    to one key. A (1)/(2) suffix stays in the key: those are different pieces
    that happen to share a name.
    """
    return re.sub(r"[\s_-]*\d+$", "", path.stem).strip()


MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def parse_month(value):
    """Accept 3, '03', 'March' or 'mar'. Returns 1-12, or None if unset."""
    text = str(value).strip().lower()
    if not text:
        return None
    if text.isdigit():
        n = int(text)
        return n if 1 <= n <= 12 else None
    return MONTHS.get(text[:3])


def view_order(path):
    """Sort views numerically so view 10 follows view 9, not view 1."""
    m = re.search(r"(\d+)$", path.stem)
    return (int(m.group(1)) if m else 0, path.name)


def optimize_animation(src, out_dir):
    """An animated source (a GIF turntable, say) becomes one animated WebP plus
    a static thumbnail taken from its first frame.

    No srcset here: every entry in a srcset must be the same image, and a still
    is not the same image as an animation. Serving the still to small screens
    would silently kill the animation on phones.
    """
    out = out_dir / f"{src.stem}.webp"
    thumb = out_dir / f"{src.stem}-thumb.webp"
    info = {"animated": True, "thumb": thumb.name}

    if out.exists() and out.stat().st_mtime >= src.stat().st_mtime:
        return [(0, out.name)], False, info

    # an animated WebP source is already in the delivery format: copy it rather
    # than re-encoding, which would be a second lossy pass for no gain
    if src.suffix.lower() == ".webp":
        shutil.copyfile(src, out)
        with Image.open(src) as im:
            poster = next(ImageSequence.Iterator(im)).convert("RGB")
            poster.thumbnail((WIDTHS[0], WIDTHS[0] * 4), Image.LANCZOS)
            poster.save(thumb, "WEBP", quality=QUALITY, method=6)
        return [(0, out.name)], True, info

    with Image.open(src) as im:
        frames, durations = [], []
        for frame in ImageSequence.Iterator(im):
            copy = frame.convert("RGB")
            if copy.width > max(WIDTHS):
                copy.thumbnail((max(WIDTHS), max(WIDTHS) * 4), Image.LANCZOS)
            frames.append(copy)
            durations.append(frame.info.get("duration", 100))

        frames[0].save(
            out, "WEBP", save_all=True, append_images=frames[1:],
            duration=durations, loop=0, quality=QUALITY, method=6,
        )
        poster = frames[0].copy()
        poster.thumbnail((WIDTHS[0], WIDTHS[0] * 4), Image.LANCZOS)
        poster.save(thumb, "WEBP", quality=QUALITY, method=6)

    return [(0, out.name)], True, info


def optimize(src, out_dir):
    """Write WebP copies at each width. Returns [(width, filename), ...]."""
    out_dir.mkdir(exist_ok=True)
    made = []
    built_any = False

    with Image.open(src) as probe:
        if getattr(probe, "n_frames", 1) > 1:
            return optimize_animation(src, out_dir)

    with Image.open(src) as im:
        # honour the camera's rotation flag, then drop EXIF (it carries GPS)
        im = ImageOps.exif_transpose(im)
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGB")

        # never upscale, and cap the largest tier at the source's own width, so
        # the width in the filename is always the real width of the file. a
        # srcset descriptor that overstates a width makes the browser pick wrong.
        targets = sorted({w for w in WIDTHS if w < im.width} | {min(im.width, max(WIDTHS))})

        for w in targets:
            out = out_dir / f"{src.stem}-{w}.webp"
            made.append((w, out.name))

            # skip work when the derivative is already newer than the original
            if out.exists() and out.stat().st_mtime >= src.stat().st_mtime:
                continue

            copy = im.copy()
            if copy.width > w:
                copy.thumbnail((w, w * 4), Image.LANCZOS)
            copy.save(out, "WEBP", quality=QUALITY, method=6)
            built_any = True

    return made, built_any, {"animated": False, "thumb": ""}


def collect(section):
    """Group a section folder's photos into pieces, applying captions.json."""
    folder = ROOT / section["folder"]
    if not folder.is_dir():
        return [], []

    captions = {}
    cap_file = folder / "captions.json"
    if cap_file.exists():
        captions = json.loads(cap_file.read_text(encoding="utf-8"))

    photos = sorted(
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in SOURCE_TYPES
    )

    skipped = [p for p in photos if p.suffix.lower() in (".heic", ".heif") and not HEIC_OK]
    photos = [p for p in photos if p not in skipped]

    # explicit "views" lists win; everything else groups by filename
    claimed, pieces = set(), {}
    for key, meta in captions.items():
        views = [folder / v for v in meta.get("views", [])]
        views = [v for v in views if v.exists()]
        if views:
            pieces[key] = views
            claimed.update(views)

    for p in photos:
        if p in claimed:
            continue
        pieces.setdefault(piece_key(p), []).append(p)

    ordered = []
    for key, views in pieces.items():
        meta = captions.get(key, {})
        ordered.append({
            "key": key,
            "views": sorted(views, key=view_order),
            "title": meta.get("title", titleize(key)),
            "medium": meta.get("medium", section["default_medium"]),
            "alt": meta.get("alt", ""),
            # display options: "ratio": square|tall|panorama, "fit": "contain",
            # "pixel": true for pixel art, "order": sorts the tile
            "ratio": meta.get("ratio", ""),
            "fit": meta.get("fit", ""),
            "pixel": bool(meta.get("pixel", False)),
            "order": meta.get("order", 999),
            "year": meta.get("year", ""),
            "month": meta.get("month", ""),
        })

    def sort_key(p):
        # reverse chronological: newest first. within a year, pieces with a
        # month are ordered newest month first and sit ahead of the ones with no
        # month. pieces with no year at all keep their manual "order" and trail
        # the dated work, so filling dates in gradually still looks deliberate.
        year = int(p["year"]) if str(p["year"]).strip().isdigit() else None
        month = parse_month(p["month"]) if year else None
        return (
            0 if year else 1,
            -(year or 0),
            0 if month else 1,
            -(month or 0),
            p["order"],
            p["title"].lower(),
        )

    ordered.sort(key=sort_key)
    return ordered, skipped


def srcset(rel, sizes):
    return ", ".join(f"{rel}/{name} {w}w" for w, name in sizes)


def render(section, pieces):
    """Build the subhead + gallery markup for one section.

    The subhead is generated too, so an empty folder produces nothing at all
    rather than a heading over a blank space.
    """
    if not pieces:
        return "\t\t\t<!-- no photos in {} yet -->".format(section["folder"])

    rel = f'{section["folder"]}/_web'
    # tiles are ~1/3 of a 1200px column on desktop, full width on a phone
    sizes_attr = "(max-width: 720px) 92vw, (max-width: 1100px) 45vw, 30vw"
    out = []

    for i, piece in enumerate(pieces):
        span = SPANS[i % len(SPANS)]
        multi = len(piece["built"]) > 1
        mods = [span]
        if piece["ratio"] in RATIOS:
            mods.append(RATIOS[piece["ratio"]])
        if piece["fit"] == "contain":
            mods.append("piece--contain")
        if multi:
            mods.append("views")
        classes = "piece " + " ".join(mods) + " reveal"
        alt = piece["alt"] or piece["title"]

        # the frame is a <button>: the tiles open a lightbox, so they must be
        # reachable by keyboard, not just clickable with a mouse
        block = [
            f'\t\t\t\t<figure class="{classes}">',
            '\t\t\t\t\t<button type="button" class="piece__frame"'
            f' aria-label="View {piece["title"]} full size">',
        ]

        for j, (name, sizes, info) in enumerate(piece["built"]):
            first = j == 0
            css = " ".join(
                (["is-on"] if multi and first else []) + (["px"] if piece["pixel"] else [])
            )
            # only the first view describes the object; the rest are the same
            # thing from another angle
            alt_attr = alt.replace('"', "&quot;") if first else ""

            if info["animated"]:
                block.append(
                    '\t\t\t\t\t\t<img{on} src="{rel}/{file}" data-full="{rel}/{file}"'
                    ' alt="{alt}" loading="lazy" decoding="async">'.format(
                        on=f' class="{css}"' if css else "",
                        rel=rel, file=sizes[0][1], alt=alt_attr,
                    )
                )
            else:
                block.append(
                    '\t\t\t\t\t\t<img{on} src="{rel}/{fallback}" srcset="{srcset}" sizes="{sizes_attr}"'
                    ' data-full="{rel}/{full}" alt="{alt}" loading="lazy" decoding="async">'.format(
                        on=f' class="{css}"' if css else "",
                        rel=rel,
                        fallback=sizes[-1][1],
                        full=sizes[-1][1],
                        srcset=srcset(rel, sizes),
                        sizes_attr=sizes_attr,
                        alt=alt_attr,
                    )
                )

        block.append("\t\t\t\t\t</button>")

        if multi:
            block.append(
                f'\t\t\t\t\t<div class="views__thumbs" role="group" aria-label="Views of {piece["title"]}">'
            )
            for j, (name, sizes, info) in enumerate(piece["built"]):
                # an animation gets a still poster for its thumbnail: 47 frames
                # looping inside a 60px button is noise, not information
                block.append(
                    '\t\t\t\t\t\t<button type="button" class="views__thumb{on}" aria-label="View {n}"'
                    ' style="background-image: url(\'{rel}/{thumb}\')"></button>'.format(
                        on=" is-on" if j == 0 else "",
                        n=j + 1,
                        rel=rel,
                        thumb=info["thumb"] or sizes[0][1],
                    )
                )
            block.append("\t\t\t\t\t</div>")

        meta_line = ", ".join(x for x in (piece["medium"], str(piece["year"]).strip()) if x)
        block.append(
            f'\t\t\t\t\t<figcaption><b>{piece["title"]}</b> <i>{meta_line}</i></figcaption>'
        )
        block.append("\t\t\t\t</figure>")
        out.append("\n".join(block))

    accent = " subhead--clay" if section.get("accent") == "clay" else ""
    note = (
        f'\n\t\t\t\t<span class="subhead__note">{section["note"]}</span>'
        if section.get("note") else ""
    )
    head = (
        f'\t\t\t<div class="subhead{accent} reveal">\n'
        f'\t\t\t\t<span class="subhead__label">{section["label"]}</span>{note}\n'
        f"\t\t\t</div>\n\n"
        f'\t\t\t<div class="gallery gallery--auto">\n'
    )
    return head + "\n\n".join(out) + "\n\t\t\t</div>"


def splice(html, key, markup):
    """Replace whatever sits between the section's markers."""
    start, end = f"<!-- GALLERY:{key}:start -->", f"<!-- GALLERY:{key}:end -->"
    pattern = re.compile(
        re.escape(start) + r".*?" + re.escape(end), re.DOTALL
    )
    if not pattern.search(html):
        sys.exit(f"markers for '{key}' not found in {PAGE.name}")
    return pattern.sub(f"{start}\n{markup}\n\t\t\t{end}", html)


def slugify(text):
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", text.lower())).strip("_")


def normalize_names():
    """Rename dropped photos to <piece>_<view>.<ext>.

        bear1.jpg            -> bear_1.jpg
        horse cup 2.jpg      -> horse_cup_2.jpg
        bear cup (1)3.jpg    -> bear_cup_a_3.jpg     two different cups, so the
        bear cup (2)1.jpg    -> bear_cup_b_1.jpg     variant becomes a letter

    captions.json keys are updated to match. Safe to re-run: already-correct
    names are left alone.
    """
    for section in SECTIONS:
        folder = ROOT / section["folder"]
        if not folder.is_dir():
            continue

        groups = {}
        for p in sorted(folder.iterdir()):
            if p.is_file() and p.suffix.lower() in SOURCE_TYPES:
                groups.setdefault(piece_key(p), []).append(p)

        renames, key_map = [], {}
        for key, views in sorted(groups.items()):
            variant = re.match(r"^(.*?)\s*\((\d+)\)\s*$", key)
            if variant:
                slug = f"{slugify(variant.group(1))}_{chr(ord('a') + int(variant.group(2)) - 1)}"
            else:
                slug = slugify(key)
            key_map[key] = slug

            for i, src in enumerate(sorted(views, key=view_order), start=1):
                dst = folder / f"{slug}_{i}{src.suffix.lower()}"
                if src != dst:
                    renames.append((src, dst))

        # two-step through temp names so a rename can never clobber a file that
        # is itself waiting to be renamed
        for i, (src, dst) in enumerate(renames):
            src.rename(folder / f"__tmp{i}__{src.suffix.lower()}")
        for i, (src, dst) in enumerate(renames):
            (folder / f"__tmp{i}__{src.suffix.lower()}").rename(dst)
            print(f"      {src.name}  ->  {dst.name}")

        cap_file = folder / "captions.json"
        if cap_file.exists():
            captions = json.loads(cap_file.read_text(encoding="utf-8"))
            moved = {key_map.get(k, k): v for k, v in captions.items()}
            if moved != captions:
                cap_file.write_text(
                    json.dumps(moved, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
                )

        print(f"  {section['folder']}: {len(groups)} pieces, {len(renames)} renamed")


def init_captions():
    """Add a captions.json entry for every piece that doesn't have one yet.

    Existing entries are never touched, so this is safe to re-run after adding
    photos. Entries whose files have disappeared are reported, not deleted.
    """
    for section in SECTIONS:
        folder = ROOT / section["folder"]
        if not folder.is_dir():
            continue

        cap_file = folder / "captions.json"
        captions = json.loads(cap_file.read_text(encoding="utf-8")) if cap_file.exists() else {}

        groups = {}
        for p in sorted(folder.iterdir()):
            if p.is_file() and p.suffix.lower() in SOURCE_TYPES:
                groups.setdefault(piece_key(p), []).append(p)

        added = []
        for key, views in sorted(groups.items()):
            if key in captions:
                continue
            captions[key] = {
                "title": titleize(key),
                "medium": section["default_medium"],
                "year": "",
                "month": "",
                "alt": "",
            }
            added.append(f"{key} ({len(views)} view{'s' if len(views) > 1 else ''})")

        stale = [k for k, v in captions.items() if k not in groups and not v.get("views")]

        cap_file.write_text(
            json.dumps(captions, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"  {section['folder']}: {len(groups)} pieces, {len(added)} new entries")
        for a in added:
            print(f"      + {a}")
        for s in stale:
            print(f"      ? '{s}' has no matching files (left in place)")


def main():
    if "--rename" in sys.argv:
        normalize_names()
        print("\nNames normalized. Run --init-captions next to scaffold titles.")
        return

    if "--init-captions" in sys.argv:
        init_captions()
        print("\nEdit the titles, then run again without --init-captions.")
        return

    html = PAGE.read_text(encoding="utf-8")
    total_new = 0

    for section in SECTIONS:
        pieces, skipped = collect(section)

        for piece in pieces:
            piece["built"] = []
            for view in piece["views"]:
                sizes, built, info = optimize(view, view.parent / "_web")
                piece["built"].append((view.name, sizes, info))
                total_new += 1 if built else 0

        # drop derivatives whose original has been deleted or renamed
        web = ROOT / section["folder"] / "_web"
        if web.is_dir():
            keep = {
                name
                for piece in pieces
                for _, sizes, _ in piece["built"]
                for _, name in sizes
            } | {
                info["thumb"]
                for piece in pieces
                for _, _, info in piece["built"]
                if info["thumb"]
            }
            for old in web.glob("*.webp"):
                if old.name not in keep:
                    old.unlink()
                    print(f"      - removed stale {old.name}")

        html = splice(html, section["key"], render(section, pieces))

        views = sum(len(p["built"]) for p in pieces)
        print(f"  {section['key']}: {len(pieces)} pieces, {views} views")
        if not pieces:
            print(f"    (drop photos into {section['folder']}/)")
        for s in skipped:
            print(f"    ! skipped {s.name} (run: pip install pillow-heif)")

    PAGE.write_text(html, encoding="utf-8")
    print(f"optimized {total_new} photos" if total_new else "no new photos to optimize")
    print(f"rewrote {PAGE.name}")


if __name__ == "__main__":
    main()
