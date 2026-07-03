---
name: d-one-technical-file
description: >
  D-One Technical File Generator. Use this skill whenever Darren or a D-One team member uploads a WeQuote PDF quote and asks for a technical file, technical pack, spec document, component schedule, conduit schedule, or wiring diagram. Also triggers for phrases like "generate the tech file", "create the technical documents", "make the conduit schedule", "draw the line drawing", or any combination of these for a D-One project. This skill automates the full technical documentation workflow from a single WeQuote quote PDF.
---

# D-One Technical File Generator

Takes a WeQuote project quote PDF and automatically generates the complete D-One technical file package:

1. **Component & Equipment Schedule** (PDF) — branded spec document with product photos, dimensions and room placement, matching the House Prinsloo format
2. **Conduit Schedule** (PDF) — electrician's document with conduit sizes, cable types and backbox specs, matching the 2 Nettleton Road format
3. **Engineering Wiring Diagram** (.drawio) — full system schematic with colour-coded cable types and specific port labelling, matching the Price Drive.drawio format

---

## Before you start

Read the reference files in this skill's `references/` directory:
- `wequote_parse_guide.md` — how to extract data from a WeQuote PDF
- `spec_doc_guide.md` — Component & Equipment Schedule format and HTML template
- `conduit_rules.md` — conduit schedule mapping rules by device type
- `drawio_style_guide.md` — draw.io XML structure, cable colours, device styles

The scripts in `scripts/` accept a `project_data.json` intermediate file as input. Generate this file in Phase 2 before running any scripts.

---

## Phase 1 — Parse the WeQuote PDF

Read the uploaded quote PDF carefully. Extract:

**Project metadata:**
- Project name (e.g. "Price Drive", "House Prinsloo")
- Client name
- Quote reference (e.g. "0179 R7")
- Date prepared
- Prepared by
- Valid to date

**Room inventory:**
WeQuote organises items under section headers formatted as `"Level: Room Name"` (e.g. `"L2 Ground: Living"`, `"Perimeter: Front Gate"`). For each section, extract every line item with its Qty and Description. Ignore pricing — only capture the bill of materials.

**Headend location:**
Identify the room containing the main network rack (usually named "Services", "Head End", "Server Room", or "Battery Room"). This is the central destination for most cable runs.

See `references/wequote_parse_guide.md` for the full extraction guide and the `project_data.json` schema.

---

## Phase 1b — Verify the parsed data (MANDATORY before proceeding)

Before moving to Phase 2, cross-check `project_data.json` against the original PDF. This step exists because LLM parsing of PDFs can silently hallucinate room names, invent devices, or drop rooms entirely.

Run this comparison:

```python
# List every room name in project_data.json
for floor in data["floors"]:
    for room in floor["rooms"]:
        print(room["full_name"])
```

Then scan the PDF for all section headers of the form `"Level: Room Name"` and confirm:

1. **No rooms missing** — every section header in the PDF has a matching entry in `project_data.json`
2. **No phantom rooms** — every room in `project_data.json` exists in the PDF (watch for renamed rooms like "Lounge" instead of "Living", or invented rooms like "Pool Bar")
3. **No extra floors** — confirm the floor list matches the PDF (e.g. a quote with only Perimeter / L1 Basement / L2 Ground should not produce an "L3 First Floor")
4. **Spot-check 3–4 rooms** — pick rooms at random and confirm the item list matches the PDF line items exactly. Pay attention to:
   - Devices that appear in one room in the PDF but were moved to another in the JSON
   - Qty mismatches (e.g. 2× keypad vs 1×)
   - Fabricated devices with no corresponding line item in the quote

**If discrepancies are found:** correct `project_data.json` directly before proceeding. Do not regenerate from the PDF — fix the specific errors.

**Do not proceed to Phase 2 until this check passes.** Generating documents from bad parse data produces incorrect technical files that have to be manually corrected after the fact (e.g. Sonos AMPs appearing in rooms that have no audio in the quote).

---

## Phase 2 — Research products

For each **unique** product description in the quote, do the following:

### 2a. Find product photo

Use `WebSearch` to find the manufacturer's product page, then `WebFetch` to retrieve the page and locate the product image URL. Then fetch the image directly with `WebFetch` and base64-encode it.

**Critical: the Python script cannot download images at runtime** (the bash sandbox blocks outbound HTTP). You must fetch each image yourself using the WebFetch tool and store the base64 result in `product_research.json` under `photo_b64`.

Workflow per product:
1. `WebSearch("{Product name} official product image site:ubnt.com OR site:sonos.com OR site:lutron.com OR site:bowerswilkins.com OR site:marantz.com OR site:klipsch.com")`
2. `WebFetch` the product page and extract the direct image URL from `<img>` or `og:image` meta tags
3. `WebFetch` the direct image URL to get the binary image
4. Store as `"photo_b64": "data:image/jpeg;base64,{base64string}"`

If an image cannot be retrieved after two attempts, set `photo_b64` to `null`. The script will show a grey placeholder box.

### 2b. Find dimensions

