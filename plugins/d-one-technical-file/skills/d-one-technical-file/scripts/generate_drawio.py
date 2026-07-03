#\!/usr/bin/env python3
"""
D-One Engineering Wiring Diagram Generator v4
Price Drive reference implementation

Usage: python generate_drawio.py project_data.json product_research.json output.drawio

Two-page draw.io output:
  Page 1 - System Topology (room boxes with device icons)
  Page 2 - Engineering Schematic (A1 landscape, column-based, port-labelled cables)
"""

import sys, json, math, re
from pathlib import Path
from collections import defaultdict

# ── ID counter ─────────────────────────────────────────────────────────────
_id = [0]
def uid(p="c"):
    _id[0] += 1
    return f"{p}_{_id[0]}"

def xe(s):
    return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace(chr(34),"&quot;")

def mk_cell(cid, val, style, x, y, w, h):
    return (f'<mxCell id="{cid}" value="{xe(val)}" style="{style}" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/>'
            f'</mxCell>\n')

def mk_edge(eid, val, cable_col, src, tgt):
    style = (f"edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;"
             f"jettySize=auto;exitX=0;exitY=0.5;exitDx=0;exitDy=0;"
             f"entryX=1;entryY=0.5;entryDx=0;entryDy=0;"
             f"strokeColor={cable_col};strokeWidth=2;fontSize=8;"
             f"fontColor={cable_col};labelBackgroundColor=#FFFFFF;")
    return (f'<mxCell id="{eid}" value="{xe(val)}" style="{style}" '
            f'edge="1" source="{src}" target="{tgt}" parent="1">'
            f'<mxGeometry relative="1" as="geometry"/></mxCell>\n')

def mk_edge_vert(eid, val, cable_col, src, tgt):
    """Vertical edge (for core infrastructure interconnects - top to bottom)"""
    style = (f"edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;"
             f"jettySize=auto;exitX=0.5;exitY=1;exitDx=0;exitDy=0;"
             f"entryX=0.5;entryY=0;entryDx=0;entryDy=0;"
             f"strokeColor={cable_col};strokeWidth=2;fontSize=7;"
             f"fontColor={cable_col};labelBackgroundColor=#FFFFFF;")
    return (f'<mxCell id="{eid}" value="{xe(val)}" style="{style}" '
            f'edge="1" source="{src}" target="{tgt}" parent="1">'
            f'<mxGeometry relative="1" as="geometry"/></mxCell>\n')

def mk_local_edge(eid, val, cable_col, src, tgt):
    """Right-side local edge — used for AMP → Speaker connections within the same column.
    Exits the right side of src, curves down and enters the right side of tgt.
    Keeps speaker wires on the right, separate from the left-side core cables."""
    style = (f"edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;"
             f"jettySize=auto;exitX=1;exitY=0.5;exitDx=0;exitDy=0;"
             f"entryX=1;entryY=0.5;entryDx=0;entryDy=0;"
             f"strokeColor={cable_col};strokeWidth=1.5;fontSize=7;"
             f"fontColor={cable_col};labelBackgroundColor=#FFFFFF;")
    return (f'<mxCell id="{eid}" value="{xe(val)}" style="{style}" '
            f'edge="1" source="{src}" target="{tgt}" parent="1">'
            f'<mxGeometry relative="1" as="geometry"/></mxCell>\n')

def page_wrap(name, content):
    return f'<diagram name="{xe(name)}">{content}</diagram>'

# ── Shared style dicts ──────────────────────────────────────────────────────
SYS_STYLE = {
    "WiFi & Network":               {"fill": "#D5E8D4", "stroke": "#82B366"},
    "Video Distribution":           {"fill": "#DAE8FC", "stroke": "#6C8EBF"},
    "Intercom & Access Control":    {"fill": "#E1D5E7", "stroke": "#9673A6"},
    "Headend & Rack Cabinets":      {"fill": "#DAE8FC", "stroke": "#6C8EBF"},
    "Multiroom Audio":              {"fill": "#F8CECC", "stroke": "#B85450"},
    "Dolby Atmos Surround Sound":   {"fill": "#F8CECC", "stroke": "#B85450"},
    "Lighting Control":             {"fill": "#FFF2CC", "stroke": "#D6B656"},
    "Security & Surveillance":      {"fill": "#FFE6CC", "stroke": "#D79B00"},
}

CABLE_COL = {
    "cat6_data":     "#1565C0",
    "cat6_poe":      "#2E7D32",
    "spanel_mylar":  "#E65100",   # Lutron SPANEL G Mylar bus cable
    "speaker":       "#B71C1C",
    "hdmi":          "#F57F17",
    "sfp_dac":       "#006064",
    "voltfree":      "#455A64",
}

CAT_TO_COL = {
    "WiFi & Network":             "network",
    "Security & Surveillance":    "security",
    "Intercom & Access Control":  "access",
    "Lighting Control":           "lighting",
    "Multiroom Audio":            "audio",
    "Dolby Atmos Surround Sound": "cinema",
    "Video Distribution":         "video",
}

