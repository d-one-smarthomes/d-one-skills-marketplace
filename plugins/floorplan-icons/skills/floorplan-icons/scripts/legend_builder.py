"""Editable-legend assembly for the floorplan-icons skill.

The legend is built from three kinds of object so the user can edit it in Preview:
  - a FRAME image  (panel, header bar, D-One logo, title, footer, row stripes) —
    placed as one movable Stamp annotation. This is chrome; it's not meant to be edited.
  - one ICON Stamp annotation per entry — copy/paste-able, exactly like floorplan icons.
  - one FreeText annotation per entry label — the text is editable in Preview.

Public API:
  make_legend_frame(entries, brand_blue, logo_path, font_dir) -> (frame_path, meta)
  place_legend(page, doc, entries, x, y, display_w, icon_xref, frame_xref, meta,
               add_image_stamp) -> None
"""
import os
from PIL import Image, ImageDraw, ImageFont

# Layout constants for the frame, in frame-pixel space
FRAME_W      = 1654
HEADER_H     = 210
FOOTER_H     = 80
ROW_H        = 190
COLS         = 2
SIDE_PAD     = 50


def _font(font_dir, bold=False, size=40):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(os.path.join(font_dir, name), size)
    except Exception:
        return ImageFont.load_default()


def make_legend_frame(entries, brand_blue, logo_path, font_dir,
                      title="Floorplan Component Legend",
                      subtitle="Standard symbols for D-One project drawings",
                      footer="D-One Electronics  |  Brand colour #1379C9"):
    """Render the legend frame (chrome only — no entry icons or labels).
    Returns (frame_png_path, meta) where meta carries the geometry the placement
    step needs to drop icons + labels into the right cells."""
    rows = (len(entries) + COLS - 1) // COLS
    frame_h = HEADER_H + rows * ROW_H + FOOTER_H

    frame = Image.new("RGBA", (FRAME_W, frame_h), (255, 255, 255, 255))
    d = ImageDraw.Draw(frame)
    blue = brand_blue + (255,)

    # header band + divider
    d.rectangle([0, 0, FRAME_W, HEADER_H], fill=(235, 244, 251, 255))
    d.line([0, HEADER_H, FRAME_W, HEADER_H], fill=blue, width=5)

    # D-One logo, top-left of the header
    if logo_path and os.path.exists(logo_path):
        logo = Image.open(logo_path).convert("RGBA")
        logo_h = 90
        logo_w = int(logo.width * (logo_h / logo.height))
        logo = logo.resize((logo_w, logo_h), Image.LANCZOS)
        frame.alpha_composite(logo, (SIDE_PAD, 28))
        title_x = SIDE_PAD + logo_w + 40
    else:
        title_x = SIDE_PAD

    d.text((title_x, 40), title, fill=blue, font=_font(font_dir, bold=True, size=58))
    d.text((title_x + 2, 118), subtitle, fill=(90, 90, 90, 255),
           font=_font(font_dir, bold=False, size=30))

    # alternating row stripes
    for r in range(rows):
        y0 = HEADER_H + r * ROW_H
        if r % 2 == 1:
            d.rectangle([0, y0, FRAME_W, y0 + ROW_H], fill=(245, 247, 249, 255))

    # footer
    fy = frame_h - FOOTER_H
    d.line([0, fy, FRAME_W, fy], fill=(210, 210, 210, 255), width=2)
    d.text((SIDE_PAD, fy + 24), footer, fill=(140, 140, 140, 255),
           font=_font(font_dir, bold=False, size=26))

    frame_path = "/tmp/_legend_frame.png"
    frame.save(frame_path)
    meta = {"frame_w": FRAME_W, "frame_h": frame_h, "rows": rows,
            "header_h": HEADER_H, "row_h": ROW_H, "footer_h": FOOTER_H,
            "cols": COLS, "side_pad": SIDE_PAD}
    return frame_path, meta


def place_legend(page, doc, entries, x, y, display_w,
                 icon_xref, frame_xref, meta, add_image_stamp):
    """Place the legend onto `page`: frame stamp + per-entry icon stamps + FreeText
    labels. `icon_xref` maps icon_key -> image xref. `frame_xref` is the frame image
    xref. `add_image_stamp(page, doc, img_xref, rect, native_w, native_h)` is the
    shared stamp helper from the skill's Step 6."""
    import fitz
    scale = display_w / meta["frame_w"]
    display_h = meta["frame_h"] * scale

    # 1. frame as a movable stamp
    add_image_stamp(page, doc, frame_xref,
                    fitz.Rect(x, y, x + display_w, y + display_h),
                    meta["frame_w"], meta["frame_h"])

    # 2. icons + labels into the grid cells
    col_w = display_w / meta["cols"]
    row_h_disp = meta["row_h"] * scale
    icon_disp = row_h_disp * 0.58
    label_fs = max(9, int(row_h_disp * 0.16))

    for i, (icon_key, label) in enumerate(entries):
        col, row = i % meta["cols"], i // meta["cols"]
        cell_x = x + col * col_w
        cell_cy = y + (meta["header_h"] * scale) + (row + 0.5) * row_h_disp
        # icon stamp, vertically centred in the row
        ix = cell_x + meta["side_pad"] * scale
        iy = cell_cy - icon_disp / 2
        add_image_stamp(page, doc, icon_xref[icon_key],
                        fitz.Rect(ix, iy, ix + icon_disp, iy + icon_disp), 256, 256)
        # label as an editable FreeText annotation, centred on the row
        tx = ix + icon_disp + 18
        trect = fitz.Rect(tx, cell_cy - label_fs, cell_x + col_w - 8, cell_cy + label_fs)
        page.add_freetext_annot(trect, label, fontsize=label_fs, fontname="helv",
                                text_color=(0.1, 0.1, 0.1), fill_color=None, align=0)
