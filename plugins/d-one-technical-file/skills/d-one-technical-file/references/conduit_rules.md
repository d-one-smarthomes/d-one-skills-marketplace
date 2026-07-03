# Conduit Schedule — Rules & Format

## Format reference: 2 Nettleton Road Conduit Schedule

The conduit schedule is an A4 document (portrait) for the electrical installer. It tells them what conduit to install in each room, where it runs to, and what cable goes inside.

---

## Page layout

**Header:** Same as spec doc — `{ProjectName} | Conduit Schedule` left, `d·one | darren@d-one.co.za | 021 012 5112` right.

**Cover banner:** Dark navy (`#1C2B4A`), with title "Conduit Schedule" and project/quote details.

**Footer:** Same format as spec doc.

---

## Table structure

**Table header columns (dark slate `#37474F`, white text):**

| Column | Width | Notes |
|---|---|---|
| Point | ~60px | Always shows `■` checkbox icon |
| Conduit Size | ~90px | In mm, e.g. "25mm" |
| Destination | ~180px | Where the conduit runs to |
| Cable | ~180px | Cable type(s) in the conduit |
| Backbox | ~100px | Backbox size required |
| Power pt | ~80px | "Yes" if a power point is needed |

---

## Section header rows

**Level header:** Full-width row, dark navy (`#1C2B4A`), white bold text, all caps.
Example: `L1 BASEMENT`

**Room header:** Full-width row, medium navy/blue (`#1E3A5F`), white bold text.
Example: `Services`

---

## Conduit mapping rules

Apply these rules to each product item from `project_data.json`. For each item, generate one or more conduit rows.

### Network & WiFi

| Device | Conduit | Destination | Cable | Backbox | Power pt |
|---|---|---|---|---|---|
| WiFi Access Point (any model) | 25mm | Head-End | 1x CAT6 | 4×4 | No |
| LAN / Data Point | 25mm | Head-End | 1x CAT6 | Single gang | No |
| IP Camera (UniFi) | 25mm | Head-End | 1x CAT6 | Deep round | No |
| UniFi NVR | — | (rack-mounted) | — | — | Yes |
| UDM-MAX / Gateway | — | (rack-mounted) | — | — | Yes |
| UniFi Switch (rack) | — | (rack-mounted) | — | — | Yes |
| Patch Panel | — | (rack-mounted) | — | — | No |

### Video Distribution

| Device | Conduit | Destination | Cable | Backbox | Power pt |
|---|---|---|---|---|---|
| TV Point (single) | 25mm | Head-End | 3x CAT6 | 4×4 | Yes |
| TV Point (double) | 32mm | Head-End | 4x CAT6 | 4×4 deep | Yes |
| DSTV Decoder | 25mm | Head-End | 1x CAT6 + RG6 | 4×4 | Yes |
| Satellite Dish | 32mm | Head-End | 2x RG6 | (external bracket) | No |

### Intercom & Access Control

| Device | Conduit | Destination | Cable | Backbox | Power pt |
|---|---|---|---|---|---|
| UniFi Access Intercom (outdoor) | 20mm | Head-End | 1x CAT6 | Flush round outdoor | No |
| Monitor for UniFi Access Intercom | 20mm | Head-End | 1x CAT6 | 2×4 | Yes |
| Electric Gate Lock | 20mm | Head-End | 2-core + CAT6 | (inline) | No |
| Electric Door Lock | 20mm | Head-End | 2-core + CAT6 | (inline) | No |
| Biometric Reader (standalone) | 20mm | Head-End | 1x CAT6 | 2×4 deep | No |

### Multiroom Audio

| Device | Conduit | Destination | Cable | Backbox | Power pt |
|---|---|---|---|---|---|
| Sonos AMP | 25mm | Head-End | 1x CAT6 | (wall/shelf) | Yes |
| In-Ceiling Speaker | 25mm | Amp location | 2x Speaker Cable | (ceiling void) | No |
| In-Wall Speaker | 25mm | Amp location | 2x Speaker Cable | In-wall cavity | No |
| Sonos Sub / Subwoofer | — | (freestanding) | — | — | Yes |

