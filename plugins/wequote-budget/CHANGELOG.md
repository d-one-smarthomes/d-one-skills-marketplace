# wequote-budget — v3.0.0 (2026-08-10)

Major rework, done with Darren.

## Pricing
- NEW default pricelist `data/pricelist.csv` (uploaded D-One pricelist: SKU, description, sales_price, cost) — now the PRIMARY price source. Falls back to estimator inventory, then price_overrides.
- Margins computed and shown ONLY where retail + cost are a matched pair from the pricelist; fallback items show a blank margin (no mismatched figures).
- Removed all De Klerk reference pricing/labour.

## Labour (published standards)
- Installation + programming are whole-hour figures per component, by labour category (labour_standards.json), from NSCA/BICSI/industry benchmarks + D-One history. Confirmed per-device hours with Darren.
- Lighting per circuit (1 circuit = 1 DALI driver): 1h install + 1h programming/circuit; keypads 1h install + 4h programming; switch interfaces 1h install.
- DALI modules = ceil(dali_circuits / 128) per Lutron LQSE-2DALUNV-D datasheet.
- System-integration host programming fixed per tier: R37,500 / R90,000 / R112,500.
- Design = 10% of (non-accessory equipment + install); PM = 12.5% of (install + programming + design).

## Hardware / structure
- Linkbasic 42U rack (CAB-42U) + R3,000 cabcon + install added to ALL system-integration tiers.
- Network point on every field device (camera, reader, viewer, AP, touch panel, motion sensor, projector); rack gear excluded.
- CCTV default rule: boundary/away-from-building cameras = perimeter (Pro); Mid = Pro perimeter, Premium = Pro + enhancers.
- Touch panels: per-floor tick-box (floors read from drawings).
- Speakers: Entry VX80R, Mid VX82R (per pair), Premium Sonance IS8.

## Outputs
- NEW scripts/build_quote_spreadsheet.py — every proposal gets a line-item quote .xlsx: per-system build-up (component, SKU, qty, retail, markup, equipment, install, programming, design, PM, tier total) + Summary with whole-project hardware margin, margin %, and labour hours + rands.

## Dependencies
- Relies on the `estimator` skill for fallback inventory, the rate card, and labour-hours reference data.
