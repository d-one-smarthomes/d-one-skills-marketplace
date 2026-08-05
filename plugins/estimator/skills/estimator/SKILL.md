---
name: estimator
description: >
  Build a detailed, itemised D-One quote — equipment plus labour (1st Fix Cabling,
  2nd Fix Installation, Programming) — as an Excel spreadsheet, using D-One's real
  inventory pricing and historical install-hour/cost data. Use this skill whenever
  someone says "price this out", "quote this", "estimate this job", "what would this
  cost", "build a quote for X items", or gives a list of products/SKUs and quantities
  and wants a cost breakdown. Also trigger when someone uploads a BOM, takeoff
  spreadsheet, or floorplan-takeoff/lighting-takeoff output and asks for pricing —
  even if they don't say the word "estimate". This is the skill for turning a list
  of hardware into a real, detailed D-One quote with services included — not just a
  rough Entry/Mid/Premium budget (that's wequote-budget's job).
---

# Estimator

Estimator turns a list of products (typed in chat or from an uploaded file) into a
detailed, line-by-line D-One quote: equipment price and cost, plus labour hours and
price for 1st Fix Cabling, 2nd Fix Installation, and Programming — the same structure
D-One's own WeQuote exports use. The output is an Excel file the team can hand
straight to a client or use internally to sanity-check a job's cost.

## Why this exists

D-One prices every job as **equipment + labour**, where labour is split into three
phases billed at different hourly rates. Getting a fast, accurate estimate normally
means someone manually looking up prices and guessing install hours. Estimator
instead uses real historical data — D-One's own past quotes — so the hours and costs
it suggests reflect how long these exact products actually took to install, not a
guess.

## Before you start: read the reference data

All the pricing and history Estimator needs lives in `assets/`:

- `inventory.csv` — D-One's live product list (SKU, name, category, sales price).
  This is the source of truth for equipment sell price.
- `equip_cost_by_sku.json` — historical unit cost per SKU, derived from past quotes.
  Used so equipment lines can show real cost/margin, not just guessed cost.
- `labour_hours_by_sku.json` — historical average install hours per SKU, broken into
  1st Fix Cabling / 2nd Fix Installation / Programming hours per unit.
- `labour_hours_by_category.json` — the same, averaged per category, used as a
  fallback when a specific SKU has no quote history yet.
- `rate_card.json` — current hourly labour rates and the fallback equipment markup
  (only used when a SKU has no cost history). Read the notes inside this file —
  rates get revised periodically, so if D-One tells you the rates changed, update
  this file, don't just remember it verbally.

You do not need to read these files into context directly — `scripts/build_quote.py`
loads them for you. Just be aware of what they contain so you can explain results
and flags sensibly.

## Step 1: Work out the item list

Estimator accepts either input style — figure out which one you have:

**A. Typed in chat.** Someone lists products and quantities directly, e.g. "20x
IPMX-E20F-IRB2, 4x subwoofer for the lounge, 2x door station". Each item can be a
SKU (best — exact match) or a plain product description (the script fuzzy-matches
it against the inventory).

**B. Uploaded file.** A BOM, takeoff spreadsheet (e.g. from floorplan-takeoff or
lighting-takeoff), or any spreadsheet with item names/SKUs and quantities. Read the
file, and pull out each row's item identifier and quantity. If a takeoff file gives
you icon/category counts rather than specific SKUs (e.g. "4x ceiling speaker" with
no model chosen yet), ask the user which specific product to price, or use the most
common SKU for that category from the inventory — flag that assumption clearly in
the output rather than silently picking one.

Both can be combined in a single request — some items typed, some from a file.

## Step 2: Build items.json

Write a JSON file matching this schema:

```json
{
  "project_name": "Smith Residence",
  "quote_ref": "Q-1234",
  "items": [
    {"query": "IPMX-E20F-IRB2", "qty": 4},
    {"query": "8 zone ceiling speaker", "qty": 8}
  ]
}
```

`query` is whatever you have — a SKU or a product description. `quote_ref` is
optional. Use the project name the user gives you, or a sensible default.

## Step 3: Run the build script

```bash
python scripts/build_quote.py items.json <ProjectName>_Estimate.xlsx
```

This matches every item against the inventory (exact SKU match first, then fuzzy
name match), pulls historical cost and labour hours, computes equipment and labour
totals at current rates, and writes a formatted Excel quote. It prints a one-line
summary telling you how many items were unmatched or flagged for review — always
read this before presenting the file.

**Cost visibility is intentional and asymmetric**: equipment lines show both price
and cost (D-One tracks margin per item). Labour lines show hours, rate, and price
only — no cost column. Don't add one; this was a deliberate call, not an oversight.

