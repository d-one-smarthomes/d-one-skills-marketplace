# Engineering Wiring Diagram — Draw.io Style Guide

Based on the Price Drive.drawio reference file.

---

## Canvas setup

```xml
<mxGraphModel dx="1422" dy="762" grid="1" gridSize="10" guides="1"
  tooltips="1" connect="1" arrows="1" fold="1" page="1"
  pageScale="1" pageWidth="2339" pageHeight="1654"
  math="0" shadow="0">
  <root>
    <mxCell id="0"/>
    <mxCell id="1" parent="0"/>
    <!-- all content cells here -->
  </root>
</mxGraphModel>
```

- Page size: A1 landscape (2339 × 1654 in draw.io units at 1:1)
- Use A1 for large projects, A2 (1654 × 1169) for smaller ones
- Grid: 10 units

---

## Title / Header cell

Full-width header bar across the top of the canvas:

```xml
<mxCell id="header" value="&lt;b&gt;ENGINEERING WIRING DIAGRAM&lt;/b&gt;&lt;br&gt;
{ProjectName} | Quote Ref: {QuoteRef} | D-One | darren@d-one.co.za | 021 012 5112"
  style="text;html=1;strokeColor=none;fillColor=#1C2B4A;align=left;verticalAlign=middle;
  whiteSpace=wrap;rounded=0;fontColor=#FFFFFF;fontSize=14;fontStyle=1;
  spacingLeft=20;"
  vertex="1" parent="1">
  <mxGeometry x="0" y="0" width="2200" height="60" as="geometry"/>
</mxCell>
```

---

## Cable type legend panel

Place at far right of canvas (x ≈ 2050, y ≈ 80). A titled box listing all cable types used in this diagram.

```xml
<!-- Legend title -->
<mxCell value="CABLE LEGEND" style="text;fillColor=#37474F;fontColor=#FFFFFF;
  fontStyle=1;fontSize=11;align=center;strokeColor=none;" vertex="1" parent="1">
  <mxGeometry x="2060" y="80" width="200" height="30" as="geometry"/>
</mxCell>
```

For each cable type present in the diagram, add a coloured line sample + label:

| Cable Type | Colour | Hex |
|---|---|---|
| CAT6 UTP (Data) | Blue | `#1565C0` |
| CAT6 UTP (PoE) | Green | `#2E7D32` |
| SFP+ DAC / Fibre | Teal | `#006064` |
| SPANEL G Mylar (Lutron) | Orange | `#E65100` |
| 2-core volt-free | Grey | `#455A64` |
| Speaker Cable | Red | `#B71C1C` |
| Mains 3-core | Brown | `#3E2723` |
| HDMI 2.1 | Amber | `#F57F17` |
| RS-232/485 | Purple | `#6A1B9A` |
| RF Wireless (dashed) | Pink | `#AD1457` |

Only include cable types that actually appear in this project's diagram.

---

## System section colours (device box fills)

| System | Fill Colour | Border |
|---|---|---|
| Network / WiFi | `#D5E8D4` | `#82B366` |
| Lighting Control | `#FFF2CC` | `#D6B656` |
| AV / Audio | `#F8CECC` | `#B85450` |
| Security | `#FFE6CC` | `#D79B00` |
| Access Control | `#E1D5E7` | `#9673A6` |
| Sensors | `#F5F5F5` | `#666666` |
| Headend / Infrastructure | `#DAE8FC` | `#6C8EBF` |

---

## Layout structure

The diagram is organised in vertical columns on an **A1 landscape canvas (2339 × 1654 units)**. Use compact row sizing so that large projects (20+ rooms) fit without scrolling.

```
Col 0          Col 1      Col 2      Col 3        Col 4           Col 5         Col 6        Col 7
[CORE INFRA] [NETWORK] [SECURITY] [ACCESS CTRL] [LIGHTING] [MULTIROOM AUDIO] [DOLBY ATMOS] [VIDEO]
  x=40,w=200  x=295,w=165 x=515,w=165 x=735,w=165 x=955,w=165  x=1175,w=185  x=1415,w=185 x=1655,w=165
```

Legend panel at x=1882, w=220.

**Core Infrastructure (Column 0, leftmost) — signal flow order, top to bottom:**
1. ISP / WAN Input
2. Gateway (UDM-MAX or equivalent)
3. Data Distribution Switch (non-PoE, general LAN)
4. PoE Distribution Switch (APs, Sonos AMPs, cameras if no dedicated switch)
5. Camera/Security Switch (PoE, dedicated to cameras)
6. NVR
7. Rack Cabinet
8. Lighting Processor (Lutron HQP)
9. Lighting Amps (Lutron M4/P4, if present)
10. AV Receiver / Cinema Amp (Marantz CINEMA 50, etc.)

Core device IDs use descriptive prefixes: `core_udm_max`, `core_sw_data`, `core_sw_poe`, `core_sw_cam`, `core_nvr_pro`, `core_rack`, `core_hqp71`, `core_m4_amp1`, `core_cinema50`, etc.

**System columns (Columns 1–7):**
Each column is dedicated to one system. Within a column:
- A small italic floor label (e.g. "L2 Ground") marks the start of each floor group
- A dark navy room label bar (`fillColor=#1C2B4A`) precedes the devices for each room
- Device boxes use the system fill/border colours from the table above

