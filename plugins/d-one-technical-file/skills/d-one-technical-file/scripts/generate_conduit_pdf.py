#!/usr/bin/env python3
"""
D-One Conduit Schedule Generator
Usage: python generate_conduit_pdf.py project_data.json output.pdf
"""

import sys
import json
from pathlib import Path

# ── Conduit mapping rules ─────────────────────────────────────────────────────
# Each entry: list of (keyword_patterns, conduit_size, destination_key, cable, backbox, power_pt)
# destination_key: "headend" = use headend room name; "amp" = nearest amp; literal = use as-is

CONDUIT_RULES = [
    # Network & WiFi
    (["wifi", "access point", " ap ", "wifi 7", "wifi 6", "unifi ap"],
     "25mm", "headend", "CAT6", "4×4", "No"),
    (["lan point", "data point", "network point"],
     "25mm", "headend", "CAT6", "Single gang", "No"),
    (["udm", "dream machine", "gateway", "router"],
     "—", "rack-mounted", "—", "—", "Yes"),
    (["switch", "pro max switch", "sw-", "sw24", "sw16"],
     "—", "rack-mounted", "—", "—", "Yes"),
    (["patch panel"],
     "—", "rack-mounted", "—", "—", "No"),
    (["unifi nvr", "nvr pro", "network video recorder"],
     "—", "rack-mounted", "—", "—", "Yes"),
    (["ip camera", "unifi camera", "unifi g5", "unifi g4"],
     "25mm", "headend", "CAT6", "Deep round", "No"),

    # Video Distribution
    (["tv point", "hdmi point", "video point"],
     "25mm", "headend", "3× CAT6", "4×4", "Yes"),
    (["explora", "decoder", "multichoice", "dstv decoder"],
     "25mm", "headend", "CAT6 + RG6", "4×4", "Yes"),
    (["satellite dish", "galvanised dish", "lnb"],
     "32mm", "headend", "2× RG6", "(outdoor bracket)", "No"),
    (["matv", "tv distribution", "rf distribution"],
     "25mm", "headend", "RG6", "4×4", "No"),

    # Intercom & Access Control
    (["unifi access intercom", "door intercom", "door station", "access intercom"],
     "20mm", "headend", "CAT6", "Flush round outdoor", "No"),
    (["monitor for unifi access", "access door monitor", "intercom monitor"],
     "20mm", "headend", "CAT6", "2×4", "Yes"),
    (["electric lock", "door lock", "gate lock", "electric strike"],
     "20mm", "headend", "2-core + CAT6", "(inline)", "No"),
    (["biometric", "fingerprint reader"],
     "20mm", "headend", "CAT6", "2×4 deep", "No"),
    (["access reader", "reader station"],
     "20mm", "headend", "CAT6", "2×4", "No"),

    # Multiroom Audio
    (["sonos amp", "sonos s16", "sonos s25"],
     "25mm", "headend", "CAT6", "(wall/shelf)", "Yes"),
    (["sonos sub", "subwoofer"],
     "—", "freestanding", "—", "—", "Yes"),
    (["in-ceiling speaker", "ceiling speaker", "ic95", "cs-18", "c6r", "custom cs"],
     "25mm", "amp", "Speaker Cable (2-core)", "(ceiling void)", "No"),
    (["in-wall speaker", "wall speaker", "iw950", "vx-80r"],
     "25mm", "amp", "Speaker Cable (2-core)", "In-wall cavity", "No"),

    # Dolby Atmos / Surround Sound
    (["av receiver", "receiver", "tx-rz", "cinema50", "onkyo", "marantz"],
     "32mm", "headend", "CAT6 + HDMI 2.1", "4×4 deep", "Yes"),
    (["atmos speaker", "in-ceiling atmos", "ic95"],
     "25mm", "av_receiver", "Speaker Cable (2-core)", "(ceiling void)", "No"),
    (["surround speaker", "m40t", "tripole"],
     "25mm", "av_receiver", "Speaker Cable (2-core)", "(bracket)", "Yes"),
    (["mk sound", "m&k", "b&w", "bowers wilkins", "klipsch vx-80"],
     "25mm", "av_receiver", "Speaker Cable (2-core)", "In-wall cavity", "No"),
    (["v10+", "v12+", "subwoofer", "sub "],
     "—", "freestanding", "—", "—", "Yes"),

    # Lighting Control (Lutron)
    # IMPORTANT: processor/dimmer/relay rules must come BEFORE the keypad catch-all
    # Processors, dimmers, relays, amps → DB/panel-mounted, NO conduit route needed
    (["hqp72", "hqp71", "hqp7", "hqp6", "lighting processor", "lutron processor"],
     "—", "panel-mounted", "—", "—", "No"),
    (["lutron m4", "lutron p4", "m4rve", "p4rve"],
     "—", "panel-mounted", "—", "—", "No"),
    (["lutron dimmer", "lut-mlv", "lut-erf", "lut-mrf", "glp", "dim module",
      "elv+", "relay", "grafik eye", "gqse", "vcp"],
     "—", "panel-mounted", "—", "—", "No"),
    (["motion sensor", "occupancy sensor", "rr-ms"],
     "20mm", "Lighting DB", "4-core Mylar", "Surface round", "No"),
    # Keypads: match_rule() sends these to KEYPAD_RULES; None signals special handling
    (["keypad", "rr-t"],
     None, None, None, None, None),

    # Headend infrastructure
    (["rack", "cabinet", "42u", "22u", "linkbasic"],
     "—", "self-contained", "—", "—", "Yes (dedicated circuit)"),
    (["ups", "eaton", "apc"],
     "—", "rack-mounted", "—", "—", "Yes"),

    # Video Conferencing
    (["interactive panel", "skye", "conference display"],
     "32mm", "headend", "CAT6 + HDMI 2.1", "4×4", "Yes"),
]

