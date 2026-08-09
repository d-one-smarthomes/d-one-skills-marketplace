#!/usr/bin/env python3
"""
Price resolver for the D-One wequote-budget skill.

Single source of truth for component pricing is the ESTIMATOR skill's
inventory.csv (kept current from the supplier price lists in the repo).
This module locates that file at runtime and resolves an ex-VAT ZAR price
for any SKU, so wequote-budget never hardcodes prices again.

Resolution order for a SKU (estimator-first — the live pricelist always wins):
  1. Estimator inventory.csv (matched case-insensitively on the SKU column)
  2. Local override in data/price_overrides.json — fallback ONLY for SKUs not
     yet in the estimator inventory, so a stored pin never shadows a live price
  3. Raise / return None so the caller can flag a missing SKU loudly

Also exposes the estimator rate card (labour R/hr) and per-category labour
hours, so labour can be derived from real historical data rather than
De-Klerk-only per-unit rates.
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


class PriceResolver:
    def __init__(self, skill_dir=None, verbose=False):
        self.verbose = verbose
        self.skill_dir = Path(skill_dir) if skill_dir else Path(__file__).resolve().parent.parent
        self._inventory = {}          # SKU(upper) -> {price, name, category, updated}
        self._overrides = {}          # SKU(upper) -> price
        self._rate_card = {}
        self._labour_cat = {}
        self._missing = set()
        self._inventory_path = None
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

        if self.verbose:
            print(f"[resolver] inventory: {inv_path}  ({len(self._inventory)} SKUs)")
            print(f"[resolver] overrides: {len(self._overrides)}")
            print(f"[resolver] rate_card: {'ok' if self._rate_card else 'MISSING'}")
            print(f"[resolver] labour_cat: {len(self._labour_cat)} categories")

    # ── public API ───────────────────────────────────────────────────────────
    def price(self, sku, required=True):
        """Return ex-VAT ZAR price for a SKU. None (or raise) if unknown."""
        key = sku.strip().upper()
        # Estimator inventory (the current pricelist) ALWAYS wins. Overrides are
        # a fallback only for SKUs not yet in the estimator inventory, so a stored
        # pin can never shadow the live pricelist.
        rec = self._inventory.get(key)
        if rec:
            return rec["price"]
        if key in self._overrides:
            return self._overrides[key]
        self._missing.add(sku)
        if required:
            raise KeyError(
                f"SKU '{sku}' not found in estimator inventory or overrides. "
                f"Add it to the estimator inventory.csv or to data/price_overrides.json."
            )
        return None

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


if __name__ == "__main__":
    # Smoke test
    r = PriceResolver(verbose=True)
    print("\nSample lookups:")
    for sku in ["LQSE-4A5-230-D", "U7-PRO", "U7-Pro-Outdoor", "UNVR-G2",
                "USW-MAX48P", "UDM-MAX", "HQP7-1", "M360-W-VOLF"]:
        p = r.price(sku, required=False)
        info = r.info(sku)
        name = info["name"][:48] if info else "— NOT FOUND —"
        print(f"  {sku:<18} R{p if p else 0:>12,.2f}   {name}")
    print("\nLabour rates:", {k: r.labour_rate(k) for k in
          ["fix1_cabling", "fix2_installation", "programming"]})
    print("CCTV Cameras labour hrs:", r.labour_hours("CCTV Cameras"))
    print("Keypads labour cost x30:", round(r.labour_cost("Keypads", 30)))
