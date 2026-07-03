---
name: lighting-takeoff
description: >-
  Count lighting items off an electrical / lighting layout floorplan PDF and
  produce a per-floor quantity spreadsheet. Use this skill whenever the user
  gives you one or more lighting-plan or electrical-layout PDFs and wants a
  count, take-off, tally, schedule, or quantities of light fittings (downlights,
  hanging/ceiling/recessed/directional lights), LED strip lighting, and switch
  positions — and a suggested number of motion/occupancy sensors for sculleries,
  ensuites and garages. Trigger on phrasings like "count the lights on this
  plan", "do a lighting take-off", "how many downlights/switches/LED strips per
  floor", "turn these floorplans into a lighting quantities sheet", or "tally the
  lighting layout into Excel", even if the user doesn't name the skill. This is
  for COUNTING existing symbols on a plan into a spreadsheet — not for placing
  icons on a plan (that's floorplan-icons) and not for building a quote document.
---

# Lighting Take-off

Turn lighting-layout floorplans into a per-floor spreadsheet of light fittings,
LED strip runs, and switch points, plus a suggested motion-sensor count for
wet/utility rooms.

## What you're counting (D-One conventions)

Read the plan's **Electrical Legend** first (it's printed on the drawing) to lock
in what each symbol looks like on *this* set, because symbol styles vary slightly
between drawings. The targets:

- **Light fittings** — every light point, counted and broken out by type. Typical
  legend entries: hanging light point, ceiling light, recessed ceiling light
  (downlight), surface-mounted ceiling light, directional recessed light, foot
  lighting, planter light, track light, outdoor up/down lighter. Count each
  symbol instance.
- **LED strip lighting** — count each distinct LED **run** (a marked length /
  "LED on shelf"-type line), not the millimetres. Note an *LED-strip circuit* is
  different: it is a set of runs **connected and switched together**, so several
  connected runs make one circuit. Runs is always **≥** LED-strip circuits — if
  your circuit count ever exceeds the run count, one of them is wrong.
- **Keypads** — the number of physical **light-control locations** on the walls.
  Drawings show these two ways: as a **switch bank** (a plate ganging switches /
  dimmers like **D**, **2**, **3**) or as an actual **keypad** symbol. Count both
  the same way — one per location — because D-One installs a keypad at each. So
  this column is the keypad quantity for the job, whether the plan drew switches
  or keypads. What matters is *how many wall locations need a control plate*,
  **not** how many individual switches/dimmers/buttons are there: a plate ganging
  a dimmer **D** plus two 2-way **2** switches is **one keypad location**, not
  three. Don't count gangs or individual switch symbols, and don't tie this to
  circuits — it's purely a tally of control locations. (Tip: switch symbols
  clustered at one wall position by a doorway are a single location = one keypad.)

  Getting this right means not over-counting **or** over-merging. Two traps:
  - **Over-counting:** reading one ganged location as several. Symbols stacked or
    touching at a *single* wall position (e.g. "D 2 3" together by one doorway,
    whose switch legs all converge to the same drop point) are **one location**.
  - **Over-merging:** collapsing genuinely separate locations. Controls at
    *different* wall positions are separate even if near each other — e.g. the two
    ends of a 2-way are two locations, and switches on opposite jambs/walls of the
    same doorway are usually two locations.

  The deciding question is always *how many distinct wall positions need a control
  plate*. When a cluster is ambiguous at tile resolution, zoom into `native.png`
  at that spot and check whether the legs converge to one drop (one location) or
  run to separate positions (separate locations) before deciding. Because this
  number is the keypad quantity and is easy to get wrong, present it as the figure
  most worth the user double-checking on the drawing.
