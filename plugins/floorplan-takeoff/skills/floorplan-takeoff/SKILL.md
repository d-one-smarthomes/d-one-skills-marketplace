---
name: floorplan-takeoff
description: >
  Generate a component quantities spreadsheet (.xlsx) from an annotated floor plan PDF. Use
  this skill whenever the user uploads a floor plan PDF (AV layout, equipment drawing, or
  similar annotated plan) and asks to count components, create a quantities table, do a
  material takeoff, list what's on the drawing, or produce a schedule of equipment. Also
  trigger when the user says things like "how many of each item are on the plan", "create a
  BOM from this drawing", "extract quantities from the floorplan", or "update the quantities
  based on this drawing". Works for D-One AV layouts, general AV/tech equipment drawings,
  and any annotated floor plan where icons represent physical components.
---

# Floorplan Component Takeoff

You produce an Excel (.xlsx) quantities spreadsheet from an annotated floor plan PDF. The
output has one tab per floor (or per PDF if floors are separate files) plus a **Summary** tab
that totals everything across all floors.

## Overview of the workflow

1. Identify the legend and icon types from the drawing
2. Tile each floor plan into readable sections and count every icon, by room
3. Exclude legend stamps (they appear in a bordered legend box, not on the floor plan itself)
4. Apply any applicable business rules (e.g. amplifier ratio — see below)
5. Build the spreadsheet with openpyxl, run recalc.py, verify zero errors
6. Save and present the file

## Step 1 — Read the legend

Before counting anything, render a crop of the legend area to identify every icon type and
its label. The legend is almost always in a bordered box in one corner (commonly top-left or
bottom-right). Note the PDF coordinate bounds of the legend box — you will need them to
exclude legend stamps from the floorplan count.

If no legend is visible, infer icon types from their visual appearance and note any uncertainty.

## Step 2 — Tile and count

Large floor plan PDFs are often a single high-resolution page. Tile each page into a grid of
overlapping sections (typically 3×5 or 4×5 at 150–200 DPI) and read each tile systematically.

For each tile:
- Identify the room(s) visible
- Count every icon of each type, noting the room it belongs to
- Skip any stamps whose coordinates fall within the legend bounding box

Keep a running tally by room. When a room spans multiple tiles, accumulate across tiles.

If the PDF has extractable PDF annotations (stamps/widgets), parse them programmatically using
PyMuPDF (`fitz`) — this is faster and more accurate than visual counting. Filter out legend
annotations by their coordinates:

```python
import fitz
doc = fitz.open("plan.pdf")
page = doc[0]
annots = [a for a in page.annots()]
# Filter: exclude annots whose rect.tl is inside the legend bounding box
```

Confirm ambiguous icons visually by rendering a tight crop around them.

## Step 3 — Business rules

Apply these rules after counting, before writing the spreadsheet:

**Amplifier ratio:** For every 2 ceiling or wall speakers on a floor, add 1 amplifier to the
rack/technical room on that floor (round up). This is in addition to any amplifiers explicitly
shown on the drawing. If the drawing already shows amplifiers, use the higher of the two counts.

Example: 14 ceiling speakers on First Floor → 7 amplifiers (plus any shown on drawing).

If other project-specific rules apply (the user may mention them), apply those too.

## Step 4 — Build the spreadsheet

Use **openpyxl** (not pandas) so formulas and formatting are preserved.

### Structure
- One sheet per floor, named clearly (e.g. "Ground Floor", "First Floor")
- A "Summary" sheet that cross-references floor totals using formulas (e.g. `='Ground Floor'!B15`)
- All totals as Excel `SUM()` formulas — never hardcoded Python calculations

### Formatting
- Brand blue header rows: hex `#1379C9`, white bold Arial text
- Alternating row shading: `#D6E8F7` / white
- Column A: Room name (left-aligned, width 22)
- Columns B+: one column per component type (center-aligned, width 13, wrap header text)
- Totals row at the bottom of each floor sheet, bold, light grey fill `#E8E8E8`
- Freeze panes at B3 on each floor sheet

### After saving, always recalculate:
```bash
python scripts/recalc.py output.xlsx 30
```
Fix any errors before presenting the file. Zero errors is mandatory.

## Step 5 — Save and present

Save the file to the outputs folder. Name it descriptively, e.g.
`{ProjectName}_AV_Component_Count.xlsx`. Use `mcp__cowork__present_files` to deliver it.

Include a brief summary of what was counted:
- Totals per floor (number of items)
- Grand total
- Any ambiguous counts or items worth double-checking on the drawing

## Tips for accuracy

- Render at ≥150 DPI for counting; 300 DPI for ambiguous icons
- Always verify uncertain icons with a tight crop before assigning them
- If a room label isn't visible in a tile, infer from adjacent tiles or the full-plan overview
- For multi-storey buildings where floors are in separate PDFs, process each PDF as its own floor sheet
- Items that appear in service corridors, risers, or plant rooms should be assigned to those
  specific rooms rather than lumped into "Other"
