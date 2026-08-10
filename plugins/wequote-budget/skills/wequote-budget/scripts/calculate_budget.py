#!/usr/bin/env python3
"""
D-One wequote-budget calculator (v3 — standards-based labour, live-priced).

Reads data/tier_definitions.json (the BOM per module/tier), resolves live
prices from the estimator inventory (price_resolver), and applies labour from
data/labour_standards.json:
  • Installation + programming = per-component hours by labour category
    (role -> category via role_to_category_rules).
  • Lighting labour is per-circuit (1 circuit = 1 DALI driver / dimmable load).
  • System-integration host programming is a fixed amount per tier.
  • Design = 10% of (non-accessory equipment + install labour).
  • Project management = 12.5% of (install + programming + design).

Outputs proposal_budgets.json (tier totals + client options) and, with
--detail, budget_detail.json (every line + labour, for the quote spreadsheet).

Usage:
  python3 calculate_budget.py --output ./out/ [--spec project.json] [--detail] [--verbose]
"""

import argparse, json, math, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from price_resolver import PriceResolver


def cat_for_role(role, rules):
    r = (role or "").lower()
    for kw, cat in rules:
        if kw in r:
            return cat
    return None


def derive(module_key, q, std):
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
        q["network_components"] = (poe + q.get("non_poe_devices", 0)
                                   + q["core_switches"] + q["poe_switches"] + 1)
    elif module_key == "lighting":
        dpm = std.get("dali_rule", {}).get("drivers_per_module", 128)
        q["dim_modules"] = math.ceil(q.get("dimming_circuits", 0) / 4)
        q["sw_modules"] = math.ceil(q.get("switched_circuits", 0) / 4)
        q["dali_modules"] = math.ceil(q.get("dali_circuits", 0) / dpm) if q.get("dali_circuits", 0) else 0
        total_mod = q["dim_modules"] + q["sw_modules"] + q["dali_modules"]
        total_circ = q.get("dimming_circuits", 0) + q.get("switched_circuits", 0) + q.get("dali_circuits", 0)
        q["link_ps"] = math.ceil(total_mod / 21) if total_mod else 0
        q["wire_reels"] = math.ceil(total_circ * 10 / 304) if total_circ else 0
        if "keypads" in q:
            q["keypad_controllers"] = math.ceil(q["keypads"] / 10) if q["keypads"] else 0
    return q


def hardware(t, q, r, excl, add5g=True):
    hw = 0.0; hw_units = 0; equip_nonacc = 0.0; lines = []
    for c in t["components"]:
        if c["sku"] == "U5G-Max-Outdoor" and not add5g:
            continue
        qty = q.get(c["scale"], 0) * c["qty_each"]
        if not qty or qty <= 0:
            continue
        price = r.price(c["sku"], required=False)
        if price is None:
            raise KeyError(f"price missing for SKU {c['sku']}")
        ext = qty * price
        acc = c["sku"] in excl
        hw += ext
        if not acc:
            hw_units += qty
            equip_nonacc += ext
        # Margin is only shown when BOTH retail and cost come from the pricelist
        # (a matched pair). Mismatched-source items get no margin.
        mcost = r.matched_cost(c["sku"])
        cost = mcost if mcost else r.cost(c["sku"])
        markup = (price / mcost - 1.0) if (mcost and mcost > 0) else None
        lines.append({"role": c["role"], "sku": c["sku"], "qty": qty, "unit": round(price, 2),
                      "ext": round(ext, 2), "accessory": acc,
                      "cost": round(cost, 2) if cost else None,
                      "markup": round(markup, 4) if markup is not None else None,
                      "psource": r.price_source(c["sku"]),
                      "lab_cat": None, "inst_h": 0.0, "prog_h": 0.0, "inst_r": 0.0, "prog_r": 0.0})
    return hw, hw_units, equip_nonacc, lines