- **Lighting circuits** — a circuit is a **group of light fittings connected
  together** (wired as one switched/dimmed group). You read circuits from the
  **switch legs**: the curved/looping lines that tie fittings to their controls.
  Count **one circuit per distinct connected group of fittings** — trace the
  curves and treat every fitting joined into one continuous run of legs as a
  single circuit. Two separate, unconnected loops are two circuits.

  Do **not** count circuits by counting switch devices. Multiple controls can sit
  on the *same* group: a dimmer **D** and a 2-way **2** at one plate, plus another
  **D**/**2** plate across the room, can all be operating one group (a dimmed
  circuit switched as 2-way from two positions) — that is **one circuit, two
  switch positions**, and the long sweeping loop between the plates is the
  strapping run, not an extra circuit. So a room with several switch plates may
  still be a single circuit. Judge it by what the legs connect, not by how many
  **D**/**2**/keypad symbols appear. Tracing legs on a dense plan is genuinely
  hard, so treat the circuit count as the softest number and always caveat it.
- Ignore non-lighting symbols (plugs, data, TV, gas, isolators, thermostats,
  cameras, intercoms) and ignore any coloured D-One AV overlay icons — those are
  not part of the lighting take-off.

## The hard truth about these PDFs

Lighting plans almost always export as **one flat raster image with no text or
vector layer** — so you can't grep symbols out, you have to *look*. A whole page
at once is far too dense to count reliably. The workflow below slices each plan
into legible tiles with a count-zone rule so nothing is double-counted or sliced
in half. Counts are still visual estimates: always tell the user to sanity-check
before ordering, and never present a count as exact.

## Workflow

Work **one floor (one PDF) at a time**, then combine.

### 1. Tile the plan

```bash
python scripts/render_and_tile.py "PLAN.pdf" WORKDIR --floor "Living Level"
```

This writes `WORKDIR/<floor-slug>/` with `native.png`, an `overview.png` (the
whole plan with the grid drawn on), `tiles/r{R}_c{C}.png`, and `manifest.json`.
Each tile has a **red count-zone rectangle**. Default tiles are ~1500px; if a
tile is still too busy to count confidently, re-run with `--target-px 1000` for a
finer grid.

