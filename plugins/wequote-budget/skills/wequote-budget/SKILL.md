---
name: wequote-budget
description: >
  Build accurate Entry/Mid/Premium budgets for D-One proposals — from floorplan quantities,
  a WeQuote URL, or manual project counts. Use whenever the user says "price out this project",
  "build budgets from the floorplan", "generate budgets for the proposal", "what would this cost",
  "analyze the WeQuote", or shares a WeQuote link. Also trigger immediately after a floorplan-icons
  or floorplan-takeoff run when the user asks about cost, budget, or pricing. Outputs
  proposal_budgets.json ready to pass directly into the d-one-proposal skill. Prices resolve LIVE
  from the estimator inventory (D-One's maintained pricelists), and hardware is module-aware
  (Lutron 4-ch modules, NVR camera limits, switch port capacity, keypad controllers) so quantities
  round to whole modules — accurate, not just per-unit multiplication.
---

# D-One Budget Builder (v2 — live-priced, data-driven)

Generates Entry/Mid/Premium budgets for all seven D-One systems. Every component price is
resolved **live** from the estimator skill's inventory (which D-One keeps current from the
supplier pricelists), so budgets track real pricing automatically. Tier make-up and client
options live in data; the calculator applies module rules, labour, design and PM.

**Key files:**
- `data/tier_definitions.json` — every module → tier → components (by SKU), driver quantities, client options, and labour rules. This is the single source of truth for what's in each tier.
- `data/price_overrides.json` — manual price pins for SKUs not yet in the estimator inventory (e.g. Planet World / Homemation items, the R1,650 network point, the R3,000 network cab-con, the R200 patch lead, the R1,200 speaker point). Prefer adding real SKUs to the estimator inventory over pinning here.
- `scripts/price_resolver.py` — locates the estimator `inventory.csv` at runtime and resolves ex-VAT price by SKU (overrides first, then inventory). Also exposes the rate card and per-category labour hours.
- `scripts/calculate_budget.py` — the engine. Reads the two data files, computes every module/tier, writes `proposal_budgets.json`.

---

## Run it

Reference (calibration) quantities:
```bash
python3 <SKILL_DIR>/scripts/calculate_budget.py --output /Users/darrenswanepoel/Downloads/budget-[project]/ --verbose
```

Real project — pass counts read off the plan (per module), overriding tier defaults:
```bash
python3 <SKILL_DIR>/scripts/calculate_budget.py --spec /tmp/[project]_spec.json --output /Users/darrenswanepoel/Downloads/budget-[project]/
```

`--spec` is `{ "<module>": { "<driver>": <count>, ... }, ... }`. Only the drivers you pass are
overridden; the rest fall back to the tier defaults. Example:
```json
{
  "cctv": { "cctv_building_cameras": 12, "cctv_perimeter_cameras": 10, "cctv_poles": 6 },
  "lighting": { "dimming_circuits": 100, "switched_circuits": 30, "dali_circuits": 4, "keypads": 34, "motion_sensors": 18 },
  "network": { "aps_indoor": 16, "aps_outdoor": 4, "poe_devices_other": 24, "non_poe_devices": 10 },
  "audio": { "audio_zones": 6, "outdoor_audio_zones": 2 }
}
```

Output `proposal_budgets.json` → `{ tier_budgets: {module: {Entry,Mid,Premium}}, options: {...} }`,
all net ex-VAT. Pass it straight to the d-one-proposal skill.

---

## The seven modules

| Module | Driver quantities (from plan) | Notes |
|--------|------------------------------|-------|
| **cctv** | building cameras, perimeter cameras, poles | NVR count = ceil(total cameras / 4K limit: UVC-NVR 18, UNVR-G2 30). Enhancer is a client dropdown (per perimeter camera). |
| **access-control** | door intercoms, tag readers, viewers | Per-device labour (1h fix1 + 2h fix2 + 1h prog). Premium = Verso + 2N tag readers, client-selectable doors. |
| **network** | APs indoor/outdoor, other PoE devices, non-PoE devices | PoE switches ceil(PoE×1.5/48); core ceil(remaining×1.5/24); DAC per switch; 5G modem is a client tick-box. |
| **audio** | audio_zones, outdoor_audio_zones | Priced per zone (room selector). Outdoor = Sonance Patio 4.1 checkbox, tier-independent. |
| **home-theatre** | ht_rooms (fixed build per tier) | Entry 5.1 TV room, Mid 5.1.2 Atmos, Premium full 7.2.4 Trinnov cinema (Barco Heimdall+, Stewart screen, room treatment). Carries a joinery/integration design allowance. |
| **lighting** | dimming/switched/DALI circuits, keypads, sensors | Modules round up (dim/sw ceil/4, DALI ceil/2); PS ceil(modules/21); wire ceil(circuits×10/304). Entry = switch interfaces, Mid = Savant Ascend keypads, Premium = Lutron Alisse. |
| **system-integration** | system, touch_panels, smart_controls | Entry S12 host (no touch panels), Mid Pro Host + touch panels, Premium + SmartControl 14. HVAC/Door/Lighting integration are client checkboxes. Touch-panel & SmartControl quantities are dropdowns. |

---

## Global rules (apply to every module)

- **Network points:** every field device (camera, reader, viewer, AP, sensor, touch panel) gets one network point at **R1,650** all-in (cable + materials + labour). Rack-mounted gear (NVR, hub, switches, hosts) is EXCLUDED — patched inside the rack.
- **Design:** 1 hour per HARDWARE unit at **R1,250/hr** (home-theatre adds a fixed joinery/integration design allowance on top).
- **Project management:** 1 hour per HARDWARE unit at **R1,250/hr**.
- **Design/PM exclusions:** cabling accessories don't attract design/PM — see `_design_pm_accessory_exclusions` (network/speaker points, patch leads, DAC leads, cab-con, engraving, keypad base units, speaker cable).
- **Labour rates** come from the estimator rate card (`fix1`/`fix2` R950/hr, `programming` R1,250/hr) so they update centrally.

---

## Client options (rendered by the d-one-proposal skill)

Carried in `tier_definitions.json` as `client_option` blocks / module `client_options`, and summarised in `proposal_budgets.json → options`:
- CCTV perimeter enhancers — dropdown (0 → perimeter cameras)
- Network 5G failover — tick-box
- Audio rooms — room selector; outdoor audio areas — checkboxes
- Access Control intercom doors / tag-reader doors — dropdowns
- System Integration HVAC / Door / Lighting — checkboxes; touch-panel & SmartControl quantities — dropdowns

---

## Maintaining prices

Prices live in the **estimator** skill's `inventory.csv` (kept current from the supplier
pricelists in the repo). When a supplier price changes, update it there and every budget
follows automatically. Only pin in `price_overrides.json` when a SKU isn't in the estimator
inventory yet; when it's added upstream, remove the pin so it goes fully live.

Planet World (Integra + M&K) and Homemation (Barco) items were added via
`planet_world_inventory_additions.csv` — append those rows to the estimator inventory to make
them fully live and drop the corresponding overrides.
