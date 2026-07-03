#!/usr/bin/env python3
"""
D-One Conduit Schedule Generator — Excel (.xlsx)
Produces an editable spreadsheet matching the D-One conduit schedule format.

Usage: python generate_conduit_xlsx.py project_data.json output.xlsx
"""

import sys
import json
from pathlib import Path

try:
    from openpyxl import Workbook
    from openpyxl.styles import (PatternFill, Font, Alignment, Border, Side,
                                  GradientFill)
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.page import PageMargins
except ImportError:
    print("openpyxl not installed. Run: pip install openpyxl --break-system-packages")
    sys.exit(1)

# ── Colours ───────────────────────────────────────────────────────────────────
NAVY     = "1C2B4A"   # Level header background
MID_BLUE = "1E3A5F"   # Room header background
SLATE    = "37474F"   # Table column header background
WHITE    = "FFFFFF"
LIGHT_GREY = "F5F5F5"
TEXT_DARK  = "212121"
TEXT_GREY  = "546E7A"

def fill(hex_colour):
    return PatternFill("solid", fgColor=hex_colour)

def font(colour=TEXT_DARK, bold=False, size=10, name="Arial"):
    return Font(name=name, size=size, bold=bold, color=colour)

def centre():
    return Alignment(horizontal="center", vertical="center", wrap_text=True)

def left(wrap=True):
    return Alignment(horizontal="left", vertical="center", wrap_text=wrap)

def thin_border():
    s = Side(style="thin", color="D0D0D0")
    return Border(left=s, right=s, top=s, bottom=s)

def bottom_border():
    s = Side(style="thin", color="D0D0D0")
    return Border(bottom=s)

# ── Conduit mapping (same logic as generate_conduit_pdf.py) ──────────────────