# ── Port counters ───────────────────────────────────────────────────────────
_ports = {"poe":0,"data":0,"cam":0,"hqp":0}

def nxt(k):
    _ports[k] += 1
    return _ports[k]

CORE_IDS = {
    "isp":       "core_isp",
    "udm_max":   "core_udm_max",
    "sw_data":   "core_sw_data",
    "sw_poe":    "core_sw_poe",
    "sw_cam":    "core_sw_cam",
    "nvr":       "core_nvr_pro",
    "rack":      "core_rack",
    "hqp":       "core_hqp71",
    "m4_1":      "core_m4_amp1",
    "m4_2":      "core_m4_amp2",
    # CINEMA 50 is NOT in core — it lives in the Entertainment room
}

def get_cable(desc, qty=1, sys_cat=""):
    """Returns (cable_key, label_text, target_core_id)  -- or None for target = local"""
    d = desc.lower()
    if any(x in d for x in ["wifi","access point"," ap ","outdoor ap","wifi 7","wifi 6"]):
        p = nxt("poe")
        tag = f"Ports {p}-{p+qty-1}" if qty>1 else f"Port {p}"
        if qty>1:
            for _ in range(qty-1): nxt("poe")
        return ("cat6_poe", f"CAT6 PoE | PoE Sw {tag} → AP PoE In", CORE_IDS["sw_poe"])
    if any(x in d for x in ["bullet","turret","dome","g6 pro","g6 entry","g6 turret","g5 pro","g4","ip camera"]):
        p = nxt("cam")
        return ("cat6_poe", f"CAT6 PoE | Cam Sw Port {p} → Camera PoE In", CORE_IDS["sw_cam"])
    if any(x in d for x in ["intercom terminal","access intercom"]):
        p = nxt("data")
        return ("cat6_data", f"CAT6 | Data Sw Port {p} → Intercom LAN", CORE_IDS["sw_data"])
    if any(x in d for x in ["access door","door controller","reader station","door reader"]):
        p = nxt("data")
        return ("cat6_data", f"CAT6 | Data Sw Port {p} → Access Ctrl LAN", CORE_IDS["sw_data"])
    if "keypad" in d or "dali module" in d or "qseio" in d or "lqse" in d:
        p = nxt("hqp")
        return ("spanel_mylar", f"SPANEL G Mylar | HQP Bus Port {p} → Device", CORE_IDS["hqp"])
    if any(x in d for x in ["sonos amp","sonos s16","marantz m4"]):
        p = nxt("poe")
        return ("cat6_poe", f"CAT6 PoE | PoE Sw Port {p} → Amp LAN", CORE_IDS["sw_poe"])
    # ── Speaker routing: use system category to distinguish amp target ──────
    # Dolby Atmos cinema speakers → Marantz CINEMA 50
    # Multiroom Audio speakers    → Marantz M4 Amp #1 (headend)
    is_speaker = any(x in d for x in [
        "in-ceiling speaker","ceiling speaker","in-wall speaker",
        "klipsch","am1 outdoor","am1","outdoor speaker",
        "ccm","cwm","isw","706","subwoofer","floorstanding","htm",
    ])
    if is_speaker:
        if sys_cat == "Dolby Atmos Surround Sound":
            # Local connection — CINEMA 50 is in the same room as its speakers
            return ("speaker", "Speaker Cable | Cinema Rcvr Out → Speaker +/-", None)
        else:   # Multiroom Audio — M4 amps are in headend
            return ("speaker", "Speaker Cable | M4 Amp Out → Speaker +/-", CORE_IDS["m4_1"])
    # ────────────────────────────────────────────────────────────────────────
    if "cinema 50" in d or "cinema50" in d:
        p = nxt("data")
        return ("cat6_data", f"CAT6 | Data Sw Port {p} → Cinema Rcvr ETH", CORE_IDS["sw_data"])
    if "tv point" in d or "hdmi point" in d:
        p = nxt("data")
        return ("cat6_data", f"CAT6 | Data Sw Port {p} → TV Point ETH + HDMI", CORE_IDS["sw_data"])
    if "data point" in d or "lan point" in d:
        p = nxt("data")
        return ("cat6_data", f"CAT6 | Data Sw Port {p} → Data Point", CORE_IDS["sw_data"])
    p = nxt("data")
    return ("cat6_data", f"CAT6 | Data Sw Port {p} → Device", CORE_IDS["sw_data"])

