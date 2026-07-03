---
name: floorplan-icons
description: >
  Place D-One AV/tech icons onto a PDF floorplan to produce a branded equipment layout.
  Use this skill whenever the user uploads a floorplan (PDF or image) and asks to place,
  add, or mark equipment icons on it — even if they say things like "mark up the floor plan",
  "drop the icons on the plan", "show where the speakers go", "annotate the floorplan",
  or "create a floorplan layout". Always use this skill when a floorplan and icon placement
  are mentioned together. The output is a PDF where: (1) the floorplan is converted to
  black and white, (2) D-One icons are overlaid in brand blue (#1379C9) at the specified
  room locations, and (3) the official D-One legend image is embedded. The default
  output is a layered PDF where every icon is a Stamp annotation the user can drag
  around in Preview to fine-tune the layout.
---

# Floorplan Icons Skill

Overlay D-One AV/tech equipment icons onto a PDF floorplan. The floorplan is stripped
to black & white. Icons are placed in D-One brand blue (#1379C9). The official pre-built
D-One legend is embedded in the output. The default deliverable is a **layered PDF**:
the floorplan is the baked-in backdrop, and every icon (plus the legend) is a separate
Stamp annotation the user can drag around in Preview to fine-tune the layout — all in
one file, no unzipping.

---

## Brand Colour
**`#1379C9`** (RGB: 19, 121, 201) — used for all icon tinting and legend elements.

---

## Icon Library (Bundled)

The icon set is bundled inside this skill. There is **no need** to ask the user to
upload a ZIP — the assets live in the skill folder itself.

```
<SKILL_DIR>/
├── SKILL.md
├── scripts/
│   └── legend_builder.py   ← assembles the editable legend (used in Step 6)
└── Floorplan Icons/
    ├── manifest.json       ← source of truth for keys + labels
    ├── png_256/            ← 256px PNGs
    ├── png_512/            ← 512px PNGs (USE THESE — higher quality)
    ├── svg/                ← SVG versions
    └── legend/
        ├── D-One_Floorplan_Icon_Legend.png   ← visual reference only (flat raster)
        ├── D-One_Floorplan_Icon_Legend.pdf
        └── D-One Logo.png  ← used in the assembled legend frame
```

`<SKILL_DIR>` is the directory this `SKILL.md` lives in. Resolve it at runtime — when
the skill is invoked, the host tells you its base directory; use that.

**Always use `png_512/` for icon placement** (better quality when scaled on floorplans).

### Complete Icon Set (from manifest.json)

| Key | Label |
|---|---|
| `wireless_access_point` | Wireless Access Point |
| `tv` | TV |
| `ceiling_speaker` | Ceiling Speaker |
| `wall_speaker` | Wall Speaker |
| `network_point` | Network Point |
| `intercom_door_station` | Intercom (Door Station) |
| `facial_recognition_reader` | Facial Recognition Reader |
| `intercom_receiver_panel` | Intercom Receiver Panel |
| `amplifier` | Amplifier |
| `server_cabinet` | Server Cabinet |
| `motorised_blind` | Motorised Blind |
| `motorised_curtain` | Motorised Curtain |
| `motion_sensor` | Motion Sensor |
| `light_switch_keypad` | Light Switch Keypad |
| `cctv_bullet` | CCTV Camera — Bullet |
| `cctv_dome` | CCTV Camera — Dome |
| `spotlight` | Spotlight |
| `audible_sounder` | Audible Sounder |
| `touch_panel` | Touch Panel |
| `exit_button` | Exit Button |

At runtime, read `manifest.json` to get the live icon list. If the user references an
icon not in the manifest, suggest the closest match.

---

## House Style — D-One Default Layout

When the user asks for "our usual setup", "standard D-One layout", "mark it up the way
we normally do", or simply doesn't specify exact placements, apply these defaults. The
goal is consistency across projects so every D-One floorplan reads the same way.

The reasoning behind these defaults: most residential projects have a recurring pattern
of where equipment goes. Capturing that pattern here lets us deliver a complete-feeling
layout from a sparse brief, and gives the client something concrete to react to.

### Equipment-by-room defaults (D-One residential standard)

These rules are derived from a real completed project (House de Klerk, 2026) and
represent D-One's proven residential layout. Match room names flexibly — "Bed 1",
"Master Bedroom", and "Main Bedroom" all map to the master-bedroom profile; "ES",
"Ensuite", and "Main Ensuite" all map to ensuite; and so on.

| Room type | Equipment placed by default |
|---|---|
| **Plant / Technical Room** | `server_cabinet`, `amplifier`, `cctv_dome`, `light_switch_keypad` |
| **Entrance / Foyer** | `facial_recognition_reader`, `intercom_door_station`, `intercom_receiver_panel`, `light_switch_keypad` |
| **Lounge / Living Room** | `ceiling_speaker` ×2, `tv`, `network_point`, `touch_panel`, `wireless_access_point`, `light_switch_keypad` |
| **Kitchen** | `ceiling_speaker` ×2, `touch_panel`, `wireless_access_point`, `intercom_receiver_panel`, `light_switch_keypad` |
| **Scullery** | `touch_panel`, `wireless_access_point`, `light_switch_keypad` |
| **Dining Room** | `ceiling_speaker` ×2, `wireless_access_point`, `light_switch_keypad` |
| **Master Bedroom (Bed 1)** | `ceiling_speaker` ×2, `tv`, `network_point`, `touch_panel`, `wireless_access_point`, `intercom_receiver_panel`, `light_switch_keypad` |
| **Guest Bedrooms (Bed 2+)** | `light_switch_keypad` only |
| **Ensuite / Bathroom / WC** | `light_switch_keypad` only |
| **Garage (single or double)** | `cctv_dome`, `light_switch_keypad` |
| **Staff Room / Laundry** | `light_switch_keypad` only |
| **Double Volume / Void** | `light_switch_keypad` only |
| **Terrace / Patio (outdoor)** | `wall_speaker` ×2, `cctv_bullet` |
| **Gate / Driveway entry** | `facial_recognition_reader`, `intercom_door_station` |
| **Gym / Fitness room** | `ceiling_speaker` ×4 (one per corner), `light_switch_keypad` |

**KEY RULE — keypads everywhere:** D-One's standard is zero traditional wall switches.
Every room that has any lighting gets a `light_switch_keypad` placed just inside the
main door on the latch (handle) side. This covers ensuites, WCs, garages, staff rooms,
laundry, and double-volume spaces. When in doubt, add the keypad — the user can always
remove it in Preview.

**Items placed only on explicit request:** `motorised_blind`, `motorised_curtain`,
`motion_sensor`, `audible_sounder`, `exit_button`, `spotlight`.

### Speaker placement patterns

Speakers are always installed in pairs (or more), never as single units. The reasoning
is musical: a lone speaker creates a one-sided sound source, which feels off for any
proper listening or relaxation space. Stereo pairs give even coverage and the music
"sits" in the room rather than coming from a point on the ceiling.

**Default ceiling-speaker pattern (most rooms):** two speakers, one on the left of the
space and one on the right, spaced evenly along the room's long axis. Think of the
room as having a stereo "sweet spot" in the centre — place the two speakers so a
listener standing in the middle hears equal coverage from both sides.

**Gym pattern (always four):** four ceiling speakers, one in each corner of the room.
Gyms are typically larger, the user moves around a lot, and music drives the workout —
even coverage across the whole floor matters more than a defined sweet spot. Four
corner speakers solve this regardless of where the user is in the room.

**Wall-speaker pattern (patios/outdoor):** also pairs — one to the left and one to the
right of the main seating area, angled inward.

When applying this, qty defaults to 2 for ceiling speakers and wall speakers, and to 4
for any room labelled "gym", "fitness", or "exercise". Don't make the user spell this
out every time — it's the house default.

### Before placing — quick checklist

Run through this in your head (or with the user) before you start dropping icons:

1. **How many floors?** Some defaults (intercom receivers, WAP coverage) scale with floor count.
2. **Which way is north / where is west?** Needed for motorised blind placement. If the
   plan doesn't show a compass rose, ask.
3. **Where is the plant room / server location?** Server cabinet, amplifier, and CCTV
   dome all key off this.
4. **Where are the gates / front door?** Facial readers + intercom door stations go here.
5. **Are there light switches drawn on the plan?** If yes, light keypads replace them
   1:1. If the plan doesn't show switches, ask whether to place keypads at all.

If any of these are unclear, ask the user **once** for all the missing info at the start
rather than dripping questions across the workflow.

### Reading switches from the plan

Do not rely on switch symbols from the architect's drawing — they're often missing,
ambiguous, or invisible on scanned plans. Instead, apply the D-One rule directly:

**Every room that has lighting gets a keypad.** Use the room-type table above to decide
which rooms qualify. Place one `light_switch_keypad` per room near the door on the
latch (handle) side. Room-centre coordinates from Step 3 are a good starting position;
offset ~60–80 PDF pts toward the nearest door.

For rooms with multiple doorways (e.g. open-plan kitchen/dining), place keypads at each
main entrance. The user can drag any keypad to the exact position in Preview afterward.

### When "standard" isn't enough

The defaults above are a sensible starting point, not a contract. Always tell the user
what you placed and where, and invite corrections. The output is designed to be
editable (see Step 6) so refining the layout afterwards is expected, not a failure.

---

## Workflow

### Step 0 — Locate the bundled icon library

```python
import os

# Resolve <SKILL_DIR> from the path the host gave you when invoking this skill.
# Example shown — substitute with the actual path at runtime.
SKILL_DIR = "/path/to/skills/floorplan-icons"   # ← replace with real path

ICON_DIR   = os.path.join(SKILL_DIR, "Floorplan Icons", "png_512")
LEGEND_PNG = os.path.join(SKILL_DIR, "Floorplan Icons", "legend",
                          "D-One_Floorplan_Icon_Legend.png")
MANIFEST   = os.path.join(SKILL_DIR, "Floorplan Icons", "manifest.json")
BRAND_BLUE = (19, 121, 201)
```

The floorplan PDF still comes from the user (uploaded to `/mnt/user-data/uploads/` or
provided as a path). Only the floorplan needs to be uploaded — icons are bundled.

---

### Step 1 — Parse the task

Read the user's placement instructions. Extract:
- **Room name(s)** — e.g. "Boardroom", "Reception", "Server Room"
- **Icon key(s)** — match user's description to the manifest table above
- **Quantity** — default to 1 if not specified
- **Positional hints** — e.g. "north wall", "near the door" (use as a nudge)

If the user asks for "standard D-One layout" or doesn't specify equipment, derive the
plan from the **House Style** section above. Show the user the proposed equipment
list before you start placing, so they can add/remove things.

The output of this step is `room_plan` — a dict mapping each room name to a list of
`(icon_key, qty)` tuples. Steps 3–6 consume it.

If anything is ambiguous, ask before proceeding.

---

### Step 2 — Convert floorplan to black & white

Keep a copy of the **colour** original — vision in Step 3 (especially switch detection)
sometimes works better on the original than on the B&W version.

```python
import fitz
from PIL import Image, ImageOps

doc = fitz.open("/mnt/user-data/uploads/floorplan.pdf")
page = doc[0]
mat = fitz.Matrix(300/72, 300/72)  # 300 DPI
pix = page.get_pixmap(matrix=mat)
pix.save("/home/claude/floorplan_color.png")

color_img = Image.open("/home/claude/floorplan_color.png").convert("RGB")
bw_img    = ImageOps.grayscale(color_img)
base      = bw_img.convert("RGBA")
base.save("/home/claude/floorplan_bw.png")
```

---

### Step 3 — Identify room locations using PyMuPDF text extraction

Extract room label positions directly from the PDF using PyMuPDF's text extraction —
no API key or vision model needed. This works because architect PDFs contain actual
text objects for room labels; extracting their bounding boxes gives us the label's
centre in PDF point space, which we then convert to PNG pixel space.

```python
import fitz, json

SCALE = 300 / 72  # PDF pts → 300 DPI pixels (matches Step 2 render)

def get_room_coords(pdf_path, room_plan):
    """
    Extract centre coordinates (in PNG pixel space) for every room in room_plan.
    Returns a dict: {room_name: {"x": px, "y": py}}
    """
    doc = fitz.open(pdf_path)
    page = doc[0]
    ph = page.rect.height  # PDF point height (for y-axis flip)

    # Collect all text words with their bounding boxes
    words = page.get_text("words")  # [(x0,y0,x1,y1,text,block,line,word), ...]

    room_coords = {}
    for room_name in room_plan.keys():
        # Flexible match: try the full name, then individual tokens
        # (handles "Bed 1" matching word "Bed" near word "1", etc.)
        tokens = room_name.lower().split()
        best_match = None
        for w in words:
            word_text = w[4].lower().strip(".,:")
            if word_text == tokens[0]:
                # Found the first token — take this word's centre as a candidate
                wx = (w[0] + w[2]) / 2 * SCALE
                wy = (ph - (w[1] + w[3]) / 2) * SCALE  # flip y for PNG space
                # y in PDF is bottom-up; PNG is top-down, so flip
                wy_png = page.rect.height * SCALE - wy
                best_match = {"x": int(wx), "y": int(wy_png)}
                break
        if best_match:
            room_coords[room_name] = best_match
        else:
            print(f"  ⚠ Could not locate '{room_name}' in PDF text — will skip.")

    doc.close()
    return room_coords

room_coords = get_room_coords(IN_PDF, room_plan)
```

**Coordinate system note:** PyMuPDF's `get_text("words")` returns coordinates in PDF
point space where y=0 is the top of the page (PyMuPDF convention). Multiplying by
`SCALE` converts to 300 DPI pixels. No y-axis flip is needed for PNG space since
PyMuPDF already uses top-down coordinates in `get_text`.

**When text extraction misses a room:** Room labels sometimes appear as part of a
larger text block or use unusual capitalisation. If a room isn't found, try:
```python
# Broader search — get all text blocks and scan for partial matches
blocks = page.get_text("blocks")
for b in blocks:
    if room_name.lower() in b[4].lower():
        cx = (b[0] + b[2]) / 2 * SCALE
        cy = (b[1] + b[3]) / 2 * SCALE
        room_coords[room_name] = {"x": int(cx), "y": int(cy)}
        break
```

For rooms still not found after this, ask the user for a rough position hint such as
"top-left area" or "right side of ground floor".

**Perimeter equipment (CCTV bullet, outdoor speakers):** For equipment that goes
outside the building footprint, use the page margin area. Bullet cameras typically go
~150px outside the building's outer wall; use the building's bounding box (the outer
extent of all room labels) as a reference and offset outward.

---

### Step 4 — Compute icon positions

This step works out **where every icon goes** — a flat list of
`{"icon": icon_key, "px": int, "py": int, "room": room_name}` entries, where `px, py`
is the icon's top-left corner in the B&W image's pixel space. Step 6 turns that list
into movable Stamp annotations. You're computing coordinates here, not compositing —
though you can optionally paste onto a copy of `base` to render a quick preview thumbnail.

`room_plan` is the per-room equipment dict you built in Step 1 (room name → list of
`(icon_key, qty)`). `room_coords` is the centre-point lookup from Step 3.

```python
# Size icons at ~2.5% of the shorter page dimension
icon_size = max(50, int(min(base.size) * 0.025))
GAP = max(6, icon_size // 12)

def layout_room(icon_list, icon_size, gap, max_per_row=3):
    """Flatten (icon_key, qty) pairs into individual icons arranged in a centred
    grid. Wrapping to 3-per-row keeps busy rooms from bleeding into their neighbours."""
    flat = []
    for icon_key, qty in icon_list:
        flat.extend([icon_key] * qty)
    n = len(flat)
    rows = (n + max_per_row - 1) // max_per_row
    out = []
    for i, key in enumerate(flat):
        row, col = divmod(i, max_per_row)
        in_row = min(max_per_row, n - row * max_per_row)
        row_w = in_row * icon_size + (in_row - 1) * gap
        x_off = -row_w // 2 + col * (icon_size + gap)
        y_off = -((rows * icon_size + (rows - 1) * gap) // 2) + row * (icon_size + gap)
        out.append((key, x_off, y_off))
    return out

placements = []   # [{"icon", "px", "py", "room"}] — consumed by Step 6
placed_log = []   # [{"label", "qty", "room"}] — for the summary message to the user

for room_name, icon_list in room_plan.items():
    coords = room_coords.get(room_name)
    if not coords:
        print(f"⚠️ Could not locate '{room_name}' on the plan — skipping.")
        continue
    cx, cy = coords["x"], coords["y"]
    for icon_key, dx, dy in layout_room(icon_list, icon_size, GAP):
        px = max(0, min(cx + dx, base.width  - icon_size))
        py = max(0, min(cy + dy, base.height - icon_size))
        placements.append({"icon": icon_key, "px": px, "py": py, "room": room_name})
    for icon_key, qty in icon_list:
        placed_log.append({"label": icon_key.replace("_", " ").title(),
                           "qty": qty, "room": room_name})
```

Icons are tinted to brand blue **#1379C9** in Step 6, as each one is written into the
PDF — the tinting helper lives there. The alpha mask is always preserved so icon
shapes stay crisp.

---

### Step 4b — Quick sanity check

After computing `placements`, scan for obvious issues before writing the PDF:

- Any icon with `px < 0` or `py < 0` or `px > image_width` — clamp to page bounds.
- Rooms where no coordinates were found — list them for the user so they know what
  was skipped.
- Rooms where many icons were requested but the room is small (e.g. an ensuite with
  6 icons) — use a smaller `icon_size` for that room or reduce `max_per_row` so
  icons don't bleed into adjacent spaces.

Tell the user in the final message which rooms had icons placed, which were skipped,
and that they can drag any icon in Preview to fine-tune the layout.

---

### Step 5 — Decide legend placement

The legend is **assembled from editable parts**, not dropped on as a flat picture. It
has three layers (the actual code lives in `scripts/legend_builder.py`, called from
Step 6):

- a **frame** image — the panel, header bar, D-One logo, title, footer and row
  stripes. This is chrome; it goes down as one movable Stamp annotation.
- one **icon Stamp annotation per entry** — each legend symbol is its own object, so
  the user can copy a symbol straight out of the legend and paste it onto the plan.
- one **FreeText annotation per label** — the text is editable in Preview, so the user
  can rename "TV" to "TV — 65 inch", correct a term, etc.

Don't use the pre-built `D-One_Floorplan_Icon_Legend.png` for placement anymore — it's
a flat raster and nothing in it can be edited. It's still fine as a visual reference
for what the assembled legend should look like.

**Finding the best legend position — priority order:**

1. **Find open space outside the building** — Use vision to scan the floorplan for
   blank areas that sit outside the house footprint (beyond the outer walls). Typical
   candidates are the corners of the page, the strip between the building edge and the
   page border, or a large empty margin. Ask vision:
   *"Identify up to 3 candidate top-left positions (x, y) for placing a legend block
   [legend_w × legend_h]px OUTSIDE the building footprint — areas with no rooms, walls,
   or drawing content, and that do not clip the page edge. If no such space exists,
   say so. Return ONLY valid JSON:
   `{"candidates": [{"x": int, "y": int, "reason": "..."}], "open_space_found": bool}`"*
   Pick the candidate with the most whitespace around it. If at least one valid
   candidate exists, place the legend there.

2. **Place over the architect's own legend** — If no usable open space is found, ask
   vision to locate the architect's existing legend or key box:
   *"Where is the architect's legend or key box on this floorplan? Return ONLY valid JSON:
   `{"legend_box": {"x": int, "y": int, "w": int, "h": int}, "found": bool}`"*
   Centre the D-One legend over that box. The D-One legend is an opaque stamp that will
   cover the original — this is expected; the client only needs the D-One version.

3. **Last resort** — If vision cannot locate either (plan too dense, response ambiguous),
   fall back to `x = pad, y = pad` (~1% page margin, top-left). Note this in the
   delivery message so the user can drag it to a better position in Preview.

```python
# Estimate legend size (legend_builder sizes to ~20% page width by default)
legend_w = int(W * 0.20)
legend_h = int(legend_w * 1.6)   # rough aspect ratio
pad = max(10, int(W * 0.01))

with open("/home/claude/floorplan_bw.png", "rb") as f:
    img_b64 = base64.standard_b64encode(f.read()).decode()

client = anthropic.Anthropic()

# Step 5a: look for open space outside the building
space_resp = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=500,
    messages=[{
        "role": "user",
        "content": [
            {"type": "image",
             "source": {"type": "base64", "media_type": "image/png", "data": img_b64}},
            {"type": "text",
             "text": (
                 f"This is a {W}x{H}px floorplan. I need to place a legend block "
                 f"{legend_w}x{legend_h}px OUTSIDE the building footprint — in an "
                 "empty margin or corner beyond the outer walls, not overlapping any "
                 "rooms, walls, or drawing content, and not clipping the page edge. "
                 "Identify up to 3 candidate top-left positions. "
                 "If no such space exists, set open_space_found to false. "
                 "Return ONLY valid JSON:\n"
                 '{"candidates": [{"x": 0, "y": 0, "reason": "..."}], '
                 '"open_space_found": true}'
             )}
        ]
    }]
)
space_data = json.loads(space_resp.content[0].text)

if space_data.get("open_space_found") and space_data.get("candidates"):
    best = space_data["candidates"][0]
    legend_x = max(pad, min(int(best["x"]), W - legend_w - pad))
    legend_y = max(pad, min(int(best["y"]), H - legend_h - pad))
    legend_placement_note = f"D-One legend placed in open margin ({best.get('reason', 'outside building')})"
else:
    # Step 5b: overlay the architect's legend
    arch_resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image",
                 "source": {"type": "base64", "media_type": "image/png", "data": img_b64}},
                {"type": "text",
                 "text": (
                     "Where is the architect's legend or key box on this floorplan? "
                     "Return ONLY valid JSON:\n"
                     '{"legend_box": {"x": 0, "y": 0, "w": 0, "h": 0}, "found": false}'
                 )}
            ]
        }]
    )
    arch_data = json.loads(arch_resp.content[0].text)
    if arch_data.get("found") and arch_data.get("legend_box"):
        lb = arch_data["legend_box"]
        legend_x = max(pad, int(lb["x"] + lb["w"] / 2 - legend_w / 2))
        legend_y = max(pad, int(lb["y"] + lb["h"] / 2 - legend_h / 2))
        legend_placement_note = "D-One legend placed over architect's existing legend"
    else:
        # Last resort: top-left margin
        legend_x, legend_y = pad, pad
        legend_placement_note = "Legend placed top-left (no open margin found — drag to reposition in Preview)"
```

By default the legend lists **every icon in `manifest.json`** (the full reference set),
so the user has the whole palette to copy from and can delete rows they don't need. If
the user would rather see only the icons actually used on that floor, pass the filtered
list instead.

---

### Step 6 — Save output as a layered PDF (icons movable in Preview)

The user needs to move icons around after the fact, and they want to do it in **one
file** — no unzipping, no Freeform assembly. The solution is a **layered PDF**: the
B&W floorplan is the baked-in backdrop, and every icon (plus the legend) is a separate
**Stamp annotation** sitting on top. Stamp annotations are draggable in Preview — the
user clicks an icon, gets selection handles, and moves it freely, while the floorplan
underneath stays put. This is the **primary and default deliverable**.

Why a Stamp annotation and not `page.insert_image()`? `insert_image` bakes the icon
into the page content stream — it can't be moved. A Stamp annotation is a separate
object layer, which is exactly what Preview lets you reposition.

For this step you need a `placements` list — every icon with its final pixel position.
Build it up during Step 4 as you compute positions: each entry is
`{"icon": icon_key, "px": int, "py": int}` where `px, py` is the icon's top-left corner
in the B&W image's pixel space. (You can still composite onto `base` for a quick
preview thumbnail, but the layered PDF is built from `placements`, not from `base`.)

```python
import fitz  # PyMuPDF
from PIL import Image

# icon_size carries over from Step 4 (~2.5% of the shorter page dimension)
BW_PATH = "/home/claude/floorplan_bw.png"   # clean B&W backdrop, no icons baked in

def tint_to_temp(icon_key, colour=BRAND_BLUE):
    """Tint an icon brand-blue and save to a temp path; return that path."""
    icon = Image.open(os.path.join(ICON_DIR, f"{icon_key}.png")).convert("RGBA")
    r, g, b, a = icon.split()
    tinted = Image.merge("RGBA", [
        Image.new("L", icon.size, colour[0]),
        Image.new("L", icon.size, colour[1]),
        Image.new("L", icon.size, colour[2]),
        a,
    ])
    out = f"/tmp/_tinted_{icon_key}.png"
    tinted.save(out)
    return out

def add_image_stamp(page, doc, img_xref, rect, native=256):
    """Create a Stamp annotation backed by an image XObject — movable in Preview.
    `rect` is a fitz.Rect in PyMuPDF's top-left coordinate space."""
    annot = page.add_stamp_annot(rect, stamp=0)
    ap_xref = int(doc.xref_get_key(annot.xref, "AP/N")[1].split()[0])
    doc.xref_set_key(ap_xref, "BBox", f"[0 0 {native} {native}]")
    doc.xref_set_key(ap_xref, "Matrix", "[1 0 0 1 0 0]")
    doc.xref_set_key(ap_xref, "Resources/XObject/Icon", f"{img_xref} 0 R")
    doc.update_stream(ap_xref, f"q {native} 0 0 {native} 0 0 cm /Icon Do Q".encode())
    # add_stamp_annot squishes the rect to a default aspect ratio — overwrite the
    # /Rect directly so the icon stays square. PDF coords measure y from the bottom.
    ph = page.rect.height
    doc.xref_set_key(annot.xref, "Rect",
                     f"[{rect.x0} {ph - rect.y1} {rect.x1} {ph - rect.y0}]")
    return annot

# ---- build the layered PDF ----
bw = Image.open(BW_PATH)
W, H = bw.size

doc = fitz.open()
page = doc.new_page(width=W, height=H)          # 1pt == 1px keeps the maths trivial
page.insert_image(fitz.Rect(0, 0, W, H), filename=BW_PATH)   # backdrop, baked in

# Register every image as an XObject. The trick: insert each on a throwaway page to
# get its xref into the document, then delete those pages at the end — the xrefs
# survive because the annotations reference them. Stage EVERYTHING up front (floor
# icons + legend icons + legend frame) so the page reference is only invalidated once.
import json, sys
sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))
import legend_builder as LB   # bundled with this skill — see Step 5

with open(MANIFEST) as f:
    legend_entries = [(ic["key"], ic["label"]) for ic in json.load(f)["icons"]]

# Generate the legend frame (panel chrome only; no entry icons/labels)
frame_path, legend_meta = LB.make_legend_frame(
    legend_entries, BRAND_BLUE,
    logo_path=os.path.join(SKILL_DIR, "Floorplan Icons", "legend", "D-One Logo.png"),
    font_dir="/usr/share/fonts/truetype/dejavu")

# Every icon we need = floor placements ∪ all legend icons
needed_icons = {p["icon"] for p in placements} | {k for k, _ in legend_entries}
icon_xref, temp_pages = {}, []
for icon_key in sorted(needed_icons):
    tp = doc.new_page(width=256, height=256)
    tp.insert_image(fitz.Rect(0, 0, 256, 256), filename=tint_to_temp(icon_key))
    icon_xref[icon_key] = tp.get_images()[0][0]
    temp_pages.append(tp.number)

fr = Image.open(frame_path)
tp = doc.new_page(width=fr.width, height=fr.height)
tp.insert_image(fitz.Rect(0, 0, fr.width, fr.height), filename=frame_path)
frame_xref = tp.get_images()[0][0]
temp_pages.append(tp.number)

page = doc[0]   # re-fetch once — adding pages invalidated the earlier reference

# Floor equipment icons as movable stamps
for p in placements:
    rect = fitz.Rect(p["px"], p["py"], p["px"] + icon_size, p["py"] + icon_size)
    add_image_stamp(page, doc, icon_xref[p["icon"]], rect)

# Editable legend: frame stamp + per-entry icon stamps + FreeText labels.
# place_legend reuses the same add_image_stamp helper for the frame and the icons.
LB.place_legend(page, doc, legend_entries, x=legend_x, y=legend_y, display_w=int(W * 0.20),
                icon_xref=icon_xref, frame_xref=frame_xref, meta=legend_meta,
                add_image_stamp=add_image_stamp)

# Drop the throwaway staging pages — image xrefs survive via the annotations
for pno in sorted(temp_pages, reverse=True):
    doc.delete_page(pno)

out_pdf = "/mnt/user-data/outputs/floorplan_layered.pdf"
doc.save(out_pdf, garbage=1, deflate=True)
doc.close()
```

**Verify before delivering:** reopen the saved PDF and check the annotation counts —
`Stamp` should be (floor icons + 20 legend icons + 1 frame) and `FreeText` should be
20 (the legend labels). If `Stamp` is zero, the xrefs were garbage-collected — save
with `garbage=0` instead.

```python
d = fitz.open(out_pdf)
counts = {}
for a in d[0].annots():
    counts[a.type[1]] = counts.get(a.type[1], 0) + 1
print(counts)   # e.g. {'Stamp': 78, 'FreeText': 20}
d.close()
```

Use `present_files` to deliver the layered PDF. In your message, tell the user:
- Which icons were placed and in which rooms (summarise from `placements` / `placed_log`)
- That every floor icon can be dragged in Preview — click to select, drag to move; the
  floorplan underneath stays fixed
- That the legend is editable too: each legend symbol is its own object (copy one
  straight out of the legend onto the plan), each legend label is editable text
  (double-click to rename), and the whole legend frame can be repositioned
- Flag any rooms that could not be confidently located on the plan

**Optional second output — Freeform bundle.** If the user specifically wants to work in
Apple Freeform instead of Preview, also produce a ZIP with the clean B&W floorplan, the
individually-tinted icon PNGs, the legend, and a `placements.txt`. But don't produce
this by default — the layered PDF covers the common case in a single file.

---

## Notes & Edge Cases

- **"Standard layout" requests**: Default to the **House Style** rules above. Always
  show the user the proposed equipment list before placing — gives them a chance to
  edit before any work is done.
- **Orientation unknown**: Motorised blinds need west-facing windows. If the plan has
  no compass, ask the user before placing blinds.
- **Multi-floor plans**: Intercom receivers scale per floor; WiFi coverage is per
  floor. Confirm floor count up front.
- **Light keypads with no switches on plan**: Default to one keypad just inside each
  main room on the latch side of the door. Confirm with the user.
- **Network points = TV points**: Whenever you place a TV, place a network point at
  the same location automatically.
- **Room not found**: Ask user for a positional description or quadrant reference.
- **Multi-page PDFs**: Default to page 1 unless user specifies otherwise.
- **Icon scale**: ~2.5% of the shorter page dimension works for most A1/A3 floorplans.
  If the floorplan is very detailed or rooms are small, reduce to ~1.8%.
- **Multiple icons same room**: Arrange in a horizontal row from the room centre so
  they don't stack on top of each other. For rooms with many devices, wrap to a
  3-per-row grid rather than letting the row bleed into neighbouring rooms.
- **Speaker pairs (always)**: Ceiling and wall speakers are always at least a pair
  (one left, one right) — never a single speaker. See **Speaker placement patterns**
  in the House Style section. Position the pair on opposite sides of the room
  rather than next to each other.
- **Gym = four corners**: Any room labelled "gym", "fitness", or "exercise" gets
  four ceiling speakers — one in each corner — for even coverage as the user moves.
- **Server cabinet location is non-negotiable**: It belongs in a plant room or
  services room (labels like "plant room", "services", "electrical service & store",
  "comms room", or "store"). If the plan has none of those, ask the user where to
  put it — don't drop it into a habitable room as a fallback.
- **Legend placement**: Use vision to find open space outside the building footprint
  first (empty margins/corners beyond the outer walls). If no open space fits, overlay
  the architect's existing legend box. Only fall back to top-left if vision can't find
  either. Everything in the legend is movable/editable, so the user can rearrange it
  afterwards. Report where the legend landed in the delivery message.
- **Editable legend**: The legend is assembled, not pasted — a frame Stamp + one icon
  Stamp per entry + one FreeText label per entry. The user can copy a symbol straight
  out of the legend onto the plan, rename any label, or reposition the frame. The code
  lives in `scripts/legend_builder.py`; don't reach for the flat
  `D-One_Floorplan_Icon_Legend.png` for placement — it's reference-only now.
- **Editability**: The layered PDF *is* repositionable — every floor icon, every legend
  icon, and the legend frame are Stamp annotations; every legend label is a FreeText
  annotation. The floorplan backdrop is baked in on purpose, so it can't be nudged by
  accident. There's no separate "flat" version to produce — the layered PDF both looks
  finished and stays editable.
- **Verify annotations survived the save**: Always reopen the output and count
  annotations before delivering. A zero `Stamp` count means garbage collection dropped
  the image xrefs — re-save with `garbage=0`.
- **FreeText fonts**: legend labels use the built-in `helv` font so they render
  everywhere without font embedding. `legend_builder.py` needs the DejaVu TTFs (for the
  baked-in frame title/footer text) — on Linux they're at
  `/usr/share/fonts/truetype/dejavu`; it falls back to a default font if absent.
