#!/usr/bin/env python3
"""
Import a confirmed quote straight into Odoo as a draft quotation.

Usage:
    python import_to_odoo.py <Quote>_OdooImport.csv

This is optional. The default hand-off is the CSV file, which a person can upload
in Odoo via Sales -> Import records. Run THIS script only when the user has said to
import the quote directly — it writes to Odoo, creating a draft sale.order from the
import CSV using the same load() path Odoo's own importer uses.

It prints the created order's number and a link so the user can open and check it.
It never confirms or sends the order — it stays a draft for a human to review.
Needs the usual Odoo env vars (ODOO_URL/DB/LOGIN/KEY).
"""
import sys
import os
import csv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import odoo_client


def main():
    if len(sys.argv) != 2:
        print("Usage: python import_to_odoo.py <Quote>_OdooImport.csv")
        sys.exit(1)
    csv_path = sys.argv[1]
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    if len(rows) < 2:
        raise SystemExit("ERROR: the import CSV has no line rows.")
    header, data = rows[0], rows[1:]

    # sanity: a partner is needed to create the order
    try:
        partner_col = header.index("partner_id")
        if not (data and data[0][partner_col].strip()):
            print("WARNING: no Customer (partner_id) in the file. Odoo will reject the "
                  "import unless a Customer is set — add it on the Meta tab and refresh, "
                  "or set it in Odoo. Continuing anyway.")
    except ValueError:
        pass

    if not odoo_client.available():
        raise SystemExit("ERROR: Odoo not reachable (no ODOO_KEY). Can't import.")
    od = odoo_client.Odoo()

    res = od.load("sale.order", header, data)
    messages = res.get("messages") or []
    ids = res.get("ids") or []

    if messages:
        print("Odoo reported problems — nothing was reliably imported:")
        for m in messages:
            loc = f" (row {m.get('record')})" if m.get("record") is not None else ""
            print(f"  - {m.get('type','error')}: {m.get('message')}{loc}")
        if not ids:
            sys.exit(2)

    if not ids:
        raise SystemExit("ERROR: Odoo returned no order id and no message — import did not complete.")

    oid = ids[0]
    so = od.search_read("sale.order", [["id", "=", oid]],
                        ["name", "partner_id", "amount_untaxed", "amount_total", "state"], limit=1)
    if so:
        s = so[0]
        print(f"Imported as draft quotation {s['name']} (id {oid})")
        print(f"  Customer: {s['partner_id'][1] if s['partner_id'] else '(none)'} | state: {s['state']}")
        print(f"  Ex-VAT: {s['amount_untaxed']:,.2f} | Total: {s['amount_total']:,.2f}")
    else:
        print(f"Imported order id {oid} (couldn't read it back for a summary).")
    print(f"  Open it: {od.record_url('sale.order', oid)}")
    print("  It's a DRAFT — review it in Odoo before sending/confirming.")


if __name__ == "__main__":
    main()
