name: estimator description: > Build a detailed, itemised D-One quote — equipment plus labour (1st Fix Cabling, 2nd Fix Installation, Programming) — as an Excel spreadsheet, pricing equipment LIVE from Odoo (with a local snapshot fallback) and using D-One's historical install-hour/cost data. Also outputs an Odoo-ready Sales Order import file so a confirmed quote can be pushed straight back into Odoo. Use this skill whenever someone says "price this out", "quote this", "estimate this job", "what would this cost", "build a quote for X items", or gives a list of products/SKUs and quantities and wants a cost breakdown. Also trigger when someone uploads a BOM, takeoff spreadsheet, or floorplan-takeoff/lighting-takeoff output and asks for pricing — even if they don't say the word "estimate". This is the skill for turning a list of hardware into a real, detailed D-One quote with services included — not just a rough Entry/Mid/Premium budget (that's wequote-budget's job).
Estimator

Estimator turns a list of products (typed in chat or from an uploaded file) into a detailed, line-by-line D-One quote: equipment price and cost, plus labour hours and price for 1st Fix Cabling, 2nd Fix Installation, and Programming — the same structure D-One's own WeQuote exports use. It produces two files:

<Project>_Estimate.xlsx — the human-facing quote the team can hand to a client or use internally to sanity-check a job's cost. This is the editable source of truth — the team edits quantities, prices, labour hours, and adds or removes lines here (see "Editing a quote and refreshing the import" below).
<Project>_Estimate_OdooImport.csv — the same quote in Odoo's Sales Order import format, so once the quote is confirmed it can be imported straight into Odoo as a quotation without re-keying anything. If the Excel was edited after generation, regenerate this file from the edited Excel before uploading — don't upload the originally generated CSV, or the import won't reflect the edits.

Equipment sell prices are pulled LIVE from Odoo (product.product → list_price) so a quote always reflects the current price in D-One's business system. If Odoo can't be reached, Estimator falls back to a local price snapshot and flags every line that used it.

Scope: what this skill does (and what comes before it)

This skill is the pricing and quote-build layer, plus the Odoo hand-off. It takes a list of products and quantities and turns it into a costed, itemised quote and the matching Odoo records. Designing the system — understanding the site, choosing which products and systems the job needs, applying D-One's product and system knowledge — happens upstream, in the conversation and in D-One's design skills (floorplan-icons, floorplan-takeoff, lighting-takeoff, wequote-budget, the proposal and technical-file skills). Do that thinking as normal; this skill prices whatever item list that produces. In other words: design and spec the job as you always would, then Estimator costs it and gets it into Odoo.

Why this exists

D-One prices every job as equipment + labour, where labour is split into three phases billed at different hourly rates. Getting a fast, accurate estimate normally means someone manually looking up prices and guessing install hours. Estimator instead uses real historical data — D-One's own past quotes — so the hours and costs it suggests reflect how long these exact products actually took to install, not a guess.

Connecting to Odoo (the live price source) — per-user API keys