def apply_component_labour(lines, std, fix, prog, skip_roles=()):
    rules = std["role_to_category_rules"]; cats = std["category_hours"]
    install = 0.0; programming = 0.0
    for ln in lines:
        if ln["accessory"]:
            continue
        if any(s in ln["role"].lower() for s in skip_roles):
            continue
        cat = cat_for_role(ln["role"], rules)
        if not cat or cat not in cats:
            continue
        ch = cats[cat]
        ln["lab_cat"] = cat
        ln["inst_h"] = round(ln["qty"] * ch["install"], 3)
        ln["prog_h"] = round(ln["qty"] * ch["programming"], 3)
        ln["inst_r"] = round(ln["inst_h"] * fix, 2)
        ln["prog_r"] = round(ln["prog_h"] * prog, 2)
        install += ln["inst_r"]; programming += ln["prog_r"]
    return install, programming


def compute(module_key, module, tier, r, std, excl, spec=None, add5g=True):
    t = module["tiers"][tier]
    q = dict(t.get("quantities", {}))
    if spec:
        q.update(spec)
    q = derive(module_key, q, std)
    hw, hw_units, equip_nonacc, lines = hardware(t, q, r, excl, add5g)
    fix = r.labour_rate("fix2_installation"); prog = r.labour_rate("programming")
    labour_lines = []

    if module_key == "lighting":
        L = std["lighting_labour"]
        circ = q.get("dimming_circuits", 0) + q.get("switched_circuits", 0) + q.get("dali_circuits", 0)
        kp = q.get("keypads", 0)
        si = q.get("switch_interfaces", 0)
        inst_circ = (circ * L["install_hours_per_circuit"]
                     + kp * L["keypad_install_hours"]
                     + si * L["switch_interface_install_hours"]) * fix
        prog_circ = (circ * L["programming_hours_per_circuit"]
                     + kp * L["keypad_programming_hours"]) * prog
        install_dev, prog_dev = apply_component_labour(
            lines, std, fix, prog,
            skip_roles=("module", "processor", "keypad", "switch interface",
                        "power supply", "link", "wire", "dali", "i/o", "interface"))
        install = inst_circ + install_dev
        programming = prog_circ + prog_dev
        labour_lines.append({"desc": f"Lighting install — {circ} circuits @1h + {kp} keypads @1h + {si} interfaces @1h", "cost": round(inst_circ, 2), "kind": "install"})
        labour_lines.append({"desc": f"Lighting programming — {circ} circuits @1h + {kp} keypads @4h", "cost": round(prog_circ, 2), "kind": "programming"})
    elif module_key == "system-integration":
        install, _ = apply_component_labour(lines, std, fix, prog)
        for ln in lines:            # SI programming is the fixed figure, not per-component
            ln["prog_h"] = 0.0; ln["prog_r"] = 0.0
        programming = std["si_host_programming_fixed_zar"][tier]
        labour_lines.append({"desc": f"System programming (fixed, {tier})", "cost": round(programming, 2), "kind": "programming"})
    else:
        install, programming = apply_component_labour(lines, std, fix, prog)

    design = std["design_pct_of_equipment_plus_install"] * (equip_nonacc + install)
    pm = std["project_management_pct_of_total_labour"] * (install + programming + design)
    total = hw + install + programming + design + pm

    # Labour quantities (hours). Per-line install/programming hours, plus the
    # synthetic labour lines (lighting circuits, SI fixed programming) converted
    # back to hours via the rate they were costed at.
    inst_hours = sum(l["inst_h"] for l in lines)
    prog_hours = sum(l["prog_h"] for l in lines)
    for lab in labour_lines:
        if lab["kind"] == "install":
            inst_hours += lab["cost"] / fix if fix else 0
        else:
            prog_hours += lab["cost"] / prog if prog else 0

    # Hardware margin — matched (pricelist) items only.
    matched = [l for l in lines if l.get("markup") is not None and l.get("cost")]
    hw_matched_ext = sum(l["ext"] for l in matched)
    hw_matched_cost = sum(l["qty"] * l["cost"] for l in matched)
    hw_margin_R = hw_matched_ext - hw_matched_cost
    hw_margin_pct = (hw_margin_R / hw_matched_ext) if hw_matched_ext else None

    return {
        "tier": tier, "hardware": round(hw, 2), "install": round(install, 2),
        "programming": round(programming, 2), "design": round(design, 2), "pm": round(pm, 2),
        "equip_nonacc": round(equip_nonacc, 2), "hw_units": hw_units,
        "inst_hours": round(inst_hours, 1), "prog_hours": round(prog_hours, 1),
        "labour_total": round(install + programming + design + pm, 2),
        "hw_matched_ext": round(hw_matched_ext, 2), "hw_margin_R": round(hw_margin_R, 2),
        "hw_margin_pct": round(hw_margin_pct, 4) if hw_margin_pct is not None else None,
        "total": round(total, 2), "lines": lines, "labour_lines": labour_lines,
    }