# ══════════════════════════════════════════════════════════════════════════
# PAGE 1 – SYSTEM TOPOLOGY
# ══════════════════════════════════════════════════════════════════════════
ICON_STYLE = {
    "W":   "ellipse;fillColor=#DBEAFE;strokeColor=#1565C0;fontStyle=1;fontSize=9;",
    "TV":  "fillColor=#E0E0E0;strokeColor=#757575;fontStyle=1;fontSize=9;",
    "S":   "ellipse;fillColor=#F8CECC;strokeColor=#B85450;fontStyle=1;fontSize=9;",
    "Sub": "ellipse;fillColor=#D1D9DD;strokeColor=#5D6D7E;fontSize=8;",
    "LAN": "ellipse;fillColor=#DBEAFE;strokeColor=#1565C0;fontSize=8;",
    "IC":  "fillColor=#E1D5E7;strokeColor=#9673A6;fontSize=8;",
    "Cam": "ellipse;fillColor=#FFE6CC;strokeColor=#D79B00;fontSize=8;",
    "KP":  "fillColor=#FFF2CC;strokeColor=#D6B656;fontSize=8;",
    "AMP": "fillColor=#D5F5E3;strokeColor=#1E8449;fontSize=8;fontStyle=1;",
}

def device_icon(desc):
    d = desc.lower()
    if any(x in d for x in ["wifi","access point"," ap","wifi 7","wifi 6","outdoor ap"]):
        return "W"
    if "tv point" in d or "hdmi point" in d:
        return "TV"
    if any(x in d for x in ["speaker","ccm","isw","klipsch","am1"]):
        return "S"
    if "subwoofer" in d:
        return "Sub"
    if "data point" in d or "lan point" in d:
        return "LAN"
    if any(x in d for x in ["intercom","door controller","reader"]):
        return "IC"
    if any(x in d for x in ["camera","bullet","turret","dome","g6","g5","g4","g3"]):
        return "Cam"
    if "keypad" in d:
        return "KP"
    if any(x in d for x in ["sonos amp","marantz","cinema 50","m4 amp"]):
        return "AMP"
    return None

def is_headend_item(desc):
    d = desc.lower()
    return any(x in d for x in [
        "udm","dream machine","pro max switch","nvr","nvr pro","patch panel",
        "42u","rack cabinet","ups","hqp71","hqp","lutron link ps","lutron dali",
        "lqse","qseio","marantz m4","m4 2-channel","linkbasic",
    ])

