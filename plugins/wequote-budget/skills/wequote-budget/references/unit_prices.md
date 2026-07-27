# D-One Unit Prices Reference

**Source:** WeQuote REF:0011 — House De Klerk, Hermanus (2026-06-30)
**All prices ex-VAT (15% VAT applies)**

---

## Lighting Control — Lutron HomeWorks

### Dimmer & Switch Modules

| Component | Model | Channels | Unit Price (ex-VAT) | Notes |
|-----------|-------|----------|---------------------|-------|
| LED+ Dimming Module | LQSE-4A5-230-D | 4 | R 24,261 | Phase-dimmable. Main dimming module |
| Switched Relay Module | LQSE-4S5-230-D | 4 | R 10,000 | On/off relay — extractors, non-dimmable loads |
| DALI Tuneable Module | LQSE-2DALUNV-D | 2 | R 34,870 | For DALI-addressable LED drivers |
| DALI Terminal Kit | — | — | R 1,478 | Required with each DALI module |
| DALI Wiring Harness | — | — | R 739 | Required with each DALI module |

**Key rule:** 1 circuit = 1 channel. Always round UP to next whole module. See module_rules.md.

### Processors & Infrastructure

| Component | Model | Unit Price (ex-VAT) | Notes |
|-----------|-------|---------------------|-------|
| HomeWorks Processor | HQP7-1 | R 30,783 | 1 per system |
| QS Link Power Supply | QSPS-DH-1-75-H | R 7,478 | 1 per ~12 modules |
| I/O Interface Module | QSE-IO | R 10,261 | Dry-contact integrations. Add for Mid/Premium |

### Keypads & Sensors

| Component | Model | Unit Price (ex-VAT) |
|-----------|-------|---------------------|
| Wall Interface Keypad | QSE-CI-WCI | R 8,087 |
| Motion Sensor (360°) | M360-W-VOLF | R 2,482 |

### Cabling

| Component | Unit Price (ex-VAT) | Notes |
|-----------|---------------------|-------|
| Lutron System Wire (304m reel) | R 10,000/reel | ~10m per circuit + 100m backbone |

### Labour — Lighting

| Task | Rate (ex-VAT) | Basis |
|------|--------------|-------|
| First fix cabling | R 346/circuit | All circuit types |
| Second fix installation | R 355/circuit | Per circuit |
| Programming — base | R 50,000 | Fixed |
| Programming — per circuit | R 2,670 | (R325,000 - R50,000) ÷ 103 circuits |

**De Klerk:** 79 dim + 22 sw + 2 DALI = 103 circuits, 30 keypads → Total net: R 1,335,523

---

## CCTV — Ubiquiti UniFi Protect

### Cameras

| Component | Model | Unit Price (ex-VAT) | Tier |
|-----------|-------|---------------------|------|
| G6 Pro Bullet | UVC-G6BPRO-W | R 13,136 | Premium |
| G6 Bullet | UVC-G6B | R 5,564 | Entry/Mid |
| Pro Bullet Enhancer | UACC-Pro-Bullet-Enhancer-W | R 5,214 | Mid+Premium |

### Mounting & Recording

| Component | Unit Price (ex-VAT) | Notes |
|-----------|---------------------|-------|
| Camera Pole (3.9m buried) | R 2,703 | Perimeter cameras |
| CABCON connector | R 3,200 | 1 per pole |
| NVR (UNVR-G2) | R 19,897 | Max 15 cameras each |
| Monitor | R 2,111 | 1 per NVR |
| HDD 8TB | R 5,206 | 1 per 8 cameras (30-day retention) |

### Labour — CCTV

| Task | Rate (ex-VAT) |
|------|--------------|
| First fix cabling | R 1,425/camera |
| Second fix installation | R 4,869/camera |
| Programming — base | R 20,000 |
| Programming — per camera | R 3,125 |

**De Klerk:** 8 cameras, 4 poles, 1 NVR, 2 HDDs → Total net: R 337,491

---

## Network & Wi-Fi — Ubiquiti UniFi

### Routing & Switching

| Component | Model | Unit Price (ex-VAT) |
|-----------|-------|---------------------|
| Router | UDM-MAX | R 15,279 |
| 5G Failover Modem | U5G-Max-Outdoor | R 12,499 |
| Core Switch 24-port | USW-MAX24 | R 9,822 |
| PoE Switch 48-port | USW-MAX48P | R 27,065 |
| DAC Cable 10Gbps | — | R 421/cable |

### Access Points

| Component | Model | Unit Price (ex-VAT) | Tier |
|-----------|-------|---------------------|------|
| AP Indoor (Entry est.) | U7-Pro | R 4,040 | Entry |
| AP Indoor (Mid) | U7-Pro-XG-W | R 5,050 | Mid |
| AP Indoor (Premium est.) | U7-Pro-XGS | R 6,818 | Premium |
| AP Outdoor | U7-Pro-Outdoor | R 7,851 | All tiers |

