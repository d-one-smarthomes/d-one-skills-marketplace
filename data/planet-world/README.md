# Planet World Catalogue: WeQuote vs Odoo

Comparison of the Planet World (Planetworld) product catalogue as it appears in D-One's two systems, pulled 2026-07-31.

## Files

- `planet_world_wequote_export.csv` — live export from WeQuote's "Planet World" catalogue (`app.wequote.cloud/d-one/catalogue/448`), synced from Planetworld's live supplier feed. 2,264 rows.
- `planetworld_odoo_export.csv` — export from Odoo (`d-one.odoo.com`), all products with vendor = Planetworld. 2,251 rows.
- `planet_world_wequote_vs_odoo_comparison.csv` — merged comparison by SKU.

## Comparison summary

| Status | Count |
|---|---|
| Matched — price identical | 2,141 |
| Matched — price mismatch | 71 |
| Only in WeQuote (missing from Odoo) | 51 |
| Only in Odoo (missing from WeQuote) | 39 |

WeQuote also has 2 SKUs listed twice (duplicate rows) — worth cleaning up in WeQuote directly.

## Notes

- WeQuote is treated as the "live" reference since it syncs from Planetworld's own feed.
- Planetworld's public website (planetworld.co.za) has no dealer/trade pricing portal accessible without a login, so it wasn't used as a third source.
- `price_diff_wequote_minus_odoo` is positive when WeQuote's sell price is higher than Odoo's sales price.
