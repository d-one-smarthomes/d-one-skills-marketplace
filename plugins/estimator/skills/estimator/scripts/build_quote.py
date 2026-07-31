#!/usr/bin/env python3
"""
Estimator - build a detailed D-One quote (equipment + labour) from a list of items.

Usage:
    python build_quote.py items.json output.xlsx

items.json schema:
{
  "project_name": "Smith Residence",
  "quote_ref": "Q-1234",           # optional
  "items": [
    {"query": "IPMX-E20F-IRB2", "qty": 4},
    {"query": "ICREALTIME 2 Megapixel IP Camera", "qty": 2}
  ]
}

"query" can be a SKU (preferred, exact match) or a free-text product name/description
(fuzzy matched against the inventory). Ambiguous or unmatched items are still included
in the output, flagged clearly so a human can price them manually rather than silently
dropped.
"""
import sys, os, csv, json, difflib
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")

# D-One brand palette - matches conduit-schedule / component-schedule skills
NAVY = "1B2A41"
DONE_BLUE = "1379C9"
MID_BLUE = "5FA8D3"
LIGHT_ROW = "EAF3FB"
WHITE = "FFFFFF"
FLAG_AMBER = "FDECC8"
FLAG_RED = "F8D7DA"


def load_reference():
    inventory = {}
    inventory_by_name = []
    with open(os.path.join(ASSETS, "inventory.csv"), newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sku = (row["sku"] or "").strip()
            item = {
                "sku": sku,
                "name": row["name"],
                "category": row["category"] or "Uncategorised",
                "price": float(row["price_zar"] or 0),
                "unit": row["unit"] or "Units",
            }
            if sku:
                inventory[sku.upper()] = item
            inventory_by_name.append(item)

    with open(os.path.join(ASSETS, "equip_cost_by_sku.json")) as f:
        equip_cost = json.load(f)
    with open(os.path.join(ASSETS, "labour_hours_by_sku.json")) as f:
        labour_sku = json.load(f)
    with open(os.path.join(ASSETS, "labour_hours_by_category.json")) as f:
        labour_cat = json.load(f)
    with open(os.path.join(ASSETS, "rate_card.json")) as f:
        rates = json.load(f)

    return inventory, inventory_by_name, equip_cost, labour_sku, labour_cat, rates


def match_item(query, inventory, inventory_by_name):
    """Return (item, match_type) where match_type is 'sku', 'name', or None."""
    q = query.strip()
    if q.upper() in inventory:
        return inventory[q.upper()], "sku"
    # fuzzy match against product names
    names = [i["name"] for i in inventory_by_name]
    best = difflib.get_close_matches(q, names, n=1, cutoff=0.6)
    if best:
        for i in inventory_by_name:
            if i["name"] == best[0]:
                return i, "name"
    return None, None


def get_labour_hours(sku, category, labour_sku, labour_cat):
    if sku and sku.upper() in {k.upper(): k for k in labour_sku}:
        # find actual key (case preserved)
        for k, v in labour_sku.items():
            if k.upper() == sku.upper():
                return v["fix1_hours"], v["fix2_hours"], v["programming_hours"], "history (this exact item)"
    if category in labour_cat:
        v = labour_cat[category]
        return v["fix1_hours"], v["fix2_hours"], v["programming_hours"], f"category average ({category})"
    return 0, 0, 0, "no data - needs manual hours"


def compute_line(query, qty, inventory, inventory_by_name, equip_cost, labour_sku, labour_cat, rates):
    item, match_type = match_item(query, inventory, inventory_by_name)
    if not item:
        return {
            "query": query, "matched_name": None, "sku": None, "category": "UNMATCHED",
            "qty": qty, "unit_price": 0, "unit_cost": 0, "cost_source": None,
            "fix1_h": 0, "fix2_h": 0, "prog_h": 0, "hours_source": None,
            "flag": "NOT FOUND IN INVENTORY - price and hours must be entered manually",
        }

    sku = item["sku"]
    unit_price = item["price"]
    if sku and sku in equip_cost:
        unit_cost = equip_cost[sku]["unit_cost"]
        cost_source = "history"
    elif sku and sku.upper() in {k.upper(): k for k in equip_cost}:
        real_key = next(k for k in equip_cost if k.upper() == sku.upper())
        unit_cost = equip_cost[real_key]["unit_cost"]
        cost_source = "history"
    else:
        unit_cost = round(unit_price / rates["equipment_fallback_markup"], 2) if unit_price else 0
        cost_source = "estimated (no cost history for this SKU)"

    fix1_h, fix2_h, prog_h, hours_source = get_labour_hours(sku, item["category"], labour_sku, labour_cat)

    flag = None
    if match_type == "name":
        flag = f"Matched by name, not SKU — verify this is the right product: \"{item['name']}\""
    if hours_source == "no data - needs manual hours":
        flag = (flag + " | " if flag else "") + "No labour history for this item or category — hours need manual entry"

    return {
        "query": query, "matched_name": item["name"], "sku": sku, "category": item["category"],
        "qty": qty, "unit_price": unit_price, "unit_cost": unit_cost, "cost_source": cost_source,
        "fix1_h": fix1_h, "fix2_h": fix2_h, "prog_h": prog_h, "hours_source": hours_source,
        "flag": flag,
    }


def build_workbook(lines, project_name, quote_ref, rates):
    wb = Workbook()
    ws = wb.active
    ws.title = "Quote"

    r = rates["labour_rates_per_hour"]
    fix1_rate, fix2_rate, prog_rate = r["fix1_cabling"]["sell"], r["fix2_installation"]["sell"], r["programming"]["sell"]

    ncols = 13
    # Title bar
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncols)
    title_cell = ws.cell(row=1, column=1, value=f"D-One Quote — {project_name}" + (f" ({quote_ref})" if quote_ref else ""))
    title_cell.font = Font(color=WHITE, size=14, bold=True)
    title_cell.fill = PatternFill("solid", fgColor=NAVY)
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    headers = ["Category", "Item", "SKU", "Qty", "Unit Price", "Unit Cost", "Equip Total",
               "Equip Cost Total", "1st Fix Hrs", "2nd Fix Hrs", "Prog Hrs", "Labour Total", "Notes"]
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=2, column=c, value=h)
        cell.font = Font(color=WHITE, bold=True)
        cell.fill = PatternFill("solid", fgColor=DONE_BLUE)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    row = 3
    grand_equip_price = grand_equip_cost = grand_labour_price = 0
    by_category_totals = {}

    for line in sorted(lines, key=lambda l: l["category"]):
        equip_total = line["unit_price"] * line["qty"]
        equip_cost_total = line["unit_cost"] * line["qty"]
        labour_total = (line["fix1_h"] * fix1_rate + line["fix2_h"] * fix2_rate + line["prog_h"] * prog_rate) * line["qty"]

        grand_equip_price += equip_total
        grand_equip_cost += equip_cost_total
        grand_labour_price += labour_total
        by_category_totals.setdefault(line["category"], {"equip": 0, "labour": 0})
        by_category_totals[line["category"]]["equip"] += equip_total
        by_category_totals[line["category"]]["labour"] += labour_total

        values = [
            line["category"], line["matched_name"] or line["query"], line["sku"] or "-",
            line["qty"], line["unit_price"], line["unit_cost"], equip_total, equip_cost_total,
            line["fix1_h"], line["fix2_h"], line["prog_h"], round(labour_total, 2), line["flag"] or "",
        ]
        fill = None
        if line["category"] == "UNMATCHED":
            fill = FLAG_RED
        elif line["flag"]:
            fill = FLAG_AMBER
        elif row % 2 == 0:
            fill = LIGHT_ROW

        for c, v in enumerate(values, start=1):
            cell = ws.cell(row=row, column=c, value=v)
            if fill:
                cell.fill = PatternFill("solid", fgColor=fill)
            if c in (5, 6, 7, 8, 12):
                cell.number_format = '#,##0.00'
        row += 1

    # Totals
    row += 1
    ws.cell(row=row, column=1, value="TOTALS").font = Font(bold=True)
    ws.cell(row=row, column=7, value=round(grand_equip_price, 2)).font = Font(bold=True)
    ws.cell(row=row, column=8, value=round(grand_equip_cost, 2)).font = Font(bold=True)
    ws.cell(row=row, column=12, value=round(grand_labour_price, 2)).font = Font(bold=True)
    for c in (7, 8, 12):
        ws.cell(row=row, column=c).number_format = '#,##0.00'
    row += 1
    margin = grand_equip_price - grand_equip_cost
    ws.cell(row=row, column=1, value="Equipment margin (price - cost)")
    ws.cell(row=row, column=7, value=round(margin, 2)).number_format = '#,##0.00'
    row += 1
    ws.cell(row=row, column=1, value="GRAND TOTAL (equip + labour, ex VAT)").font = Font(bold=True, size=12)
    ws.cell(row=row, column=7, value=round(grand_equip_price + grand_labour_price, 2)).font = Font(bold=True, size=12)
    ws.cell(row=row, column=7).number_format = '#,##0.00'

    # Column widths
    widths = [20, 40, 16, 6, 11, 11, 12, 13, 10, 10, 9, 12, 40]
    for c, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(c)].width = w
    ws.freeze_panes = "A3"

    return wb


def main():
    if len(sys.argv) != 3:
        print("Usage: python build_quote.py items.json output.xlsx")
        sys.exit(1)
    items_path, out_path = sys.argv[1], sys.argv[2]
    with open(items_path) as f:
        req = json.load(f)

    inventory, inventory_by_name, equip_cost, labour_sku, labour_cat, rates = load_reference()

    lines = []
    for it in req["items"]:
        lines.append(compute_line(it["query"], it["qty"], inventory, inventory_by_name,
                                   equip_cost, labour_sku, labour_cat, rates))

    wb = build_workbook(lines, req.get("project_name", "Untitled Project"), req.get("quote_ref", ""), rates)
    wb.save(out_path)

    n_unmatched = sum(1 for l in lines if l["category"] == "UNMATCHED")
    n_flagged = sum(1 for l in lines if l["flag"] and l["category"] != "UNMATCHED")
    print(f"Saved {out_path} — {len(lines)} lines, {n_unmatched} unmatched, {n_flagged} flagged for review")


if __name__ == "__main__":
    main()
