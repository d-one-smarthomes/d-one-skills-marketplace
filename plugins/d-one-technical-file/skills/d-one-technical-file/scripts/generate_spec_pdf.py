#!/usr/bin/env python3
"""
D-One Component & Equipment Schedule Generator
Usage: python generate_spec_pdf.py project_data.json product_research.json output.pdf
"""

import sys
import json
import base64
import os
from pathlib import Path

# ── System category colours ───────────────────────────────────────────────────
CATEGORY_COLOURS = {
    "WiFi & Network":               "#1565C0",
    "Video Distribution":           "#7B1FA2",
    "Intercom & Access Control":    "#B71C1C",
    "Video Conferencing":           "#00838F",
    "Headend & Rack Cabinets":      "#37474F",
    "Multiroom Audio":              "#2E7D32",
    "Dolby Atmos Surround Sound":   "#E65100",
    "Lighting Control":             "#F57F17",
    "Security & Surveillance":      "#6A1B9A",
}


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_image_data_uri(product_key, research):
    """Return a base64 data URI for the product photo, or None if unavailable.

    Prioritises photo_b64 (pre-fetched by Claude during research phase),
    then falls back to photo_local (a local file path), then gives up.
    The script never attempts live HTTP downloads — those are blocked in the sandbox.
    """
    info = research.get("products", {}).get(product_key, {})

    # 1. Pre-fetched base64 from research phase (preferred)
    b64 = info.get("photo_b64")
    if b64 and b64.startswith("data:"):
        return b64

    # 2. Local file path
    local = info.get("photo_local")
    if local and Path(local).exists():
        data = Path(local).read_bytes()
        mime = "image/jpeg"
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            mime = "image/png"
        elif data[:4] == b"RIFF":
            mime = "image/webp"
        return f"data:{mime};base64,{base64.b64encode(data).decode()}"

    return None


def badge(category):
    colour = CATEGORY_COLOURS.get(category, "#607D8B")
    return (f'<span class="badge" style="background:{colour}">'
            f'{category}</span>')


def photo_cell(product_key, research, _cache_dir=None):
    data_uri = get_image_data_uri(product_key, research)
    if data_uri:
        return f'<img src="{data_uri}" alt="">'
    # Placeholder — show abbreviated model name in grey box
    words = [w for w in product_key.replace("(", "").replace(")", "").split() if len(w) > 1]
    short = " ".join(words[:3]) if words else product_key[:15]
    return f'<div class="photo-placeholder">{short}</div>'


def dimensions_cell(product_key, research):
    info = research.get("products", {}).get(product_key, {})
    dim = info.get("dimensions", "—")
    return f'<span class="dim">{dim}</span>'


def get_categories_present(floors):
    cats = set()
    for floor in floors:
        for room in floor.get("rooms", []):
            for item in room.get("items", []):
                c = item.get("system_category", "")
                if c:
                    cats.add(c)
    return sorted(cats, key=lambda x: list(CATEGORY_COLOURS.keys()).index(x)
                  if x in CATEGORY_COLOURS else 99)