KEYPAD_RULES = {
    "8": ("25mm", "Lighting DB / Spanel", "4-core Mylar", "4×4", "No"),
    "4": ("25mm", "Lighting DB / Spanel", "4-core Mylar", "2×4", "No"),
    "2": ("20mm", "Lighting DB / Spanel", "4-core Mylar", "Single gang", "No"),
    "1": ("20mm", "Lighting DB / Spanel", "4-core Mylar", "Single gang", "No"),
}


def match_rule(description):
    """Return (conduit, destination_key, cable, backbox, power_pt) for a description."""
    desc_lower = description.lower()

    # Special Lutron keypad handling
    if "keypad" in desc_lower or "rr-t" in desc_lower:
        for btn_count, rule in KEYPAD_RULES.items():
            if f"{btn_count}-button" in desc_lower or f"{btn_count}-btn" in desc_lower \
                    or f"{btn_count}btn" in desc_lower or f"-{btn_count}b" in desc_lower:
                return rule
        return KEYPAD_RULES["4"]  # default to 4-button if unspecified

    for patterns, conduit, dest, cable, backbox, power_pt in CONDUIT_RULES:
        if patterns is None:
            continue
        if any(p in desc_lower for p in patterns):
            return conduit, dest, cable, backbox, power_pt

    # Default fallback
    return "25mm", "headend", "CAT6", "4×4", "No"


def resolve_destination(dest_key, headend_room, room_name):
    if dest_key == "headend":
        return "Head-End"
    elif dest_key in ("amp", "av_receiver"):
        return "Headend / Rack"
    elif dest_key in ("rack-mounted", "panel-mounted", "self-contained", "freestanding"):
        return f"({dest_key})"
    else:
        return dest_key


