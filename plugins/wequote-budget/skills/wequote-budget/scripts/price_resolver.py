#!/usr/bin/env python3
"""
Price resolver for the D-One wequote-budget skill.

Prices resolve LIVE from Odoo first — via the estimator skill's odoo_client,
reading product.product → list_price / standard_price — so a budget always
reflects the current price in D-One's business system. Local snapshots are the
fallback only when Odoo is unreachable or a SKU isn't in Odoo.

Resolution order for a SKU (live Odoo first):
  1. Live Odoo product.product.list_price (via the estimator's odoo_client;
     needs ODOO_LOGIN / ODOO_KEY in the environment — per-user keys)
  2. Local pricelist.csv (Darren's uploaded default pricelist snapshot)
  3. Estimator inventory.csv snapshot (matched case-insensitively on SKU)
  4. Local override in data/price_overrides.json — for allowances not in any list
  5. Raise / return None so the caller can flag a missing SKU loudly

Cost resolves the same way: live Odoo standard_price first, then pricelist Cost,
then equip_cost history. A live Odoo (list_price, standard_price) pair counts as
a genuine matched pair for margin.

Also exposes the estimator rate card (labour R/hr) and per-category labour
hours, so labour can be derived from real historical data.
"""

import csv
import json
import os
from pathlib import Path

# ─── Locate the estimator skill's data at runtime ─────────────────────────────
# Skills get synced to different roots on different machines, so search broadly
# rather than assuming one path.
_SEARCH_ROOTS = [
    Path.home() / ".claude" / "plugins" / "synced",
    Path.home() / ".claude" / "skills",
    Path("/root/.claude/plugins/synced"),
    Path("/root/.claude/skills"),
    Path(__file__).resolve().parent.parent,          # this skill dir
    Path(__file__).resolve().parent.parent / "vendor_estimator_snapshot",
]

_INVENTORY_NAME = "inventory.csv"
_RATE_CARD_NAME = "rate_card.json"
_LABOUR_CAT_NAME = "labour_hours_by_category.json"
_EQUIP_COST_NAME = "equip_cost_by_sku.json"
_ODOO_CLIENT_NAME = "odoo_client.py"


def _find_file(filename, must_contain="estimator"):
    """Find the newest matching file under the search roots.

    must_contain: if set, prefer a path whose parts include this token
    (so we grab the estimator copy, not some unrelated inventory.csv).
    A snapshot bundled inside this skill is an accepted fallback.
    """
    candidates = []
    for root in _SEARCH_ROOTS:
        if not root.exists():
            continue
        for p in root.rglob(filename):
            candidates.append(p)
    if not candidates:
        return None
    # Prefer estimator-owned copies, then bundled snapshot, then anything.
    def rank(p):
        parts = {s.lower() for s in p.parts}
        if must_contain and must_contain in parts:
            return 0
        if "vendor_estimator_snapshot" in parts:
            return 1
        return 2
    candidates.sort(key=lambda p: (rank(p), -p.stat().st_mtime))
    return candidates[0]


