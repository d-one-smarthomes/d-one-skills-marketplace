#!/usr/bin/env python3
"""D-One contractor call-out helper for Odoo (JSON-RPC).

Credentials come ONLY from the environment: ODOO_USER and ODOO_API_KEY
(optional ODOO_URL, ODOO_DB). Never put a key in this file.

Commands
  find-client  "<text>"          customers + their projects matching text
  contractors                    helpdesk teams and their members
  create       <plan.json> [--dry-run]
                                 SO (confirmed) -> task -> helpdesk ticket,
                                 guide PDF attached to the ticket
  check        [--days 120 | --since YYYY-MM-DD]
                                 call-outs with something missing (JSON)
"""
import base64, json, os, sys, urllib.request
from pathlib import Path

URL = os.environ.get("ODOO_URL", "https://d-one.odoo.com").rstrip("/")
DB = os.environ.get("ODOO_DB", "d-one")
LOGIN = os.environ.get("ODOO_USER") or os.environ.get("ODOO_LOGIN")
KEY = os.environ.get("ODOO_API_KEY") or os.environ.get("ODOO_KEY")
HERE = Path(__file__).resolve().parent
GUIDE = HERE.parent / "assets" / "contractor-time-logging-guide.pdf"
PL_CODE = "PL"          # [PL] Professional Labour
DASH = "–"         # en dash used in all names
_UID = None


