#!/usr/bin/env python3
"""D-One Area Summary - read-only. Builds a per-area materials summary for one or
more Odoo projects from the Materials lines (model x_project_task_material) on the
project's "Stock Movement" task.

Credentials come from the environment, never from this file:
    ODOO_USER / ODOO_LOGIN      the person's Odoo login
    ODOO_API_KEY / ODOO_KEY     that person's API key
    ODOO_URL  (default https://d-one.odoo.com)   ODOO_DB (default d-one)

Usage:
    area_summary.py projects                       list projects that have Stock Movement materials
    area_summary.py build "Gnodde" [--all-tasks] [--out DIR]
    area_summary.py build --all [--include-done] [--out DIR]

Outputs <out>/area_summary.json and <out>/area_summary.html (self-contained).
Exit code 2 = ambiguous or unknown project name (the message lists candidates).
Nothing is ever written to Odoo by this script.
"""
import argparse
import json
import os
import re
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

URL = os.environ.get("ODOO_URL", "https://d-one.odoo.com")
DB = os.environ.get("ODOO_DB", "d-one")
USER = os.environ.get("ODOO_USER") or os.environ.get("ODOO_LOGIN")
KEY = os.environ.get("ODOO_API_KEY") or os.environ.get("ODOO_KEY")
TZ = ZoneInfo("Africa/Johannesburg")
HERE = Path(__file__).resolve().parent.parent
MAT = "x_project_task_material"
SM_NAME = "Stock Movement"

# Area spellings seen in Odoo that mean the same floor. Raw names are kept on each line.
AREA_ALIASES = {
    "gf": "Ground Floor", "ground": "Ground Floor", "ground floor": "Ground Floor",
    "ff": "First Floor", "first": "First Floor", "first floor": "First Floor",
    "sf": "Second Floor", "second": "Second Floor", "second floor": "Second Floor",
    "third": "Third Floor", "third floor": "Third Floor",
    "peremiter": "Perimeter", "perimeter": "Perimeter",
}
SYSTEM_LABELS = {
    "wifi": "WiFi and Network", "cctv": "CCTV", "av": "Video Distribution",
    "access": "Headend and Rack Cabinets", "intercom": "Intercom and Access Control",
}


# ------------------------------------------------------------------ Odoo plumbing
def rpc(service, method, args):
    body = json.dumps({"jsonrpc": "2.0", "method": "call", "id": 1,
                       "params": {"service": service, "method": method, "args": args}})
    req = urllib.request.Request(f"{URL}/jsonrpc", body.encode(), {"Content-Type": "application/json"})
    data = json.loads(urllib.request.urlopen(req, timeout=120).read())
    if "error" in data:
        msg = data["error"].get("data", {}).get("message") or data["error"].get("message", "unknown")
        raise SystemExit("Odoo error: " + msg.strip().splitlines()[-1])
    return data["result"]


_uid = None


def uid():
    global _uid
    if _uid is None:
        if not USER or not KEY:
            raise SystemExit("Set ODOO_USER and ODOO_API_KEY in the environment. Never write a key into a file.")
        try:
            _uid = rpc("common", "login", [DB, USER, KEY])
        except OSError as e:
            raise SystemExit(f"Cannot reach {URL} ({e}). If the network blocks it, ask an org owner to allow d-one.odoo.com.")
        if not _uid:
            raise SystemExit("Odoo authentication failed - check ODOO_USER / ODOO_API_KEY.")
    return _uid


def call(model, method, args=None, kw=None):
    return rpc("object", "execute_kw", [DB, uid(), KEY, model, method, args or [], kw or {}])


def read(model, ids, fields):
    out = []
    ids = list(ids)
    for i in range(0, len(ids), 500):
        out += call(model, "read", [ids[i:i + 500]], {"fields": fields})
    return out


# ------------------------------------------------------------------ helpers
def norm_area(raw):
    if not raw or not str(raw).strip() or str(raw).strip() == "0":
        return "No area set"
    s = re.sub(r"\s+", " ", str(raw)).strip()
    return AREA_ALIASES.get(s.lower(), s)


