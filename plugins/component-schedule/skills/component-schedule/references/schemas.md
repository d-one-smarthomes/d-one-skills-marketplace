# JSON Schemas

## project_data.json

```json
{
  "project_name": "Price Drive",
  "quote_ref": "0179 R10",
  "prepared_by": "D-One",
  "headend_room": "Services",
  "floors": [
    {
      "level": "PERIMETER",
      "rooms": [
        {
          "room": "Front Gate",
          "items": [
            {
              "description": "Door Intercom Terminal",
              "model": "UA-G3-Intercom",
              "qty": 1,
              "system_category": "Intercom & Access Control",
              "is_provisional": false
            }
          ]
        }
      ]
    }
  ]
}
```

**Fields:**
- `project_name` — client-facing project name
- `quote_ref` — quote number / revision
- `prepared_by` — always "D-One"
- `headend_room` — name of the server/rack room
- `floors[].level` — floor label in CAPS (e.g. "PERIMETER", "L1 BASEMENT", "L2 GROUND FLOOR")
- `rooms[].room` — exact room name as it appears in the quote
- `items[].description` — **must exactly match** the key in product_research.json
- `items[].model` — product model number (optional, shown as sub-text)
- `items[].qty` — integer quantity
- `items[].system_category` — one of the known category strings (see SKILL.md)
- `items[].is_provisional` — true if quote marks this as provisional/TBC

**Exclude from items:** cables, labour, consumables, network/TV point terminations, backboxes.

---

## product_research.json

```json
{
  "products": {
    "Door Intercom Terminal": {
      "dimensions": "325 × 114 × 28 mm",
      "photo_b64": "data:image/jpeg;base64,/9j/4AAQ..."
    },
    "Linkbasic 42U Server Cabinet": {
      "dimensions": "600 × 2054 × 1000 mm",
      "photo_b64": null
    }
  }
}
```

**Fields:**
- Key = exact product description (must match project_data.json `description`)
- `dimensions` — "W × H × D mm" format; use "—" if unavailable
- `photo_b64` — full data URI string, or null if not yet fetched