**Compact row sizing for large projects:**
- Device box height: 32px
- Room label height: 18px
- Gap between devices: 6px
- Gap between rooms: 18px
- Gap between floors: 10px (extra, before floor label)
- Content starts at y=96 (header 60px + section header 28px + 8px margin)

---

## Device box style

Standard device box:
```xml
<mxCell value="{DeviceName}&lt;br&gt;&lt;font style='font-size:8px'&gt;{Model}&lt;/font&gt;"
  style="rounded=1;whiteSpace=wrap;html=1;fillColor={systemFill};strokeColor={systemBorder};
  fontSize=9;fontStyle=0;verticalAlign=middle;arcSize=10;"
  vertex="1" parent="1">
  <mxGeometry x="{x}" y="{y}" width="120" height="40" as="geometry"/>
</mxCell>
```

**Room label box** (above device group):
```xml
<mxCell value="{Floor}: {RoomName}"
  style="text;html=1;strokeColor=#1C2B4A;fillColor=#1C2B4A;fontColor=#FFFFFF;
  fontStyle=1;fontSize=10;align=center;verticalAlign=middle;"
  vertex="1" parent="1">
  <mxGeometry x="{x}" y="{y}" width="160" height="24" as="geometry"/>
</mxCell>
```

**Section header** (above each system column):
```xml
<mxCell value="{SYSTEM NAME}"
  style="text;html=1;strokeColor={border};fillColor={fill};fontColor=#FFFFFF;
  fontStyle=1;fontSize=12;align=center;verticalAlign=middle;"
  vertex="1" parent="1">
  <mxGeometry x="{x}" y="70" width="200" height="30" as="geometry"/>
</mxCell>
```

---

## Edge (cable connection) style

```xml
<mxCell value="{CableLabel}"
  style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;
  jettySize=auto;exitX=1;exitY=0.5;exitDx=0;exitDy=0;
  entryX=0;entryY=0.5;entryDx=0;entryDy=0;
  strokeColor={cableColour};strokeWidth=2;fontSize=9;
  fontColor={cableColour};labelBackgroundColor=none;"
  edge="1" source="{sourceId}" target="{targetId}" parent="1">
  <mxGeometry relative="1" as="geometry"/>
</mxCell>
```

**Cable label format:** Always `{CableType} | {SourcePort} → {DestPort}`. Never just a cable type alone.

| Device type | Cable | Source | Destination |
|---|---|---|---|
| WiFi AP | CAT6 PoE | `PoE Sw Port {n}` | `AP PoE In` |
| IP Camera | CAT6 PoE | `Cam Sw Port {n}` | `Camera PoE In` |
| Sonos AMP | CAT6 PoE | `PoE Sw Port {n}` | `Amp LAN` |
| In-ceiling speaker | Speaker Cable | `Amp Ch.A/B Out` | `Speaker +/-` |
| Lutron Keypad | SPANEL G Mylar | `HQP Bus Port {n}` | `Keypad` |
| Intercom terminal | CAT6 | `Data Sw Port {n}` | `Intercom LAN` |
| Access controller | CAT6 | `Data Sw Port {n}` | `Access Ctrl LAN` |
| TV Point | CAT6 | `Data Sw Port {n}` | `TV Point ETH + HDMI` |
| Data point | CAT6 | `Data Sw Port {n}` | `Data Point` |
| Cinema speakers | Speaker Cable | `Cinema Rcvr Out` | `Speaker +/-` |
| UDM → Data Switch | SFP+ DAC | `UDM SFP+1` | `Data Sw SFP+1` |
| Data → PoE Switch | SFP+ DAC | `Data Sw SFP+2` | `PoE Sw SFP+1` |
| Data → Cam Switch | SFP+ DAC | `Data Sw SFP+3` | `Cam Sw SFP+1` |

Port counters are sequential and shared within a switch type. APs use the PoE switch first; Sonos AMPs continue on the same counter. If the PoE switch (24 ports) is exceeded, flag the overflow as a design note in the diagram.

---

## Spacing guidelines

- Core infrastructure column: x=40, width=200
- System columns: width=165–185px, spaced ~220px apart (column + 40px gap)
- Device box height: 32px (compact), 38px (rack equipment)
- Room label height: 18px
- Vertical gap between devices: 6px
- Vertical gap between rooms: 18px
- Floor separator: 10px + 13px italic floor label

---

## Routing rules

- All edges use `orthogonalEdgeStyle` (right-angle bends, no diagonals)
- Endpoint devices exit LEFT (`exitX=0;exitY=0.5`) → core device enters RIGHT (`entryX=1;entryY=0.5`)
- Core interconnects (ISP → UDM → switches) exit BOTTOM → enter TOP (vertical flow)
- Use waypoints sparingly — let draw.io auto-route where possible
- Avoid edge crossings by ordering rooms top-to-bottom across columns in the same sequence

---

## Cell ID conventions

Use descriptive IDs to avoid conflicts:
- `core_udm_max` — gateway device in core
- `core_sw_data` — data distribution switch
- `net_lounge_ap1` — lounge WiFi AP
- `audio_dining_amp` — dining Sonos AMP
- `edge_lounge_ap1_to_sw_poe` — cable from lounge AP to PoE switch
