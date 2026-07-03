---
name: component-schedule
description: >
  Generates a D-One branded Component & Equipment Schedule PDF from a project quote.
  Use this skill whenever the user mentions: component schedule, equipment schedule,
  spec sheet, product list PDF, or asks to turn a quote into a document showing
  products/photos/dimensions. Also trigger when the user says things like "make the
  schedule", "generate the spec doc", "build the equipment list", or "update the
  component PDF". The output is a polished A4 PDF with product photos, dimensions,
  quantities, room-by-room layout, and colour-coded system categories — ready to
  hand to a client or include in a proposal.
---

# Component & Equipment Schedule Skill

## What this produces

A professional A4 PDF containing:
- Project banner (name, quote ref, prepared by)
- Colour-coded system-category legend
- Room-by-room table with product photo, description, qty, dimensions, system badge
- 12-month SLA note and D-One footer

## Quick start — the four-step workflow

```
1. Parse quote  →  project_data.json
2. Look up products in bundled database  →  product_research.json
3. Fetch photos via Chrome  (only for products NOT already in the database)
4. Run generate_spec_pdf.py  →  PDF
```

The bundled `references/product_database.json` already contains **35 D-One standard products** with dimensions and photos pre-loaded. For most D-One quotes, Step 3 will be skipped entirely.

---

## Step 1 · Parse the quote into project_data.json

The user will provide a quote as one of: Excel file, PDF, image, or plain text.

Parse it into the `project_data.json` schema (see `references/schemas.md`).

Key rules:
- `description` values in each item must **exactly match** the keys used in `product_research.json`. Decide on the canonical product name early and use it consistently in both files.
- Group items by floor then by room. If the quote lists items without rooms, put them all under a single room named "General".
- `system_category` must be one of the known values listed below. If unsure, pick the closest match.
- Mark items as `"is_provisional": true` when the quote says "(Prov)", "provisional", "TBC", or similar.
- `headend_room` in the project dict is the rack/services room name — used for reference only.
- **Exclude** from project_data.json: cables, labour, consumables, network/TV points (cable terminations), and backboxes. Only include physical equipment items.

---

## Step 2 · Build product_research.json from the bundled database

**Always check `references/product_database.json` first.** This database has all D-One standard products pre-loaded with dimensions AND photos.

For each unique product description in the quote:
1. Look up the exact key in `references/product_database.json`
2. If found → copy the entry (dimensions + photo_b64) into the working `product_research.json`
3. If NOT found → research dimensions via web search; leave `photo_b64: null` for now

The working `product_research.json` format:
```json
{
  "products": {
    "Exact Product Name": {
      "dimensions": "440 × 44 × 380 mm",
      "photo_b64": "data:image/jpeg;base64,/9j/4AAQ..."
    }
  }
}
```

Dimensions format: `W × H × D mm`. Use `"—"` if genuinely unavailable.

---

## Step 3 · Fetch photos via Chrome (only for new/unknown products)

**Skip this step entirely if all products are in the bundled database.**

Photos must be fetched via Chrome browser — the Linux sandbox has no internet access.

### Canvas technique

Navigate Chrome to the vendor's product page, then inject:

```javascript
// Setup: run once
window._b64 = {};
window._fr2 = function(key, url, size, quality) {
  return fetch(url).then(r => r.blob()).then(blob => new Promise(resolve => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      const c = document.createElement('canvas');
      c.width = size; c.height = size;
      c.getContext('2d').drawImage(img, 0, 0, size, size);
      window._b64[key] = c.toDataURL('image/jpeg', quality).split(',')[1];
      resolve(window._b64[key].length);
    };
    img.onerror = () => { window._b64[key] = null; resolve(0); };
    img.src = URL.createObjectURL(blob);
  }));
};
```

Fetch at 120px / 0.7 quality, extract in 900-char slices:
```javascript
window._fr2('KEY', 'https://example.com/image.png', 120, 0.7).then(len => len + ' chars ready')
window._b64['KEY'].slice(0, 900)
window._b64['KEY'].slice(900, 1800)
// ...keep slicing until empty string
```

Store as: `"photo_b64": "data:image/jpeg;base64," + chunk1 + chunk2 + ...`

### After fetching new photos

**Always merge new products back into `references/product_database.json`** so they're available for future quotes. Use the product's canonical description as the key.

---

## Step 4 · Generate the PDF

The skill includes `scripts/generate_spec_pdf.py`. Copy it to the working directory, then run:

```bash
pip install weasyprint --break-system-packages -q
python3 generate_spec_pdf.py project_data.json product_research.json output.pdf
```

Save the PDF to the user's workspace folder as `[ProjectName]_Component_Schedule.pdf`.

---

## Known system categories

Use exactly these strings in `system_category`:

| Category | Badge colour |
|---|---|
| WiFi & Network | Blue (#1379C9) |
| Video Distribution | Purple (#7030A0) |
| Intercom & Access Control | Dark Red (#C00000) |
| Video Conferencing | Teal (#00695C) |
| Headend & Rack Cabinets | Dark Grey (#404040) |
| Multiroom Audio | Green (#375623) |
| Dolby Atmos Surround Sound | Orange (#E06C00) |
| Lighting Control | Amber (#BF8F00) |
| Security & Surveillance | Dark Purple (#3D1F6B) |

Anything not in this list gets a grey badge.

---

## Products already in the bundled database

The following D-One standard products are pre-loaded with dimensions and photos in `references/product_database.json`. No web search or Chrome fetch needed for these:

**Security & Surveillance**
- G6 Turret Camera, G6 Pro Bullet Camera, G6 Entry Door Camera, UniFi NVR Pro

**Intercom & Access Control**
- Door Intercom Terminal, Intercom Viewer, UniFi Access Door Hub, Door Hub Mini

**WiFi & Network**
- UniFi Dream Machine Pro Max, UniFi Pro Max Switch 24, UniFi Pro Max Switch 24 PoE,
  UniFi Pro Max Switch 16 PoE, UniFi WiFi 7 Pro XGS AP, UniFi WiFi 7 Outdoor AP

**Headend & Rack Cabinets**
- Linkbasic 42U Server Cabinet

**Multiroom Audio**
- Marantz Model M1 Network Amplifier, Marantz Model M4 Streaming Amplifier,
  B&W CCM7.5 S2 In-Ceiling Speaker, B&W CWM7.4 S2 In-Wall Speaker,
  B&W CWM7.5 S2 In-Wall Speaker, B&W CCM683 In-Ceiling Speaker,
  B&W AM1 Outdoor Speaker, B&W 607 S3 Bookshelf Speaker,
  JBL Control 28-1 Speaker, SVS 3000 In-Wall Subwoofer

**Dolby Atmos Surround Sound**
- Marantz Cinema50 AV Amplifier

**Lighting Control**
- Lutron HomeWorks QSX Processor, Lutron LQSE Dimmer Module,
  Lutron Universal DALI Module, Lutron QS Link Power Supply,
  Lutron QS Wall Box Interface, Lutron Alisse S2 Keypad,
  Motion Sensor 360

---

## Tips

- **Key consistency is critical** — a mismatch between `description` in project_data.json and the key in product_research.json produces a missing photo. Double-check casing, spacing, and punctuation.
- **Placeholder graceful degradation** — products with no `photo_b64` get a text placeholder box, not an error.
- **Grow the database** — after each project, merge any new products back into `references/product_database.json` to avoid re-fetching next time.
- **WeasyPrint renders to A4** — the generate_spec_pdf.py script handles all layout, colour coding, and page breaks automatically.
