#!/usr/bin/env python3
"""D-One contractor call-out helper for Odoo (JSON-RPC).

Credentials come ONLY from the environment: ODOO_USER and ODOO_API_KEY
(optional ODOO_URL, ODOO_DB). Never put a key in this file.

Commands
  find-project "<text>"          projects matching text (by project or customer
                                 name), each with its customer - use this first
  find-client  "<text>"          alias of find-project
  contractors                    helpdesk teams and their members
  create       <plan.json> [--dry-run]
                                 SO (confirmed) -> task -> helpdesk ticket ->
                                 Planning shift on the visit date, guide PDF
                                 sent to the contractor on the ticket
  plan         --ticket ID --date YYYY-MM-DD [--time HH:MM] [--hours N]
                                 add a Planning shift to an existing call-out
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
TZ_OFFSET = 2           # Africa/Johannesburg (no DST); Odoo stores UTC
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
def find_project(text):
    projects = sr("project.project", ['|', ("name", "ilike", text), ("partner_id.name", "ilike", text)],
                  ["name", "partner_id"], 20)
    out({"projects": [{"project_id": p["id"], "project": p["name"],
                       "customer_id": p["partner_id"] and p["partner_id"][0],
                       "customer": p["partner_id"] and p["partner_id"][1]} for p in projects],
         "note": "Project is required. Customer comes from the project."})


def contractors():
    teams = sr("helpdesk.team", [], ["name", "member_ids"])
    for t in teams:
        t["members"] = sr("res.users", [("id", "in", t.pop("member_ids"))], ["name", "login"])
    out(teams)


# ---------------------------------------------------------------- planning
def to_utc(date, time):
    import datetime as dt
    local = dt.datetime.strptime(f"{date} {time or '08:00'}", "%Y-%m-%d %H:%M")
    return local - dt.timedelta(hours=TZ_OFFSET)


def make_slot(ticket_id, date, time=None, hours=1.0):
    """Planning shift for the visit, assigned to the contractor's Planning
    resource (found by their Odoo user). Saved as Draft so it can be moved.
    Returns (slot_id, assigned_name_or_None)."""
    import datetime as dt
    t = sr("helpdesk.ticket", [("id", "=", ticket_id)],
           ["name", "partner_id", "user_id", "x_studio_project_1", "sale_line_id"], 1)[0]
    task = sr("project.task", [("x_helpdesk_ticket_id", "=", ticket_id)], ["id"], 1)
    start = to_utc(date, time)
    end = start + dt.timedelta(hours=float(hours or 1))
    vals = {
        "name": f"{t['name']} · Contractor: {t['user_id'][1] if t['user_id'] else '?'} (ticket #{ticket_id})",
        "start_datetime": start.strftime("%Y-%m-%d %H:%M:%S"),
        "end_datetime": end.strftime("%Y-%m-%d %H:%M:%S"),
        "allocated_hours": float(hours or 1), "state": "draft",
        "helpdesk_ticket_id": ticket_id,
    }
    if t["x_studio_project_1"]:
        vals["project_id"] = t["x_studio_project_1"][0]
    if t["partner_id"]:
        vals["partner_id"] = t["partner_id"][0]
    if task:
        vals["task_id"] = task[0]["id"]
    res = []
    if t["user_id"]:
        res = sr("resource.resource", [("user_id", "=", t["user_id"][0])], ["name"], 1)
    slot_id = ex("planning.slot", "create", [vals])
    # Odoo may auto-assign someone (e.g. the task owner): always set it explicitly
    ex("planning.slot", "write", [[slot_id], {"resource_ids": [(6, 0, [res[0]["id"]] if res else [])]}])
    if task:  # task deadline = visit date/time
        ex("project.task", "write", [[task[0]["id"]], {"date_deadline": vals["start_datetime"]}])
    return slot_id, (res[0]["name"] if res else None)


def plan_cmd(a):
    g = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    if not g("--ticket") or not g("--date"):
        sys.exit("Usage: plan --ticket ID --date YYYY-MM-DD [--time HH:MM] [--hours N]")
    sid, who = make_slot(int(g("--ticket")), g("--date"), g("--time"), g("--hours", 1))
    out({"ok": True, "planning_shift": link("planning.slot", sid), "assigned_to": who,
         "notes": [] if who else ["Shift is unassigned: contractors aren't Planning resources. "
                                  "The contractor's name is in the shift title."]})


# ---------------------------------------------------------------- create
def create(plan_path, dry):
    p = json.loads(Path(plan_path).read_text())
    if not p.get("project_id"):
        sys.exit("NO_PROJECT: a call-out must have the client's project. Ask which project.")
    if not p.get("partner_id"):
        pr = sr("project.project", [("id", "=", p["project_id"])], ["partner_id"], 1)
        if pr and pr[0]["partner_id"]:
            p["partner_id"] = pr[0]["partner_id"][0]
        else:
            sys.exit("NO_CUSTOMER: this project has no customer in Odoo. Ask who the customer is "
                     "(never use the person who is logged in).")
    if uid() and sr("res.users", [("id", "=", uid()), ("partner_id", "=", p["partner_id"])], ["id"], 1):
        sys.exit("CUSTOMER_IS_YOU: the customer is the logged-in user. Ask who the real customer is.")
    need = ["project_id", "partner_id", "problem", "description", "team_id", "contractor_user_id"]
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
        "planning": ({"date": p["date"], "time": p.get("time") or "08:00", "hours": hours}
                     if p.get("date") else "NO DATE - ask when the contractor is going"),
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
        # x_studio_project_1 is the visible, required "Project" on the ticket form.
        # Never write project_id here: it is related to team_id.project_id and
        # writing it would change the contractor team's own project.
        "x_studio_project_1": project["id"], "x_studio_project": project["id"],
        "sale_order_id": so_id, "description": desc_html,
    }
    try:
        ticket_id = ex("helpdesk.ticket", "create", [{**tvals, "sale_line_id": line_id}])
    except RuntimeError:
        ticket_id = ex("helpdesk.ticket", "create", [tvals])

    notes = []
    tk = sr("helpdesk.ticket", [("id", "=", ticket_id)], ["x_studio_project_1"], 1)[0]
    if not tk["x_studio_project_1"] or tk["x_studio_project_1"][0] != project["id"]:
        ex("helpdesk.ticket", "write", [[ticket_id], {"x_studio_project_1": project["id"]}])
    # sale_order_id is recomputed by Odoo from sale_line_id; set and verify
    try:
        ex("helpdesk.ticket", "write", [[ticket_id], {"sale_line_id": line_id}])
        ex("helpdesk.ticket", "write", [[ticket_id], {"sale_order_id": so_id}])
    except RuntimeError as e:
        notes.append(f"Ticket SO link: {e}")
    so_on_ticket = sr("helpdesk.ticket", [("id", "=", ticket_id)], ["sale_order_id"], 1)[0]["sale_order_id"]
    if not so_on_ticket:
        notes.append("Ticket is not linked to the SO in Odoo (the SO number is in the ticket title).")
    project_on_ticket = sr("helpdesk.ticket", [("id", "=", ticket_id)], ["x_studio_project_1"], 1)[0]["x_studio_project_1"]
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
            msg_body = ("<p>Hi, please see the job above. When you're done, open the "
                        "<b>Timesheets</b> tab, add a line with the date, hours on site and a detailed "
                        "description (arrival/leave time, what was wrong, what you did, how you tested). "
                        "Then set the ticket to <b>Solved</b>. Guide attached.</p>")
            # message_post over RPC stores the body as plain text, so the HTML tags
            # would show. Post it, then write the real HTML onto the message.
            mid = ex("helpdesk.ticket", "message_post", [[ticket_id]], {
                "body": "How to log your time - guide attached.",
                "message_type": "comment", "subtype_xmlid": "mail.mt_comment",
                "partner_ids": [contractor["partner_id"][0]], "attachment_ids": [att]})
            mid = mid[0] if isinstance(mid, list) else mid
            ex("mail.message", "write", [[mid], {"body": msg_body}])
        except RuntimeError as e:
            notes.append(f"GUIDE NOT SENT to the contractor - tell the person: {e}")
    else:
        notes.append("GUIDE NOT SENT: guide PDF missing from the skill folder.")

    slot_id = None
    if p.get("date") and p.get("planning", True):
        try:
            slot_id, who = make_slot(ticket_id, p["date"], p.get("time"), hours)
            if not who:
                notes.append("Shift is unassigned: contractors aren't Planning resources. "
                             "The contractor's name is in the shift title.")
        except RuntimeError as e:
            notes.append(f"PLANNING NOT CREATED - tell the person: {e}")
    elif p.get("date"):
        notes.append("Not put in Planning (the person said no).")
    else:
        notes.append("No visit date given - nothing put in Planning yet.")

    out({"ok": True, "so": so_name, "so_state": so["state"],
         "links": {"sales_order": link("sale.order", so_id), "task": link("project.task", task_id),
                   "ticket": link("helpdesk.ticket", ticket_id),
                   "planning": slot_id and link("planning.slot", slot_id)},
         "checklist": {"so_confirmed": so["state"] == "sale",
                       "reference_says_service_call_out": True, "project_set": True,
                       "task_created": True, "ticket_assigned_to_contractor": True,
                       "project_on_ticket": bool(project_on_ticket) and project_on_ticket[0] == project["id"],
                       "ticket_linked_to_so": bool(so_on_ticket),
                       "in_planning": bool(slot_id),
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
            prob.append("NO PROJECT on the SO - fix first")
        tasks = sr("project.task", [("name", "ilike", so["name"])], ["name"], 5)
        if not tasks:
            prob.append("No task with the SO number")
        tickets = sr("helpdesk.ticket", ['|', ("sale_order_id", "=", so["id"]), ("name", "ilike", so["name"])],
                     ["name", "stage_id", "user_id", "timesheet_ids", "x_studio_project_1"], 5)
        if not tickets:
            prob.append("No Helpdesk ticket for the contractor")
        logged, solved = 0.0, False
        for t in tickets:
            if not t["user_id"]:
                prob.append(f"Ticket '{t['name']}' not assigned")
            if t["stage_id"] and t["stage_id"][1] not in ("Solved", "Cancelled") and not \
                    ex("planning.slot", "search_count", [[("helpdesk_ticket_id", "=", t["id"])]]):
                prob.append("No visit date in Planning")
            if not t.get("x_studio_project_1"):
                prob.append(f"Ticket '{t['name']}' has no project")
            elif so["project_id"] and t["x_studio_project_1"][0] != so["project_id"][0]:
                prob.append(f"Ticket project ({t['x_studio_project_1'][1]}) differs from SO project")
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
    if cmd in ("find-project", "find-client"):
        find_project(" ".join(a[1:]))
    elif cmd == "contractors":
        contractors()
    elif cmd == "create":
        create(a[1], "--dry-run" in a)
    elif cmd == "plan":
        plan_cmd(a)
    elif cmd == "check":
        check(int(a[a.index("--days") + 1]) if "--days" in a else 120,
              a[a.index("--since") + 1] if "--since" in a else None)
    else:
        sys.exit(__doc__)
