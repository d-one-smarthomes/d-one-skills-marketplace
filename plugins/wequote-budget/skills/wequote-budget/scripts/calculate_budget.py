#!/usr/bin/env python3
"""
D-One wequote-budget calculator (v2 — data-driven).

Reads data/tier_definitions.json, resolves live prices from the estimator
inventory (via price_resolver, with data/price_overrides.json pins), applies
each module's labour + global design + PM rules, and writes proposal_budgets.json.

Design & PM are global: 1 hour per HARDWARE unit at R1,250/hr each, excluding the
accessory SKUs listed in _design_pm_accessory_exclusions (cabling points, patch
leads, DAC leads, allowances, engraving, keypad base units, speaker cable).

Usage:
  python3 calculate_budget.py --output ./out/                       # reference quantities
  python3 calculate_budget.py --spec project.json --output ./out/   # project quantities
  python3 calculate_budget.py --output ./out/ --verbose
"""

import argparse, json, math, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from price_resolver import PriceResolver

DESIGN_RATE = 1250          # R/hr, design (programming-grade)
PM_RATE = 1250              # R/hr, project management
VAT = 1.15


# ─── derived quantities per module ────────────────────────────────────────────
def derive(module_key, q, add5g=True):
    """Expand driver quantities into all scale keys a module's components use."""
    q = dict(q)

    if module_key == "cctv":
        q["total_cameras"] = q.get("cctv_building_cameras", 0) + q.get("cctv_perimeter_cameras", 0)
        lim = q.get("nvr_camera_limit_4k", 30)
        q["nvr_count"] = math.ceil(q["total_cameras"] / lim) if q["total_cameras"] else 0

    elif module_key == "network":
        poe = q.get("aps_indoor", 0) + q.get("aps_outdoor", 0) + q.get("poe_devices_other", 0)
        q["poe_switches"] = math.ceil(poe * 1.5 / 48) if poe else 0
        total_dev = poe + q.get("non_poe_devices", 0)
        q["core_switches"] = max(1, math.ceil((total_dev * 1.5 - q["poe_switches"] * 48) / 24)) if total_dev else 1
        q["dac_cables"] = q["core_switches"] + q["poe_switches"]

    elif module_key == "lighting":
        q["dim_modules"] = math.ceil(q.get("dimming_circuits", 0) / 4)
        q["sw_modules"] = math.ceil(q.get("switched_circuits", 0) / 4)
        q["dali_modules"] = math.ceil(q.get("dali_circuits", 0) / 2)
        total_mod = q["dim_modules"] + q["sw_modules"] + q["dali_modules"]
        total_circ = q.get("dimming_circuits", 0) + q.get("switched_circuits", 0) + q.get("dali_circuits", 0)
        q["link_ps"] = math.ceil(total_mod / 21) if total_mod else 0
        q["wire_reels"] = math.ceil(total_circ * 10 / 304) if total_circ else 0
        if "keypads" in q:                       # Mid: Savant keypad controllers
            q["keypad_controllers"] = math.ceil(q["keypads"] / 10) if q["keypads"] else 0

    return q


def network_components_count(t, q, add5g):
    roles = set(t["labour"].get("component_roles", []))
    n = 0
    for c in t["components"]:
        if c["sku"] == "U5G-Max-Outdoor" and not add5g:
            continue
        if c["role"] in roles:
            n += q.get(c["scale"], 0) * c["qty_each"]
    return n


# ─── hardware + unit count ────────────────────────────────────────────────────
def hardware(module_key, t, q, r, excl, add5g=True):
    hw = 0.0
    hw_units = 0
    lines = []
    for c in t["components"]:
        if c["sku"] == "U5G-Max-Outdoor" and not add5g:
            continue
        qty = q.get(c["scale"], 0) * c["qty_each"]
        if qty <= 0:
            continue
        price = r.price(c["sku"], required=False)
        if price is None:
            raise KeyError(f"[{module_key}/{t.get('_tier','?')}] price missing for SKU {c['sku']}")
        ext = qty * price
        hw += ext
        if c["sku"] not in excl:
            hw_units += qty
        lines.append({"role": c["role"], "sku": c["sku"], "qty": qty, "unit": price, "ext": ext})
    return hw, hw_units, lines


# ─── base labour (module-specific) ────────────────────────────────────────────
def base_labour(module_key, t, q, r, add5g=True):
    lb = t.get("labour", {})
    mode = lb.get("mode")
    R1 = r.labour_rate("fix1_cabling")
    R2 = r.labour_rate("fix2_installation")
    RP = r.labour_rate("programming")

    if mode == "total_scaled_by_cameras":
        ref = lb["reference_total_cameras"]
        total = lb["fix1_total"] + lb["fix2_total"] + lb["programming_total"]
        return total * (q["total_cameras"] / ref) if ref else 0.0

    if mode == "per_device_hours":
        h = lb["hours_per_device"]
        per = h["fix1"] * R1 + h["fix2"] * R2 + h["programming"] * RP
        return sum(q.get(d, 0) for d in lb["device_drivers"]) * per

    if mode == "per_component_hours":
        h = lb["hours_per_component"]
        per = h["fix1"] * R1 + h["fix2"] * R2 + h["programming"] * RP
        return network_components_count(t, q, add5g) * per

    if mode == "per_zone":
        per = lb["fix1_per_zone"] + lb["fix2_per_zone"] + lb["programming_per_zone"]
        return per * sum(q.get(z, 0) for z in lb["zone_drivers"])

    if mode == "home_theatre_hours":
        return None  # computed in compute() where hw_units is known

    if mode == "lighting_hours":
        circ = sum(q.get(k, 0) for k in lb["circuit_drivers"])
        kp = q.get(lb["keypad_driver"], 0)
        rate = lb.get("rate", 950)
        return (circ * lb["hours_per_circuit"] + kp * lb["hours_per_keypad"]) * rate

    if mode == "fixed_programming":
        return lb["programming_fixed"]

    if mode == "si_hours":
        rate = lb.get("rate", 950)
        lab = lb.get("programming_fixed", 0)
        lab += q.get("touch_panels", 0) * lb.get("touch_panel_install_hours", 0) * rate
        lab += q.get("smart_controls", 0) * lb.get("smart_control_install_hours", 0) * rate
        return lab

    return 0.0


