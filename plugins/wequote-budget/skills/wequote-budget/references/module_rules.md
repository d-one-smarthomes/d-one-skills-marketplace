# D-One Module & Sizing Rules (v2)

**Core rule: hardware comes in fixed-capacity modules / limited-capacity units. Always round UP.**
These are implemented in `scripts/calculate_budget.py` (`derive()`), driven off the plan counts.

## Lighting — Lutron HomeWorks
- Dimming modules = `ceil(dimming_circuits / 4)` (LQSE-4A5, 4 channels)
- Switch modules  = `ceil(switched_circuits / 4)` (LQSE-4S5, 4 channels)
- DALI modules    = `ceil(dali_circuits / 2)` (LQSE-2DAL, 2 channels) + 1 terminal kit + 1 harness each
- Link power supply = `ceil(total_modules / 21)`  *(calibrated to the reference; confirm real Lutron QS power-budget rule)*
- Wire reels = `ceil(total_circuits × 10m / 304m reel)`
- Keypad controllers (Savant, Mid) = `ceil(keypads / 10)` (SKL-1010-00 hosts 10 keypads)

## CCTV — Ubiquiti UniFi Protect
- NVR count = `ceil(total_cameras / 4K-limit)` — official Ubiquiti 4K max: **UVC-NVR/UNVR = 18, UNVR-G2 = 30**
- HDD count is a per-tier quantity (retention rule TBD)

## Network — Ubiquiti
- PoE devices = APs (indoor+outdoor) + other PoE devices (cameras, intercoms, readers) from the plan
- PoE switches (USW-…-48) = `ceil(PoE_devices × 1.5 / 48)`  — **+50% growth headroom**
- Core switches (USW-…-24) = `max(1, ceil((all_devices × 1.5 − PoE_ports) / 24))`
- DAC uplinks = 1 per switch = core + PoE switches
- 5G modem = client tick-box (optional)

## Audio — per zone
- `audio_zones = ceil(speaker positions / 2)` (stereo pairs); each zone = speakers + amp + speaker point
- Outdoor zones = Sonance Patio 4.1 checkbox, tier-independent

## Access Control / System Integration
- Access control: 1 network point per reader/viewer; hub excluded (rack)
- SI: touch-panel & SmartControl quantities are client dropdowns; HVAC/Door/Lighting are checkboxes

## Global
- Network point per field device @ R1,650 (rack gear excluded)
- Design + PM: 1h each per hardware unit @ R1,250 (accessory SKUs excluded — see `_design_pm_accessory_exclusions`)
- Labour rates from the estimator rate card (R950 fix, R1,250 programming)
