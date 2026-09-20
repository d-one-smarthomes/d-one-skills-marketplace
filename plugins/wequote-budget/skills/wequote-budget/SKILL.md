Build accurate Entry/Mid/Premium budgets AND a full line-item quote for D-One proposals — from floorplan quantities, a WeQuote URL, or manual project counts. Use whenever the user says "price out this project", "build budgets from the floorplan", "generate budgets for the proposal", "what would this cost", "analyze the WeQuote", or shares a WeQuote link. Also trigger immediately after a floorplan-icons or floorplan-takeoff run when the user asks about cost, budget, or pricing. Outputs proposal_budgets.json (for the d-one-proposal skill) and a per-project line-item spreadsheet (components, qty, retail price, markup, and labour in hours + rands). Prices resolve LIVE from Odoo (via the estimator's odoo_client), falling back to the local pricelist/inventory snapshots when Odoo is unreachable — and labour is calculated from published standards per component (install + programming hours by device, design 10%, PM 12.5%).

D-One Budget & Quote Builder (v3 — pricelist-driven, standards labour)

Generates Entry/Mid/Premium budgets for all seven D-One systems and a full line-item quote spreadsheet. What goes in each tier lives in data (editable); the engine resolves live prices, applies labour from published standards, and writes both outputs.

Key files

data/tier_definitions.json — the bill of materials per module → tier (SKU, role, driver, qty). Single source of what's in each tier. Also carries client options and the CCTV camera-classification rule.
data/pricelist.csv — the local D-One pricelist snapshot (SKU, description, sales_price, cost). FALLBACK price source, used only when live Odoo is unreachable. Live Odoo (product.product) is the primary source.
data/labour_standards.json — per-component install + programming hours (by labour category), the lighting per-circuit rule, the DALI-per-module rule, SI fixed programming per tier, and design/PM percentages.
data/price_overrides.json — pins for a few non-catalogue allowances (network point R1,650, speaker point R1,200, rack cabcon R3,000).
scripts/price_resolver.py — resolves price + cost by SKU: live Odoo (via the estimator's odoo_client) → local pricelist snapshot → estimator inventory → override. Exposes rate card, matched-cost (for margin), and odoo_status for the run.
scripts/calculate_budget.py — the engine → proposal_budgets.json (+ budget_detail.json with --detail).
scripts/build_quote_spreadsheet.py — turns budget_detail.json into the client/internal line-item quote .xlsx.
Run it
bash
# 1) budgets + detail (reference quantities, or --spec for a real project)
python3 <SKILL_DIR>/scripts/calculate_budget.py --spec /tmp/[project]_spec.json --output /tmp/[project]/ --detail

# 2) line-item quote spreadsheet
python3 <SKILL_DIR>/scripts/build_quote_spreadsheet.py \
    --detail /tmp/[project]/budget_detail.json \
    --project "[Client, address]" \
    --output "/tmp/[project]/[Client] — Detailed Quote.xlsx"

--spec is { "<module>": { "<driver>": <count>, ... } } — only the drivers you pass override the tier defaults. Example:

json
{
  "cctv": {"cctv_building_cameras": 6, "cctv_perimeter_cameras": 4, "cctv_poles": 4},
  "network": {"aps_indoor": 13, "aps_outdoor": 2, "poe_devices_other": 18, "non_poe_devices": 6},
  "audio": {"audio_zones": 16},
  "lighting": {"dimming_circuits": 44, "switched_circuits": 12, "dali_circuits": 1, "keypads": 17, "switch_interfaces": 17, "motion_sensors": 14},
  "access-control": {"door_intercoms": 4, "intercom_viewers": 3},
  "system-integration": {"touch_panels": 3}
}
Pricing
Primary source: LIVE Odoo (product.product → list_price for retail, standard_price for cost), resolved through the estimator skill's odoo_client. So a budget always reflects the current price in D-One's business system. Needs the per-user ODOO_LOGIN / ODOO_KEY in the environment (same keys the estimator uses); price_resolver reports the connection state via odoo_status.
Fallbacks (only when Odoo is unreachable or a SKU isn't in Odoo): data/pricelist.csv snapshot → estimator inventory.csv → data/price_overrides.json (allowances). The order is: Odoo → pricelist → inventory → override.
Margin is only shown for a genuine matched pair — live Odoo (list_price + standard_price) preferred, else a matched Sales+Cost row in the pricelist snapshot. Items priced from a fallback with no matching cost show a blank margin — never a mismatched figure.
To keep pricing accurate, keep Odoo current — it's the live source. Refresh pricelist.csv occasionally only so the offline fallback isn't wildly stale.
Labour (from published standards — NSCA/BICSI/industry + D-One history)
Installation and programming are whole hours per component, by labour category (see labour_standards.json → category_hours, mapped from each component's role). Rates from the estimator rate card: install R950/hr, programming R1,250/hr.
Lighting is costed per circuit (1 circuit = 1 DALI driver / dimmable / switched load): 1 h install + 1 h programming per circuit; keypads 1 h install + 4 h programming; switch interfaces 1 h install.
DALI modules = ceil(dali_circuits / 128) — the Lutron LQSE-2DALUNV-D drives 128 drivers (2 loops × 64).
System-integration host programming is a fixed figure per tier: R37,500 / R90,000 / R112,500.
Design = 10% of (non-accessory equipment + install labour). Project management = 12.5% of (install + programming + design).
Accessories (network/speaker points, cabling, cabcon, engraving, cable reels) carry no separate labour and no design/PM.
Network points

Every field device that connects to the network (camera, reader, viewer, AP, touch panel, motion sensor, projector) gets one network point at R1,650 all-in. Rack-mounted gear (NVR, hub, switches, hosts, amps) is excluded — patched in the rack.

CCTV camera classification (default)

Cameras on the property boundary / away from the building are perimeter cameras (Pro; Premium adds enhancers). Cameras on/against the building are building cameras (standard). Classify from the plan by position — a camera outside the building footprint (extent of the indoor devices) is perimeter.

Every SI tier includes the rack

Linkbasic 42U 800-deep cabinet (CAB-42U) + R3,000 cabcon + installation, in Entry, Mid and Premium.

Outputs
proposal_budgets.json — tier totals + client options → feed straight to the d-one-proposal skill.
budget_detail.json (with --detail) — every line + labour, consumed by the spreadsheet builder.
[Client] — Detailed Quote.xlsx — Summary tab (tier totals + whole-project hardware margin, margin %, labour hours and rands) and a tab per system with the full build-up: component, SKU, qty, retail price, markup, equipment, installation, programming, design, PM, and tier total.
Split proposal contract (for the interactive proposal)

The interactive proposal treats Audio and Access Control as baseline + per-unit, so it needs more than the flat tier totals. scripts/build_proposal_contract.py turns budget_detail.json into the v2 proposal_budgets.json the generator consumes:

bash
python3 scripts/build_proposal_contract.py \
    --detail /tmp/[project]/budget_detail.json \
    --spec   /tmp/[project]_spec.json \
    --takeoff /tmp/[project]_takeoff.json \
    --output /tmp/[project]/proposal_budgets.json

It emits:

tier_budgets — audio baseline = 0 (priced per zone); access baseline = the minimum config (Entry/Mid: 1 reader + 1 viewer; Premium: 1 Savant gate intercom); all other systems = their tier total.
per_unit — tier-specific add-on prices, all-inclusive (equipment + labour + pro-rata design/PM + network point), never shown to the client: audio_zone, access_viewer (Entry/Mid), access_reader, access_intercom (Premium). Audio per-zone × zone count reconstructs the tier's audio total.
takeoff — passed through from --takeoff: audio_zones, access_viewer_locations, access_intercom_locations, access_reader_max (drive the selectors and their max counts).
network_sizing — the design-methodology switch recommendation: total PoE devices → PoE ports, non-PoE (TVs) → LAN ports, +25% spare rounded to the next 24/48-port switch, +1 LAN drop per TV. Surface this at the counts checkpoint.

Access Control hardware (confirmed): Entry/Mid are priced on UniFi (door intercom + viewer); Premium on Savant/2N — gate intercom DOR-VERSO2SMN-00, tag reader 9160347. The per-unit numbers are computed all-inclusive from those detail lines; keep the SKUs in tier_definitions.json in step with the pricelist.

Maintaining it

Edit the tier build-ups in tier_definitions.json, prices in pricelist.csv, and labour in labour_standards.json. Keep SKUs matching the pricelist so prices and margins resolve.