**Use the floor name the drawing itself uses.** Read the title block (visible on
`overview.png`, usually bottom-left/right — e.g. "Ground Floor plan", "First Floor
plan") and pass that as `--floor`, rather than inventing a name from the filename.
The spreadsheet tabs and Summary columns should match the architect's floor
labels so it ties back to the drawings. Order the floors as in the building
(ground up).

### 2. Find the legend

Open `overview.png`, locate the Electrical Legend, then open the tile(s) covering
it and read the actual symbol shapes for downlights, LED strip, switches, etc.
Note them so you count consistently. The legend column itself is a *reference* —
don't count its example symbols as fittings.

### 3. Count tile by tile — and attribute every count to a room

Open every `tiles/r{R}_c{C}.png` in order. For each tile, **count only symbols
whose centre falls inside the red count-zone rectangle** — symbols in the
overlap margin belong to the neighbouring tile and are counted there. This is how
overlap avoids both double-counting and lost border symbols.

**Tally everything per room, not just per floor.** Read the room labels printed on
the plan and assign each fitting, LED run, switch point and circuit to the room it
sits in. This is the single most important discipline: a floor total like "2
hanging lights" is unfalsifiable, but "2 hanging lights in the Dining" can be
checked and corrected. Building the count room by room also stops phantom counts —
if you can't name the room a fitting is in, you probably mis-read the symbol.
Floor totals are just the sum of the rooms.

Keep, per room: a tally per fitting type, LED strip runs, keypads (one per
control location — switch bank or keypad symbol — never per gang/device), and
circuits (next section). Tiles that are pure exterior/landscape or just the
legend/title block contribute zero — skip them quickly. Be systematic; the main
failure mode is losing track, not misreading a symbol.

**Circuits need a second look across tiles, not per-tile.** A circuit (a connected
group of fittings) is traced from switch legs that often span several tiles, so
don't try to tally circuits tile-by-tile. Instead, after counting fittings, go
room by room on the `overview.png` (zoom into the relevant tiles) and follow the
curved legs: count how many **distinct connected groups of fittings** the room
has, not how many switch plates or devices. A room with two D/2 plates that feed
one continuous loop is one circuit; a room split into two independent loops is two
circuits.

**Label each circuit by type using the legend.** Name the circuit after the kind
of fitting it controls, using the legend's fitting names — e.g. a group of
recessed downlights is a *Downlight circuit*, a run of LED strip is an *LED-strip
circuit*, perimeter foot lights are a *Foot-lighting circuit*, planter lights a
*Planter-lighting circuit*, and so on. If a single group mixes fitting types,
name it after the dominant one. Tally circuits per type across the floor.

### 4. Identify rooms for motion sensors

Room names are printed on the plan. Scan the tiles (or overview) for **sculleries,
ensuites, and garages** — the rooms D-One fits with motion/occupancy sensors.
Suggest:

- **1 sensor** per scullery and per ensuite.
- **1 sensor** per single garage; **2** for a large/double garage (judge from the
  room size / car bays drawn).

List the actual room labels you found so the user can see your reasoning. If none
are present on a floor, say so.

### 5. Assemble the counts JSON

Combine all floors into one room-level JSON file (see
`scripts/build_workbook.py` header for the full spec). Each floor holds a `rooms`
array; floor and project totals are computed from the rooms:

```json
{
  "project": "12 Mountain Road",
  "floors": [
    {
      "name": "First Floor",
      "rooms": [
        {
          "name": "Master Bedroom",
          "lights": { "Recessed downlight": 6, "Wall mounted light point": 4 },
          "led_strips": 2,
          "keypads": 2,
          "circuits": { "Downlight circuit": 1, "Wall-light circuit": 1, "LED-strip circuit": 1 },
          "sensors": 0
        },
        {
          "name": "Master en-suite",
          "lights": { "Recessed downlight": 4 },
          "led_strips": 1, "keypads": 1,
          "circuits": { "Downlight circuit": 1, "LED-strip circuit": 1 },
          "sensors": 1
        }
      ],
      "notes": "Counts are visual estimates."
    }
  ]
}
```

### 6. Double-check BEFORE building the spreadsheet

A polished spreadsheet makes wrong numbers look authoritative, so always validate
first. This is two passes:

**a) Self-review pass.** Re-open the `overview.png` and walk room by room against
your JSON. For each room ask: are the fittings really in *that* room? Could any be
a different fitting type (downlight vs wall light is the usual mix-up)? Does every
room with lights have a keypad/control? Does each LED-strip circuit have at least
as many LED runs? This catches phantom counts — the kind where a fitting was
recorded in a room that doesn't actually contain it.

**b) Run the validator.** It mechanically catches the impossibilities:

```bash
python scripts/check_counts.py counts.json
```

Fix every ERROR (the script exits non-zero) and resolve or explain every WARNING.
Only once it reports PASSED do you build the workbook.

### 7. Build the spreadsheet

```bash
python scripts/build_workbook.py counts.json "Lighting_Takeoff.xlsx"
```

The workbook renders each floor tab as a **room-by-room matrix** (rooms as rows;
columns for each fitting type, LED runs, keypads, each circuit type, and sensors)
with a bold TOTAL row, plus a Summary tab totalling everything across floors. Save
it to the user's selected folder and present it.

### 8. Report honestly

Give the user the headline totals in chat and **state clearly these are visual
counts to be verified**. Offer to re-tile any floor at finer resolution, or to
adjust the sensor rule, if a number looks off.

## Output rules

- Every count is recorded **per room**; floor and project totals are sums of the
  rooms. Never report a fitting you can't place in a named room.
- Keypads = count of control locations (each → a keypad), whether the plan drew a
  switch bank or a keypad symbol; one per location regardless of how many
  switches/gangs sit there. Not tied to circuits.
- A circuit = one connected group of fittings; count by tracing legs, not by
  counting switch devices. Multiple plates on one group = one circuit. Circuits
  are the softest number — always caveat them.
- One spreadsheet for the whole project, one tab per floor + Summary.
- Don't invent fitting types that aren't in the legend; use the legend's names.
- Always caveat that counts are estimates from a flat image.

## Dependencies

`pdfimages`/`pdftoppm` (poppler), Python `Pillow` and `openpyxl`.