## Step 4: Check flags before presenting

The script highlights rows that need a human look:

- **Red rows ("UNMATCHED")** — the item wasn't found in inventory at all, even by
  fuzzy match. Price and hours are zero. Tell the user which items these are so
  they can supply a SKU or manual price.
- **Amber rows** — matched, but with a caveat: either it matched by name rather than
  exact SKU (worth a sanity check that it's the right product), or there's no
  labour-hour history for that item or its category (hours default to zero and need
  manual entry).

Don't silently smooth these over — call them out to the user in your summary, the
same way you'd flag a gap to a colleague rather than quietly guessing.

## Step 5: Present the result

Save the Excel file and hand it to the user. Briefly note the grand total, and
mention anything flagged (unmatched items, name-matched items worth double-checking,
zero-hour items). Keep this brief — the spreadsheet itself has the detail.

## A note on accuracy over time

The labour hours and costs here are historical averages, not a fixed spec — a
product's real install time varies with site conditions, cable runs, and job
complexity. Treat Estimator's output as a strong starting estimate, not a
contractually final number. If the reference data in `assets/` gets stale (new
products with no history, or D-One's rate card changes), the next person extending
this skill should refresh it from the latest WeQuote exports rather than patching
numbers by hand in this file.

## Supplier price lists that are not yet in the active inventory

`references/supplier_price_lists/` holds raw supplier price lists that haven't
been merged into `assets/inventory.csv` yet — currently Polar Bear Design's
2025 SRP list (thermostats/HVAC controls, GBP ex VAT), plus an extracted CSV
of its line items. If someone asks to quote a Polar Bear product, it will show
up as UNMATCHED against the main inventory — check this folder before telling
them it doesn't exist, but don't silently convert GBP to ZAR or invent a
markup. Tell the user you found it in the supplier list and ask for the
exchange rate and markup before pricing it, then once you have that, add the
converted line(s) to `assets/inventory.csv` so it's priced correctly next time.

## Keeping `assets/` current: importing a fresh supplier price list

`inventory.csv` and `equip_cost_by_sku.json` are meant to behave like one
living spreadsheet — a single row per SKU holding the latest known price, not
a growing pile of snapshots. When someone hands you a new supplier price
list in D-One's own currency (ZAR) — a Scoop export, a Homemation export, a
refreshed version of one you've already imported — merge it straight in:

1. **D-One's sell price (`price_zar`) = the distributor's retail price
   INCLUDING VAT, used as-is.** This is a deliberate house rule, decided
   2026-08-05 (Darren + Berna): distributors like Scoop set their own retail
   markup too thin for D-One's margin needs, so D-One takes the incl-VAT
   number itself — not divided by 1.15 — as its own (nominally ex-VAT)
   selling price. This applies uniformly, even where it's lower than
   whatever price is already on file for that SKU — don't make exceptions
   for individual items; the rule was chosen and confirmed knowing this.
   **This reverses an earlier version of this file, which said to store the
   ex-VAT retail figure and treat incl-VAT-as-price as a bug — it isn't a
   bug, it's the house rule now.**
2. **D-One's cost (`equip_cost_by_sku.json` → `unit_cost`) = the
   distributor's dealer/trade price EXCLUDING VAT, used as-is.** This part
   hasn't changed — always ex VAT for cost, always the freshest number from
   the supplier's own list, overwriting any older historical-average cost.
   Store `{"unit_cost": ..., "source": "<supplier>_pricelist", "last_updated": "<date>"}`.
3. **Match by SKU** (case-insensitive, trimmed) against `inventory.csv`.
   Existing SKU → update `price_zar` and `last_updated` in place. New SKU,
   not in `inventory.csv` at all → add one new row (category
   `Uncategorised`, note source + date in `last_updated`).
4. **One row per SKU, always.** Never append a duplicate row for a SKU that
   already exists — upsert in place. After any import, check
   `inv['sku'].str.strip().str.upper().duplicated().sum() == 0` before saving.
5. Keep the original file under `references/supplier_price_lists/` for
   provenance (what was imported, when), same as Polar Bear's.
6. If a supplier's list only shows one VAT treatment (e.g. only incl-VAT
   retail, no separate dealer/cost column), don't guess the other number —
   ask the user, the same way Polar Bear's GBP pricing was held back until
   the exchange rate and markup were confirmed.

This is what makes "ask Estimator for a quote" always reflect the latest
price you've fed it, without the reference data silently drifting out of
sync or accumulating stale duplicate entries.