Search for exact physical dimensions: W × H × D in mm. For ceiling/wall speakers, find cutout diameter and depth. Check the manufacturer's tech specs or datasheet page.

### 2c. Find port specifications

For rack equipment and active devices (switches, gateways, AV receivers, amplifiers), identify all ports with their exact labels as printed on the hardware. These are used for accurate cable labelling in the wiring diagram. Example:
- UDM-MAX: "WAN: 1× 10G SFP+, LAN 1–8: 8× GbE RJ45, PoE 1–8: 802.3bt"
- Sonos AMP: "Speaker A+/A–, B+/B–, Ethernet: 1× GbE, USB-A: 1×"

Store everything in `product_research.json`. See `references/wequote_parse_guide.md` for the full schema.

**If a photo cannot be found:** leave `photo_b64` as `null` — the script handles missing photos gracefully.

---

## Phase 3 — Assign system categories

Map every product to a D-One system category using this table:

| Category | Badge Colour (CSS) | Typical Products |
|---|---|---|
| WiFi & Network | `#1565C0` (blue) | UniFi APs, switches, UDM-MAX, patch panels, CAT6 infrastructure |
| Video Distribution | `#7B1FA2` (purple) | TV points, HDMI, DSTV decoders, satellite dish, MATV |
| Intercom & Access Control | `#B71C1C` (red) | UniFi Access Intercom, door stations, reader stations, electric locks |
| Video Conferencing | `#00838F` (teal) | Interactive panels, conference displays, SKYE panels |
| Headend & Rack Cabinets | `#37474F` (dark slate) | Server racks, patch panels, UPS, PDU, rack shelves, 42U cabinets |
| Multiroom Audio | `#2E7D32` (green) | Sonos AMP, in-ceiling speakers, in-wall speakers, Klipsch, Sonance |
| Dolby Atmos Surround Sound | `#E65100` (orange) | AV receivers, surround speakers, subwoofers, in-wall cinema speakers |
| Lighting Control | `#F57F17` (amber) | Lutron keypads, Lutron HW-QS processor, dimmers, modules |
| Security & Surveillance | `#6A1B9A` (purple-dark) | UniFi cameras, NVR, motion sensors, alarm panels |

Save the `system_category` for every item into `project_data.json`.

---

## Session path — IMPORTANT

The bash sandbox session ID changes every conversation. Always detect the current session path at runtime:

```bash
SESSION=$(ls /sessions/ | head -1)
WORKSPACE="/sessions/${SESSION}/mnt/D-One workflow"
OUTPUTS="/sessions/${SESSION}/mnt/outputs"
SCRIPTS="${WORKSPACE}/d-one-technical-file/scripts"
```

Use `${OUTPUTS}`, `${WORKSPACE}`, and `${SCRIPTS}` in all subsequent commands.

---

## Phase 4 — Generate Component & Equipment Schedule (PDF)

Run:
```bash
SESSION=$(ls /sessions/ | head -1)
WORKSPACE="/sessions/${SESSION}/mnt/D-One workflow"
OUTPUTS="/sessions/${SESSION}/mnt/outputs"
SCRIPTS="${WORKSPACE}/d-one-technical-file/scripts"
cd ${OUTPUTS}
pip install weasyprint Pillow requests --break-system-packages -q
python ${SCRIPTS}/generate_spec_pdf.py \
  project_data.json \
  product_research.json \
  "{ProjectName}_Component_Schedule.pdf"
```

The script generates an HTML document styled to match the House Prinsloo Component & Equipment Schedule reference, then converts it to PDF via WeasyPrint.

See `references/spec_doc_guide.md` for the exact visual format.

**Output filename convention:** `{ProjectName}_Component_Schedule.pdf`
Example: `Price_Drive_Component_Schedule.pdf`

---

## Phase 5 — Generate Conduit Schedule (Excel)

Run:
```bash
SESSION=$(ls /sessions/ | head -1)
WORKSPACE="/sessions/${SESSION}/mnt/D-One workflow"
OUTPUTS="/sessions/${SESSION}/mnt/outputs"
SCRIPTS="${WORKSPACE}/d-one-technical-file/scripts"
cd ${OUTPUTS}
pip install openpyxl --break-system-packages -q
python ${SCRIPTS}/generate_conduit_xlsx.py \
  project_data.json \
  "{ProjectName}_Conduit_Schedule.xlsx"
```

The script applies the conduit mapping rules (see `references/conduit_rules.md`) and produces an editable Excel spreadsheet. The `.xlsx` format allows the team to edit entries after generation — add notes, adjust conduit sizes, reorder rows — without needing to re-run the script.

**Output filename convention:** `{ProjectName}_Conduit_Schedule.xlsx`

---

## Phase 6 — Generate Engineering Wiring Diagram (.drawio)

Run:
```bash
SESSION=$(ls /sessions/ | head -1)
WORKSPACE="/sessions/${SESSION}/mnt/D-One workflow"
OUTPUTS="/sessions/${SESSION}/mnt/outputs"
SCRIPTS="${WORKSPACE}/d-one-technical-file/scripts"
cd ${OUTPUTS}
python ${SCRIPTS}/generate_drawio.py \
  project_data.json \
  product_research.json \
  "{ProjectName}_Wiring_Diagram.drawio"
```

