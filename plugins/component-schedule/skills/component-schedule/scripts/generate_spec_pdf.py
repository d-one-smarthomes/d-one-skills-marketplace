#!/usr/bin/env python3
"""
D-One Component & Equipment Schedule PDF Generator
Usage: python3 generate_spec_pdf.py project_data.json product_research.json output.pdf
"""

import sys
import json
import base64
import textwrap
from pathlib import Path

# ── System-category colour map ────────────────────────────────────────────────
CAT_COLOURS = {
    "WiFi & Network":               "#1379C9",
    "Video Distribution":           "#7030A0",
    "Intercom & Access Control":    "#C00000",
    "Video Conferencing":           "#00695C",
    "Headend & Rack Cabinets":      "#404040",
    "Multiroom Audio":              "#375623",
    "Dolby Atmos Surround Sound":   "#E06C00",
    "Lighting Control":             "#BF8F00",
    "Security & Surveillance":      "#3D1F6B",
}
DEFAULT_CAT_COLOUR = "#666666"

BRAND_BLUE  = "#1379C9"
BRAND_NAVY  = "#1F3864"
LEVEL_BG    = "#1379C9"
ROOM_BG     = "#2E75B6"
ALT_ROW     = "#F2F2F2"


def cat_colour(cat: str) -> str:
    return CAT_COLOURS.get(cat, DEFAULT_CAT_COLOUR)


def make_badge(cat: str) -> str:
    c = cat_colour(cat)
    return (
        f'<span style="background:{c};color:#fff;font-size:8px;font-weight:700;'
        f'padding:2px 6px;border-radius:3px;white-space:nowrap;letter-spacing:0.3px">'
        f'{cat}</span>'
    )


def photo_tag(photo_b64: str | None, size: int = 72) -> str:
    if photo_b64:
        src = photo_b64 if photo_b64.startswith("data:") else f"data:image/jpeg;base64,{photo_b64}"
        return (
            f'<img src="{src}" width="{size}" height="{size}" '
            f'style="object-fit:contain;display:block;margin:auto"/>'
        )
    return (
        f'<div style="width:{size}px;height:{size}px;border:1px solid #ddd;'
        f'display:flex;align-items:center;justify-content:center;'
        f'color:#aaa;font-size:9px;text-align:center;margin:auto">No photo</div>'
    )


def build_legend(all_cats: set) -> str:
    items = ""
    for cat in sorted(all_cats):
        c = cat_colour(cat)
        items += (
            f'<span style="display:inline-flex;align-items:center;gap:5px;margin:3px 6px 3px 0">'
            f'<span style="width:12px;height:12px;background:{c};border-radius:2px;display:inline-block"></span>'
            f'<span style="font-size:9px;color:#333">{cat}</span>'
            f'</span>'
        )
    return f'<div style="padding:6px 14px 8px;border-bottom:1px solid #e0e0e0;line-height:1.8">{items}</div>'