### Dolby Atmos / Surround Sound

| Device | Conduit | Destination | Cable | Backbox | Power pt |
|---|---|---|---|---|---|
| AV Receiver / Amplifier | 32mm | Head-End | 1x CAT6 + HDMI | 4×4 deep | Yes |
| In-Ceiling Atmos Speaker | 25mm | AV Receiver | 2x Speaker Cable | (ceiling void) | No |
| In-Wall Surround Speaker | 25mm | AV Receiver | 2x Speaker Cable | In-wall cavity | No |
| Subwoofer (in-room) | — | AV Receiver | Speaker Cable | — | Yes |
| Surround Speaker (surface) | 25mm | AV Receiver | Speaker Cable | (bracket) | Yes |

### Lighting Control (Lutron)

| Device | Conduit | Destination | Cable | Backbox | Power pt |
|---|---|---|---|---|---|
| Lutron Keypad (8-button) | 25mm | Lighting DB / Spanel | 4-core Mylar | 4×4 | No |
| Lutron Keypad (4-button) | 25mm | Lighting DB / Spanel | 4-core Mylar | 2×4 | No |
| Lutron Keypad (2-button) | 20mm | Lighting DB / Spanel | 4-core Mylar | Single gang | No |
| Motion Sensor (Lutron) | 20mm | Lighting DB | 4-core Mylar | Surface round | No |

> **Note:** Lutron processors (HQP), dimmers/ELV modules, relays, and M4/P4 amps are all DB/panel-mounted. They **do not require conduit routes** and must be **excluded from the conduit schedule**.

### Headend / Rack

| Device | Conduit | Destination | Cable | Backbox | Power pt |
|---|---|---|---|---|---|
| Server / Network Rack | — | (self-contained) | — | — | Yes (dedicated circuit) |
| UPS | — | (rack-mounted) | — | — | Yes |

### Video Conferencing

| Device | Conduit | Destination | Cable | Backbox | Power pt |
|---|---|---|---|---|---|
| Interactive Panel / SKYE Panel | 32mm | Head-End | 1x CAT6 + HDMI | 4×4 | Yes |

---

## Special rules

1. **"Head-End" as destination:** Use the `headend_room` value from `project_data.json` as the full destination string (e.g. "L1 Basement: Services"). Abbreviate to "Head-End" in the table.

2. **Provisional items:** Include in the conduit schedule. Add "(Prov)" to the Point column: `■ (Prov)`.

3. **Perimeter / outdoor items:** Conduit size increases by 5mm for outdoor runs due to weatherproofing requirement. Indicate "(outdoor)" in the Destination column.

4. **Items not requiring conduit** (rack-mounted, freestanding with power only):
   - Skip them in the conduit schedule entirely, OR add a single row with "–" in Conduit Size and a note in the Cable column like "Power circuit only".

5. **Multiple cables in one conduit:** List all cables in the Cable column separated by " + ". Example: `CAT6 + HDMI 2.1`.

---

## Cable abbreviation reference

| Full name | Abbreviation used in schedule |
|---|---|
| Category 6A UTP | CAT6 |
| Category 6A UTP PoE | CAT6 (PoE) |
| Category 5e UTP | CAT5e |
| 2-core volt-free | 2-core |
| Speaker cable (2-core) | Speaker Cable |
| HDMI 2.1 High Speed | HDMI 2.1 |
| RG6 coaxial | RG6 |
| SFP+ DAC / Fibre | SFP+ DAC |

---

## Ordering in the schedule

Order rooms exactly as they appear in the quote (level → room order from the WeQuote PDF). Do not alphabetise. Keep the headend room first within its level.