# ─── full compute for one module/tier ─────────────────────────────────────────
def compute(module_key, module, tier, r, excl, spec=None, add5g=True):
    t = dict(module["tiers"][tier]); t["_tier"] = tier
    q = dict(t.get("quantities", {}))
    if spec:                                   # project quantities override tier defaults
        q.update({k: v for k, v in spec.items()})
    q = derive(module_key, q, add5g)
    if module_key == "network":
        q["network_components"] = network_components_count(t, q, add5g)

    hw, hw_units, lines = hardware(module_key, t, q, r, excl, add5g)

    lb = t.get("labour", {})
    if lb.get("mode") == "home_theatre_hours":
        R1 = r.labour_rate("fix1_cabling"); R2 = r.labour_rate("fix2_installation"); RP = r.labour_rate("programming")
        labour = (lb["fix1_hours_per_component"] * hw_units * R1
                  + lb["fix2_hours_per_component"] * hw_units * R2
                  + lb["programming_fixed_hours"] * RP)
        joinery = lb.get("design_joinery_fixed_hours", 0) * DESIGN_RATE
    else:
        labour = base_labour(module_key, t, q, r, add5g) or 0.0
        joinery = 0.0

    design = hw_units * DESIGN_RATE + joinery
    pm = hw_units * PM_RATE
    total = hw + labour + design + pm
    return {
        "tier": tier, "hardware": round(hw, 2), "labour": round(labour, 2),
        "design": round(design, 2), "pm": round(pm, 2), "hw_units": hw_units,
        "total": round(total, 2), "lines": lines,
    }


# ─── options (client-selectable add-ons, priced per unit) ─────────────────────
def option_prices(defs, r):
    opts = {}
    opts["cctv_enhancer_each"] = round(r.price("UACC-Pro-Bullet-Enhancer-W", required=False) or 0, 2)
    opts["network_5g_backup"] = round(r.price("U5G-Max-Outdoor", required=False) or 0, 2)
    patio = (r.price("93429") + r.price("AMPG1EU1BLK") + r.price("SPEAKER_POINT"))
    patio_lab = 1900 + 4900 + 1250
    patio_dpm = 2 * (DESIGN_RATE + PM_RATE)   # patio + amp = 2 hardware units
    opts["audio_outdoor_zone"] = round(patio + patio_lab + patio_dpm, 2)
    for o in defs.get("system-integration", {}).get("client_options", []):
        opts[f"si_{o['id']}"] = round(o["price_net"], 2)
    return opts


def main():
    ap = argparse.ArgumentParser(description="D-One wequote-budget calculator v2")
    ap.add_argument("--spec", help="project quantities JSON (optional)")
    ap.add_argument("--output", default=".")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    skill_dir = Path(__file__).resolve().parent.parent
    defs = json.load(open(skill_dir / "data" / "tier_definitions.json"))
    excl = set(defs.get("_design_pm_accessory_exclusions", []))
    r = PriceResolver(skill_dir=skill_dir, verbose=args.verbose)

    spec_all = json.load(open(args.spec)) if args.spec else {}

    modules = [k for k in defs if not k.startswith("_")]
    tier_budgets, detail = {}, {}
    for m in modules:
        module = defs[m]
        tier_budgets[m], detail[m] = {}, {}
        mspec = spec_all.get(m) if isinstance(spec_all.get(m), dict) else None
        for tier in module["tiers"]:
            res = compute(m, module, tier, r, excl, spec=mspec)
            tier_budgets[m][tier] = res["total"]
            detail[m][tier] = res

    out = {
        "_note": "Net ex-VAT ZAR. Reference-project quantities unless --spec supplied. Prices resolved live from estimator inventory + overrides.",
        "tier_budgets": tier_budgets,
        "options": option_prices(defs, r),
    }
    Path(args.output).mkdir(parents=True, exist_ok=True)
    json.dump(out, open(os.path.join(args.output, "proposal_budgets.json"), "w"), indent=2)

    print("\n─── Budget summary (net ex-VAT) ───────────────────────────────")
    print(f"{'Module':<20}{'Entry':>13}{'Mid':>13}{'Premium':>13}")
    for m in modules:
        row = tier_budgets[m]
        e = row.get("Entry", 0); mi = row.get("Mid", 0); p = row.get("Premium", 0)
        print(f"{m:<20}{e:>13,.0f}{mi:>13,.0f}{p:>13,.0f}")
    print("\nOptions (net ex-VAT):")
    for k, v in out["options"].items():
        print(f"  {k:<24} R{v:>12,.2f}")
    if r.missing:
        print("\n⚠ Missing SKUs:", r.missing)
    if args.verbose:
        json.dump(detail, open(os.path.join(args.output, "budget_detail.json"), "w"), indent=2)
        print(f"\nDetail written to {args.output}/budget_detail.json")
    print(f"\nSaved {args.output}/proposal_budgets.json")


if __name__ == "__main__":
    main()
