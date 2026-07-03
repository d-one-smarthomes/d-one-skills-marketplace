# WeQuote PDF Parse Guide

## What WeQuote looks like

WeQuote generates multi-page PDFs with this structure:

**Cover page / header:**
- Project name (e.g. "Price Drive reviewed")
- Client name (e.g. "Yves Devis")
- Quote Ref (e.g. "0179 R7") — always starts with a number, then a revision letter
- Date prepared (e.g. "27/03/2026")
- Prepared by (e.g. "Caleb Thetard")
- Valid to date

**Body — Room sections:**
Each room is introduced by a bold section header in the format:
```
{Level}: {Room Name}
```
Examples:
- `L1 Basement: Services`
- `L2 Ground: Living`
- `L2 Ground: Entertainment`
- `L3 First: Main Bedroom`
- `Perimeter: Front Gate`
- `L2 Ground: Main DB` (DB = Distribution Board, usually contains Lutron or electrical equipment)

Under each heading is a table with columns: Qty | Description | (small thumbnail) | Net Total

**End of document:**
- Project Summary by system/area
- Terms and conditions

## Extraction rules

1. **Level naming:** Normalise level names for consistency:
   - "L1 Basement" / "Basement" → `"L1 Basement"`
   - "L2 Ground" / "Ground Floor" / "Ground" → `"L2 Ground"`
   - "L3 First" / "First Floor" / "First" → `"L3 First"`
   - "Perimeter" / "External" / "Outdoor" → `"Perimeter"`

2. **Room naming:** Keep the room name exactly as written, including suffixes like "1", "2", "(Prov)", etc.

3. **Ignore these line items** (they are not hardware):
   - Labour / installation lines
   - Cable supply lines (e.g. "50m CAT6 cable")  
   - Warranty / support lines (e.g. "12 Months Support")
   - Accessory packs (e.g. "Wall plate pack")
   - Lines where Description contains only "—" or is blank

4. **Headend identification:** The headend/services room typically contains:
   - A UDM-MAX or gateway device
   - Network switches
   - A rack cabinet
   - An NVR (if security cameras are in the quote)
   Look for room names like "Services", "Head End", "Server Room", "Battery Room", "Network Room", "Comms Room"

---

## project_data.json schema

```json
{
  "project": {
    "name": "Price Drive",
    "client": "Yves Devis",
    "quote_ref": "0179 R7",
    "date": "27/03/2026",
    "prepared_by": "Caleb Thetard",
    "valid_to": "10/04/2026",
    "headend_room": "L1 Basement: Services"
  },
  "floors": [
    {
      "level": "L1 Basement",
      "rooms": [
        {
          "name": "Services",
          "full_name": "L1 Basement: Services",
          "is_headend": true,
          "items": [
            {
              "qty": 1,
              "description": "Ubiquiti UniFi Dream Machine MAX (UDM-MAX)",
              "system_category": "WiFi & Network",
              "is_provisional": false
            },
            {
              "qty": 3,
              "description": "UniFi Pro Max Switch 24",
              "system_category": "WiFi & Network",
              "is_provisional": false
            }
          ]
        }
      ]
    }
  ]
}
```

**Field notes:**
- `is_provisional`: set to `true` if the room name contains "(Prov)" or the description contains "Provisional"
- `system_category`: assigned per the mapping table in SKILL.md
- `full_name`: always `"{level}: {room}"` — used as the display label in documents
- `headend_room`: the `full_name` of the headend room — used in conduit schedule as the "Destination" for most cable runs

---

## product_research.json schema

```json
{
  "products": {
    "Ubiquiti UniFi Dream Machine MAX (UDM-MAX)": {
      "photo_url": "https://...",
      "photo_b64": "data:image/png;base64,iVBORw0KGgo...",
      "dimensions": "442 x 43.7 x 285 mm (1U rack)",
      "system_category": "WiFi & Network",
      "ports": {
        "WAN": "1x 10GbE SFP+",
        "LAN 1-8": "8x GbE RJ45",
        "SFP+ 1": "10GbE uplink"
      },
      "notes": ""
    },
    "Ubiquiti UniFi WiFi 7 Pro XG Tri-Band White AP": {
      "photo_url": "https://...",
      "photo_local": "photos/wifi7_pro_xg.jpg",
      "dimensions": "Ø 200 mm x H 35 mm",
      "system_category": "WiFi & Network",
      "ports": {
        "PoE In": "802.3bt PoE++ (90W)"
      },
      "notes": ""
    }
  }
}
```

**Fetching photos — IMPORTANT:**
Do NOT rely on the Python script to download images at runtime (the bash sandbox blocks outbound HTTP). Instead, during Phase 2, use the `WebFetch` tool to download each product image yourself and store it as a base64 string in the `photo_b64` field. The script reads this field directly.

For each product:
1. Use `WebFetch` to fetch the image URL
2. If WebFetch returns binary/image data, base64-encode it and store in `photo_b64`
3. If WebFetch returns HTML (the URL is a product page, not a direct image), look in the HTML for the actual image src URL and fetch that instead
4. If no image can be found after 2 attempts, set `photo_b64` to `null` — the script will show a placeholder

Good image sources by brand:
- Ubiquiti: `https://static.ui.com/fingerprint/ui/icons/{model}.png` or the techspecs page image tag
- Sonos: `https://www.sonos.com` product pages contain og:image meta tags with direct image URLs
- Lutron: `https://www.lutron.com` product pages — look for product hero images
- B&W: `https://www.bowerswilkins.com` product images are in the page HTML
- Marantz: `https://www.marantz.com` product page contains image tags
- Klipsch: `https://www.klipsch.com` product pages

**Dimensions format guide:**
- Rack equipment: `"W x H x D mm (NU rack)"` e.g. `"442 x 43.7 x 285 mm (1U rack)"`
- Round ceiling items: `"Cutout: Ø XXX mm | Depth: XX mm"` or `"Ø XXX mm x H XX mm"`
- Rectangular wall items: `"W x H x D mm | Cutout: W x H mm | Depth: D mm"`
- Freestanding: `"W x H x D mm | Weight: X.X kg"`
- Wall plates / generic points: `"Single gang wall plate"` or `"Double gang wall plate"`
