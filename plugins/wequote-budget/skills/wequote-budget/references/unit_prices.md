# D-One Unit Prices — now LIVE (this file is superseded)

**As of the v2 rebuild (2026-08), unit prices are no longer hardcoded here.**

Every component price is resolved at runtime from the **estimator** skill's `inventory.csv`
(kept current from the supplier pricelists) via `scripts/price_resolver.py`. The tier make-up
lives in `data/tier_definitions.json` (components referenced by SKU).

To see or change a price:
- **In the estimator inventory** (preferred) — update `inventory.csv` there; every budget follows.
- **Pinned override** — `data/price_overrides.json`, for SKUs not yet in the estimator inventory.

### Current manual pins (`data/price_overrides.json`)

| Item | Key | ex-VAT | Why pinned |
|------|-----|--------|-----------|
| Network point (all-in) | `NETWORK_POINT` | R1,650 | D-One standard (cable+materials+labour) |
| Speaker point | `SPEAKER_POINT` | R1,200 | audio cabling point |
| Cat6 patch lead 0.5m | `CAT6-PATCH-0.5M-HQ` | R200 | high-quality patch lead |
| Network cab-con allowance | `NET-CABCON-ALLOWANCE` | R3,000 | cables/connectors/plugs, fixed per network |
| Camera pole (Triwes 3.9m) | `CAM-POLE-TRIWES-3.9M` | R2,703.33 | not in inventory |
| 18.5" monitor | `MON-18.5-BL` | R2,110.57 | not in inventory |
| Room treatment allowance | `ROOM-TREATMENT-ALLOWANCE` | R350,000 | HT Premium acoustic treatment |
| Planet World (Integra + M&K), Homemation (Barco), Stewart screen | see file | RRP÷1.15 / sell price | pending add to estimator inventory (`planet_world_inventory_additions.csv`) |

### Labour & services rates (from the estimator rate card)
- 1st fix cabling / 2nd fix installation: **R950/hr**
- Programming: **R1,250/hr**
- Design: **R1,250/hr** — 1h per hardware unit (+ fixed joinery allowance on home theatre)
- Project management: **R1,250/hr** — 1h per hardware unit

Historical De Klerk baseline is retained in `data/deklerk_reference.json` for reference only —
the calculator no longer uses it.
