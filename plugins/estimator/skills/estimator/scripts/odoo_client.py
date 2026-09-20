#!/usr/bin/env python3
"""
Minimal, dependency-free Odoo JSON-RPC client for the Estimator skill.

Read-only for pricing: build/refresh only ever call `search_read`. The single
write path is `create()` — used solely by create_products.py to add a new product a
person explicitly asked to add — never triggered by building or refreshing a quote.
Credentials are read from the environment at run time and are NEVER hardcoded or
written to any file (the plugin syncs to a shared repo — keeping secrets out of
it is non-negotiable):

    ODOO_URL    (default https://d-one.odoo.com)
    ODOO_DB     (default d-one)
    ODOO_LOGIN  (default darren@d-one.co.za)
    ODOO_KEY    (required — Darren's scoped Odoo API key; no default)

If ODOO_KEY is not present, `available()` returns False and the Estimator falls
back to the local inventory.csv snapshot. This mirrors the `odoo` skill's
JSON-RPC pattern so behaviour is consistent across the D-One plugins.

Uses only the Python standard library (urllib), so it runs anywhere the rest of
the skill runs — no pip install required.
"""
import os
import json
import urllib.request
import urllib.error


class OdooError(Exception):
    pass


def config():
    """Return (url, db, login, key) from the environment."""
    url = os.environ.get("ODOO_URL", "https://d-one.odoo.com").rstrip("/")
    db = os.environ.get("ODOO_DB", "d-one")
    login = os.environ.get("ODOO_LOGIN", "darren@d-one.co.za")
    key = os.environ.get("ODOO_KEY")
    return url, db, login, key


def available():
    """True only if a key is present — the one thing without a safe default."""
    return bool(os.environ.get("ODOO_KEY"))


def _rpc(url, service, method, args, timeout=30):
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {"service": service, "method": method, "args": args},
        "id": 1,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url + "/jsonrpc", data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            out = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
        raise OdooError(f"could not reach Odoo at {url}: {e}")
    if "error" in out:
        err = out["error"]
        msg = err.get("data", {}).get("message") or err.get("message") or json.dumps(err)
        raise OdooError(msg)
    return out.get("result")


class Odoo:
    """Authenticated, read-only Odoo session."""

    def __init__(self):
        self.url, self.db, self.login, self.key = config()
        if not self.key:
            raise OdooError("ODOO_KEY not set in environment")
        self.uid = _rpc(self.url, "common", "authenticate", [self.db, self.login, self.key, {}])
        if not self.uid:
            raise OdooError("Odoo authentication failed — check ODOO_LOGIN / ODOO_KEY / ODOO_DB")

    # --- WRITE (gated) --------------------------------------------------- #
    # The estimator's build/refresh steps are read-only. The ONLY write path is
    # creating new products (create_products.py), and only when a person has asked
    # to add a not-yet-in-Odoo item. Nothing here writes on its own.
    def create(self, model, vals):
        return _rpc(
            self.url, "object", "execute_kw",
            [self.db, self.uid, self.key, model, "create", [vals]],
        )

    def load(self, model, fields, data):
        """Import rows the same way Odoo's UI CSV import does (base_import).
        Returns {"ids": [...], "messages": [...]}. Used only by import_to_odoo.py
        when a person has asked to push a confirmed quote into Odoo."""
        return _rpc(
            self.url, "object", "execute_kw",
            [self.db, self.uid, self.key, model, "load", [fields, data]],
        )

    def record_url(self, model, rec_id):
        """Web link to a record (the /web# hash form that renders in Odoo 19)."""
        return f"{self.url}/web#id={rec_id}&model={model}&view_type=form"

    def sale_tax_id(self, amount=15.0):
        """Return the id of the plain sale tax at `amount`% (e.g. the '15%' VAT),
        matching how existing D-One products are taxed. None if not found."""
        res = self.search_read(
            "account.tax",
            [["type_tax_use", "=", "sale"], ["amount", "=", amount], ["name", "=", "%g%%" % amount]],
            ["id"], limit=1,
        )
        if res:
            return res[0]["id"]
        res = self.search_read(
            "account.tax", [["type_tax_use", "=", "sale"], ["amount", "=", amount]], ["id"], limit=1
        )
        return res[0]["id"] if res else None

    def category_id(self, name):
        """Resolve a product category by name (case-insensitive). None if blank/not found."""
        n = (name or "").strip()
        if not n:
            return None
        res = self.search_read("product.category", [["name", "=ilike", n]], ["id"], limit=1)
        return res[0]["id"] if res else None

    def search_read(self, model, domain, fields, limit=0):
        # NOTE: this Odoo instance treats an explicit limit=0 as "return 0 rows",
        # not "no limit". So only send limit when it's a positive number; omit it
        # entirely for an unbounded read.
        opts = {"fields": fields}
        if limit and limit > 0:
            opts["limit"] = limit
        return _rpc(
            self.url,
            "object",
            "execute_kw",
            [self.db, self.uid, self.key, model, "search_read", [domain], opts],
        )


PRODUCT_FIELDS = ["id", "default_code", "name", "list_price", "uom_name"]


def lookup_product(od, query):
    """
    Resolve a query (SKU or free-text name) to a single Odoo product.product.

    Returns (product_dict, match_type) where match_type is:
      'sku'  — exact, case-insensitive match on Internal Reference (default_code)
      'name' — first case-insensitive substring match on product name
      None   — not found in Odoo
    """
    q = (query or "").strip()
    if not q:
        return None, None
    # 1) exact SKU match on Internal Reference
    res = od.search_read("product.product", [["default_code", "=ilike", q]], PRODUCT_FIELDS, limit=1)
    if res:
        return res[0], "sku"
    # 2) fall back to a name search. (Don't filter on sale_ok — D-One's catalogue
    #    doesn't set it, so that filter would match nothing. search_read already
    #    excludes archived records by default.)
    res = od.search_read("product.product", [["name", "ilike", q]], PRODUCT_FIELDS, limit=1)
    if res:
        return res[0], "name"
    return None, None


def resolve_service_product(od, ref):
    """
    Resolve a labour service product by its Internal Reference (default_code) or,
    failing that, by name. Returns the product dict or None. Used to map D-One's
    labour phases to real Odoo products so labour lines can be imported.
    """
    r = (ref or "").strip()
    if not r:
        return None
    res = od.search_read("product.product", [["default_code", "=ilike", r]], PRODUCT_FIELDS, limit=1)
    if res:
        return res[0]
    res = od.search_read("product.product", [["name", "ilike", r]], PRODUCT_FIELDS, limit=1)
    if res:
        return res[0]
    return None


if __name__ == "__main__":
    # Quick connectivity check: prints uid on success, like the odoo skill.
    try:
        od = Odoo()
        print(f"Connected to {od.url} (db={od.db}) as uid {od.uid}")
    except OdooError as e:
        print(f"Odoo not available: {e}")
