---
name: conduit-schedule
description: >
  Generate a D-One branded Conduit Schedule Excel (.xlsx) from a project quote (PDF or Excel)
  OR from a D-One annotated floorplan PDF (output of the floorplan-icons skill).
  Use this skill whenever the user says "make a conduit schedule", "build the conduit schedule",
  "conduit schedule for [project]", "first-fix conduit doc", or uploads a D-One quote or
  floorplan and asks for the installation or pre-wire document. Also trigger when the user
  asks to update, regenerate, or reformat an existing conduit schedule. The output is a
  print-ready A4 landscape Excel with D-One brand styling: dark-navy title bar, D-One-blue
  level headers, mid-blue area sub-headers, and alternating row shading — organised by
  area/room (not by system type).
---

# Conduit Schedule Skill

A conduit schedule is the document electricians use during first fix to know where to chase
conduit for every AV/tech device. It is organised by **area** (room by room), and for each
device lists: the point name, conduit size, where the cable runs to, cable type, backbox
type, and whether power is needed.

Before starting, read `references/device_specs.md` — it contains the full lookup table you
will need regardless of input type.

---

## Input Mode A — Quote PDF or Excel

Use this mode when the user uploads a D-One quote document.

### Step A1: Read the quote

Open the quote file (PDF or Excel) and read every page. Extract:
- Project name and quote reference number
- Floor / level breakdown (Basement, Ground, First, etc.)
- Every room / area and the devices installed in each one

Look for **field devices** — things physically mounted in rooms needing a conduit run.
Skip rack equipment (switches, processors, amps in a rack) — those have no conduit entry.

### Step A2: Map devices to specs

For every device extracted, look it up in `references/device_specs.md` (Device Lookup table).
If a device isn't listed, default to 25mm / CAT6 / Head-End / 4×4 and note it.

### Step A3: Build conduit_data.json

See the JSON schema in the **Build & Output** section below.

---

## Input Mode B — D-One Floorplan PDF (from floorplan-icons skill)

Use this mode when the user uploads a floorplan annotated by the D-One floorplan-icons skill.
The floorplan will have D-One blue icons (#1379C9) placed in each room, with room names
visible as text labels.

### Step B1: Render the floorplan flat

Use PyMuPDF to render the floorplan with annotations flattened into the image. The
`annots=True` flag is critical — without it the Stamp annotation icons won't appear.

```python
import fitz
doc = fitz.open("floorplan.pdf")
page = doc[0]
mat = fitz.Matrix(2.0, 2.0)          # 2× scale for better vision accuracy
pix = page.get_pixmap(matrix=mat, annots=True)
pix.save("/tmp/floorplan_flat.png")
doc.close()
```

### Step B2: Use vision to extract rooms and icons

Send the flattened image to Claude vision. Ask it to identify every room name and count
each icon type per room. The icons are D-One blue symbols — the model should recognise
them by shape.

```python
import anthropic, base64, json

with open("/tmp/floorplan_flat.png", "rb") as f:
    img_b64 = base64.standard_b64encode(f.read()).decode()

client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=3000,
    messages=[{
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": img_b64}
            },
            {
                "type": "text",
                "text": """This is a D-One branded floorplan. Blue icons (#1379C9) mark equipment
in each room. Room names are visible as text labels.

Identify every room/area name and count each icon type per room.

Possible icon types (match by visual shape):
wireless_access_point, tv, ceiling_speaker, wall_speaker, network_point,
intercom_door_station, facial_recognition_reader, intercom_receiver_panel,
amplifier, server_cabinet, motion_sensor, light_switch_keypad,
cctv_bullet, cctv_dome, motorised_blind, motorised_curtain,
spotlight, audible_sounder, touch_panel, exit_button

Also note the floor/level each room belongs to if shown (e.g. Ground Floor, First Floor,
Basement). If floor labels are not visible on the plan, group all rooms under "Ground Floor"
and note this.

Return ONLY valid JSON — no markdown:
{
  "project_name": "inferred from plan title if visible, else null",
  "floors": [
    {
      "level": "GROUND FLOOR",
      "rooms": [
        {
          "name": "Living Room",
          "icons": [
            {"type": "ceiling_speaker", "count": 2},
            {"type": "wireless_access_point", "count": 1}
          ]
        }
      ]
    }
  ]
}"""
            }
        ]
    }]
)

plan_data = json.loads(response.content[0].text)
```

### Step B3: Map icon keys to conduit specs

Use the **Icon → Device Lookup** table in `references/device_specs.md` to convert each
icon key into: point name, conduit size, destination, cable, backbox, power.

When a room has multiple icons of the same type (e.g. `ceiling_speaker × 2`), create a
separate item row for each one: "In-Ceiling Speaker 1", "In-Ceiling Speaker 2", etc.

Ignore `server_cabinet` and `spotlight` — these are rack/lighting circuit items that do
not generate conduit runs in the schedule.

If `tv` and `network_point` appear in the same room, they likely represent the same TV
point location. Combine them into a single "TV Point" row with conduit 2×25 rather than
creating two separate rows.

### Step B4: Build conduit_data.json

Use the mapped data to build the JSON (same schema as Mode A — see below).

For `level` names, use the floor labels from the floorplan. If the plan shows only one
floor, use the floor name directly (e.g. "GROUND FLOOR"). For multi-floor plans, map to
D-One convention: PERIMETER / L1 BASEMENT / L2 GROUND / L3 FIRST as appropriate.

---

## Build & Output

### JSON schema

```json
{
  "project_name": "Price Drive",
  "quote_ref": "0179 R10",
  "sections": [
    {
      "level": "PERIMETER",
      "areas": [
        {
          "name": "Front Gate",
          "items": [
            {
              "point": "Door Intercom (UA-G3-Intercom)",
              "conduit": "25",
              "destination": "Head-End",
              "cable": "CAT6",
              "backbox": "Flush round outdoor",
              "power": "No"
            }
          ]
        }
      ]
    }
  ]
}
```

**Point names** — include the product model in brackets where known:
- ✓ `WiFi AP (U7-PRO-XGS-W)`  ·  ✓ `In-Ceiling Speaker 1 (B+W CCM683)`
- When reading from a floorplan (Mode B), model is unknown — use generic name: `WiFi AP`, `In-Ceiling Speaker 1`

**TV Points** — always `"conduit": "2×25"`.

**Speaker pairs** — list as separate rows: Speaker 1, Speaker 2.

**Rack items** — omit (no conduit run needed).

### Run the build script

```bash
python scripts/build_conduit.py conduit_data.json \
  <ProjectName>_Conduit_Schedule_<QuoteRef>.xlsx
```

Save output to the outputs directory.

### Verify before presenting

- No conduit size is 20mm anywhere
- TV Points show 2×25
- Area count matches the source document
- Total rows are reasonable for the project size

Present the file to the user.

---

## Key Rules

| Rule | Detail |
|------|--------|
| Minimum conduit | 25mm — never 20mm |
| TV Points | Always 2×25mm |
| Organise by | Area (room), not by system type |
| Rack / head-end equipment | Omit — no conduit run needed |
| Speaker pairs | List each speaker as a separate row |
| Icon → device (Mode B) | Use the Icon → Device Lookup in device_specs.md |
| `server_cabinet` icon | Skip — it's the head-end rack, no field conduit |
| `spotlight` icon | Skip — lighting circuit, not AV conduit |
| `tv` + `network_point` same room | Merge into one "TV Point" row (2×25) |