def build_topology(project_data):
    proj = project_data["project"]
    floors = project_data.get("floors",[])
    cells = []

    cells.append(mk_cell("topo_hdr",
        f"{proj.get('name','')} | System Topology | Quote Ref: {proj.get('quote_ref','')} | D-One",
        "text;html=1;fillColor=#1C2B4A;strokeColor=none;fontColor=#FFFFFF;"
        "fontStyle=1;fontSize=13;align=left;verticalAlign=middle;spacingLeft=16;",
        0,0,1654,50))

    CTR_X, CTR_W, ctr_y = 700, 200, 70
    cells.append(mk_cell(uid("ch"),"HEAD-END RACK",
        "fillColor=#455A64;strokeColor=none;fontColor=#FFFFFF;fontStyle=1;"
        "fontSize=12;align=center;verticalAlign=middle;",
        CTR_X,ctr_y,CTR_W,30))
    ctr_y += 34

    headend_room = next((r for f in floors for r in f.get("rooms",[]) if r.get("is_headend")),None)
    core_ids = {}
    if headend_room:
        he_items = [i for i in headend_room.get("items",[]) if is_headend_item(i.get("description",""))]
        # Also add Main DB items (processors/amps)
        for f in floors:
            for r in f.get("rooms",[]):
                if r.get("name","").lower() in ["main db","db","distribution board"]:
                    he_items += [i for i in r.get("items",[]) if is_headend_item(i.get("description",""))]
        for item in he_items:
            desc = item.get("description","")
            lbl = desc
            for p in ["Ubiquiti UniFi ","UniFi ","Lutron "]:
                lbl = lbl.replace(p,"")
            if len(lbl)>26: lbl=lbl[:24]+"…"
            s = SYS_STYLE.get(item.get("system_category",""),{"fill":"#F5F5F5","stroke":"#9E9E9E"})
            cid = uid("he")
            core_ids[desc] = cid
            cells.append(mk_cell(cid,lbl,
                f"rounded=1;whiteSpace=wrap;html=1;fillColor={s['fill']};"
                f"strokeColor={s['stroke']};fontSize=9;",
                CTR_X,ctr_y,CTR_W,36))
            ctr_y += 40

    default_target = list(core_ids.values())[0] if core_ids else None
    if not default_target:
        rid = uid("rack")
        cells.append(mk_cell(rid,"Head-End Rack",
            "rounded=1;fillColor=#D6DBDF;strokeColor=#5D6D7E;fontSize=11;fontStyle=1;",
            CTR_X,ctr_y,CTR_W,50))
        default_target = rid

    LEFT_X, RIGHT_X, ROOM_W = 30, CTR_X+CTR_W+50, 190
    ICON_SIZE, ICONS_PER_ROW, ICON_GAP = 32, 4, 6
    ROOM_HEADER_H, FLOOR_H = 22, 28
    left_y = right_y = 70
    left_toggle = True

    for floor in floors:
        cells.append(mk_cell(uid("fl"),floor.get("level","").upper(),
            "text;fillColor=#1C2B4A;strokeColor=none;fontColor=#FFFFFF;"
            "fontStyle=1;fontSize=11;align=center;verticalAlign=middle;",
            LEFT_X,left_y,ROOM_W,FLOOR_H))
        cells.append(mk_cell(uid("flr"),floor.get("level","").upper(),
            "text;fillColor=#1C2B4A;strokeColor=none;fontColor=#FFFFFF;"
            "fontStyle=1;fontSize=11;align=center;verticalAlign=middle;",
            RIGHT_X,right_y,ROOM_W,FLOOR_H))
        left_y += FLOOR_H+4
        right_y += FLOOR_H+4

        for room in floor.get("rooms",[]):
            if room.get("is_headend"): continue
            icons = []
            for item in room.get("items",[]):
                icon = device_icon(item.get("description",""))
                if icon:
                    for _ in range(min(item.get("qty",1),4)):
                        icons.append(icon)
            if not icons: continue
            icon_rows = math.ceil(len(icons)/ICONS_PER_ROW)
            room_h = ROOM_HEADER_H + icon_rows*(ICON_SIZE+ICON_GAP)+10
            col_x = LEFT_X if left_toggle else RIGHT_X
            col_y = left_y if left_toggle else right_y
            room_id = uid("rm")
            cells.append(mk_cell(room_id,"",
                "rounded=1;fillColor=#FFFFFF;strokeColor=#90A4AE;",
                col_x,col_y,ROOM_W,room_h))
            cells.append(mk_cell(uid("rh"),room.get("name",""),
                f"fillColor=#1E3A5F;strokeColor=none;fontColor=#FFFFFF;"
                f"fontStyle=1;fontSize=10;align=left;verticalAlign=middle;spacingLeft=8;rounded=0;",
                col_x,col_y,ROOM_W,ROOM_HEADER_H))
            for i,ic in enumerate(icons):
                row,col2 = i//ICONS_PER_ROW, i%ICONS_PER_ROW
                ix = col_x+6+col2*(ICON_SIZE+ICON_GAP)
                iy = col_y+ROOM_HEADER_H+6+row*(ICON_SIZE+ICON_GAP)
                s = ICON_STYLE.get(ic,"ellipse;fillColor=#F5F5F5;strokeColor=#9E9E9E;fontSize=8;")
                cells.append(mk_cell(uid("ic"),ic,s,ix,iy,ICON_SIZE,ICON_SIZE))
            e_style = ("edgeStyle=orthogonalEdgeStyle;rounded=0;strokeColor=#90A4AE;strokeWidth=1.5;"
                      +(f"exitX=1;exitY=0.5;exitDx=0;exitDy=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0;" if left_toggle
                        else f"exitX=0;exitY=0.5;exitDx=0;exitDy=0;entryX=1;entryY=0.5;entryDx=0;entryDy=0;"))
            eid = uid("e")
            cells.append(f'<mxCell id="{eid}" value="" style="{e_style}" edge="1" source="{room_id}" target="{default_target}" parent="1"><mxGeometry relative="1" as="geometry"/></mxCell>\n')
            if left_toggle: left_y = col_y+room_h+12
            else:           right_y= col_y+room_h+12
            left_toggle = not left_toggle
        max_y = max(left_y,right_y)+10
        left_y = right_y = max_y

    leg_x = RIGHT_X+ROOM_W+30
    leg_y = 70
    cells.append(mk_cell(uid("lh"),"LEGEND",
        "fillColor=#37474F;strokeColor=none;fontColor=#FFFFFF;fontStyle=1;"
        "fontSize=11;align=center;verticalAlign=middle;",
        leg_x,leg_y,160,28))
    leg_y+=32
    for ik,il in [("W","WiFi AP"),("TV","TV/HDMI"),("S","Speaker"),("Sub","Subwoofer"),
                  ("LAN","Data Point"),("IC","Intercom/Access"),("Cam","IP Camera"),
                  ("KP","Lutron Keypad"),("AMP","Amplifier")]:
        s = ICON_STYLE.get(ik,"ellipse;fillColor=#F5F5F5;strokeColor=#9E9E9E;fontSize=8;")
        cells.append(mk_cell(uid("li"),ik,s,leg_x,leg_y,28,28))
        cells.append(mk_cell(uid("ll"),il,
            "text;strokeColor=none;fillColor=none;fontSize=10;align=left;verticalAlign=middle;",
            leg_x+34,leg_y,126,28))
        leg_y+=32

    return ('<mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1" '
            'tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
            'pageWidth="1654" pageHeight="1169" math="0" shadow="0">'
            '<root><mxCell id="0"/><mxCell id="1" parent="0"/>'
            + "".join(cells) +
            '</root></mxGraphModel>')


# ══════════════════════════════════════════════════════════════════════════
# PAGE 2 – ENGINEERING SCHEMATIC  (A1 landscape, bus-line layout)
# ══════════════════════════════════════════════════════════════════════════
import re as _re

PW, PH = 2339, 1654
HEADER_H2 = 60
SECTION_H2 = 28
CONTENT_Y2 = HEADER_H2 + SECTION_H2 + 8   # y = 96