def system_label(code):
    if not code:
        return "No system set"
    return SYSTEM_LABELS.get(code, code)


def words(s):
    return [w for w in re.findall(r"[a-z0-9]+", s.lower()) if len(w) > 1 or w.isdigit()]


def resolve_projects(query):
    """Every word of the query must appear in the project name. Ties are reported, never guessed."""
    projs = call("project.project", "search_read", [[]], {"fields": ["id", "name"], "context": {"active_test": False}})
    q = words(query)
    hits = [p for p in projs if all(w in words(p["name"]) for w in q)]
    exact = [p for p in hits if p["name"].strip().lower() == query.strip().lower()]
    return exact or hits


def stock_movement_tasks(project_ids=None, include_done=False):
    dom = [["name", "ilike", SM_NAME], ["parent_id", "=", False]]
    if project_ids:
        dom.append(["project_id", "in", project_ids])
    if not include_done:
        dom.append(["state", "not in", ["1_done", "1_canceled"]])
    return call("project.task", "search_read", [dom], {"fields": ["id", "name", "project_id", "state", "stage_id"]})


# ------------------------------------------------------------------ build
F = ["x_task_id", "x_name", "x_notes", "x_product_id", "x_sale_line_id", "x_studio_sales_order",
     "x_studio_customer_reference", "x_studio_area", "x_studio_room", "x_studio_system",
     "x_qty_quoted", "x_studio_demand", "x_studio_received_qty", "x_studio_delivered_qty",
     "x_studio_installed_qty", "x_studio_outstanding_qty", "x_studio_po", "x_studio_supplier"]


def build_project(project, sm_tasks, all_tasks):
    pid, pname = project["id"], project["name"]
    rows = call(MAT, "search_read", [[["x_task_id.project_id", "=", pid]]], {"fields": F})
    task_names = {t["id"]: t["name"] for t in read("project.task", {r["x_task_id"][0] for r in rows if r["x_task_id"]}, ["name"])}
    sm_ids = {t["id"] for t in sm_tasks}

    prod_ids = {r["x_product_id"][0] for r in rows if r["x_product_id"]}
    ptype = {p["id"]: p["type"] for p in read("product.product", prod_ids, ["type"])}
    po_ids = {r["x_studio_po"][0] for r in rows if r["x_studio_po"]}
    try:
        po_info = {p["id"]: p for p in read("purchase.order", po_ids, ["name", "state", "receipt_status"])}
    except SystemExit as e:  # login without Purchase access: fall back to the PO name on the line
        print(f"Note: cannot read purchase orders with this login ({e}); PO state not checked.", file=sys.stderr)
        po_info = {r["x_studio_po"][0]: {"name": r["x_studio_po"][1], "state": "purchase"}
                   for r in rows if r["x_studio_po"]}

    # Group copies of the same sales-order line (one line is copied onto Stock Movement,
    # the labour tasks and room tasks). Only goods, not services.
    groups = defaultdict(list)
    for r in rows:
        if r["x_product_id"] and ptype.get(r["x_product_id"][0]) == "service":
            continue
        key = ("sol", r["x_sale_line_id"][0]) if r["x_sale_line_id"] else ("row", r["id"])
        groups[key].append(r)

    lines, off_sm = [], []
    for key, copies in groups.items():
        on_sm = [c for c in copies if c["x_task_id"] and c["x_task_id"][0] in sm_ids]
        # The Stock Movement copy is the one procurement updates; else the most-received copy.
        best = on_sm[0] if on_sm else max(copies, key=lambda c: (c["x_studio_received_qty"] or 0, c["id"]))
        tasks = sorted({task_names.get(c["x_task_id"][0], "?") for c in copies if c["x_task_id"]})
        line = shape_line(best, po_info, bool(on_sm), tasks)
        if on_sm:
            lines.append(line)
        else:
            off_sm.append(line)
            if all_tasks:
                lines.append(line)

    return summarise(pid, pname, sm_tasks, lines, off_sm, all_tasks)


