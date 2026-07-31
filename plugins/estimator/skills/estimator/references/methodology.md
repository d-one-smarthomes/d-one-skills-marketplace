# How the reference data was built

This documents where `assets/` came from, for whoever maintains this skill next.

## Source data

Built from D-One's live product inventory export (5,083 products with sales prices)
plus 22 real WeQuote quote exports (the "Formula" / "- lines" workbooks), each of
which has a second sheet with one row per quoted line item, including:

`unit_cost, unit_price, labour_hours, labour_price, labour_cost, 1st Fix Cabling,
2nd Fix Installation, Programming, category, sku, total_quantity, accepted_date`

## What we found

**Labour is always billed as hours × hourly rate, split into three phases**
(1st Fix Cabling, 2nd Fix Installation, Programming). Across 1,773 labour line
items checked, labour cost was **exactly 50% of labour price every single time** —
a flat margin rule, not a coincidence. So labour cost never needs separate
tracking — it's always sell / 2.

**The hourly rate itself has increased over time.** Pure single-phase line items
(only one of the three phase-hours nonzero) let us solve for the exact rate on
each historical quote. We saw 700/800/950 per hour for 1st Fix Cabling and 2nd Fix
Installation, and 900/1000/1250 per hour for Programming, with the highest tier
appearing in the most recent (July 2026) quotes. `rate_card.json` uses the highest
/ most recent tier as the current default — check with D-One if it's since changed
again.

**Equipment markup (price vs cost) is much less consistent** — historical markups
ranged anywhere from ~1.0x to ~2.4x depending on the product, with a median around
1.45x. Rather than guess a single margin for everything, we built a per-SKU cost
lookup (`equip_cost_by_sku.json`) from the 1,907 historical equipment lines that had
real cost data, and only fall back to the 1.45x median markup for SKUs with zero
quote history.

**Labour hours per product also came from history, not a spec sheet.** For each
SKU that appeared in more than one historical quote, we took the mode (most common
value, falling back to median) of hours-per-unit for each phase. 239 SKUs had
enough history for a per-SKU figure; everything else falls back to a per-category
average (39 categories, computed the same way).

## Known limitations

- Only ~332 of the 5,083 inventory SKUs have real historical cost data; the rest use
  the fallback markup and should be treated as rougher estimates.
- Only 239 SKUs have direct labour-hour history; everything else uses a category
  average, which can be noisy for categories with few historical observations (check
  `n_observations` in `labour_hours_by_category.json` before trusting a low-count
  category too heavily).
- Hours-per-unit doesn't always scale perfectly linearly with quantity in the
  source data (e.g. cable reels), so per-unit figures are an approximation, not an
  exact physical model.
- This was built from 22 quotes — a bigger sample (more quotes, exported the same
  way) would sharpen every number here. If more WeQuote exports become available,
  re-run the same extraction approach: pull the second sheet from each workbook,
  aggregate by SKU, and regenerate the four JSON/CSV files in `assets/`.
