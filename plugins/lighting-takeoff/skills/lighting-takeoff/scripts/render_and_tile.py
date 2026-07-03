#!/usr/bin/env python3
"""
render_and_tile.py — prepare a lighting-layout PDF for visual symbol counting.

Lighting plans are usually exported as one big flat raster image with NO text or
vector layer, so symbols can only be counted by *looking*. A single full-page
render is too dense to count accurately in one glance, so this script slices the
plan into a grid of legible, slightly-overlapping tiles. Each tile is drawn with
a red "count zone" rectangle marking its non-overlapping core; when counting you
only tally a symbol if its CENTRE sits inside that rectangle. That rule lets the
tiles overlap (so no symbol is ever sliced in half and lost) while guaranteeing
each symbol is counted in exactly one tile.

Usage:
    python render_and_tile.py INPUT.pdf OUTDIR [--floor "Living Level"]
                              [--target-px 1500] [--dpi 200] [--overlap 0.10]

INPUT may be a .pdf (single page) or an image (.png/.jpg).
Outputs into OUTDIR/<floor-slug>/:
    native.png          full-resolution plan
    overview.png        downscaled whole plan with the tile grid drawn on top
    tiles/r{R}_c{C}.png  one image per grid cell (with count-zone rectangle)
    manifest.json       grid + tile metadata
"""
import argparse, json, os, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
Image.MAX_IMAGE_PIXELS = None


def slugify(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-') or 'floor'


def render_to_png(inp, workdir):
    """Return path to a full-res PNG of the plan."""
    ext = os.path.splitext(inp)[1].lower()
    if ext in ('.png', '.jpg', '.jpeg', '.tif', '.tiff'):
        im = Image.open(inp).convert('RGB')
        out = os.path.join(workdir, 'native.png')
        im.save(out)
        return out
    # PDF: first try to pull the embedded raster at native resolution (sharpest),
    # fall back to rasterising the page at high DPI.
    tmp = os.path.join(workdir, '_img')
    subprocess.run(['pdfimages', '-png', inp, tmp],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    imgs = sorted(p for p in os.listdir(workdir) if p.startswith('_img'))
    best = None
    for p in imgs:
        fp = os.path.join(workdir, p)
        try:
            w, h = Image.open(fp).size
        except Exception:
            continue
        if best is None or w * h > best[1]:
            best = (fp, w * h)
    out = os.path.join(workdir, 'native.png')
    if best and best[1] > 1_000_000:        # a real plan-sized image was embedded
        Image.open(best[0]).convert('RGB').save(out)
    else:                                    # rasterise the page instead
        dpi = ARGS.dpi
        subprocess.run(['pdftoppm', '-png', '-r', str(dpi), '-singlefile', inp,
                        os.path.join(workdir, 'native')],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        Image.open(out).convert('RGB').save(out)
    for p in imgs:                           # tidy up the pdfimages scratch files
        try: os.remove(os.path.join(workdir, p))
        except OSError: pass
    return out


def grid_dims(w, h, target):
    cols = max(1, round(w / target))
    rows = max(1, round(h / target))
    return rows, cols


def main():
    global ARGS
    ap = argparse.ArgumentParser()
    ap.add_argument('input')
    ap.add_argument('outdir')
    ap.add_argument('--floor', default=None, help='Floor name (default: from filename)')
    ap.add_argument('--target-px', type=int, default=1500,
                    help='Approx tile size in px; smaller = more tiles, easier counting')
    ap.add_argument('--dpi', type=int, default=200, help='Fallback rasterisation DPI')
    ap.add_argument('--overlap', type=float, default=0.10,
                    help='Fractional overlap between tiles (0.10 = 10%%)')
    ARGS = ap.parse_args()

    floor = ARGS.floor or os.path.splitext(os.path.basename(ARGS.input))[0]
    slug = slugify(floor)
    workdir = os.path.join(ARGS.outdir, slug)
    tiles_dir = os.path.join(workdir, 'tiles')
    os.makedirs(tiles_dir, exist_ok=True)

    native = render_to_png(ARGS.input, workdir)
    im = Image.open(native).convert('RGB')
    W, H = im.size
    rows, cols = grid_dims(W, H, ARGS.target_px)
    cw, ch = W / cols, H / rows
    ox, oy = cw * ARGS.overlap, ch * ARGS.overlap

    manifest = {'floor': floor, 'floor_slug': slug, 'source': os.path.abspath(ARGS.input),
                'image_size': [W, H], 'grid': {'rows': rows, 'cols': cols}, 'tiles': []}

    for r in range(rows):
        for c in range(cols):
            # core = the cell this tile is responsible for counting
            cx0, cy0 = int(c * cw), int(r * ch)
            cx1, cy1 = int((c + 1) * cw), int((r + 1) * ch)
            # full crop adds overlap padding so border symbols stay whole
            fx0, fy0 = max(0, int(cx0 - ox)), max(0, int(cy0 - oy))
            fx1, fy1 = min(W, int(cx1 + ox)), min(H, int(cy1 + oy))
            tile = im.crop((fx0, fy0, fx1, fy1)).copy()
            d = ImageDraw.Draw(tile)
            # draw the count-zone rectangle (core box, in tile-local coords)
            rect = (cx0 - fx0, cy0 - fy0, cx1 - fx0 - 1, cy1 - fy0 - 1)
            d.rectangle(rect, outline=(220, 0, 0), width=4)
            name = f'r{r}_c{c}'
            d.text((rect[0] + 8, rect[1] + 8), name, fill=(220, 0, 0))
            path = os.path.join(tiles_dir, name + '.png')
            tile.save(path)
            manifest['tiles'].append({
                'name': name, 'row': r, 'col': c,
                'path': os.path.relpath(path, workdir),
                'core_box': [cx0, cy0, cx1, cy1],
                'full_box': [fx0, fy0, fx1, fy1]})

    # overview with grid drawn on
    scale = 2000 / max(W, H)
    ov = im.resize((int(W * scale), int(H * scale)))
    d = ImageDraw.Draw(ov)
    for r in range(rows):
        for c in range(cols):
            box = (int(c * cw * scale), int(r * ch * scale),
                   int((c + 1) * cw * scale), int((r + 1) * ch * scale))
            d.rectangle(box, outline=(220, 0, 0), width=2)
            d.text((box[0] + 5, box[1] + 5), f'r{r}_c{c}', fill=(220, 0, 0))
    ov.save(os.path.join(workdir, 'overview.png'))

    with open(os.path.join(workdir, 'manifest.json'), 'w') as f:
        json.dump(manifest, f, indent=2)

    print(json.dumps({'floor': floor, 'workdir': workdir,
                      'image_size': [W, H], 'grid': [rows, cols],
                      'tiles': len(manifest['tiles'])}, indent=2))


if __name__ == '__main__':
    main()