def shape_line(r, po_info, on_sm, tasks):
    po = po_info.get(r["x_studio_po"][0]) if r["x_studio_po"] else None
    quoted = r["x_qty_quoted"] or 0
    ordered = r["x_studio_demand"] or 0
    received = r["x_studio_received_qty"] or 0
    po_live = bool(po) and po["state"] not in ("cancel",)
    text = " ".join(filter(None, [r["x_studio_area"] or "", r["x_notes"] or "", r["x_name"] or ""])).lower()
    if "do not order" in text:
        status = "do_not_order"
    elif not po_live or ordered <= 0:
        status = "not_ordered"
    elif received <= 0:
        status = "on_order"
    elif received + 1e-9 < ordered:
        status = "part_received"
    else:
        status = "received"
    flags = []
    if po and po["state"] == "cancel":
        flags.append("PO cancelled")
    if po_live and abs(ordered - quoted) > 1e-9:
        flags.append(f"PO qty {fmt(ordered)} vs quoted {fmt(quoted)}")
    if not r["x_studio_area"]:
        flags.append("No area")
    if not on_sm:
        flags.append("Not on Stock Movement")
    name = (r["x_name"] or (r["x_product_id"][1] if r["x_product_id"] else "")).split("\n")[0]
    m = re.match(r"\[([^\]]+)\]\s*(.*)", name)
    return {
        "id": r["id"], "sku": m.group(1) if m else "", "name": (m.group(2) if m else name).strip(),
        "area_raw": r["x_studio_area"] or "", "area": norm_area(r["x_studio_area"]),
        "room": (r["x_studio_room"] or "").strip() or "No room set",
        "system": system_label(r["x_studio_system"]),
        "quoted": quoted, "ordered": ordered if po_live else 0, "received": received,
        "outstanding": max((ordered if po_live else quoted) - received, 0),
        "po": po["name"] if po else "", "po_state": po["state"] if po else "",
        "supplier": r["x_studio_supplier"][1] if r["x_studio_supplier"] else "",
        "so": r["x_studio_sales_order"][1] if r["x_studio_sales_order"] else "",
        "so_ref": r["x_studio_customer_reference"] or "",
        "status": status, "flags": flags, "tasks": tasks, "on_stock_movement": on_sm,
    }


def fmt(x):
    return str(int(x)) if float(x).is_integer() else f"{x:g}"


def totals(ls):
    t = {"lines": len(ls), "quoted": 0, "ordered": 0, "received": 0, "outstanding": 0,
         "by_status": defaultdict(int)}
    for l in ls:
        for k in ("quoted", "ordered", "received", "outstanding"):
            t[k] += l[k]
        t["by_status"][l["status"]] += 1
    t["by_status"] = dict(t["by_status"])
    return t


def floor_rank(a):
    order = ["basement", "ground", "first", "second", "third", "level", "perimeter"]
    al = a.lower()
    for i, k in enumerate(order):
        if k in al:
            return (i, a)
    return (len(order) + (1 if a == "No area set" else 0), a)


def summarise(pid, pname, sm_tasks, lines, off_sm, all_tasks):
    areas = defaultdict(list)
    for l in lines:
        areas[l["area"]].append(l)
    area_out = []
    for a in sorted(areas, key=floor_rank):
        ls = areas[a]
        rooms = defaultdict(list)
        for l in ls:
            rooms[l["room"]].append(l)
        merged = sorted({l["area_raw"] for l in ls if l["area_raw"] and l["area_raw"] != a})
        area_out.append({
            "area": a, "merged_from": merged, "totals": totals(ls),
            "systems": dict(sorted(((s, sum(1 for l in ls if l["system"] == s)) for s in {l["system"] for l in ls}))),
            "rooms": [{"room": r, "totals": totals(rooms[r]),
                       "lines": sorted(rooms[r], key=lambda l: (l["system"], l["name"]))}
                      for r in sorted(rooms)],
        })
    attention = {
        "not_ordered": [l for l in lines if l["status"] == "not_ordered"],
        "do_not_order": [l for l in lines if l["status"] == "do_not_order"],
        "qty_mismatch": [l for l in lines if any(f.startswith("PO qty") for f in l["flags"])],
        "no_area": [l for l in lines if "No area" in l["flags"]],
    }
    sos = sorted({l["so"] for l in lines if l["so"]})
    return {
        "project_id": pid, "project": pname,
        "stock_movement_tasks": [{"id": t["id"], "state": t["state"],
                                  "stage": t["stage_id"][1] if t["stage_id"] else ""} for t in sm_tasks],
        "scope": "all-tasks" if all_tasks else "stock-movement",
        "sales_orders": sos, "totals": totals(lines), "areas": area_out,
        "attention": {k: [slim(l) for l in v] for k, v in attention.items()},
        "off_stock_movement": {"count": len(off_sm), "lines": [slim(l) for l in off_sm]},
        "delivered_installed_tracked": False,
    }