def short_label(description):
    """Return a concise item label for the Point column (e.g. 'WiFi AP', 'TV Point', 'Speaker')."""
    dl = description.lower()
    # Network
    if any(x in dl for x in ["wifi", "access point", " ap ", "wifi 6", "wifi 7"]):
        return "WiFi AP"
    if "switch" in dl and "pro max" in dl and "poe" in dl:
        return "PoE Switch"
    if "switch" in dl:
        return "Data Switch"
    if "udm" in dl or "dream machine" in dl:
        return "Gateway"
    if "patch panel" in dl:
        return "Patch Panel"
    if "nvr" in dl or "network video" in dl:
        return "NVR"
    if "ip camera" in dl or "g5 pro" in dl or "g4 pro" in dl or "unifi camera" in dl:
        return "IP Camera"
    # Video
    if "tv point" in dl:
        return "TV Point"
    if "explora" in dl or "decoder" in dl:
        return "DSTV Decoder"
    if "satellite dish" in dl or "galvanised dish" in dl:
        return "Satellite Dish"
    # Intercom
    if "access intercom" in dl or "door intercom" in dl:
        return "Door Intercom"
    if "monitor for unifi" in dl or "intercom monitor" in dl:
        return "Intercom Monitor"
    if "electric lock" in dl or "door lock" in dl:
        return "Door Lock"
    # Audio
    if "sonos amp" in dl or "s16" in dl:
        return "Sonos AMP"
    if "sonos sub" in dl:
        return "Sonos Sub"
    if "in-ceiling speaker" in dl or "ceiling speaker" in dl or "cs-18" in dl or "ic95" in dl or "c6r" in dl:
        return "Ceiling Speaker"
    if "in-wall speaker" in dl or "wall speaker" in dl or "iw950" in dl or "vx-80r" in dl:
        return "Wall Speaker"
    if "subwoofer" in dl or "v10+" in dl or "v12+" in dl or "db4s" in dl:
        return "Subwoofer"
    if "surround" in dl or "m40t" in dl or "tripole" in dl:
        return "Surround Spkr"
    if "av receiver" in dl or "receiver" in dl or "marantz" in dl or "onkyo" in dl:
        return "AV Receiver"
    # Lighting
    if "keypad" in dl:
        # Try to extract button count
        for n in ["8", "6", "4", "3", "2", "1"]:
            if f"{n}-button" in dl or f"{n}-btn" in dl or f"-{n}b" in dl:
                return f"Lutron {n}-btn Keypad"
        return "Lutron Keypad"
    if "hqp" in dl or "lighting processor" in dl:
        return "Lutron Processor"
    if "m4rve" in dl or "p4rve" in dl or "lutron m4" in dl or "lutron p4" in dl:
        return "Lutron Amp"
    if "dimmer" in dl or "lut-mlv" in dl or "glp" in dl:
        return "Dimmer Module"
    if "motion sensor" in dl or "occupancy" in dl:
        return "Motion Sensor"
    # Rack
    if "rack" in dl or "cabinet" in dl or "42u" in dl:
        return "Server Rack"
    if "ups" in dl:
        return "UPS"
    # Interactive
    if "interactive panel" in dl or "skye" in dl:
        return "Conf. Panel"
    # Fallback — use first 3 meaningful words
    words = [w for w in description.split() if len(w) > 2 and w not in
             ("The", "For", "And", "With", "Pro", "Max")]
    return " ".join(words[:3]) if words else description[:18]


def build_rows(project_data):
    """Generate list of (level, room, point_label, conduit, destination, cable, backbox, power_pt)."""
    headend = project_data["project"].get("headend_room", "Head-End")
    rows = []

    for floor in project_data.get("floors", []):
        level = floor.get("level", "")
        for room in floor.get("rooms", []):
            room_name = room.get("name", "")
            full_name = room.get("full_name", f"{level}: {room_name}")

            for item in room.get("items", []):
                desc = item.get("description", "")
                qty = item.get("qty", 1)
                is_prov = item.get("is_provisional", False)

                conduit, dest_key, cable, backbox, power_pt = match_rule(desc)

                # Skip items with no conduit route needed
                # (panel/DB-mounted, rack-mounted, freestanding power-only)
                if conduit is None:
                    continue  # keypad rule returned None — handled by KEYPAD_RULES path
                if conduit == "—" and dest_key in ("rack-mounted", "panel-mounted",
                                                     "freestanding", "self-contained"):
                    continue

                destination = resolve_destination(dest_key, headend, room_name)
                item_label = short_label(desc)
                prov_suffix = " (Prov)" if is_prov else ""

                for i in range(qty):
                    # Show "■ WiFi AP" or "■ WiFi AP 2" for multiples
                    count_suffix = f" {i+1}" if qty > 1 else ""
                    point_display = f"■ {item_label}{prov_suffix}{count_suffix}"
                    rows.append((level, full_name, point_display,
                                 conduit, destination, cable, backbox, power_pt))

    return rows