def _load_estimator_odoo():
    """Import the estimator skill's odoo_client module at runtime, or None.

    Both skills ship in the same synced plugin bundle, so the client is found
    under the same search roots as the other estimator data files. Kept as a
    soft dependency: if it can't be found or imported, the resolver simply falls
    back to the local snapshots.
    """
    path = _find_file(_ODOO_CLIENT_NAME)
    if not path:
        return None
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("estimator_odoo_client", str(path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


class PriceResolver:
    def __init__(self, skill_dir=None, verbose=False):
        self.verbose = verbose
        self.skill_dir = Path(skill_dir) if skill_dir else Path(__file__).resolve().parent.parent
        self._inventory = {}          # SKU(upper) -> {price, name, category, updated}
        self._overrides = {}          # SKU(upper) -> price
        self._pricelist = {}          # SKU(upper) -> {sales, cost, desc}  (PRIMARY source)
        self._equip_cost = {}         # SKU(upper) -> {unit_cost}
        self._rate_card = {}
        self._labour_cat = {}
        self._missing = set()
        self._inventory_path = None
        self._odoo = {}               # SKU(upper) -> {sales, cost, name}  (LIVE Odoo)
        self._odoo_status = "not attempted"
        self._odoo_count = 0
        self._load()

    # ── loading ──────────────────────────────────────────────────────────────
    def _load(self):
        # overrides (optional, lives in this skill)
        ov = self.skill_dir / "data" / "price_overrides.json"
        if ov.exists():
            with open(ov) as f:
                raw = json.load(f)
            self._overrides = {k.strip().upper(): float(v)
                               for k, v in raw.items() if not k.startswith("_")}

        # Primary local pricelist (Darren's uploaded default pricelist), if present.
        # Carries matched Sales Price (retail) + Cost per SKU, so markups are consistent.
        pl = self.skill_dir / "data" / "pricelist.csv"
        if pl.exists():
            with open(pl, newline="") as f:
                for row in csv.DictReader(f):
                    sku = (row.get("sku") or "").strip()
                    if not sku:
                        continue
                    def _f(x):
                        try:
                            return float(x)
                        except (TypeError, ValueError):
                            return None
                    self._pricelist[sku.upper()] = {"sales": _f(row.get("sales_price")),
                                                    "cost": _f(row.get("cost")),
                                                    "desc": row.get("description", "")}

        ec = _find_file(_EQUIP_COST_NAME)
        if ec:
            with open(ec) as f:
                raw = json.load(f)
            self._equip_cost = {k.upper(): v for k, v in raw.items()}

        inv_path = _find_file(_INVENTORY_NAME)
        self._inventory_path = inv_path
        if inv_path:
            with open(inv_path, newline="") as f:
                for row in csv.DictReader(f):
                    sku = (row.get("sku") or "").strip()
                    if not sku:
                        continue
                    try:
                        price = float(row.get("price_zar") or 0)
                    except ValueError:
                        price = 0.0
                    self._inventory[sku.upper()] = {
                        "price": price,
                        "name": row.get("name", ""),
                        "category": row.get("category", ""),
                        "updated": row.get("last_updated", ""),
                    }
        rc = _find_file(_RATE_CARD_NAME)
        if rc:
            with open(rc) as f:
                self._rate_card = json.load(f)
        lc = _find_file(_LABOUR_CAT_NAME)
        if lc:
            with open(lc) as f:
                self._labour_cat = json.load(f)

        # Live Odoo pricelist (primary). Loaded once so per-SKU lookups are just
        # dict hits. Degrades silently to the snapshots above if Odoo is
        # unreachable or no per-user key is set.
        self._load_odoo()

        if self.verbose:
            print(f"[resolver] odoo: {self._odoo_status}")
            print(f"[resolver] inventory: {inv_path}  ({len(self._inventory)} SKUs)")
            print(f"[resolver] pricelist: {len(self._pricelist)} SKUs")
            print(f"[resolver] overrides: {len(self._overrides)}")
            print(f"[resolver] rate_card: {'ok' if self._rate_card else 'MISSING'}")
            print(f"[resolver] labour_cat: {len(self._labour_cat)} categories")

    def _load_odoo(self):
        """Populate self._odoo with the live product list from Odoo, or leave it
        empty and record why in self._odoo_status."""
        oc = _load_estimator_odoo()
        if oc is None:
            self._odoo_status = "client unavailable"
            return
        if not oc.available():
            self._odoo_status = "no ODOO_KEY in environment"
            return
        try:
            od = oc.Odoo()
            rows = od.search_read(
                "product.product",
                [["default_code", "!=", False]],
                ["default_code", "list_price", "standard_price", "name"],
            )
        except Exception as e:  # OdooError or any transport failure
            self._odoo_status = f"unreachable ({e})"
            return
        for r in rows:
            code = (r.get("default_code") or "").strip().upper()
            if not code:
                continue
            self._odoo[code] = {
                "sales": r.get("list_price"),
                "cost": r.get("standard_price"),
                "name": r.get("name", ""),
            }
        self._odoo_count = len(self._odoo)
        self._odoo_status = f"live ({self._odoo_count} SKUs)"

    # ── public API ───────────────────────────────────────────────────────────
    def price(self, sku, required=True):
        """Return ex-VAT ZAR price for a SKU. None (or raise) if unknown."""
        key = sku.strip().upper()
        # Priority: (1) LIVE Odoo list_price, (2) local pricelist snapshot,
        # (3) estimator inventory snapshot, (4) local override.
        o = self._odoo.get(key)
        if o and o.get("sales") is not None:
            return o["sales"]
        pl = self._pricelist.get(key)
        if pl and pl.get("sales") is not None:
            return pl["sales"]
        rec = self._inventory.get(key)
        if rec:
            return rec["price"]
        if key in self._overrides:
            return self._overrides[key]
        self._missing.add(sku)
        if required:
            raise KeyError(
                f"SKU '{sku}' not found in Odoo, the pricelist, the estimator "
                f"inventory, or overrides. Add it in Odoo, or to "
                f"data/price_overrides.json."
            )
        return None

    def cost(self, sku):
        """Ex-VAT cost for a SKU: live Odoo standard_price first, then pricelist
        Cost, then equip_cost history."""
        key = sku.strip().upper()
        o = self._odoo.get(key)
        if o and o.get("cost"):        # truthy: a real Odoo cost (0/None -> fall through)
            return o["cost"]
        pl = self._pricelist.get(key)
        if pl and pl.get("cost") is not None:
            return pl["cost"]
        ec = self._equip_cost.get(key)
        if ec and ec.get("unit_cost"):
            return ec["unit_cost"]
        return None

    def matched_cost(self, sku):
        """Cost ONLY when the SKU has BOTH a sell price and a cost from the SAME
        source — a genuine matched pair — so a margin is never shown from mismatched
        sources. Live Odoo (list_price + standard_price) is preferred; the uploaded
        pricelist is the fallback."""
        key = sku.strip().upper()
        o = self._odoo.get(key)
        if o and o.get("sales") is not None and o.get("cost"):
            return o["cost"]           # genuine same-record Odoo pair
        pl = self._pricelist.get(key)
        if pl and pl.get("sales") is not None and pl.get("cost") is not None:
            return pl["cost"]
        return None

    def price_source(self, sku):
        key = sku.strip().upper()
        o = self._odoo.get(key)
        if o and o.get("sales") is not None:
            return "odoo_live"
        pl = self._pricelist.get(key)
        if pl and pl.get("sales") is not None:
            return "pricelist"
        if key in self._inventory:
            return "inventory"
        if key in self._overrides:
            return "override"
        return "missing"

    def info(self, sku):
        return self._inventory.get(sku.strip().upper())

    def search(self, text, limit=15):
        """Fuzzy name search — helps find the right SKU when unsure."""
        t = text.lower()
        hits = [
            (k, v["name"], v["price"])
            for k, v in self._inventory.items()
            if t in v["name"].lower() or t in k.lower()
        ]
        return hits[:limit]

    def labour_rate(self, kind):
        """kind in {fix1_cabling, fix2_installation, programming} -> sell R/hr."""
        try:
            return self._rate_card["labour_rates_per_hour"][kind]["sell"]
        except KeyError:
            defaults = {"fix1_cabling": 950, "fix2_installation": 950, "programming": 1250}
            return defaults[kind]

    def labour_hours(self, category):
        """Return {fix1_hours, fix2_hours, programming_hours} for a category."""
        rec = self._labour_cat.get(category)
        if not rec:
            return {"fix1_hours": 0.0, "fix2_hours": 0.0, "programming_hours": 0.0}
        return {
            "fix1_hours": rec.get("fix1_hours", 0.0),
            "fix2_hours": rec.get("fix2_hours", 0.0),
            "programming_hours": rec.get("programming_hours", 0.0),
        }

    def labour_cost(self, category, qty=1):
        """Total labour (sell, ex-VAT) for qty units of a category."""
        h = self.labour_hours(category)
        return qty * (
            h["fix1_hours"] * self.labour_rate("fix1_cabling")
            + h["fix2_hours"] * self.labour_rate("fix2_installation")
            + h["programming_hours"] * self.labour_rate("programming")
        )

    @property
    def missing(self):
        return sorted(self._missing)

    @property
    def inventory_path(self):
        return str(self._inventory_path) if self._inventory_path else None

    @property
    def odoo_status(self):
        """Human-readable state of the live Odoo connection for this run
        (e.g. 'live (5210 SKUs)', 'no ODOO_KEY in environment', 'unreachable (...)')."""
        return self._odoo_status


if __name__ == "__main__":
    # Smoke test
    r = PriceResolver(verbose=True)
    print("\nSample lookups (SKU  price  source):")
    for sku in ["LQSE-4A5-230-D", "U7-PRO", "U7-Pro-Outdoor", "UNVR-G2",
                "USW-MAX48P", "UDM-MAX", "HQP7-1", "M360-W-VOLF"]:
        p = r.price(sku, required=False)
        src = r.price_source(sku)
        c = r.matched_cost(sku)
        cstr = f"cost R{c:,.2f}" if c else "cost —"
        print(f"  {sku:<18} R{p if p else 0:>12,.2f}   [{src}]   {cstr}")
    print("\nLabour rates:", {k: r.labour_rate(k) for k in
          ["fix1_cabling", "fix2_installation", "programming"]})
    print("CCTV Cameras labour hrs:", r.labour_hours("CCTV Cameras"))
    print("Keypads labour cost x30:", round(r.labour_cost("Keypads", 30)))