# Column definitions — wider spacing gives clean routing room between buses and core
# key: (x, width, label, fill, border, bus_entry_y_on_target)
COLS = {
    "core":     (40,   210, "CORE INFRASTRUCTURE",   "#455A64",  "#37474F",  0.5),
    "network":  (330,  170, "WiFi & NETWORK",         "#D5E8D4",  "#82B366",  0.25),
    "security": (545,  170, "SECURITY",               "#FFE6CC",  "#D79B00",  0.5 ),
    "access":   (760,  170, "ACCESS CONTROL",         "#E1D5E7",  "#9673A6",  0.3 ),
    "lighting": (975,  170, "LIGHTING CONTROL",       "#FFF2CC",  "#D6B656",  0.5 ),
    "audio":    (1190, 190, "MULTIROOM AUDIO",        "#F8CECC",  "#B85450",  0.75),
    "cinema":   (1430, 190, "DOLBY ATMOS",            "#F8CECC",  "#B85450",  0.5 ),
    "video":    (1670, 170, "VIDEO DISTRIBUTION",     "#DAE8FC",  "#6C8EBF",  0.7 ),
}

# Row sizing
DEV_H2    = 32
DEV_GAP2  = 6
ROOM_LBL_H = 18
ROOM_GAP2 = 20
FLOOR_SEP = 10
BUS_OFFSET = 22   # px left of column start where the vertical bus sits
BUS_W      = 5    # bus rectangle width (px)


def mk_trunk_edge(eid, cable_col, src_x, src_y, via_y, tgt_x, tgt_y):
    """Trunk cable routed through a dedicated lane below all content.
    Path: bus-left-edge → drop to via_y → travel left to tgt_x → rise to tgt_y.
    Uses absolute geometry points (no source/target cells) so draw.io cannot
    re-route the line through device boxes in intermediate columns."""
    style = (f"rounded=0;strokeColor={cable_col};strokeWidth=2.5;")
    return (
        f'<mxCell id="{eid}" value="" style="{style}" edge="1" parent="1">'
        f'<mxGeometry relative="1" as="geometry">'
        f'<mxPoint x="{src_x}" y="{src_y}" as="sourcePoint"/>'
        f'<mxPoint x="{tgt_x}" y="{tgt_y}" as="targetPoint"/>'
        f'<Array as="points">'
        f'<mxPoint x="{src_x}" y="{via_y}"/>'
        f'<mxPoint x="{tgt_x}" y="{via_y}"/>'
        f'</Array>'
        f'</mxGeometry>'
        f'</mxCell>\n'
    )


def _port_range(dev_list):
    """Extract min/max port numbers from list of cable label strings."""
    nums = []
    for lbl in dev_list:
        m = _re.search(r'Port[s]?\s+(\d+)', lbl)
        if m: nums.append(int(m.group(1)))
    if not nums: return None, None
    return min(nums), max(nums)