def rpc(service, method, args):
    body = json.dumps({"jsonrpc": "2.0", "method": "call", "id": 1,
                       "params": {"service": service, "method": method, "args": args}}).encode()
    req = urllib.request.Request(URL + "/jsonrpc", body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        out = json.load(r)
    if "error" in out:
        raise RuntimeError(out["error"].get("data", {}).get("message", out["error"]))
    return out["result"]


def uid():
    global _UID
    if _UID is None:
        if not LOGIN or not KEY:
            sys.exit("NO_CREDENTIALS: set ODOO_USER and ODOO_API_KEY.")
        _UID = rpc("common", "authenticate", [DB, LOGIN, KEY, {}])
        if not _UID:
            sys.exit("LOGIN_FAILED: Odoo didn't accept that login or key.")
    return _UID


def ex(model, method, args, kw=None):
    return rpc("object", "execute_kw", [DB, uid(), KEY, model, method, args, kw or {}])


def sr(model, domain, fields, limit=50, order=None):
    kw = {"fields": fields, "limit": limit}
    if order:
        kw["order"] = order
    return ex(model, "search_read", [domain], kw)


def link(model, rid):
    return f"{URL}/web#id={rid}&model={model}&view_type=form"


def out(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


# ---------------------------------------------------------------- lookups
def find_client(text):
    partners = sr("res.partner", ['|', ("name", "ilike", text), ("commercial_company_name", "ilike", text)],
                  ["name", "email", "phone"], 15)
    projects = sr("project.project", ['|', ("name", "ilike", text), ("partner_id.name", "ilike", text)],
                  ["name", "partner_id"], 15)
    out({"customers": partners, "projects": projects})


def contractors():
    teams = sr("helpdesk.team", [], ["name", "member_ids"])
    for t in teams:
        t["members"] = sr("res.users", [("id", "in", t.pop("member_ids"))], ["name", "login"])
    out(teams)


# ---------------------------------------------------------------- create
def create(plan_path, dry):
    p = json.loads(Path(plan_path).read_text())
    need = ["partner_id", "project_id", "problem", "description", "team_id", "contractor_user_id"]
    miss = [k for k in need if not p.get(k)]
    if miss:
        sys.exit(f"MISSING: {', '.join(miss)}")
    hours = float(p.get("hours") or 1)

    project = sr("project.project", [("id", "=", p["project_id"])], ["name"], 1)[0]
    partner = sr("res.partner", [("id", "=", p["partner_id"])], ["name"], 1)[0]
    team = sr("helpdesk.team", [("id", "=", p["team_id"])], ["name"], 1)[0]
    contractor = sr("res.users", [("id", "=", p["contractor_user_id"])], ["name", "partner_id"], 1)[0]
    prod = sr("product.product", [("default_code", "=", PL_CODE)], ["name", "uom_id"], 1)
    if not prod:
        sys.exit("NO_PRODUCT: [PL] Professional Labour not found.")
    prod = prod[0]

    problem = p["problem"].strip()
    ref = f"SERVICE {DASH} CALL OUT {DASH} {project['name']} {DASH} {problem}"
    desc_html = "<p>" + p["description"].strip().replace("\n", "<br/>") + "</p>"

    preview = {
        "sales_order": {"customer": partner["name"], "project": project["name"],
                        "customer_reference": ref, "line": f"[PL] {prod['name']} x {hours:g} hr"},
        "task": {"project": project["name"], "name": f"S#### {DASH} Call out {DASH} {problem}"},
        "ticket": {"team": team["name"], "assigned_to": contractor["name"], "customer": partner["name"],
                   "title": f"S#### {DASH} CALL OUT {DASH} {project['name']} {DASH} {problem}"},
    }
    if dry:
        out({"dry_run": True, **preview})
        return

    # 1. Sales Order, confirmed
    so_id = ex("sale.order", "create", [{
        "partner_id": partner["id"], "project_id": project["id"], "x_studio_project": project["id"],
        "client_order_ref": ref,
        "order_line": [(0, 0, {"product_id": prod["id"], "product_uom_qty": hours})],
    }])
    ex("sale.order", "action_confirm", [[so_id]])
    so = sr("sale.order", [("id", "=", so_id)], ["name", "state", "order_line"], 1)[0]
    so_name, line_id = so["name"], so["order_line"][0]

    # 2. Task in the client's project
    task_id = ex("project.task", "create", [{
        "name": f"{so_name} {DASH} Call out {DASH} {problem}",
        "project_id": project["id"], "description": desc_html,
        "sale_line_id": line_id, "user_ids": [(6, 0, [uid()])],
    }])

    # 3. Helpdesk ticket for the contractor (saving it emails them)
    tvals = {
        "name": f"{so_name} {DASH} CALL OUT {DASH} {project['name']} {DASH} {problem}",
        "team_id": team["id"], "user_id": contractor["id"], "partner_id": partner["id"],
        "project_id": project["id"], "x_studio_project": project["id"],
        "sale_order_id": so_id, "description": desc_html,
    }
    try:
        ticket_id = ex("helpdesk.ticket", "create", [{**tvals, "sale_line_id": line_id}])
    except RuntimeError:
        ticket_id = ex("helpdesk.ticket", "create", [tvals])

    notes = []
    try:
        ex("project.task", "write", [[task_id], {"x_helpdesk_ticket_id": ticket_id}])
    except RuntimeError as e:
        notes.append(f"Task not linked to ticket field: {e}")

    # Guide PDF to the contractor on the ticket
    if GUIDE.exists():
        try:
            att = ex("ir.attachment", "create", [{
                "name": "How to log your time - D-One.pdf", "res_model": "helpdesk.ticket",
                "res_id": ticket_id, "mimetype": "application/pdf",
                "datas": base64.b64encode(GUIDE.read_bytes()).decode()}])
            ex("helpdesk.ticket", "message_post", [[ticket_id]], {
                "body": ("<p>Hi, please see the job above. When you're done, open the "
                         "<b>Timesheets</b> tab, add a line with the date, hours on site and a detailed "
                         "description (arrival/leave time, what was wrong, what you did, how you tested). "
                         "Then set the ticket to <b>Solved</b>. Guide attached.</p>"),
                "message_type": "comment", "subtype_xmlid": "mail.mt_comment",
                "partner_ids": [contractor["partner_id"][0]], "attachment_ids": [att]})
        except RuntimeError as e:
            notes.append(f"Guide not attached: {e}")

    out({"ok": True, "so": so_name, "so_state": so["state"],
         "links": {"sales_order": link("sale.order", so_id), "task": link("project.task", task_id),
                   "ticket": link("helpdesk.ticket", ticket_id)},
         "checklist": {"so_confirmed": so["state"] == "sale",
                       "reference_says_service_call_out": True, "project_set": True,
                       "task_created": True, "ticket_assigned_to_contractor": True,
                       "so_number_on_all_three": True},
         "notes": notes, **preview})


# ---------------------------------------------------------------- check
def check(days, since=None):
    import datetime as dt
    since = since or (dt.date.today() - dt.timedelta(days=days)).isoformat()
    sos = sr("sale.order", [("client_order_ref", "ilike", "call out"), ("state", "=", "sale"),
                            ("date_order", ">=", since)],
             ["name", "client_order_ref", "partner_id", "project_id", "order_line", "invoice_status",
              "user_id", "create_uid"], 500, "date_order desc")
    issues = []
    for so in sos:
        prob = []
        if not so["project_id"]:
            prob.append("No project on the SO")
        tasks = sr("project.task", [("name", "ilike", so["name"])], ["name"], 5)
        if not tasks:
            prob.append("No task with the SO number")
        tickets = sr("helpdesk.ticket", ['|', ("sale_order_id", "=", so["id"]), ("name", "ilike", so["name"])],
                     ["name", "stage_id", "user_id", "timesheet_ids"], 5)
        if not tickets:
            prob.append("No Helpdesk ticket for the contractor")
        logged, solved = 0.0, False
        for t in tickets:
            if not t["user_id"]:
                prob.append(f"Ticket '{t['name']}' not assigned")
            if t["stage_id"] and t["stage_id"][1] == "Solved":
                solved = True
                if not t["timesheet_ids"]:
                    prob.append("Ticket Solved but no time logged")
            if t["timesheet_ids"]:
                logged += sum(l["unit_amount"] for l in
                              sr("account.analytic.line", [("id", "in", t["timesheet_ids"])], ["unit_amount"], 200))
        pl = sr("sale.order.line", [("order_id", "=", so["id"]), ("product_id.default_code", "=", PL_CODE)],
                ["product_uom_qty"], 5)
        pl_qty = sum(l["product_uom_qty"] for l in pl)
        if solved and logged and abs(pl_qty - logged) > 0.01:
            prob.append(f"SO labour is {pl_qty:g} hr but {logged:g} hr logged - update SO")
        if solved and logged:
            pos = sr("purchase.order", [("origin", "ilike", so["name"]), ("state", "!=", "cancel")], ["name"], 5)
            if not pos:
                prob.append("Work done but no contractor PO linked to the SO")
            if so["invoice_status"] == "to invoice":
                prob.append("Work done - client not invoiced yet")
        if prob:
            issues.append({"so": so["name"], "reference": so["client_order_ref"],
                           "customer": so["partner_id"] and so["partner_id"][1],
                           "project": so["project_id"] and so["project_id"][1],
                           "hours_logged": logged, "issues": prob, "link": link("sale.order", so["id"])})
    out({"checked": len(sos), "since": since, "with_issues": len(issues), "items": issues})


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    cmd = a[0]
    if cmd == "find-client":
        find_client(" ".join(a[1:]))
    elif cmd == "contractors":
        contractors()
    elif cmd == "create":
        create(a[1], "--dry-run" in a)
    elif cmd == "check":
        check(int(a[a.index("--days") + 1]) if "--days" in a else 120,
              a[a.index("--since") + 1] if "--since" in a else None)
    else:
        sys.exit(__doc__)
