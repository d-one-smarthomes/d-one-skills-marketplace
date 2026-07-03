---
name: wequote-budget
description: >
  Build accurate Entry/Mid/Premium budgets for D-One proposals — from floorplan icon counts,
  a WeQuote URL, or manual project quantities. Use whenever the user says "price out this project",
  "build budgets from the floorplan", "generate budgets for the proposal", "what would this cost",
  "analyze the WeQuote", or shares a WeQuote link. Also trigger immediately after a floorplan-icons
  or floorplan-takeoff run when the user asks about cost, budget, or pricing. Outputs
  proposal_budgets.json ready to pass directly into the d-one-proposal skill. The calculator
  accounts for module-based hardware (Lutron 4-channel dimmer modules, NVR camera limits, switch
  port capacity) so circuit counts are always rounded to whole modules — this is what makes
  estimates accurate rather than just multiplying per-unit rates.
---

# D-One Budget Builder

Generates Entry/Mid/Premium budgets for all D-One systems, calibrated against
WeQuote REF:0011 (House De Klerk, Hermanus — 2026). Understands module-based hardware
so estimates are accurate, not just linear extrapolations.

**Read first:** `references/unit_prices.md` — every component price and labour rate.
**Read for module rules:** `references/module_rules.md` — how quantities drive module counts.
**Reference data:** `data/deklerk_reference.json` — the full De Klerk baseline.

---

## Three input modes

| Mode | When | Command |
|------|------|---------|
| **Icon counts** | After floorplan-icons / floorplan-takeoff | `--icons icon_counts.json` |
| **Manual spec** | User provides quantities | `--spec project_spec.json` |
| **WeQuote URL** | Live quote exists in WeQuote | Extract via Claude in Chrome (see below) |

---

## Mode 1 — From Floorplan Icon Counts ✓ recommended

After annotating a floorplan with icons, count every icon type and pass the counts directly
to the calculator. The script maps icons to hardware components and applies all module rules.

### Get the counts

If you have a floorplan PDF with icons already placed, run floorplan-takeoff:
> "Count the components on this floorplan and give me a JSON of icon counts"

Or read the counts directly from the floorplan-takeoff output Excel.

Build a JSON dict:
```json
{
  "cctv_dome": 4,
  "cctv_bullet": 6,
  "wireless_access_point": 12,
  "ceiling_speaker": 14,
  "wall_speaker": 4,
  "light_switch_keypad": 28,
  "touch_panel": 3,
  "facial_recognition_reader": 2,
  "intercom_door_station": 2,
  "intercom_receiver_panel": 4,
  "motion_sensor": 5,
  "tv": 4,
  "network_point": 8
}
```

Save to `/tmp/[project]_icons.json` and run:
```bash
python3 <SKILL_DIR>/scripts/calculate_budget.py \
  --icons /tmp/[project]_icons.json \
  --output /Users/darrenswanepoel/Downloads/budget-[project]/
```

The script prints derived quantities (how many dimming circuits it estimated, AP split, etc.)
and all tier totals. Review the estimation notes — if dimming circuit count seems off,
switch to Mode 2 with a manual spec to override it.

### Icon → spec mapping (what the script does automatically)

| Icon | Maps to |
|------|---------|
| `cctv_dome` + `cctv_bullet` | `cctv_cameras` total |
| `cctv_bullet` × 0.5 | `cctv_poles` estimate |
| `wireless_access_point` × 0.85 | `aps_indoor` |
| `wireless_access_point` × 0.15 | `aps_outdoor` |
| `ceiling_speaker` ÷ 2 | `audio_zones` (stereo pairs always) |
| `wall_speaker` ÷ 2 | added to `audio_zones` |
| `light_switch_keypad` | `keypads` + drives circuit estimates |
| `touch_panel` | `touch_panels` |
| `facial_recognition_reader` or `intercom_door_station` (max) | `door_stations` |
| `motion_sensor` | `motion_sensors` |

### Lighting circuits from keypads

Dimming circuits aren't shown as icons — they come from the electrical drawing.
The script estimates from keypad count (De Klerk ratio: 30 keypads → 79 dim + 22 sw):

- `dimming_circuits` = keypads × 2.5 → rounded UP to next multiple of 4
- `switched_circuits` = keypads × 0.7 → rounded UP to next multiple of 4
- `dali_circuits` = keypads ÷ 10

