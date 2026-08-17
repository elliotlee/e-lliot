GALLERY WORKFLOW
================

The Art galleries on the site are generated. Photos live in:

    assets/art/physical/     clay and other hand-made work
    assets/art/digital/      3D, posters, pixel work

After changing anything in those folders, run this from the repo root:

    python tools/build_gallery.py

Then commit. The page will not change until you run it.


WHEN TO RUN IT
--------------

Run it after you:

  - add photos to either folder
  - delete or replace photos
  - rename photos
  - edit a captions.json (title, medium, year, month, alt, ratio, order...)

You do NOT need to run it after:

  - editing the text in index.html outside the gallery markers
  - editing assets/site.css
  - anything that doesn't touch the two art folders

Running it when nothing changed is harmless. It skips photos that are already
converted, so a re-run with no changes takes a couple of seconds.


ADDING NEW PHOTOS: THE USUAL SEQUENCE
-------------------------------------

  1. Drop the photos into assets/art/physical/ or assets/art/digital/

  2. python tools/build_gallery.py --rename
     Renames files to piece_view.jpg (bear1.jpg -> bear_1.jpg). Photos of the
     SAME piece must share a name and differ only in the trailing number:

         bear_cup_a_1.jpg  \
         bear_cup_a_2.jpg   >  one tile, three thumbnails
         bear_cup_a_3.jpg  /

     Two different pieces with the same name get a letter: bear_cup_a_*,
     bear_cup_b_*. The letter marks the piece, the number marks the view.

  3. python tools/build_gallery.py --init-captions
     Adds a captions.json entry for each new piece, with a guessed title.
     Existing entries are never overwritten, so this is safe to re-run.

  4. Edit captions.json. Fix the guessed titles, and fill in year/month.

  5. python tools/build_gallery.py
     Converts the photos and rewrites the galleries in the page.

  6. git add / commit / push


ORDER OF PIECES
---------------

Newest first. Within a year, pieces with a month come first in reverse month
order, then the ones without a month. Anything with no year keeps its manual
"order" number and sits after all the dated work.

Month accepts 3, "03", "Mar" or "March". It affects order only; the caption
shows the year alone.


CAPTIONS.JSON FIELDS
--------------------

All optional. Only "title" is really worth filling in for every piece.

    "title"    shown in bold under the tile
    "medium"   shown next to it, e.g. Clay. Defaults per folder.
    "year"     e.g. "2026". Drives the ordering, shown in the caption.
    "month"    e.g. "March". Ordering only, not shown.
    "alt"      description for screen readers. Falls back to the title.
    "ratio"    "square", "tall" or "panorama" to change the crop
    "fit"      "contain" to letterbox instead of crop (for transparent PNGs)
    "pixel"    true for pixel art, keeps the pixels crisp
    "order"    manual position, used only for pieces with no year
    "views"    explicit list of filenames, if the numbering doesn't group them


WHAT IT DOES TO THE PHOTOS
--------------------------

Originals are left untouched. Web copies are written to a _web/ subfolder at
three widths, as WebP, and the page serves whichever fits the screen: a phone
pulls ~15KB per tile instead of the full file. It never upscales, so a small
original just gets fewer sizes.

EXIF is stripped in the process, which also removes the GPS coordinates phones
attach to photos.

_web/ is generated. Don't edit it. Deleting it is safe, the next run rebuilds
it. Derivatives whose original is gone get cleaned up automatically.


DON'T HAND-EDIT THE GALLERIES
-----------------------------

In index.html, everything between these markers is generated and will be
overwritten on the next run:

    <!-- GALLERY:art-physical:start -->
    <!-- GALLERY:art-physical:end -->

    <!-- GALLERY:art-digital:start -->
    <!-- GALLERY:art-digital:end -->

To change a tile, edit the photo or captions.json and re-run. Everything
outside the markers is yours and is never touched.


REQUIREMENTS
------------

Python with Pillow (already installed). Only needed if you drop iPhone .heic
files in:

    pip install pillow-heif

Without it, .heic files are skipped and the script tells you so.
