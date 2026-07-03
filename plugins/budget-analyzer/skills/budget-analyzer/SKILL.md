---
name: budget-analyzer
description: >
  Analyze supplier and contractor quotes to derive per-unit budget averages for each D-One system.
  Upload any number of quotes in any format (PDF, Excel, Word). The skill reads each quote,
  extracts the system type, quantity of zones/components/access points, and pricing, then
  calculates per-unit averages across all quotes. Outputs a formatted Excel breakdown and a
  zone_prices.json ready to pass directly into the d-one-proposal skill.
  Trigger when the user says "analyze these quotes", "calculate per-zone cost", "build budget
  averages from quotes", "price out the proposal", or uploads quote files and asks for budget estimates.
---

# D-One Budget Analyzer Skill

You read supplier/contractor quotes, extract per-unit pricing for each D-One system, and produce
averaged rates. The output feeds directly into the proposal skill — no manual number-entry needed.

---

## Step 1 — Collect the Quote Files

Ask the user to upload their quote files if not already attached. Accept any format:
- PDF (supplier quotes, BOQs)
- Excel (.xlsx) — contractor schedules, rate cards
- Word (.docx) — narrative quotes, proposals
- Multiple files at once — one quote per file, or one file with multiple systems

**Ideal upload pattern — 3 tiers per system:**
For the most accurate pricing, ask the user to provide one quote per tier per system:
- CCTV Entry quote + CCTV Mid quote + CCTV Premium quote
- Audio Entry quote + Audio Mid quote + Audio Premium quote
- ...and so on for each system

This gives the proposal skill real tier prices (Entry/Mid/Premium card values) AND per-unit
rates for the zone/reader checkboxes — fully replacing the demo numbers.

If only some tiers or systems are covered, that's fine — missing tiers will fall back to TBD
in the proposal.

Confirm what was received: "Got X quotes across Y systems — reading them now."

---

## Step 2 — Read and Extract Data from Each Quote

For each file, read it fully using the appropriate method:
- PDF: use the `pdf` skill or Read tool to extract text
- XLSX: use the `xlsx` skill or Read tool
- DOCX: use the `docx` skill or Read tool
- Images: read them directly with vision

For each quote file, extract one or more entries. Each entry represents one system priced in
that quote. A single quote may cover multiple systems — create a separate entry for each.

**For each system found in the quote, identify:**

| Field | What to look for |
|---|---|
| `source` | Filename of the quote |
| `system` | One of: cctv, access-control, network, audio, home-theatre, lighting, system-integration |
| `tier` | Entry / Mid / Premium — infer from spec quality if not stated explicitly |
| `unit_type` | What the quantity refers to — see table below |
| `quantity` | Number of units (zones, cameras, readers, APs, circuits, rooms) |
| `supply_price` | Equipment / materials cost only (ex VAT if possible) |
| `install_price` | Labour / installation cost only |
| `total_price` | Supply + install combined. If only total given, use that |
| `notes` | Brief description of what's included |

**Unit types by system:**

| System | Unit type | What to count |
|---|---|---|
| audio | zone / room | Number of rooms/areas with speakers |
| access-control | reader / point | Number of facial recognition readers or intercom points |
| cctv | camera | Number of cameras |
| network | access-point | Number of Wi-Fi access points |
| lighting | circuit / zone | Number of lighting circuits or controlled zones |
| home-theatre | room | Number of cinema/TV rooms |
| system-integration | system | Treat as 1 unit (lump sum) |

**Extraction rules:**
- If a quote says "8-room audio system for R 96,000" → quantity=8, unit_type=zone, total=96000
- If supply and install are separate line items, record them separately
- If the quote covers both supply and install in one lump sum, put it all in total_price
- If VAT is included and clearly stated, note it and use ex-VAT figures
- If tier is unclear, make your best inference from the spec (basic gear = Entry, mid-range = Mid, premium brands = Premium)
- If quantity is ambiguous (e.g. "full house audio"), estimate based on context or note as approximate

**Do not skip any system** — if a quote covers 4 systems, extract 4 entries.

---

## Step 3 — Build the Structured Data Table

Compile all extracted entries into a JSON array:

```json
[
  {
    "source": "audio_quote_legrand.pdf",
    "system": "audio",
    "tier": "Mid",
    "unit_type": "zone",
    "quantity": 8,
    "supply_price": 64000,
    "install_price": 16000,
    "total_price": 80000,
    "per_unit_rate": 10000,
    "notes": "8-zone Sonos system, in-ceiling speakers, Legrand keypads"
  },
  {
    "source": "access_control_quote.pdf",
    "system": "access-control",
    "tier": "Mid",
    "unit_type": "reader",
    "quantity": 4,
    "supply_price": 72000,
    "install_price": 18000,
    "total_price": 90000,
    "per_unit_rate": 22500,
    "notes": "4x facial recognition readers, intercom, app control"
  }
]
```

Calculate `per_unit_rate = total_price / quantity` for each entry.

---

## Step 4 — Run the Analysis Script

Save the JSON data to a temp file and call analyze.py:

```bash
# Save extracted data to temp file
cat > /tmp/quote_data.json << 'JSONEOF'
[... your JSON array ...]
JSONEOF

# Run analysis
python3 /path/to/budget-analyzer/scripts/analyze.py \
  --data /tmp/quote_data.json \
  --output /Users/darrenswanepoel/Downloads/budget-analysis/
```

The script produces:
- `budget_analysis.xlsx` — full breakdown with raw data + averages summary
- `zone_prices.json` — per-unit averages ready for the proposal skill

---

## Step 5 — Present the Results

Share both output files with the user:
- **budget_analysis.xlsx** — full breakdown with raw data + averages
- **proposal_budgets.json** — the file to feed into the proposal skill

Show a plain-language summary:

**Tier card prices (from quotes):**
```
CCTV:            Entry R 55,000  ·  Mid R 90,000  ·  Premium R 160,000
Access Control:  Entry R 35,000  ·  Mid R 70,000  ·  Premium R 130,000
Audio:           Entry R 40,000  ·  Mid R 80,000  ·  Premium R 180,000
...
```

**Per-unit add-on rates (for zone checkboxes):**
```
Audio:           R 10,500 per zone   (avg across quotes)
Access Control:  R 22,000 per reader (avg across quotes)
```

Then tell the user how to use it in the proposal:

> "To use these prices in a proposal, just say:
> **'Make a proposal for [Client], use the budget file at [path]'**
> The proposal skill will read the file and use all the real prices automatically."

The exact generate.py command for reference:
```bash
python3 scripts/generate.py \
  --client "[Client]" \
  --project "[Project]" \
  --output /Users/darrenswanepoel/Downloads/proposal-[slug]/ \
  --budgets-file '/Users/darrenswanepoel/Downloads/budget-analysis/proposal_budgets.json'
```

---

## Step 6 — Handle Edge Cases

**Quote covers a full system with no zone breakdown:**
- If total price is given but no zone count, ask the user: "This quote doesn't break down by zone
  — do you know roughly how many zones/rooms/cameras it covers?"
- If not, record it with quantity=null and exclude from per-unit averages but include in notes.

**Wildly different rates across quotes:**
- Flag outliers (rates more than 40% above/below the average) and note them in the Excel.
- Ask the user: "One quote is significantly higher/lower — do you want to include or exclude it?"

**Mixed supply-only and supply+install quotes:**
- Keep them separate in the raw data sheet.
- For averages, use comparable like-for-like quotes (both supply+install, or both supply-only).

**VAT:**
- Always use ex-VAT figures for averages.
- If VAT is included and rate is not stated, assume 15% South African VAT and divide by 1.15.