def build_html(project_data, rows):
    proj = project_data["project"]

    # Group rows by level → room
    from collections import OrderedDict
    grouped = OrderedDict()
    for level, room, point, conduit, dest, cable, backbox, power in rows:
        if level not in grouped:
            grouped[level] = OrderedDict()
        if room not in grouped[level]:
            grouped[level][room] = []
        grouped[level][room].append((point, conduit, dest, cable, backbox, power))

    table_rows = ""
    for level, rooms in grouped.items():
        table_rows += f"""
<tr class="level-header">
  <td colspan="6">{level.upper()}</td>
</tr>"""
        for room_name, items in rooms.items():
            table_rows += f"""
<tr class="room-header">
  <td colspan="6">{room_name}</td>
</tr>"""
            for point, conduit, dest, cable, backbox, power in items:
                table_rows += f"""
<tr class="item-row">
  <td class="point-cell">{point}</td>
  <td class="size-cell">{conduit}</td>
  <td>{dest}</td>
  <td>{cable}</td>
  <td>{backbox}</td>
  <td class="center">{power}</td>
</tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  @page {{ size: A4 portrait; margin: 15mm; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: Arial, Helvetica, sans-serif; font-size: 12px;
         color: #212121; margin: 0; }}

  .page-header {{
    display: flex; justify-content: space-between; align-items: center;
    border-bottom: 1px solid #CFD8DC; padding-bottom: 6px; margin-bottom: 10px;
    font-size: 11px;
  }}
  .page-header .left {{ font-weight: bold; color: #1C2B4A; }}
  .page-header .right {{ color: #546E7A; }}

  .cover-banner {{
    background: #1C2B4A; color: white; border-radius: 4px;
    padding: 16px 20px; display: flex; justify-content: space-between;
    align-items: center; margin-bottom: 16px;
  }}
  .cover-banner h1 {{ margin: 0; font-size: 24px; font-weight: bold; }}
  .cover-banner .meta {{ text-align: right; font-size: 11px; line-height: 1.8; }}

  table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
  th {{
    background: #37474F; color: white; font-weight: bold;
    padding: 7px 9px; font-size: 11px; text-align: left;
  }}
  th.center {{ text-align: center; }}

  tr.level-header td {{
    background: #1C2B4A; color: white; font-weight: bold;
    font-size: 12px; padding: 8px 12px; letter-spacing: 0.5px;
  }}
  tr.room-header td {{
    background: #1E3A5F; color: white; font-weight: 600;
    font-size: 11px; padding: 6px 12px;
  }}
  tr.item-row td {{
    padding: 6px 9px; border-bottom: 1px solid #ECEFF1;
    vertical-align: middle; font-size: 11px;
  }}
  tr.item-row:nth-child(even) td {{ background: #F5F5F5; }}

  .point-cell {{ width: 130px; font-weight: bold; font-size: 10px; }}
  .size-cell {{ width: 80px; text-align: center; }}
  .center {{ text-align: center; }}

  .footer {{
    margin-top: 14px; padding-top: 6px; border-top: 1px solid #CFD8DC;
    font-size: 10px; color: #546E7A;
    display: flex; justify-content: space-between;
  }}
</style>
</head>
<body>

<div class="page-header">
  <span class="left">{proj.get('name', '')} &nbsp;|&nbsp; Conduit Schedule</span>
  <span class="right">d&middot;one &nbsp;|&nbsp; darren@d-one.co.za &nbsp;|&nbsp; 021 012 5112</span>
</div>

<div class="cover-banner">
  <h1>Conduit Schedule</h1>
  <div class="meta">
    {proj.get('name', '')}<br>
    Quote Ref: {proj.get('quote_ref', '')}<br>
    Prepared by {proj.get('prepared_by', '')} | D-One
  </div>
</div>

<table>
  <thead>
    <tr>
      <th>Point</th>
      <th class="center">Conduit Size</th>
      <th>Destination</th>
      <th>Cable</th>
      <th>Backbox</th>
      <th class="center">Power pt</th>
    </tr>
  </thead>
  <tbody>
    {table_rows}
  </tbody>
</table>

<div class="footer">
  <span>{proj.get('client', '')} &nbsp;|&nbsp; Quote Ref: {proj.get('quote_ref', '')}
  &nbsp;|&nbsp; Prepared: {proj.get('date', '')}
  &nbsp;|&nbsp; Valid to: {proj.get('valid_to', '')}</span>
</div>

</body>
</html>"""
    return html


def main():
    if len(sys.argv) < 3:
        print("Usage: generate_conduit_pdf.py project_data.json output.pdf")
        sys.exit(1)

    project_path, output_path = sys.argv[1], sys.argv[2]
    project_data = json.loads(Path(project_path).read_text(encoding="utf-8"))

    print("Building conduit rows…")
    rows = build_rows(project_data)
    print(f"  → {len(rows)} conduit entries")

    html = build_html(project_data, rows)
    html_path = output_path.replace(".pdf", ".html")
    Path(html_path).write_text(html, encoding="utf-8")
    print(f"HTML written to {html_path}")

    try:
        from weasyprint import HTML
        print("Converting to PDF…")
        HTML(filename=html_path).write_pdf(output_path)
        print(f"✓ PDF saved: {output_path}")
    except ImportError:
        print("WeasyPrint not installed: pip install weasyprint --break-system-packages")
        print(f"HTML available at: {html_path}")
        sys.exit(1)
    except Exception as e:
        print(f"PDF error: {e}")
        print(f"HTML available at: {html_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