def zone_option_cost(r, std):
    fix = r.labour_rate("fix2_installation"); prog = r.labour_rate("programming")
    patio = r.price("93429"); amp = r.price("AMPG1EU1BLK"); pt = r.price("SPEAKER_POINT")
    equip = patio + amp
    ch = std["category_hours"]
    inst = (ch["Audio Speakers"]["install"] + ch["Amplifiers & Audio Matrix"]["install"]) * fix
    prg = (ch["Audio Speakers"]["programming"] + ch["Amplifiers & Audio Matrix"]["programming"]) * prog
    design = std["design_pct_of_equipment_plus_install"] * (equip + inst)
    pm = std["project_management_pct_of_total_labour"] * (inst + prg + design)
    return round(equip + pt + inst + prg + design + pm, 2)


def option_prices(defs, r, std):
    opts = {}
    opts["cctv_enhancer_each"] = round(r.price("UACC-Pro-Bullet-Enhancer-W", required=False) or 0, 2)
    opts["network_5g_backup"] = round(r.price("U5G-Max-Outdoor", required=False) or 0, 2)
    opts["audio_outdoor_zone"] = zone_option_cost(r, std)
    for o in defs.get("system-integration", {}).get("client_options", []):
        opts[f"si_{o['id']}"] = round(o["price_net"], 2)
    return opts


def main():
    ap = argparse.ArgumentParser(description="D-One wequote-budget calculator v3")
    ap.add_argument("--spec")
    ap.add_argument("--output", default=".")
    ap.add_argument("--detail", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    skill_dir = Path(__file__).resolve().parent.parent
    defs = json.load(open(skill_dir / "data" / "tier_definitions.json"))
    std = json.load(open(skill_dir / "data" / "labour_standards.json"))
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
            res = compute(m, module, tier, r, std, excl, spec=mspec)
            tier_budgets[m][tier] = res["total"]
            detail[m][tier] = res

    out = {
        "_note": "Net ex-VAT ZAR. Labour from data/labour_standards.json; prices live from estimator inventory.",
        "tier_budgets": tier_budgets,
        "options": option_prices(defs, r, std),
    }
    Path(args.output).mkdir(parents=True, exist_ok=True)
    json.dump(out, open(os.path.join(args.output, "proposal_budgets.json"), "w"), indent=2)
    if args.detail or args.verbose:
        json.dump({"modules": {m: defs[m].get("label", m) for m in modules},
                   "category_group": {m: defs[m].get("category_group", "") for m in modules},
                   "detail": detail},
                  open(os.path.join(args.output, "budget_detail.json"), "w"), indent=2)

    print("\n─── Budget summary (net ex-VAT) ───")
    print(f"{'Module':<20}{'Entry':>13}{'Mid':>13}{'Premium':>13}")
    for m in modules:
        row = tier_budgets[m]
        print(f"{m:<20}{row.get('Entry',0):>13,.0f}{row.get('Mid',0):>13,.0f}{row.get('Premium',0):>13,.0f}")
    if r.missing:
        print("\n⚠ Missing SKUs:", r.missing)
    print(f"\nSaved {args.output}/proposal_budgets.json")


if __name__ == "__main__":
    main()