When electrical drawings are available, use Mode 2 with exact circuit counts instead.

---

## Mode 2 — Manual Project Spec

Build a spec JSON with exact quantities. Use this when you have electrical drawings,
a project brief with circuit counts, or want to override the icon-based estimates.

```json
{
  "_source": "Project Name — client brief",
  "cctv_cameras": 8,
  "cctv_poles": 4,
  "aps_indoor": 10,
  "aps_outdoor": 2,
  "dimming_circuits": 79,
  "switched_circuits": 22,
  "dali_circuits": 2,
  "keypads": 30,
  "motion_sensors": 5,
  "audio_zones": 1,
  "door_stations": 1,
  "touch_panels": 3
}
```

```bash
python3 <SKILL_DIR>/scripts/calculate_budget.py \
  --spec /tmp/[project]_spec.json \
  --output /Users/darrenswanepoel/Downloads/budget-[project]/ \
  --verbose
```

`--verbose` prints the per-system module breakdown (dimming modules, switch count, etc.)
so you can sanity-check the hardware assumptions.

---

## Mode 3 — From WeQuote URL

WeQuote is client-rendered (Vue/React) — cannot be read with web_fetch. Requires
**Claude in Chrome** to be connected.

If not connected: ask the user to install the Claude in Chrome extension and sign in.

### Extraction steps

1. Navigate to the WeQuote URL via `mcp__Claude_in_Chrome__navigate`
2. Wait for page title = "WeQuote - Proposal"
3. Extract the Project Summary (net totals per system) and Options blocks (tier deltas)

```javascript
// Get project summary
const allText = document.body.innerText;
const summaryIdx = allText.indexOf('Project Summary');
allText.substring(summaryIdx, summaryIdx + 3000)
```

```javascript
// Get CCTV options
const cctvIdx = allText.indexOf('Options\nCCTV\nEntry');
allText.substring(cctvIdx, cctvIdx + 500)
```

Work section by section. For each system collect:
- `base_total_incvat`: the "Total Cost" line (inc VAT)
- `base_tier`: which tier is "Included"
- `option_deltas`: {tier: delta_incvat} — negative = cheaper than Included tier

```python
# Calculate tier totals (inc VAT)
premium_incvat = base_total_incvat                    # if Premium is Included
mid_incvat     = premium_incvat + mid_delta           # delta is negative
entry_incvat   = premium_incvat + entry_delta         # delta is negative

# Convert to net ex-VAT for proposal_budgets.json
net = round(incvat / 1.15)
```

Build `proposal_budgets.json` manually from the extracted totals (see format below)
and save to `/Users/darrenswanepoel/Downloads/budget-[project]/`.

---

## Output format — proposal_budgets.json

This is what the d-one-proposal skill reads:

```json
{
  "tier_budgets": {
    "cctv":               {"Entry": 143770, "Mid": 285777, "Premium": 337491},
    "access-control":     {"Entry": 41857,  "Mid": 46704,  "Premium": 228799},
    "network":            {"Entry": 127330, "Mid": 153009, "Premium": 259331},
    "audio":              {"Entry": 34822,  "Mid": 46244,  "Premium": 65614},
    "home-theatre":       {"Entry": 389217, "Mid": 572524, "Premium": 822609},
    "lighting":           {"Entry": 823645, "Mid": 1001828,"Premium": 1335523},
    "system-integration": {"Entry": 80970,  "Mid": 172970, "Premium": 261274}
  },
  "zone_prices": {
    "cctv": 37273,
    "access-control": 57675,
    "network": 14224,
    "audio": 65614,
    "lighting": 13248,
    "system-integration": 80970
  }
}
```

All values are **net ex-VAT** in ZAR. The proposal skill displays them as "From R X".

---

## Pass budgets to the proposal skill

Once `proposal_budgets.json` is saved:

> "Make a proposal for [Client], use the budget file at /Users/darrenswanepoel/Downloads/budget-[project]/proposal_budgets.json"

---

## Reference data (De Klerk baseline)

All unit prices and module rules are in:
- `references/unit_prices.md` — every component price and labour rate used in the calculator
- `references/module_rules.md` — how quantities drive module counts (the key accuracy rules)
- `data/deklerk_reference.json` — full tier totals and option deltas from WeQuote REF:0011

The De Klerk project (Hermanus, 2026) is the calibration source for all pricing. When
adding new quotes, update these files so the skill improves over time.