### Labour — Network

| Task | Rate (ex-VAT) |
|------|--------------|
| First fix cabling | R 79/AP |
| Second fix installation | R 238/AP |
| Programming | R 17,500 fixed |

**De Klerk:** 10 indoor + 2 outdoor APs → Total net: R 153,009

---

## Access Control — 2N / Savant

**Tiering fix (2026-07-14):** door station pricing now varies by tier — previously
`calc_access_control()` ignored the `tier` argument entirely and always priced off the
IP One rate, so Entry/Mid/Premium came out identical. Each tier now uses a distinct model:

| Component | Model | Unit Price (ex-VAT) | Tier |
|-----------|-------|---------------------|------|
| IP Video Door Station | 2N IP Base | R 30,167 | Entry (~70% of IP One — fewer features) |
| IP Video Door Station | 2N IP One | R 43,096 | Mid |
| IP Video Door Station | 2N IP Verso | R 68,954 | Premium (~1.6x IP One — larger touchscreen) |
| Surface Mount Box | — | R 1,845 | All tiers, per door |
| Touch Panel 8" | Savant ITP-E8000V3W | R 56,670 | Premium only — bundled into the door station cost at Premium |

Premium door station total = IP Verso + Touch Panel 8" + mount = R 127,469/door (before labour).

### Labour — Access Control

| Task | Rate (ex-VAT) |
|------|--------------|
| First fix | R 1,900 fixed |
| Second fix | R 1,900/panel |
| Programming | R 6,250 fixed |

---

## Audio — Sonance / Sonos

**Card price vs. zone panel fix (2026-07-14):** the Audio option card is priced as a
**single reference zone** at that tier's quality level (`calc_audio(1, tier)`), NOT the
full property zone count. Previously the card baked in the entire project's zone total
(e.g. 24 zones on a large multi-house property), so selecting a tier alone — before
ticking a single room in the "which rooms would you like audio in?" panel — already
added the full whole-property cost to the budget. The room-selection panel is what's
meant to grow the total; the card itself should only show a "from" price for one zone.
`zone_prices.audio` (used for each additional room ticked in the panel) is unchanged —
still `calc_audio(1, "Entry")`.

| Component | Model | Unit Price (ex-VAT) |
|-----------|-------|---------------------|
| Ceiling speakers (Premium) | Sonance IS8 pair | R 41,974/zone |
| Ceiling speakers (Mid est.) | — | R 36,937/zone (88%) |
| Ceiling speakers (Entry est.) | — | R 31,480/zone (75%) |
| Amplifier | Sonos Amp | R 17,390/zone |
| Speaker cable point | — | R 1,200/zone |

1-zone reference totals now shown on the option cards: Entry R 55,120 · Mid R 60,577 ·
Premium R 65,614 (Premium matches the De Klerk reference exactly).

### Labour — Audio

| Task | Rate (ex-VAT) |
|------|--------------|
| First fix | R 1,900/zone |
| Second fix | R 1,900/zone |
| Programming | R 1,250/zone |

---

## Home Theatre — Fixed Tier Values

| Tier | Description | Net (ex-VAT) | Inc VAT |
|------|-------------|-------------|---------|
| Entry | ARCAM AVR, M&K 7.1.4 Atmos, in-wall sub | R 389,217 | R 447,600 |
| Mid | Entry + larger M&K + premium 15" sub | R 572,524 | R 658,353 |
| Premium | ARCAM AVR21 + heavy-duty amp, top M&K, dual 15" subs | R 822,609 | R 946,350 |

---

## System Integration — Savant (Fixed Tier Values)

| Tier | What's included | Net (ex-VAT) | Inc VAT |
|------|----------------|-------------|---------|
| Entry | S12 controller + programming | R 80,970 | R 93,115 |
| Mid | Entry + HVAC + door + lighting integration | R 172,970 | R 198,865 |
| Premium | Mid + Pro processor | R 261,274 | R 300,515 |

Add-on rates (inc VAT): HVAC +R52,375 | Door +R23,155 | Lighting +R30,220 | Pro processor +R101,650

---

## Full Tier Totals — WeQuote REF:0011 (inc VAT)

| System | Entry | Mid | Premium |
|--------|-------|-----|---------|
| Lighting Control | R 947,692 | R 1,152,152 | R 1,535,852 |
| CCTV | R 165,335 | R 328,644 | R 388,115 |
| Network & Wi-Fi | R 146,429 | R 175,960 | R 298,231 |
| Audio | R 40,046 | R 53,176 | R 75,456 |
| Home Theatre | R 447,600 | R 658,353 | R 946,350 |
| Access Control | R 48,135 | R 53,709 | R 263,119 |
| System Integration | R 93,115 | R 198,865 | R 300,515 |