def build_engineering(project_data):
    proj   = project_data["project"]
    floors = project_data["floors"]
    cells  = []

    # ── Page header ──
    cells.append(mk_cell("eng_hdr",
        f"ENGINEERING WIRING DIAGRAM  |  {proj['name']}  |  Quote Ref: {proj['quote_ref']}  "
        f"|  D-One  |  darren@d-one.co.za  |  021 012 5112",
        "text;html=1;strokeColor=none;fillColor=#1C2B4A;align=left;verticalAlign=middle;"
        "whiteSpace=wrap;rounded=0;fontColor=#FFFFFF;fontSize=12;fontStyle=1;spacingLeft=20;",
        0, 0, 2280, HEADER_H2))

    # ── Section headers ──
    for col_key, (cx,cw,lbl,fill,bdr,_ey) in COLS.items():
        fc = "#FFFFFF" if col_key == "core" else "#222222"
        cells.append(mk_cell(f"sec_{col_key}", lbl,
            f"text;html=1;strokeColor={bdr};fillColor={fill};fontColor={fc};"
            f"fontStyle=1;fontSize=10;align=center;verticalAlign=middle;",
            cx, HEADER_H2+2, cw, SECTION_H2))

    # ── Pre-scan: collect Lutron infrastructure from DB rooms ──────────────
    # Items like LQSE dimmers, DALI modules, QSEIO in "Main DB" belong in the
    # core column (they're rack/panel-mounted), not in the lighting room column.
    lutron_infra = []
    DB_ROOM_NAMES = {"main db", "db", "distribution board", "db room"}
    for floor in floors:
        for room in floor.get("rooms", []):
            if room.get("name","").lower() not in DB_ROOM_NAMES:
                continue
            for item in room.get("items", []):
                if item.get("system_category") != "Lighting Control":
                    continue
                desc = item["description"]
                if "keypad" in desc.lower():
                    continue          # keypads stay in the lighting column
                if "hqp" in desc.lower():
                    continue          # HQP71 already hardcoded above
                short = desc.replace("Lutron ","")
                qty = item.get("qty", 1)
                if qty > 1: short = f"{qty}× {short}"
                if len(short) > 26: short = short[:24] + "…"
                lutron_infra.append((uid("core_lt"), short, desc, "#FFF2CC","#D6B656"))

    # ── Core infrastructure: place devices and record their Y-midpoints ──
    CORE_X, CORE_W = 40, 210
    core_device_defs = [
        (CORE_IDS["isp"],      "ISP / WAN",         "Fibre Broadband Input",           "#DAE8FC","#6C8EBF"),
        (CORE_IDS["udm_max"],  "UDM-MAX",            "UniFi Dream Machine MAX",         "#D5E8D4","#82B366"),
        (CORE_IDS["sw_data"],  "Data Switch",        "Pro Max 24 (data/management)",    "#D5E8D4","#82B366"),
        (CORE_IDS["sw_poe"],   "PoE Switch",         "Pro Max 24 PoE  (APs + AMPs)",    "#D5E8D4","#82B366"),
        (CORE_IDS["sw_cam"],   "Camera Switch",      "Pro Max 16 PoE  (cameras)",       "#FFE6CC","#D79B00"),
        (CORE_IDS["nvr"],      "NVR Pro",            "UniFi NVR Pro",                   "#FFE6CC","#D79B00"),
        (CORE_IDS["rack"],     "42U Server Rack",    "Linkbasic 42U Cabinet",           "#DAE8FC","#6C8EBF"),
        (CORE_IDS["hqp"],      "Lutron HQP71",       "HomeWorks QSX Processor",         "#FFF2CC","#D6B656"),
    ] + lutron_infra + [
        (CORE_IDS["m4_1"],     "M4 Amp #1",          "Marantz 2-ch Power Amp",          "#F8CECC","#B85450"),
        (CORE_IDS["m4_2"],     "M4 Amp #2",          "Marantz 2-ch Power Amp",          "#F8CECC","#B85450"),
        # CINEMA 50 omitted — placed in Entertainment room in cinema column
    ]

    cy2 = CONTENT_Y2 + 4
    core_mid_y = {}   # cid → y-midpoint (for reference)
    for (cid, name, model, fill, bdr) in core_device_defs:
        lbl = f'<b>{name}</b><br><font style="font-size:7px;color:#555">{model}</font>'
        cells.append(mk_cell(cid, lbl,
            f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={bdr};"
            f"fontSize=9;verticalAlign=middle;arcSize=8;",
            CORE_X, cy2, CORE_W, DEV_H2+6))
        core_mid_y[cid] = cy2 + (DEV_H2+6)//2
        cy2 += DEV_H2 + 6 + DEV_GAP2

    # ── Core interconnects (vertical spine) ────────────────────────────────
    SFP  = CABLE_COL["sfp_dac"]
    CAT6 = CABLE_COL["cat6_data"]
    HW   = CABLE_COL["spanel_mylar"]

    cells.append(mk_edge_vert("ce_isp_udm",  "", SFP,  CORE_IDS["isp"],     CORE_IDS["udm_max"]))
    cells.append(mk_edge_vert("ce_udm_sw",   "", SFP,  CORE_IDS["udm_max"], CORE_IDS["sw_data"]))
    cells.append(mk_edge_vert("ce_sw_poe",   "", SFP,  CORE_IDS["sw_data"], CORE_IDS["sw_poe"]))
    cells.append(mk_edge_vert("ce_sw_cam",   "", SFP,  CORE_IDS["sw_poe"],  CORE_IDS["sw_cam"]))
    cells.append(mk_edge_vert("ce_cam_nvr",  "", CAT6, CORE_IDS["sw_cam"],  CORE_IDS["nvr"]))
    cells.append(mk_edge_vert("ce_sw_hqp",   "", CAT6, CORE_IDS["rack"],    CORE_IDS["hqp"]))

    # HQP71 → Lutron DB infra items (SPANEL G Mylar spine) → M4 amps
    prev_id = CORE_IDS["hqp"]
    for (cid, _, _, _, _) in lutron_infra:
        cells.append(mk_edge_vert(uid("ce"), "", HW, prev_id, cid))
        prev_id = cid
    cells.append(mk_edge_vert("ce_hqp_m4_1", "", HW, prev_id, CORE_IDS["m4_1"]))
    cells.append(mk_edge_vert("ce_hqp_m4_2", "", HW, CORE_IDS["m4_1"], CORE_IDS["m4_2"]))

    CORE_RX = CORE_X + CORE_W   # right edge of core column (x=250) — trunk entry point

    # ── Collect rooms per system column ──
    col_rooms = defaultdict(list)
    for floor in floors:
        fl_name = floor["level"]
        for room in floor.get("rooms", []):
            if room.get("is_headend"): continue
            if room.get("name","").lower() in ["main db"]: continue
            cols_seen = set()
            for item in room.get("items", []):
                col = CAT_TO_COL.get(item.get("system_category",""))
                if col and col not in cols_seen:
                    col_rooms[col].append((fl_name, room))
                    cols_seen.add(col)

    col_order = ["network","security","access","lighting","audio","cinema","video"]

    # ══ PHASE 1: lay out devices, collect bus data per column ══
    # No trunk edges yet — we need global_max_y first to set routing lanes.
    # ═══════════════════════════════════════════════════════════════════════
    all_col_data = {}   # col_key → {cells, bus_groups, max_y, BUS_X, TAP_W}

    for col_key in col_order:
        rooms_list = col_rooms.get(col_key, [])
        if not rooms_list: continue

        cx, cw, col_lbl, fill, bdr, _entry_y = COLS[col_key]
        BUS_X = cx - BUS_OFFSET
        TAP_W = BUS_OFFSET - BUS_W - 2

        col_cells = []
        col_y = CONTENT_Y2 + 4
        current_floor = None
        bus_devices = defaultdict(list)   # (cable_key, tgt_id) → [(dev_id, y_mid, lbl)]

        for (fl_name, room) in rooms_list:
            room_amp_id        = None   # Sonos AMP id, reset per room
            room_cinema_amp_id = None   # CINEMA 50 id, reset per room

            if fl_name != current_floor:
                if current_floor is not None:
                    col_y += FLOOR_SEP
                col_cells.append(mk_cell(uid("fl"), fl_name,
                    "text;strokeColor=none;fillColor=none;fontColor=#546E7A;"
                    "fontStyle=3;fontSize=8;align=left;verticalAlign=middle;",
                    cx+2, col_y, cw-4, 13))
                col_y += 15
                current_floor = fl_name

            cat_items = [i for i in room.get("items",[])
                         if CAT_TO_COL.get(i.get("system_category","")) == col_key]
            if not cat_items: continue

            col_cells.append(mk_cell(uid("rl"), room["name"],
                f"text;html=1;strokeColor={bdr};fillColor=#1C2B4A;fontColor=#FFFFFF;"
                f"fontStyle=1;fontSize=9;align=center;verticalAlign=middle;",
                cx, col_y, cw, ROOM_LBL_H))
            col_y += ROOM_LBL_H + 2

            for item in cat_items:
                desc  = item["description"]
                qty   = item.get("qty", 1)
                d_low = desc.lower()

                short = desc
                for p in ["Ubiquiti UniFi ","UniFi ","Lutron ","Bowers & Wilkins ","Marantz ","Klipsch "]:
                    short = short.replace(p,"")
                if qty > 1: short = f"{qty}× {short}"
                if len(short) > 32: short = short[:30]+"…"

                s = SYS_STYLE.get(item.get("system_category",""),{"fill":"#F5F5F5","stroke":"#9E9E9E"})
                dev_id    = uid("dv")
                dev_mid_y = col_y + DEV_H2 // 2

                col_cells.append(mk_cell(dev_id, short,
                    f"rounded=1;whiteSpace=wrap;html=1;fillColor={s['fill']};"
                    f"strokeColor={s['stroke']};fontSize=9;arcSize=10;",
                    cx, col_y, cw, DEV_H2))

                cable_key, cable_lbl, tgt = get_cable(desc, qty, sys_cat=item.get("system_category",""))

                if tgt is not None:
                    bus_devices[(cable_key, tgt)].append((dev_id, dev_mid_y, cable_lbl))
                    # Track in-room amps for local speaker wiring
                    if any(x in d_low for x in ["sonos amp","sonos s16"]) and col_key == "audio":
                        room_amp_id = dev_id
                    elif any(x in d_low for x in ["cinema 50","cinema50"]) and col_key == "cinema":
                        room_cinema_amp_id = dev_id
                elif tgt is None:
                    if col_key == "audio" and room_amp_id:
                        # Sonos AMP → speaker (right-side local curve)
                        qty_str = f"{qty}× " if qty > 1 else ""
                        col_cells.append(mk_local_edge(uid("sp"),
                            f"Speaker | Amp Ch.A & B Out → {qty_str}Speaker +/-",
                            CABLE_COL["speaker"], room_amp_id, dev_id))
                    elif col_key == "cinema" and room_cinema_amp_id:
                        # CINEMA 50 → speaker (right-side local curve, no label)
                        col_cells.append(mk_local_edge(uid("sp"), "",
                            CABLE_COL["speaker"], room_cinema_amp_id, dev_id))

                col_y += DEV_H2 + DEV_GAP2

            col_y += ROOM_GAP2

        all_col_data[col_key] = {
            "cells":       col_cells,
            "bus_devices": bus_devices,
            "max_y":       col_y,
            "BUS_X":       BUS_X,
            "TAP_W":       TAP_W,
        }

    # Emit all device / label cells now
    for col_key in col_order:
        if col_key in all_col_data:
            cells.extend(all_col_data[col_key]["cells"])

    # ══ PHASE 2: routing lanes (one dedicated horizontal lane per column) ══
    # Lanes sit below ALL device content so trunk cables never pass through
    # device boxes.  Rightmost columns (longest run) use the lowest lanes.
    # ═══════════════════════════════════════════════════════════════════════
    if all_col_data:
        global_max_y = max(d["max_y"] for d in all_col_data.values())
    else:
        global_max_y = CONTENT_Y2 + 400

    ROUTING_BASE = int(global_max_y) + 30   # first lane starts 30px below content
    LANE_STEP    = 18                        # px between successive lanes

    routing_lanes = {}
    for i, col_key in enumerate(col_order):
        # network=lane 0 (shortest run, highest y closest to content)
        # video=lane 6 (longest run, lowest y furthest from content)
        routing_lanes[col_key] = ROUTING_BASE + i * LANE_STEP

    # ══ PHASE 3: draw buses, tap stubs, and trunk edges ══
    for col_key in col_order:
        if col_key not in all_col_data: continue
        d       = all_col_data[col_key]
        BUS_X   = d["BUS_X"]
        TAP_W   = d["TAP_W"]
        via_y   = routing_lanes[col_key]

        for (cable_key, tgt_id), devs in d["bus_devices"].items():
            if not devs: continue
            cable_color = CABLE_COL.get(cable_key, "#607D8B")

            y_mids  = [dv[1] for dv in devs]
            bus_y1  = min(y_mids) - 6
            bus_y2  = max(y_mids) + 6
            bus_h   = max(bus_y2 - bus_y1, 4)
            bus_mid = (bus_y1 + bus_y2) / 2

            # 1. Vertical bus bar
            bus_id = uid("bus")
            cells.append(mk_cell(bus_id, "",
                f"fillColor={cable_color};strokeColor={cable_color};strokeWidth=0;",
                BUS_X, bus_y1, BUS_W, bus_h))

            # 2. Horizontal tap stubs (device left edge → bus right edge)
            for (dev_id, dev_y_mid, _) in devs:
                cells.append(mk_cell(uid("tap"), "",
                    f"fillColor={cable_color};strokeColor={cable_color};strokeWidth=0;",
                    BUS_X + BUS_W, dev_y_mid - 1, TAP_W, 2))

            # 3. Trunk edge: fixed waypoint path through routing lane
            tgt_y = core_mid_y.get(tgt_id, int(bus_mid))
            cells.append(mk_trunk_edge(
                uid("tr"), cable_color,
                int(BUS_X), int(bus_mid),
                int(via_y),
                CORE_RX,   int(tgt_y),
            ))

    # ── Cable legend ──
    LEG_X  = 1890
    leg_y  = CONTENT_Y2 + 4
    cells.append(mk_cell("leg_hdr", "CABLE LEGEND",
        "fillColor=#37474F;strokeColor=none;fontColor=#FFFFFF;fontStyle=1;"
        "fontSize=11;align=center;verticalAlign=middle;",
        LEG_X, leg_y, 220, 28))
    leg_y += 34

    legend_entries = [
        ("CAT6 UTP (Data)",        "cat6_data"),
        ("CAT6 UTP (PoE)",         "cat6_poe"),
        ("SFP+ DAC / Fibre",       "sfp_dac"),
        ("SPANEL G Mylar (Lutron)",  "spanel_mylar"),
        ("Speaker Cable",           "speaker"),
        ("HDMI 2.1",                "hdmi"),
        ("2-core Volt-free",        "voltfree"),
    ]
    for (leg_lbl, leg_key) in legend_entries:
        c = CABLE_COL[leg_key]
        cells.append(mk_cell(uid("ls"), "",
            f"fillColor={c};strokeColor={c};strokeWidth=0;",
            LEG_X, leg_y+8, 28, 6))
        cells.append(mk_cell(uid("lt"), leg_lbl,
            "text;strokeColor=none;fillColor=none;fontSize=9;align=left;verticalAlign=middle;",
            LEG_X+36, leg_y, 184, 22))
        leg_y += 28

    # ── Assemble ──
    return (f'<mxGraphModel dx="1422" dy="762" grid="1" gridSize="10" guides="1" '
            f'tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
            f'pageWidth="{PW}" pageHeight="{PH}" math="0" shadow="0">'
            f'<root><mxCell id="0"/><mxCell id="1" parent="0"/>'
            + "".join(cells) +
            f'</root></mxGraphModel>')


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════
def main():
    if len(sys.argv)<4:
        print("Usage: generate_drawio.py project_data.json product_research.json output.drawio")
        sys.exit(1)
    pdata_path, research_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    pdata = json.loads(Path(pdata_path).read_text(encoding="utf-8"))
    print(f"Building topology diagram for {pdata['project']['name']}...")
    topo = build_topology(pdata)
    print("Building engineering schematic...")
    eng  = build_engineering(pdata)
    output = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<mxfile host="D-One" version="21.0">\n'
        f'  {page_wrap("System Topology", topo)}\n'
        f'  {page_wrap("Engineering Schematic", eng)}\n'
        '</mxfile>'
    )
    Path(out_path).write_text(output,encoding="utf-8")
    sz = Path(out_path).stat().st_size
    print(f"✓ Saved: {out_path}  ({sz:,} bytes)")
    print("  Page 1: System Topology")
    print("  Page 2: Engineering Schematic (A1 landscape, port-labelled cables)")

if __name__=="__main__":
    main()
