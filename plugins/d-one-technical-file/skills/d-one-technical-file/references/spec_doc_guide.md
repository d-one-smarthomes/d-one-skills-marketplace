# Component & Equipment Schedule — Format Guide

This document describes the exact visual format of the D-One Component & Equipment Schedule, based on the House Prinsloo reference (Quote 0252 R1.2).

---

## Page layout

- **Page size:** A4 landscape (297mm × 210mm) OR A4 portrait — the Prinsloo reference uses portrait. Use portrait.
- **Margins:** ~15mm all sides
- **Font:** System sans-serif (Inter, Helvetica, or Arial)

---

## Header bar (top of every page except cover)

Single line across the top, light border below:
```
House Prinsloo | Component & Equipment Schedule          d·one | darren@d-one.co.za | 021 012 5112
```
- Left: `{ProjectName} | Component & Equipment Schedule` — bold, dark
- Right: `d·one | darren@d-one.co.za | 021 012 5112` — lighter weight

---

## Cover banner (first page only)

Dark navy rectangle (`#1C2B4A`) spanning full width, ~100px tall.

Left side (white text):
- Large heading: **"Component & Equipment Schedule"** (~28px, bold)

Right side (smaller white text, right-aligned):
```
{ProjectName}
Quote Ref: {QuoteRef}
Prepared by {PreparedBy} | D-One
```

---

## System category colour tabs (first page, below cover banner)

A row of coloured pill/badge buttons showing all system categories present in this project. These are for visual reference only.

| Category | Background Colour |
|---|---|
| WiFi & Network | `#1565C0` |
| Video Distribution | `#7B1FA2` |
| Intercom & Access Control | `#B71C1C` |
| Video Conferencing | `#00838F` |
| Headend & Rack Cabinets | `#37474F` |
| Multiroom Audio | `#2E7D32` |
| Dolby Atmos Surround Sound | `#E65100` |
| Lighting Control | `#F57F17` |
| Security & Surveillance | `#6A1B9A` |

Only show categories that actually appear in the project. Text is white, bold, ~12px. Pill shape (border-radius ~4px). Display in a single flex-wrap row.

---

## Table header row

Dark slate background (`#37474F`), white text, bold:

| Column | Width | Notes |
|---|---|---|
| Photo | ~120px | Centred |
| Component Description | flex/fill | Left-aligned |
| Qty | ~60px | Centred, bold |
| Dimensions (W x H x D) | ~220px | Monospace font for dimensions |
| System | ~180px | Right-aligned |

---

## Room section header rows

**Background:** `#1C2B4A` (same dark navy as cover)
**Text:** White, bold, ~14px
**Format:** `■ {Floor}: {Room Name}` — spans all 5 columns

The "■" is a filled black square (Unicode U+25A0 or ■). In the rendered document it appears as a small dark square before the room name.

---

## Product item rows

Alternating white / very light grey (`#F9F9F9`) background.

**Photo cell:**
- Image centred in cell, max height 80px, max width 100px
- If no photo available: light grey box with product initials or model number in grey text

**Description cell:**
- Product name in regular weight, dark text
- Font size ~13px

**Qty cell:**
- Number, bold, centred, dark text

**Dimensions cell:**
- Dimensions text in a slightly smaller monospace style (~11px), grey colour (`#546E7A`)
- Example: `442 x 43.7 x 285 mm (1U rack)` or `Cutout: Ø 165 mm | Depth: 70 mm | Baffle: Ø 215 mm`

**System cell:**
- Coloured badge/pill matching system category colour (see table above)
- White text, bold, ~11px, centred
- Border-radius ~4px, padding ~4px 8px

---

## Footer (bottom of every page)

Light grey background, small text (~10px):
```
{ClientName} | Quote Ref: {QuoteRef} | Prepared: {Date} | Valid to: {ValidDate}          Page {N}
```

Left-aligned client/quote info, right-aligned page number.

---

## Final page note

After the last product row, add an italicised note in D-One blue:
```
12 Months Free Remote & Onsite Support included with all installed works. A paid SLA is available after the initial 12-month period.
```

---

## HTML generation notes for generate_spec_pdf.py

The script generates a complete HTML document with embedded CSS. Key CSS patterns:

```css
/* Table layout */
table { width: 100%; border-collapse: collapse; }
td, th { padding: 8px 10px; vertical-align: middle; }

/* Room header */
.room-header td { 
  background: #1C2B4A; color: white; font-weight: bold; 
  font-size: 14px; padding: 10px 12px; 
}

/* System badge */
.badge { 
  display: inline-block; color: white; font-weight: bold;
  font-size: 11px; padding: 4px 10px; border-radius: 4px; 
  text-align: center; white-space: nowrap;
}

/* Dimensions */
.dim { 
  font-family: 'Courier New', monospace; font-size: 11px;
  color: #546E7A; 
}

/* Photo */
.photo-cell img { max-width: 100px; max-height: 80px; object-fit: contain; }
.photo-placeholder { 
  width: 80px; height: 70px; background: #ECEFF1; 
  display: flex; align-items: center; justify-content: center;
  color: #90A4AE; font-size: 10px; text-align: center; 
}
```

For WeasyPrint, ensure images are embedded as base64 data URIs (download → base64 encode → embed inline) rather than using external URLs, which may not resolve in the sandboxed environment.
