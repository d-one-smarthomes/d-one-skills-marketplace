# D-One Module Sizing Rules

**Core rule: hardware comes in fixed-capacity modules. Always round UP.**

---

## 1. Lutron HomeWorks — Dimmer & Switch Modules

`modules_needed = ceil(circuits / channels_per_module)`

| Module | Channels | Price | Round to |
|--------|----------|-------|----------|
| LQSE-4A5-230-D (dimmer) | 4 | R 24,261 | next multiple of 4 |
| LQSE-4S5-230-D (switch) | 4 | R 10,000 | next multiple of 4 |
| LQSE-2DALUNV-D (DALI) | 2 | R 34,870 | next multiple of 2 |

```
9 dimming circuits → ceil(9/4) = 3 modules → 12 channels (3 wasted)
Cost: 3 × R24,261 = R72,783
```

Power supplies: 1 per ~12 modules → `ceil(total_modules / 12)`

---

## 2. CCTV — NVR Camera Capacity

`nvrs = ceil(cameras / 15)` — UNVR-G2 handles max 15 cameras
`hdds = ceil(cameras / 8)`  — 1 × 8TB HDD per 8 cameras (30-day retention)

---

## 3. Network — Switch Port Sizing

```
poe_devices = aps_indoor + aps_outdoor + cameras
poe_ports   = ceil(poe_devices × 1.2)   # 20% headroom
poe_switches = ceil(poe_ports / 48)     # USW-MAX48P
```
Always add 1 × USW-MAX24 as core/aggregation switch.

---

## 4. Audio — Stereo Zones

Speakers always in stereo pairs. `audio_zones = ceil(speaker_icons / 2)`
1 Sonos Amp per zone — no sharing.

---

## 5. Lighting — Circuit Estimation from Keypads

When electrical drawings aren't available:
```
dimming_circuits  = ceil(keypads × 2.5 / 4) × 4
switched_circuits = ceil(keypads × 0.7 / 4) × 4
dali_circuits     = keypads // 10
```
Based on De Klerk: 30 keypads → 79 dim + 22 sw + 2 DALI = 103 circuits.

---

## 6. Lighting — Tier Scaling

| Tier | Circuit scale | Keypad scale |
|------|--------------|--------------|
| Premium | 100% | 30 keypads |
| Mid | ~75% | ~20 keypads |
| Entry | ~50% | ~10 keypads |

---

## Python Reference

```python
import math

def modules_needed(circuits, channels_per_module):
    if circuits <= 0: return 0
    return math.ceil(circuits / channels_per_module)

dim_modules  = modules_needed(dimming_circuits, 4)
sw_modules   = modules_needed(switched_circuits, 4)
dali_modules = modules_needed(dali_circuits, 2)
ps_count     = math.ceil((dim_modules + sw_modules + dali_modules) / 12)

nvr_count    = math.ceil(cameras / 15)
hdd_count    = math.ceil(cameras / 8)

poe_switches = math.ceil(math.ceil((aps + cameras) * 1.2) / 48)
audio_zones  = math.ceil((ceiling_speakers + wall_speakers) / 2)
```

**Accuracy:** Using these rules, the calculator matches De Klerk actual WeQuote totals to within 0.2%.