def build_html(project: dict, research: dict) -> str:
    pname    = project.get("project_name", "Project")
    qref     = project.get("quote_ref", "")
    prep_by  = project.get("prepared_by", "D-One")
    floors   = project.get("floors", [])

    products = research.get("products", {})

    # Collect all categories
    all_cats = set()
    for floor in floors:
        for room in floor.get("rooms", []):
            for item in room.get("items", []):
                all_cats.add(item.get("system_category", "Other"))

    # ── Header ────────────────────────────────────────────────────────────────
    header = f"""
    <div style="background:{BRAND_NAVY};color:#fff;padding:18px 24px 14px;display:flex;
                justify-content:space-between;align-items:flex-end">
      <div>
        <div style="font-size:22px;font-weight:800;letter-spacing:1px">D-ONE</div>
        <div style="font-size:14px;font-weight:600;margin-top:4px">Component &amp; Equipment Schedule</div>
        <div style="font-size:11px;margin-top:3px;opacity:0.85">{pname}</div>
      </div>
      <div style="text-align:right;font-size:10px;opacity:0.8">
        <div>Quote ref: {qref}</div>
        <div>Prepared by: {prep_by}</div>
      </div>
    </div>
    """

    legend = build_legend(all_cats)

    # ── Floor / Room / Item sections ──────────────────────────────────────────
    body = ""
    for floor in floors:
        level = floor.get("level", "")
        body += f"""
        <div style="background:{LEVEL_BG};color:#fff;font-size:11px;font-weight:700;
                    padding:5px 14px;letter-spacing:1px;margin-top:10px">{level}</div>
        """

        for room in floor.get("rooms", []):
            rname = room.get("room", "")
            items = room.get("items", [])
            if not items:
                continue

            body += f"""
            <div style="background:{ROOM_BG};color:#fff;font-size:10px;font-weight:600;
                        padding:4px 14px 3px 24px">{rname}</div>
            """

            # table header
            body += """
            <table style="width:100%;border-collapse:collapse;font-size:9.5px">
              <thead>
                <tr style="background:#e8e8e8">
                  <th style="width:80px;padding:4px 6px;text-align:center;font-weight:600;
                             border-bottom:1px solid #ccc">Photo</th>
                  <th style="padding:4px 6px;text-align:left;font-weight:600;
                             border-bottom:1px solid #ccc">Description</th>
                  <th style="width:34px;padding:4px 6px;text-align:center;font-weight:600;
                             border-bottom:1px solid #ccc">Qty</th>
                  <th style="width:120px;padding:4px 6px;text-align:center;font-weight:600;
                             border-bottom:1px solid #ccc">Dimensions (W×H×D)</th>
                  <th style="width:120px;padding:4px 6px;text-align:center;font-weight:600;
                             border-bottom:1px solid #ccc">System</th>
                </tr>
              </thead>
              <tbody>
            """

            for i, item in enumerate(items):
                desc  = item.get("description", "")
                qty   = item.get("qty", 1)
                cat   = item.get("system_category", "Other")
                prov  = item.get("is_provisional", False)
                model = item.get("model", "")

                prod  = products.get(desc, {})
                dims  = prod.get("dimensions", "—")
                photo = prod.get("photo_b64")

                row_bg = ALT_ROW if i % 2 == 0 else "#ffffff"
                prov_mark = ' <span style="color:#C00000;font-size:8px">(Provisional)</span>' if prov else ""
                model_text = f'<div style="color:#888;font-size:8px;margin-top:1px">{model}</div>' if model else ""

                body += f"""
                <tr style="background:{row_bg};vertical-align:middle">
                  <td style="padding:5px 6px;text-align:center;border-bottom:1px solid #e8e8e8">
                    {photo_tag(photo, 60)}
                  </td>
                  <td style="padding:5px 6px;border-bottom:1px solid #e8e8e8">
                    <strong>{desc}</strong>{prov_mark}
                    {model_text}
                  </td>
                  <td style="padding:5px 6px;text-align:center;border-bottom:1px solid #e8e8e8;
                             font-weight:700">{qty}</td>
                  <td style="padding:5px 6px;text-align:center;border-bottom:1px solid #e8e8e8;
                             color:#444;font-size:8.5px">{dims}</td>
                  <td style="padding:5px 6px;text-align:center;border-bottom:1px solid #e8e8e8">
                    {make_badge(cat)}
                  </td>
                </tr>
                """

            body += "</tbody></table>"

    # ── Footer ────────────────────────────────────────────────────────────────
    footer = f"""
    <div style="margin-top:20px;padding:12px 14px;background:#f5f5f5;
                border-top:2px solid {BRAND_BLUE};font-size:8.5px;color:#555">
      <strong>12-Month SLA</strong> — All equipment supplied and installed by D-One carries a 12-month
      service-level warranty from date of practical completion. Provisional items are subject to final
      client selection and may vary in specification or price.
    </div>
    <div style="padding:8px 14px;text-align:right;font-size:8px;color:#999">
      D-One · www.d-one.co.za · {pname} · {qref}
    </div>
    """

    # ── Full HTML ─────────────────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
  @page {{
    size: A4;
    margin: 10mm 12mm 12mm 12mm;
  }}
  body {{
    font-family: Arial, Helvetica, sans-serif;
    font-size: 10px;
    margin: 0;
    padding: 0;
    color: #222;
  }}
  table {{ page-break-inside: auto; }}
  tr     {{ page-break-inside: avoid; page-break-after: auto; }}
</style>
</head>
<body>
{header}
{legend}
{body}
{footer}
</body>
</html>"""

    return html


def main():
    if len(sys.argv) < 4:
        print("Usage: python3 generate_spec_pdf.py project_data.json product_research.json output.pdf")
        sys.exit(1)

    project_path  = sys.argv[1]
    research_path = sys.argv[2]
    output_path   = sys.argv[3]

    project  = json.load(open(project_path))
    research = json.load(open(research_path))

    html = build_html(project, research)

    # Write HTML for debugging
    html_path = output_path.replace(".pdf", ".html")
    Path(html_path).write_text(html, encoding="utf-8")
    print(f"HTML written: {html_path}")

    try:
        from weasyprint import HTML
        HTML(string=html, base_url=".").write_pdf(output_path)
        print(f"PDF written: {output_path}")
    except ImportError:
        print("WeasyPrint not installed — run: pip install weasyprint --break-system-packages")
        print(f"HTML version saved at: {html_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