The script generates a two-page draw.io XML file:
- **Page 1 — System Topology:** room boxes with device icons connecting to a central head-end
- **Page 2 — Engineering Schematic:** A1 landscape (2339 × 1654 units), 8 system columns, port-labelled cables

**Layout — 8 system columns (left to right):**
1. **Core Infrastructure** (x=40, w=200) — UDM-MAX, Data Switch, PoE Switch, Camera Switch, NVR, Lutron HQP71, M4 Amps, Marantz CINEMA50
2. **WiFi & Network** (x=295) — APs grouped by room, cables: `CAT6 PoE | PoE Sw Port {n} → AP PoE In`
3. **Security** (x=515) — Cameras by room, cables: `CAT6 PoE | Cam Sw Port {n} → Camera PoE In`
4. **Access Control** (x=735) — Intercoms/door controllers, cables: `CAT6 | Data Sw Port {n} → Device LAN`
5. **Lighting Control** (x=955) — Lutron keypads by room, cables: `Cat5e HW | HQP Link Port {n} → Keypad`
6. **Multiroom Audio** (x=1175) — Sonos AMPs + speakers by room, AMP cables: `CAT6 PoE | PoE Sw Port {n} → Amp LAN`
7. **Dolby Atmos** (x=1415) — Cinema speakers, cables: `Speaker Cable | Cinema Rcvr Out → Speaker +/-`
8. **Video Distribution** (x=1655) — TV points, cables: `CAT6 | Data Sw Port {n} → TV Point ETH + HDMI`

**Port numbering rules:**
- Port counters are sequential per switch type (PoE switch, Data switch, Camera switch, HQP link ports)
- APs use PoE switch ports 1–N; Sonos AMPs continue from where APs left off on the same PoE switch
- If PoE ports exceed 24, this flags a real engineering issue — note it and split across two PoE switches
- HQP link ports: each keypad gets its own port number (the HQP71 supports up to 100 Lutron devices; the "port" label is the HW-Link bus connection number)

**Cable label format:** Always use `{CableType} | {SourcePort} → {DestPort}` — never just a cable type alone.

See `references/drawio_style_guide.md` for full style specification. The `Price_Drive_Wiring_Diagram.drawio` in the workspace root is the definitive reference example.

**Output filename convention:** `{ProjectName}_Wiring_Diagram.drawio`

---

## Phase 7 — Copy to workspace and save to Google Drive

Copy all three generated files to the workspace folder:
```bash
SESSION=$(ls /sessions/ | head -1)
WORKSPACE="/sessions/${SESSION}/mnt/D-One workflow"
OUTPUTS="/sessions/${SESSION}/mnt/outputs"
cp ${OUTPUTS}/{ProjectName}_Component_Schedule.pdf   "${WORKSPACE}/"
cp ${OUTPUTS}/{ProjectName}_Conduit_Schedule.xlsx     "${WORKSPACE}/"
cp ${OUTPUTS}/{ProjectName}_Wiring_Diagram.drawio     "${WORKSPACE}/"
```

Then search Google Drive for the client's project folder:
```
Search Google Drive for: "{ClientName}" or "{ProjectName}"
```

If found, tell Darren the folder location and advise him to upload the files there manually, or offer to use the Chrome browser tool to navigate to Drive and upload them. The Google Drive MCP is read-only, so direct upload via MCP is not possible.

Create a summary message like:
> "Three technical files are ready for **[Project Name]** (Quote Ref: [REF]):
> - [Component_Schedule.pdf](computer://...)
> - [Conduit_Schedule.pdf](computer://...)
> - [Wiring_Diagram.drawio](computer://...)
>
> Found your Google Drive folder at: [link]. Would you like me to upload these via Chrome, or will you upload them manually?"

---

## Troubleshooting

**WeasyPrint not available:** Try `pip install weasyprint --break-system-packages`. If fonts render poorly, ensure `fonttools` and `brotli` are installed too.

**Product photo download fails:** The script will insert a grey placeholder box with the product model number. This is acceptable — Darren can replace photos manually.

**Draw.io port labelling uncertain:** If port specifications for a device are not found via web search, label connections with cable type only and add a comment in the diagram: "(verify port)". Don't leave connections unlabelled.

**Quote has no headend room:** If there's no obvious server/headend room in the quote, ask Darren to confirm the head-end location before proceeding.

---

## Key D-One conventions

- All documents use **D-One branding**: header line reads `d·one | darren@d-one.co.za | 021 012 5112`
- Footer on every page: `{ClientName} | Quote Ref: {REF} | Prepared: {Date} | Valid to: {ValidDate} | Page N`
- The "■" checkbox icon appears in the Point column of the conduit schedule
- Room names in the spec doc are formatted as `■ {Floor}: {Room Name}` (dark navy header row)
- "(Prov)" suffix in room names means provisional — include these items but note they are provisional
- Prices are never shown in technical documents — only quantities and descriptions