Estimator prices equipment from live Odoo (https://d-one.odoo.com, database d-one). scripts/build_quote.py reads Odoo read-only through scripts/odoo_client.py, which takes its credentials from four environment variables — never from a file, because this plugin syncs to a shared repo and must contain no secrets:

ODOO_URL    (default https://d-one.odoo.com)
ODOO_DB     (default d-one)
ODOO_LOGIN  (the CURRENT user's Odoo login e-mail — per person)
ODOO_KEY    (the CURRENT user's scoped Odoo API key — per person)

Each D-One team member uses their OWN Odoo login + API key. An Odoo API key is tied to one Odoo user, so authenticating with it logs Estimator in as that person — their permissions apply and Odoo attributes every read to the real user. Never share one key across the team, and never put a key in this repo or any synced file.

Where each person's key lives: their Claude personal settings

Each teammate adds their Odoo login and key to their Claude personal settings as environment variables (the env block in Claude settings), once:

json
"env": {
  "ODOO_LOGIN": "their-name@d-one.co.za",
  "ODOO_KEY": "their-scoped-odoo-api-key"
}

Claude injects these into the session environment when they run the skill, so whoever uses Estimator authenticates as themselves automatically — no key is ever pasted into the chat, stored in memory, or written to a file. ODOO_URL and ODOO_DB default correctly and don't need setting.

At run time
scripts/build_quote.py reads ODOO_LOGIN / ODOO_KEY straight from the environment — if the person has set them in their settings, live pricing just works. Quick check:
bash
   python3 scripts/odoo_client.py     # prints "Connected ... as uid N" on success
If they're not set (or Odoo can't be reached), Estimator falls back to the local inventory.csv snapshot and flags every fallback-priced line. Tell the user, point them to the setup below, and note a snapshot price may be stale.
First-time setup (once per person)
In Odoo (top-right avatar → My Profile → Account Security → Developer API Keys → New API Key), create a scoped key. That same screen is where they revoke it later.
In Claude → Settings, add ODOO_LOGIN (their Odoo login e-mail) and ODOO_KEY (the key) as environment variables, as shown above.
Re-run the skill — pricing is now live.

Keys are per-user, scoped and revocable — if one ever leaks, revoke it in Odoo and replace it in settings.

Before you start: the reference data in assets/

Odoo holds the live sell price; everything else Estimator needs is local:

inventory.csv — a fallback snapshot of D-One's product list (SKU, name, category, price). Used only when Odoo is unreachable, and as the source of each SKU's D-One category (for labour category-averages) and cost lookups.
equip_cost_by_sku.json — historical unit cost per SKU, from past quotes. Odoo gives sell price, not D-One's cost, so cost/margin still come from here.
labour_hours_by_sku.json — historical average install hours per SKU, split into 1st Fix Cabling / 2nd Fix Installation / Programming hours per unit.
labour_hours_by_category.json — the same, averaged per category, used as a fallback when a specific SKU has no quote history yet.
rate_card.json — current hourly labour rates, the fallback equipment markup (only used when a SKU has no cost history), and odoo_labour_products (see below). Read the notes inside this file — rates get revised periodically, so if D-One tells you the rates changed, update this file, don't just remember it.

odoo_labour_products in rate_card.json maps the three labour phases to their Odoo service products (by Internal Reference / default_code, or name). This is what lets labour lines be written into the Odoo import file. It ships blank — set it once, after confirming the real labour product references in Odoo. While it's blank, equipment still imports fine; labour is just left out of the import file and flagged.

You do not need to read these files into context directly — scripts/build_quote.py loads them for you. Just be aware of what they contain so you can explain results and flags sensibly.

Step 1: Work out the item list

Estimator accepts either input style — figure out which one you have:

A. Typed in chat. Someone lists products and quantities directly, e.g. "20x IPMX-E20F-IRB2, 4x subwoofer for the lounge, 2x door station". Each item can be a SKU (best — exact match) or a plain product description (the script fuzzy-matches it against the inventory).

B. Uploaded file. A BOM, takeoff spreadsheet (e.g. from floorplan-takeoff or lighting-takeoff), or any spreadsheet with item names/SKUs and quantities. Read the file, and pull out each row's item identifier and quantity. If a takeoff file gives you icon/category counts rather than specific SKUs (e.g. "4x ceiling speaker" with no model chosen yet), ask the user which specific product to price, or use the most common SKU for that category from the inventory — flag that assumption clearly in the output rather than silently picking one.

Both can be combined in a single request — some items typed, some from a file.

Step 2: Build items.json

Write a JSON file matching this schema:

json
{
  "project_name": "Smith Residence",
  "quote_ref": "Q-1234",
  "customer": "Smith Family Trust",
  "items": [
    {"query": "IPMX-E20F-IRB2", "qty": 4, "room": "Lounge"},
    {"query": "8 zone ceiling speaker", "qty": 8, "room": "Main Bedroom"}
  ]
}

room is optional per item — the area/room the hardware goes in. It shows in the Excel Room / Area column (the quote sorts room-by-room), is editable there, and imports into Odoo's native Room field (x_room) on each order line. Set it from the take-off / design where you can; blank is fine and can be filled in the Excel later. Labour lines are aggregated across the whole quote, so they carry no room.

query is whatever you have — a SKU (best, exact match) or a product description. quote_ref (→ Odoo Order Reference) and customer (→ Odoo Customer/partner) are both optional. If you know the client, set customer — it saves setting it by hand in Odoo. It must match a Customer name that already exists in Odoo, so use the exact name from Odoo if you have it; otherwise leave it out and set the Customer at import time. Use the project name the user gives you, or a sensible default.

Step 3: Run the build script

Make sure ODOO_KEY is exported first (see "Connecting to Odoo" above), then:

bash
python scripts/build_quote.py items.json <ProjectName>_Estimate.xlsx

For each item it looks up the live Odoo sell price (exact SKU / Internal Reference first, then a name search), and only falls back to the inventory.csv snapshot if Odoo is unreachable or the item isn't in Odoo. It pulls historical cost and labour hours from the local data, computes equipment and labour totals at current rates, and writes:

the formatted Excel quote, and
the <ProjectName>_Estimate_OdooImport.csv import file (written next to the xlsx automatically; pass a third argument to choose a different path).

It prints a multi-line summary: how many items were priced live from Odoo, how many were unmatched or flagged, and which lines were left out of the import file and why. Always read this before presenting the files.

Cost visibility is intentional and asymmetric: equipment lines show both price and cost (D-One tracks margin per item). Labour lines show hours, rate, and price only — no cost column. Don't add one; this was a deliberate call, not an oversight.

Step 4: Check flags before presenting

The script highlights rows that need a human look:

Red rows ("UNMATCHED") — the item wasn't found in Odoo or the snapshot at all, even by fuzzy match. Price and hours are zero. Tell the user which items these are so they can supply a SKU or manual price.
Amber rows — matched, but with a caveat: it matched by name rather than exact SKU (worth a sanity check that it's the right product); or the price came from the local snapshot rather than live Odoo (Odoo was unreachable or the item isn't in Odoo — the price may be stale); or there's no labour-hour history for that item or its category (hours default to zero and need manual entry). The Price Source column shows where each line's price came from ("Odoo live (list_price)" vs "inventory.csv snapshot").

Don't silently smooth these over — call them out to the user in your summary, the same way you'd flag a gap to a colleague rather than quietly guessing.

Step 5: Present the result

Save both files and hand them to the user. Briefly note the grand total, and mention anything flagged (unmatched items, name-matched items worth double-checking, snapshot-priced items, zero-hour items, and any lines left out of the import file). Keep this brief — the spreadsheets themselves have the detail.

The Odoo import file — format and how to import

<Project>_Estimate_OdooImport.csv is a Sales Order import file in Odoo's exact one-to-many format. Send the Excel for review; the import CSV is for after the quote is confirmed, to create the quotation in Odoo without re-keying it.

How the file is structured (don't reformat it — Odoo relies on this shape):

Columns: id, name, partner_id, order_line/product_id/.id, order_line/name, order_line/product_uom_qty, order_line/price_unit.
One order, many lines. The order-level fields (id, name = Order Reference, partner_id = Customer) appear only on the first row; every following row leaves them blank so Odoo attaches the line to the same order.
Products are referenced by database id via order_line/product_id/.id — the exact id fetched live from Odoo, so there's no name-matching ambiguity on import.
Labour is aggregated into up to three service lines (1st Fix Cabling, 2nd Fix Installation, Programming): quantity = total hours across the whole quote, unit price = the phase's hourly rate. These only appear if odoo_labour_products is set (see the reference-data section); otherwise they're left out and flagged.
Only lines that resolved to a real Odoo product id are written, so the file imports cleanly. Anything held back (snapshot-priced, unmatched, or labour with no mapped product) is listed in the run summary and stays in the Excel for a human to add manually.

There are two ways to get it into Odoo — the CSV is the default, and Claude can do the import directly when asked:

Hand over the CSV (default). Give the user the CSV; they import it in Odoo via Sales → Orders → Favorites → Import records, uploading the file and confirming the column mapping (the technical headers map automatically). If partner_id was left blank, set the Customer on the import screen or on the draft order.
Claude imports it directly (on request). When the user says to import/push the quote, run:
bash
  python scripts/import_to_odoo.py <Quote>_OdooImport.csv

This creates the quotation in Odoo as a draft (via the same load path the UI uses) and prints the order number and a link to open it. It never confirms or sends the order — it stays a draft for a human to review. Because it writes to Odoo, only do this when the user has asked to import; the default remains handing over the CSV. It needs a Customer on the Meta tab (or the import errors on the missing partner).

Editing a quote and refreshing the import

The Excel is the editable source of truth. The team will change quantities and prices, override a price, add or remove lines, and adjust labour hours directly in the Quote tab. When they do, the originally generated import CSV goes stale — so regenerate it from the edited Excel before uploading, with refresh_import.py:

bash
python scripts/refresh_import.py <EditedQuote>.xlsx

This reads the edited workbook and rebuilds <EditedQuote>_OdooImport.csv to match exactly what's in the Excel right now:

Quantities, prices, labour hours and the Room / Area come straight from the edited cells — a manual price override in the Excel is preserved (the price is NOT re-pulled from Odoo), and an edited room flows to Odoo's Room field. Only the Odoo product id is looked up live (by SKU, then name), so lines still import unambiguously.
Added lines are picked up automatically — put the SKU in the SKU column (best) or a clear product name, and the refresh resolves it to an Odoo product. Removed lines simply don't appear. Labour is re-aggregated from the current hour columns.
Anything that can't be matched to an Odoo product is left out and reported, same as the initial build.

The workbook carries a Meta tab with Project, Quote Ref and Customer — the order-header fields for the import. Edit the Customer there (it must match a Customer that exists in Odoo) so the refreshed import attaches to the right partner. Because refresh_import.py needs live Odoo access for the product ids, make sure ODOO_KEY is set (see "Connecting to Odoo"); if Odoo is unreachable it stops rather than writing an import file that wouldn't load.

Where the files live (keep the round-trip smooth). Save the Excel and its import file into the user's Claude Cowork folder (their synced/connected folder), not just as a chat download. The team then edits the Excel in place there, and the refresh reads the latest version straight from that folder — no re-uploading. When you refresh, read the current file from that folder and write the refreshed import back beside it. (If no folder is connected in a given session, fall back to the chat upload/download round-trip.)

So the end-to-end flow is: build (into the Cowork folder) → the team edits the Excel in place → refresh_import.py → then either hand over the CSV or, on request, import_to_odoo.py to create the draft in Odoo.

Adding items that aren't in Odoo yet

A quote will sometimes include a bespoke or newly-sourced product that isn't in the Odoo pricelist. You can still put it on the quote — add a line in the Quote tab with its Item name, a SKU, Unit Price (and Unit Cost, category, labour hours if you have them). Because it has no Odoo product, it can't be imported until it's created in Odoo. refresh_import.py handles this in the import phase:

On refresh, any line with no Odoo match is left out of the import CSV, reported in the summary, and written to <Quote>_NewProducts.json — seeded with the name, SKU, sell price, cost and category read from the Excel row.
Before creating anything, confirm the required details with the user. Adding a product writes to Odoo, so treat it as a deliberate step the user has asked for — don't create products silently. Ask for and confirm, per new item: name (required), SKU / Internal Reference (strongly recommended so it matches next time), sell price (required), cost, product category, and type (consu goods — the default — or service). The seeded JSON already has whatever was in the Excel; only ask for what's missing or needs confirming, then update the JSON.
Create them in Odoo:
bash
   python scripts/create_products.py <Quote>_NewProducts.json

This creates each item as a real product.product (goods are storable and taxed at the 15% sale VAT to match existing products, category resolved by name), so it now has a database id and appears in the pricelist for every future quote. It also upserts the item into the local snapshot. It won't duplicate a SKU that already exists. This is the only step that writes to Odoo. 4. Re-run refresh_import.py — the new items now resolve to their fresh Odoo ids and are included in the import CSV.

So the flow with new products is: build → edit / add lines → refresh_import.py (flags new items) → confirm details → create_products.py → refresh_import.py again → hand over the CSV or import_to_odoo.py.

A note on accuracy over time

The labour hours and costs here are historical averages, not a fixed spec — a product's real install time varies with site conditions, cable runs, and job complexity. Treat Estimator's output as a strong starting estimate, not a contractually final number. If the reference data in assets/ gets stale (new products with no history, or D-One's rate card changes), the next person extending this skill should refresh it from the latest WeQuote exports rather than patching numbers by hand in this file.

Keeping the price data current (Odoo is live; the snapshot is the fallback)

Live equipment pricing now comes from Odoo, so the day-to-day way to keep quotes accurate is to keep Odoo's product prices current — Estimator reads them automatically. The best long-term fix for a stale or missing price is to correct it in Odoo, not here.

inventory.csv is the offline fallback used only when Odoo is unreachable. Keep it reasonably fresh so fallback quotes aren't wildly off (e.g. refresh it from a recent WeQuote/Odoo export), and follow the supplier-import rules below when merging new supplier price lists into it. equip_cost_by_sku.json (D-One's cost/margin) and the labour data are always local — Odoo holds sell price, not those — so those still live and evolve here.

Supplier price lists that are not yet in the active inventory

references/supplier_price_lists/ holds raw supplier price lists that haven't been merged into assets/inventory.csv yet — currently Polar Bear Design's 2025 SRP list (thermostats/HVAC controls, GBP ex VAT), plus an extracted CSV of its line items. If someone asks to quote a Polar Bear product, it will show up as UNMATCHED against the main inventory — check this folder before telling them it doesn't exist, but don't silently convert GBP to ZAR or invent a markup. Tell the user you found it in the supplier list and ask for the exchange rate and markup before pricing it, then once you have that, add the converted line(s) to assets/inventory.csv so it's priced correctly next time.

Keeping assets/ current: importing a fresh supplier price list

inventory.csv and equip_cost_by_sku.json are meant to behave like one living spreadsheet — a single row per SKU holding the latest known price, not a growing pile of snapshots. When someone hands you a new supplier price list in D-One's own currency (ZAR) — a Scoop export, a Homemation export, a refreshed version of one you've already imported — merge it straight in:

D-One's sell price (price_zar) = the distributor's retail price INCLUDING VAT, used as-is. This is a deliberate house rule, decided 2026-08-05 (Darren + Berna): distributors like Scoop set their own retail markup too thin for D-One's margin needs, so D-One takes the incl-VAT number itself — not divided by 1.15 — as its own (nominally ex-VAT) selling price. This applies uniformly, even where it's lower than whatever price is already on file for that SKU — don't make exceptions for individual items; the rule was chosen and confirmed knowing this. This reverses an earlier version of this file, which said to store the ex-VAT retail figure and treat incl-VAT-as-price as a bug — it isn't a bug, it's the house rule now.
D-One's cost (equip_cost_by_sku.json → unit_cost) = the distributor's dealer/trade price EXCLUDING VAT, used as-is. This part hasn't changed — always ex VAT for cost, always the freshest number from the supplier's own list, overwriting any older historical-average cost. Store {"unit_cost": ..., "source": "<supplier>_pricelist", "last_updated": "<date>"}.
Match by SKU (case-insensitive, trimmed) against inventory.csv. Existing SKU → update price_zar and last_updated in place. New SKU, not in inventory.csv at all → add one new row (category Uncategorised, note source + date in last_updated).
One row per SKU, always. Never append a duplicate row for a SKU that already exists — upsert in place. After any import, check inv['sku'].str.strip().str.upper().duplicated().sum() == 0 before saving.
Keep the original file under references/supplier_price_lists/ for provenance (what was imported, when), same as Polar Bear's.
If a supplier's list only shows one VAT treatment (e.g. only incl-VAT retail, no separate dealer/cost column), don't guess the other number — ask the user, the same way Polar Bear's GBP pricing was held back until the exchange rate and markup were confirmed.
