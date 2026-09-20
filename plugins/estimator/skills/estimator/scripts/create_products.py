#!/usr/bin/env python3
"""
Add new products to D-One's Odoo pricelist database.

Usage:
    python create_products.py new_products.json

This is the ONE write path in the estimator. Run it only when a person has asked to
add items that aren't in Odoo yet (e.g. a bespoke or newly-sourced product on a
quote). It creates each item as a real product.product in Odoo, so it then has a
database id and appears in the pricelist for every future quote — and it upserts the
same item into the local snapshot (inventory.csv + equip_cost_by_sku.json) so
fallback pricing stays in sync.

new_products.json schema:
{
  "products": [
    {
      "name": "Custom Rack Shelf 2U",     # required
      "sku": "D1-RACK-2U",                 # Internal Reference — strongly recommended
      "list_price": 1450.0,                # sell price (ex VAT), required
      "standard_price": 900.0,            # cost (optional)
      "category": "Accessories",           # Odoo product category name (optional)
      "type": "consu"                      # "consu" (goods, default) or "service"
    }
  ]
}

Required Odoo fields are filled sensibly: goods are created storable and taxed at
the 15% sale VAT (matching existing D-One products) so imported quotes compute VAT
correctly. Needs the usual Odoo env vars (ODOO_URL/DB/LOGIN/KEY).
"""
import sys
import os
import csv
import json
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import odoo_client

ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")


def _fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def upsert_snapshot(created):
    """Add/refresh created items in inventory.csv + equip_cost_by_sku.json.
    Best-effort: warns but doesn't fail if the files aren't writable."""
    inv_path = os.path.join(ASSETS, "inventory.csv")
    cost_path = os.path.join(ASSETS, "equip_cost_by_sku.json")
    try:
        rows, fieldnames = [], None
        if os.path.exists(inv_path):
            with open(inv_path, newline="", encoding="utf-8") as f:
                r = csv.DictReader(f)
                fieldnames = r.fieldnames
                rows = list(r)
        if not fieldnames:
            fieldnames = ["sku", "name", "category", "price_zar", "unit", "qty_on_hand", "last_updated"]
        by_sku = {(row.get("sku") or "").strip().upper(): row for row in rows}
        stamp = f"{date.today().isoformat()} (added via estimator)"
        for c in created:
            sku = (c["sku"] or "").strip()
            if not sku:
                continue
            row = by_sku.get(sku.upper())
            if row:
                row["price_zar"] = c["list_price"]
                row["name"] = c["name"]
                if c.get("category"):
                    row["category"] = c["category"]
                row["last_updated"] = stamp
            else:
                rows.append({
                    "sku": sku, "name": c["name"], "category": c.get("category") or "Uncategorised",
                    "price_zar": c["list_price"], "unit": "Units", "qty_on_hand": 0, "last_updated": stamp,
                })
        with open(inv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for row in rows:
                w.writerow({k: row.get(k, "") for k in fieldnames})
    except OSError as e:
        print(f"  (note: couldn't update inventory.csv snapshot: {e})")

    try:
        cost = {}
        if os.path.exists(cost_path):
            with open(cost_path) as f:
                cost = json.load(f)
        stamp = date.today().isoformat()
        for c in created:
            sku = (c["sku"] or "").strip()
            if sku and c.get("standard_price"):
                cost[sku] = {"unit_cost": c["standard_price"], "source": "added_via_estimator", "last_updated": stamp}
        with open(cost_path, "w") as f:
            json.dump(cost, f, indent=2)
    except OSError as e:
        print(f"  (note: couldn't update equip_cost_by_sku.json snapshot: {e})")


def main():
    if len(sys.argv) != 2:
        print("Usage: python create_products.py new_products.json")
        sys.exit(1)
    with open(sys.argv[1]) as f:
        req = json.load(f)
    products = req.get("products", [])
    if not products:
        print("No products in the file — nothing to create.")
        return

    if not odoo_client.available():
        raise SystemExit("ERROR: Odoo not reachable (no ODOO_KEY). Can't create products.")
    od = odoo_client.Odoo()
    tax_id = od.sale_tax_id(15.0)

    created = []
    for p in products:
        name = (p.get("name") or "").strip()
        if not name:
            print(f"  SKIPPED (no name): {p}")
            continue
        sku = (p.get("sku") or "").strip()
        # don't create a duplicate if the SKU already exists in Odoo
        if sku:
            existing = od.search_read("product.product", [["default_code", "=ilike", sku]], ["id"], limit=1)
            if existing:
                print(f"  EXISTS already, skipped create: {sku} (id {existing[0]['id']})")
                created.append({"id": existing[0]["id"], "name": name, "sku": sku,
                                "list_price": _fnum(p.get("list_price")),
                                "standard_price": _fnum(p.get("standard_price")),
                                "category": p.get("category")})
                continue
        ptype = (p.get("type") or "consu").strip()
        vals = {
            "name": name,
            "list_price": _fnum(p.get("list_price")),
            "standard_price": _fnum(p.get("standard_price")),
            "type": ptype,
            "sale_ok": True,
            "purchase_ok": True,
        }
        if sku:
            vals["default_code"] = sku
        if ptype == "consu":
            vals["is_storable"] = True
        cat_id = od.category_id(p.get("category"))
        if cat_id:
            vals["categ_id"] = cat_id
        if tax_id:
            vals["taxes_id"] = [(6, 0, [tax_id])]
        new_id = od.create("product.product", vals)
        print(f"  CREATED id {new_id}: {sku or '(no SKU)'} — {name} @ {vals['list_price']}")
        created.append({"id": new_id, "name": name, "sku": sku,
                        "list_price": vals["list_price"], "standard_price": vals["standard_price"],
                        "category": p.get("category")})

    upsert_snapshot(created)
    print(f"Done — {len(created)} product(s) in Odoo. Re-run refresh_import.py so they "
          f"appear in the import file.")
    # emit a machine-readable result next to the input
    out = os.path.splitext(sys.argv[1])[0] + "_created.json"
    with open(out, "w") as f:
        json.dump({"created": created}, f, indent=2)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