def slim(l):
    return {k: l[k] for k in ("id", "sku", "name", "area", "room", "system", "quoted", "ordered",
                              "received", "po", "flags", "tasks")}


def render(data, out):
    out.mkdir(parents=True, exist_ok=True)
    (out / "area_summary.json").write_text(json.dumps(data, indent=1, default=str))
    tpl = (HERE / "assets" / "template.html").read_text()
    html = tpl.replace("/*__DATA__*/null", json.dumps(data, default=str).replace("</", "<\\/"))
    (out / "area_summary.html").write_text(html)
    return out / "area_summary.html"


# ------------------------------------------------------------------ CLI
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("projects")
    b = sub.add_parser("build")
    b.add_argument("project", nargs="?")
    b.add_argument("--all", action="store_true", help="every project with an open Stock Movement task")
    b.add_argument("--include-done", action="store_true", help="include projects whose Stock Movement task is done")
    b.add_argument("--all-tasks", action="store_true", help="also include goods lines that sit only on other tasks")
    b.add_argument("--out", default="/mnt/user-data/outputs")
    a = ap.parse_args()

    if a.cmd == "projects":
        sm = stock_movement_tasks(include_done=True)
        counts = defaultdict(int)
        for r in call(MAT, "search_read", [[["x_task_id", "in", [t["id"] for t in sm]]]], {"fields": ["x_task_id"]}):
            counts[r["x_task_id"][0]] += 1
        for t in sorted(sm, key=lambda t: t["project_id"][1]):
            print(f'{t["project_id"][1]:<28} task {t["id"]:<6} {t["state"]:<15} materials {counts[t["id"]]}')
        return

    now = datetime.now(TZ).strftime("%Y-%m-%d %H:%M")
    if a.all:
        sm = stock_movement_tasks(include_done=a.include_done)
        by_p = defaultdict(list)
        for t in sm:
            by_p[(t["project_id"][0], t["project_id"][1])].append(t)
        projects = [build_project({"id": p[0], "name": p[1]}, ts, a.all_tasks) for p, ts in sorted(by_p.items(), key=lambda x: x[0][1])]
        projects = [p for p in projects if p["totals"]["lines"] or p["off_stock_movement"]["count"]]
    else:
        if not a.project:
            raise SystemExit("Give a project name, or --all.")
        hits = resolve_projects(a.project)
        if len(hits) != 1:
            print(("Ambiguous" if hits else "No project matches") + f' "{a.project}". Candidates:', file=sys.stderr)
            for p in hits[:20]:
                print(f'  {p["id"]}  {p["name"]}', file=sys.stderr)
            sys.exit(2)
        p = hits[0]
        sm = stock_movement_tasks([p["id"]], include_done=True)
        if not sm:
            raise SystemExit(f'Project "{p["name"]}" has no Stock Movement task.')
        projects = [build_project(p, sm, a.all_tasks)]

    data = {"generated": now, "generated_by": USER, "projects": projects}
    path = render(data, Path(a.out))
    for p in projects:
        t = p["totals"]
        print(f'{p["project"]}: {t["lines"]} lines in {len(p["areas"])} areas | ' +
              ", ".join(f"{k} {v}" for k, v in sorted(t["by_status"].items())) +
              f' | not on Stock Movement: {p["off_stock_movement"]["count"]}')
    print("HTML:", path)


if __name__ == "__main__":
    main()
