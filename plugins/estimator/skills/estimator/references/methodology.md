# How the reference data was built

This documents where `assets/` came from, for whoever maintains this skill next.
It was built in two passes — read both, since the second pass explains why the
data is structured the way it is.

## Pass 1: initial build (22 sample quotes)

The first version was built from D-One's live product inventory export (5,083
products with sales prices, from Odoo) plus 22 real WeQuote quote exports (the
"Formula" / "- lines" workbooks), each of which has a second sheet with one row
per quoted line item, including a rare and valuable field: hours broken into
`1st Fix Cabling`, `2nd Fix Installation`, and `Programming` per line.

That breakdown is what let us establish the core pricing model: **labour is
billed as hours x hourly rate, split into three phases**, and **labour cost is
always exactly 50% of labour price** (confirmed on 1,773 labour lines, zero
exceptions). The per-phase hourly rates found in that sample: 700/800/950 per
hour for 1st Fix Cabling and 2nd Fix Installation, 900/1000/1250 for Programming,
climbing over time, with the highest tier in the most recent (July 2026) quotes.

## Pass 2: full WeQuote database export (453 quotes, 20,814 line items)

D-One then provided a complete WeQuote data export (`wequote-export` skill, all
tables: quotes, quote_lines, products, customers, projects, invoices, etc. —
see the export's own README.md for the table grain and join keys). This is
roughly 12x more line items than pass 1, and — critically — `products.csv`
carries the current `cost_price` and `sell_price` directly per product, so
equipment cost/price no longer needs to be inferred from quote history alone.

**The catch**: this full export's `quote_lines.csv` only has *aggregate* labour
hours per line (`unit_labour_hours`) — it does not preserve the 1st Fix / 2nd
Fix / Programming split that pass 1's sample happened to have. To keep that
useful three-phase breakdown without throwing away the much bigger dataset, we:

1. Took the per-category phase ratios learned in pass 1 (e.g. "AI CCTV" is
   ~100% 2nd Fix Installation hours, "Panelised Lighting Controls" is ~100%
   Programming hours, "Access Points" splits 50/50 between 1st Fix and 2nd Fix).
2. Applied those ratios to the much larger, more current total-hours-per-SKU
   and total-hours-per-category figures from the full export.
3. Recomputed equipment cost/price primarily from `products.csv` (current,
   authoritative), backfilled by `quote_lines` history for SKUs missing from
   the product catalogue, and merged with the original Odoo inventory export
   for any SKU present there but never yet quoted in WeQuote (broadest
   coverage, ~5,500 SKUs total).
4. Re-validated the hourly rate card against the full 13,897-line labour
   sample — confirmed 950/950/1250 is still the right current tier (blended
   per-line rates in the data land at intermediate values like 867, 1100, 1150
   purely because most real lines mix more than one phase; the underlying
   three rates haven't moved).

If a future refresh only has the small-sample structure (phase-labelled
"Formula" exports), redo pass 1's extraction. If it's another full database
export, redo pass 2 and reuse the phase ratios already saved in this
methodology rather than re-deriving them, unless you also have fresh
phase-labelled quotes to recompute them from.

## Known limitations

- Phase-hour splits for SKUs/categories with no direct phase history are a
  ratio-based estimate, not observed fact. They're only as good as the
  category match — an item genuinely never quoted before (no category history
  at all) is correctly flagged as "no history", not silently guessed.
- `products.csv` and the Odoo inventory export can disagree on price for the
  same SKU if one is stale; `products.csv` (the live WeQuote catalogue) wins
  whenever both have a value.
- Cost data covers roughly 1,050 of the ~5,500 SKUs in the merged inventory
  (products.csv cost_price plus quote_lines history); everything else falls
  back to the median historical markup in `rate_card.json`.
- This is still a real-world operational dataset, not a lab-clean one — a
  handful of task names, categories, and hour entries in the source data look
  like test/QA entries rather than real jobs. At this scale they wash out in
  the medians, but don't be surprised if you spot one while digging in.