CONDUIT_RULES = [
    # ── Non-physical / service items — skip entirely ──────────────────────────
    (["offsite monitoring", "monitoring integration", "sla free", "12 month sla",
      "offsite monitoring integration"],
     None, None, None, None, None),

    # ── Network & WiFi ────────────────────────────────────────────────────────
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
    # Cameras — match G6 Pro, G6 Entry when used as camera, G5, G4 etc.
    (["bullet", "turret", "dome", "g6 pro", "g5 pro", "g4 pro", "g3 pro",
      "ip camera", "unifi camera"],
     "25mm", "headend", "CAT6", "Deep round", "No"),

    # ── Video Distribution ────────────────────────────────────────────────────
    (["tv point", "hdmi point", "video point"],
     "25mm", "headend", "3× CAT6", "4×4", "Yes"),
    (["picture slider", "tv slider", "tv lift"],
     "20mm", "headend", "2-core", "—", "Yes"),
    (["explora", "decoder", "multichoice", "dstv decoder"],
     "25mm", "headend", "CAT6 + RG6", "4×4", "Yes"),
    (["satellite dish", "galvanised dish", "lnb"],
     "32mm", "headend", "2× RG6", "(outdoor bracket)", "No"),

    # ── Intercom & Access Control ─────────────────────────────────────────────
    # G6 Entry used as door intercom/access (not a security camera)
    (["g6 entry", "door station", "entry door", "access intercom terminal"],
     "20mm", "headend", "CAT6", "Flush round outdoor", "No"),
    (["unifi access intercom", "door intercom", "access intercom"],
     "20mm", "headend", "CAT6", "Flush round outdoor", "No"),
    (["monitor for unifi access", "access door monitor", "intercom monitor",
      "access intercom monitor"],
     "20mm", "headend", "CAT6", "2×4", "Yes"),
    (["electric lock", "door lock", "gate lock", "electric strike"],
     "20mm", "headend", "2-core + CAT6", "(inline)", "No"),
    (["biometric", "fingerprint reader"],
     "20mm", "headend", "CAT6", "2×4 deep", "No"),

    # ── Dolby Atmos / Surround Sound ─────────────────────────────────────────
    # CINEMA 50 is room-mounted, not rack
    (["cinema 50", "cinema50"],
     "32mm", "av_receiver_loc", "CAT6 + HDMI 2.1", "4×4 deep", "Yes"),
    (["av receiver", "receiver", "tx-rz", "onkyo"],
     "32mm", "headend", "CAT6 + HDMI 2.1", "4×4 deep", "Yes"),
    # In-wall subwoofer needs conduit (before general subwoofer rule)
    (["isw-8", "isw8", "in-wall subwoofer"],
     "25mm", "av_receiver", "Speaker Cable (2-core)", "In-wall cavity", "No"),
    # Dolby Atmos B&W speakers (CCM7.x, CWM7.x) — MUST come before generic
    # in-ceiling/in-wall rules because descriptions contain "in-ceiling speaker" etc.
    (["ccm7", "cwm7", "cwm8", "b&w ccm", "b&w cwm"],
     "25mm", "av_receiver", "Speaker Cable (2-core)", "(ceiling/wall void)", "No"),
    (["mk sound", "m&k", "b&w", "bowers wilkins", "klipsch vx-80"],
     "25mm", "av_receiver", "Speaker Cable (2-core)", "In-wall cavity", "No"),
    (["surround speaker", "m40t", "tripole"],
     "25mm", "av_receiver", "Speaker Cable (2-core)", "(bracket)", "Yes"),
    (["v10+", "v12+", "db4s", "subwoofer"],
     "—", "freestanding", "—", "—", "Yes"),

    # ── Multiroom Audio ───────────────────────────────────────────────────────
    (["sonos amp", "sonos s16", "sonos s25"],
     "25mm", "headend", "CAT6", "(wall/shelf)", "Yes"),
    # M4 Streaming Amp is DB/panel-mounted — no conduit route required
    (["marantz m4", "m4 streaming", "m4rve", "p4rve"],
     "—", "panel-mounted", "—", "—", "Yes"),
    (["sonos sub"],
     "—", "freestanding", "—", "—", "Yes"),
    # AM1 Outdoor and other outdoor/ceiling/wall speakers → M4 amp (headend)
    (["am1 outdoor", "am1", "outdoor speaker"],
     "25mm", "amp", "Speaker Cable (2-core)", "(outdoor bracket)", "No"),
    (["in-ceiling speaker", "ceiling speaker", "ic95", "cs-18", "c6r", "ccm683"],
     "25mm", "amp", "Speaker Cable (2-core)", "(ceiling void)", "No"),
    (["in-wall speaker", "iw950", "vx-80r"],
     "25mm", "amp", "Speaker Cable (2-core)", "In-wall cavity", "No"),

    # ── Lighting Control (Lutron) ─────────────────────────────────────────────
    # DB/panel-mounted items — NO conduit route required
    (["hqp72", "hqp71", "hqp7", "hqp6", "lighting processor", "lutron processor"],
     "—", "panel-mounted", "—", "—", "No"),
    (["lqse", "qseio", "qse-io", "dali module", "link power supply", "link ps",
      "lutron m4", "lutron p4", "m4rve", "p4rve"],
     "—", "panel-mounted", "—", "—", "No"),
    (["lutron dimmer", "lut-mlv", "lut-erf", "lut-mrf", "glp", "dim module",
      "elv+", "relay", "grafik eye", "gqse", "vcp"],
     "—", "panel-mounted", "—", "—", "No"),
    (["motion sensor", "occupancy sensor", "volt-free", "rr-ms"],
     "20mm", "Lighting DB", "4-core Mylar", "Surface round", "No"),
    # Keypads — handled by KEYPAD_RULES below
    (["keypad", "rr-t"],
     None, None, None, None, None),

    # ── Headend / Rack ────────────────────────────────────────────────────────
    (["rack", "cabinet", "42u", "22u", "linkbasic"],
     "—", "self-contained", "—", "—", "Yes (dedicated circuit)"),
    (["ups", "eaton", "apc"],
     "—", "rack-mounted", "—", "—", "Yes"),

    # ── Video Conferencing ────────────────────────────────────────────────────
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
    dl = description.lower()
    # Keypad special handling
    if "keypad" in dl or "rr-t" in dl:
        for btn, rule in KEYPAD_RULES.items():
            if (f"{btn}-button" in dl or f"{btn}-btn" in dl
                    or f"{btn}btn" in dl or f"-{btn}b" in dl):
                return rule
        return KEYPAD_RULES["4"]
    for patterns, conduit, dest, cable, backbox, power_pt in CONDUIT_RULES:
        if patterns is None:
            continue
        if any(p in dl for p in patterns):
            return conduit, dest, cable, backbox, power_pt
    return "25mm", "headend", "CAT6", "4×4", "No"


def short_label(description):
    dl = description.lower()
    if any(x in dl for x in ["wifi", "access point", "wifi 6", "wifi 7"]):
        return "WiFi AP"
    if "tv point" in dl:
        return "TV Point"
    if "udm" in dl or "dream machine" in dl:
        return "Gateway"
    if "switch" in dl and "poe" in dl:
        return "PoE Switch"
    if "switch" in dl:
        return "Data Switch"
    if "nvr" in dl:
        return "NVR"
    if any(x in dl for x in ["g5 pro", "g4 pro", "camera"]):
        return "IP Camera"
    if "access intercom" in dl or "door intercom" in dl:
        return "Door Intercom"
    if "monitor for unifi" in dl or "intercom monitor" in dl:
        return "Intercom Monitor"
    if "electric lock" in dl or "door lock" in dl:
        return "Door Lock"
    if "sonos amp" in dl or "s16" in dl:
        return "Sonos AMP"
    if "sonos sub" in dl:
        return "Sonos Sub"
    if any(x in dl for x in ["in-ceiling speaker", "ceiling speaker", "cs-18",
                               "ic95", "c6r", "ccm7.5"]):
        return "Ceiling Speaker"
    if any(x in dl for x in ["in-wall speaker", "iw950", "vx-80r", "cwm8.5"]):
        return "Wall Speaker"
    if any(x in dl for x in ["subwoofer", "v10+", "v12+", "db4s"]):
        return "Subwoofer"
    if any(x in dl for x in ["av receiver", "marantz", "onkyo", "cinema50"]):
        return "AV Receiver"
    if "keypad" in dl:
        for n in ["8", "6", "4", "3", "2", "1"]:
            if f"{n}-button" in dl or f"{n}-btn" in dl or f"-{n}b" in dl:
                return f"Lutron {n}-btn Keypad"
        return "Lutron Keypad"
    if any(x in dl for x in ["rack", "cabinet", "42u"]):
        return "Server Rack"
    if "interactive panel" in dl or "skye" in dl:
        return "Conf. Panel"
    words = [w for w in description.split() if len(w) > 2]
    return " ".join(words[:3]) if words else description[:20]


def build_rows(project_data):
    headend = project_data["project"].get("headend_room", "Head-End")
    rows = []
    for floor in project_data.get("floors", []):
        level = floor.get("level", "")
        for room in floor.get("rooms", []):
            full_name = room.get("full_name", room.get("name", ""))
            for item in room.get("items", []):
                desc = item.get("description", "")
                qty = item.get("qty", 1)
                is_prov = item.get("is_provisional", False)
                conduit, dest_key, cable, backbox, power_pt = match_rule(desc)
                if conduit is None:
                    continue
                if conduit == "—" and dest_key in ("rack-mounted", "panel-mounted",
                                                     "freestanding", "self-contained"):
                    continue
                destination = "Head-End" if dest_key == "headend" else \
                              "Headend / Rack" if dest_key == "amp" else \
                              "AV Receiver" if dest_key == "av_receiver" else \
                              "Entertainment Room" if dest_key == "av_receiver_loc" else \
                              dest_key
                label = short_label(desc)
                prov = " (Prov)" if is_prov else ""
                for i in range(qty):
                    count = f" {i+1}" if qty > 1 else ""
                    rows.append((level, full_name,
                                 f"■ {label}{prov}{count}",
                                 conduit, destination, cable, backbox, power_pt))
    return rows


# ── Spreadsheet builder ───────────────────────────────────────────────────────

def build_xlsx(project_data, rows, output_path):
    proj = project_data["project"]
    wb = Workbook()
    ws = wb.active
    ws.title = "Conduit Schedule"

    # ── Page setup ────────────────────────────────────────────────────────────
    ws.page_setup.orientation = "portrait"
    ws.page_setup.paperSize = 9   # A4
    ws.page_setup.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_margins = PageMargins(left=0.5, right=0.5, top=0.6, bottom=0.6,
                                   header=0.3, footer=0.3)
    ws.print_title_rows = "1:2"   # repeat header rows when printing
    ws.oddHeader.center.text = (
        f"&B{proj.get('name','')} | Conduit Schedule&B    "
        f"d·one | darren@d-one.co.za | 021 012 5112"
    )
    ws.oddFooter.left.text = (
        f"{proj.get('client','')} | Quote Ref: {proj.get('quote_ref','')} | "
        f"Prepared: {proj.get('date','')} | Valid to: {proj.get('valid_to','')}"
    )
    ws.oddFooter.right.text = "Page &P of &N"

    # ── Column widths ─────────────────────────────────────────────────────────
    col_widths = {
        "A": 22,   # Point
        "B": 13,   # Conduit Size
        "C": 22,   # Destination
        "D": 24,   # Cable
        "E": 16,   # Backbox
        "F": 11,   # Power pt
    }
    for col, width in col_widths.items():
        ws.column_dimensions[col].width = width

    # ── Row 1 — Title bar ─────────────────────────────────────────────────────
    ws.row_dimensions[1].height = 30
    ws.merge_cells("A1:F1")
    title_cell = ws["A1"]
    title_cell.value = f"Conduit Schedule — {proj.get('name','')}  |  Quote Ref: {proj.get('quote_ref','')}"
    title_cell.fill = fill(NAVY)
    title_cell.font = font(WHITE, bold=True, size=13)
    title_cell.alignment = left(wrap=False)

    # ── Row 2 — Column headers ────────────────────────────────────────────────
    ws.row_dimensions[2].height = 22
    headers = ["Point", "Conduit Size", "Destination", "Cable", "Backbox", "Power pt"]
    for col_idx, header in enumerate(headers, start=1):
        c = ws.cell(row=2, column=col_idx, value=header)
        c.fill = fill(SLATE)
        c.font = font(WHITE, bold=True, size=10)
        c.alignment = centre() if col_idx in (2, 6) else left(wrap=False)
        c.border = thin_border()

    # ── Data rows ─────────────────────────────────────────────────────────────
    current_level = None
    current_room = None
    data_row = 3

    from collections import OrderedDict
    grouped = OrderedDict()
    for level, room, point, conduit, dest, cable, backbox, power in rows:
        if level not in grouped:
            grouped[level] = OrderedDict()
        if room not in grouped[level]:
            grouped[level][room] = []
        grouped[level][room].append((point, conduit, dest, cable, backbox, power))

    for level, rooms in grouped.items():
        # Level header row
        ws.row_dimensions[data_row].height = 20
        ws.merge_cells(f"A{data_row}:F{data_row}")
        c = ws.cell(row=data_row, column=1, value=level.upper())
        c.fill = fill(NAVY)
        c.font = font(WHITE, bold=True, size=11)
        c.alignment = left(wrap=False)
        data_row += 1

        for room_name, items in rooms.items():
            # Room header row
            ws.row_dimensions[data_row].height = 18
            ws.merge_cells(f"A{data_row}:F{data_row}")
            c = ws.cell(row=data_row, column=1, value=room_name)
            c.fill = fill(MID_BLUE)
            c.font = font(WHITE, bold=True, size=10)
            c.alignment = left(wrap=False)
            data_row += 1

            for i, (point, conduit, dest, cable, backbox, power) in enumerate(items):
                ws.row_dimensions[data_row].height = 18
                row_fill = fill("FFFFFF") if i % 2 == 0 else fill(LIGHT_GREY)
                values = [point, conduit, dest, cable, backbox, power]
                aligns = [left(), centre(), left(), left(), left(), centre()]
                for col_idx, (val, aln) in enumerate(zip(values, aligns), start=1):
                    c = ws.cell(row=data_row, column=col_idx, value=val)
                    c.fill = row_fill
                    c.font = font(TEXT_DARK, size=10)
                    c.alignment = aln
                    c.border = bottom_border()
                data_row += 1

    # ── Freeze panes below headers ────────────────────────────────────────────
    ws.freeze_panes = "A3"

    # ── Auto-filter on header row ─────────────────────────────────────────────
    ws.auto_filter.ref = f"A2:F{data_row - 1}"

    wb.save(output_path)
    print(f"✓ Spreadsheet saved: {output_path}  ({data_row - 3} data rows)")


def main():
    if len(sys.argv) < 3:
        print("Usage: generate_conduit_xlsx.py project_data.json output.xlsx")
        sys.exit(1)

    project_path, output_path = sys.argv[1], sys.argv[2]
    project_data = json.loads(Path(project_path).read_text(encoding="utf-8"))

    print("Building conduit rows…")
    rows = build_rows(project_data)
    print(f"  → {len(rows)} conduit entries")

    build_xlsx(project_data, rows, output_path)


if __name__ == "__main__":
    main()