def build_html(project_data, research, cache_dir):
    proj = project_data["project"]
    floors = project_data.get("floors", [])
    categories = get_categories_present(floors)

    # ── Category tabs ─────────────────────────────────────────────────────────
    tab_html = ""
    for cat in categories:
        colour = CATEGORY_COLOURS.get(cat, "#607D8B")
        tab_html += (f'<span class="cat-tab" style="background:{colour}">'
                     f'{cat}</span>\n')

    # ── Table rows ────────────────────────────────────────────────────────────
    rows_html = ""
    for floor in floors:
        for room in floor.get("rooms", []):
            room_label = room.get("full_name", room.get("name", ""))
            rows_html += f"""
<tr class="room-header">
  <td colspan="5">&#9632; {room_label}</td>
</tr>"""
            for item in room.get("items", []):
                desc = item.get("description", "")
                qty = item.get("qty", 1)
                sys_cat = item.get("system_category", "")
                prov = " <em>(Prov)</em>" if item.get("is_provisional") else ""
                photo_html = photo_cell(desc, research, cache_dir)
                dim_html = dimensions_cell(desc, research)
                badge_html = badge(sys_cat)
                rows_html += f"""
<tr class="item-row">
  <td class="photo-cell">{photo_html}</td>
  <td class="desc-cell">{desc}{prov}</td>
  <td class="qty-cell">{qty}</td>
  <td class="dim-cell">{dim_html}</td>
  <td class="sys-cell">{badge_html}</td>
</tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  @page {{ size: A4 portrait; margin: 15mm; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: Arial, Helvetica, sans-serif; font-size: 13px;
         color: #212121; margin: 0; }}

  /* ── Page header ── */
  .page-header {{
    display: flex; justify-content: space-between; align-items: center;
    border-bottom: 1px solid #CFD8DC; padding-bottom: 6px; margin-bottom: 10px;
    font-size: 12px;
  }}
  .page-header .left {{ font-weight: bold; color: #1C2B4A; }}
  .page-header .right {{ color: #546E7A; }}

  /* ── Cover banner ── */
  .cover-banner {{
    background: #1C2B4A; color: white; border-radius: 4px;
    padding: 18px 20px; display: flex; justify-content: space-between;
    align-items: center; margin-bottom: 16px;
  }}
  .cover-banner h1 {{ margin: 0; font-size: 26px; font-weight: bold; }}
  .cover-banner .meta {{ text-align: right; font-size: 12px; line-height: 1.8; }}

  /* ── Category tabs ── */
  .cat-tabs {{ display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 16px; }}
  .cat-tab {{
    color: white; font-weight: bold; font-size: 11px;
    padding: 5px 10px; border-radius: 4px; white-space: nowrap;
  }}

  /* ── Table ── */
  table {{ width: 100%; border-collapse: collapse; }}
  th {{
    background: #37474F; color: white; font-weight: bold;
    padding: 8px 10px; font-size: 12px; text-align: left;
  }}
  th.center {{ text-align: center; }}
  th.right {{ text-align: right; }}

  tr.room-header td {{
    background: #1C2B4A; color: white; font-weight: bold;
    font-size: 13px; padding: 9px 12px;
  }}
  tr.item-row td {{ padding: 8px 10px; border-bottom: 1px solid #ECEFF1;
                   vertical-align: middle; }}
  tr.item-row:nth-child(even) td {{ background: #F9F9F9; }}

  .photo-cell {{ width: 110px; text-align: center; }}
  .photo-cell img {{ max-width: 100px; max-height: 80px; object-fit: contain; }}
  .photo-placeholder {{
    width: 80px; height: 65px; background: #ECEFF1; border-radius: 4px;
    display: inline-flex; align-items: center; justify-content: center;
    color: #90A4AE; font-size: 11px; text-align: center; margin: auto;
  }}
  .qty-cell {{ width: 55px; text-align: center; font-weight: bold; }}
  .dim-cell {{ width: 210px; }}
  .dim {{ font-family: "Courier New", monospace; font-size: 11px; color: #546E7A; }}
  .sys-cell {{ width: 175px; text-align: center; }}
  .badge {{
    display: inline-block; color: white; font-weight: bold;
    font-size: 11px; padding: 4px 10px; border-radius: 4px;
    white-space: nowrap;
  }}

  /* ── Footer ── */
  .footer {{
    margin-top: 16px; padding-top: 6px; border-top: 1px solid #CFD8DC;
    font-size: 10px; color: #546E7A;
    display: flex; justify-content: space-between;
  }}
  .sla-note {{
    font-style: italic; color: #1565C0; font-size: 11px; margin-top: 20px;
  }}
</style>
</head>
<body>

<!-- Page header (repeated on every page via CSS @page in WeasyPrint) -->
<div class="page-header">
  <span class="left">{proj.get('name', '')} &nbsp;|&nbsp; Component &amp; Equipment Schedule</span>
  <span class="right">d&middot;one &nbsp;|&nbsp; darren@d-one.co.za &nbsp;|&nbsp; 021 012 5112</span>
</div>

<!-- Cover banner -->
<div class="cover-banner">
  <h1>Component &amp; Equipment Schedule</h1>
  <div class="meta">
    {proj.get('name', '')}<br>
    Quote Ref: {proj.get('quote_ref', '')}<br>
    Prepared by {proj.get('prepared_by', '')} | D-One
  </div>
</div>

<!-- System category tabs -->
<div class="cat-tabs">
{tab_html}
</div>

<!-- Main table -->
<table>
  <thead>
    <tr>
      <th class="center">Photo</th>
      <th>Component Description</th>
      <th class="center">Qty</th>
      <th>Dimensions (W x H x D)</th>
      <th class="right">System</th>
    </tr>
  </thead>
  <tbody>
    {rows_html}
  </tbody>
</table>

<p class="sla-note">12 Months Free Remote &amp; Onsite Support included with all installed works.
A paid SLA is available after the initial 12-month period.</p>

<div class="footer">
  <span>{proj.get('client', '')} &nbsp;|&nbsp; Quote Ref: {proj.get('quote_ref', '')}
  &nbsp;|&nbsp; Prepared: {proj.get('date', '')}
  &nbsp;|&nbsp; Valid to: {proj.get('valid_to', '')}</span>
</div>

</body>
</html>"""
    return html


def main():
    if len(sys.argv) < 4:
        print("Usage: generate_spec_pdf.py project_data.json product_research.json output.pdf")
        sys.exit(1)

    project_path, research_path, output_path = sys.argv[1], sys.argv[2], sys.argv[3]
    project_data = load_json(project_path)
    research = load_json(research_path) if Path(research_path).exists() else {"products": {}}

    print("Building HTML…")
    html = build_html(project_data, research, None)

    html_path = output_path.replace(".pdf", ".html")
    Path(html_path).write_text(html, encoding="utf-8")
    print(f"HTML written to {html_path}")

    # Convert to PDF via WeasyPrint
    try:
        from weasyprint import HTML
        print("Converting to PDF via WeasyPrint…")
        HTML(filename=html_path).write_pdf(output_path)
        print(f"✓ PDF saved: {output_path}")
    except ImportError:
        print("WeasyPrint not installed. Install with: pip install weasyprint --break-system-packages")
        print(f"HTML file available at: {html_path}")
        sys.exit(1)
    except Exception as e:
        print(f"PDF conversion error: {e}")
        print(f"HTML file available at: {html_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
