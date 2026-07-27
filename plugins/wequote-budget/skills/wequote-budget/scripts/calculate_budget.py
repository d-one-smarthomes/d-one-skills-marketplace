#!/usr/bin/env python3
"""
D-One Budget Calculator — calibrated against WeQuote REF:0011 (House De Klerk, Hermanus 2026)
Accounts for module-based hardware: Lutron 4-ch dimmer/switch, NVR 15-cam limit, switch port sizing.

Usage:
  python3 calculate_budget.py --spec spec.json --output ./budget-project/ [--verbose]
  python3 calculate_budget.py --icons icons.json --output ./budget-project/ [--verbose]
"""

import math, json, argparse, os, sys
from pathlib import Path

# ─── UNIT PRICES (ex-VAT, ZAR) ────────────────────────────────────────────────
PRICES = {
    # Lutron HomeWorks
    "lutron_4ch_dimmer_module":   24261,   # LQSE-4A5-230-D  (4 channels)
    "lutron_4ch_switch_module":   10000,   # LQSE-4S5-230-D  (4 channels)
    "lutron_2ch_dali_module":     34870,   # LQSE-2DALUNV-D  (2 channels)
    "lutron_keypad":               8087,   # QSE-CI-WCI
    "lutron_processor":           30783,   # HQP7-1
    "lutron_link_ps":              7478,   # QSPS-DH-1-75-H (1 per ~12 modules)
    "lutron_io_module":           10261,   # QSE-IO
    "lutron_dali_terminal_kit":    1478,   # 1 per DALI module
    "lutron_dali_harness":          739,   # 1 per DALI module
    "lutron_wire_per_reel_304m":  10000,   # 304m reel
    "lutron_motion_sensor":        2482,   # M360-W-VOLF
    # CCTV
    "camera_g6_pro_bullet":       13136,   # UVC-G6BPRO-W (Premium)
    "camera_g6_bullet":            5564,   # UVC-G6B (Entry/Mid)
    "camera_enhancer":             5214,   # UACC-Pro-Bullet-Enhancer-W (Mid+Premium)
    "camera_pole":                 2703,   # buried 3.9m pole
    "camera_cabcon":               3200,   # weatherproof connector per pole
    "nvr_unvr_g2":                19897,   # max 15 cameras each
    "nvr_monitor":                 2111,   # 18.5" monitor per NVR
    "hdd_8tb":                     5206,   # 1 per 8 cameras (30-day retention)
    # Network
    "router_udm_max":             15279,   # UDM-MAX
    "modem_5g":                   12499,   # U5G-Max-Outdoor
    "switch_usw_max24":            9822,   # 24-port core switch
    "switch_usw_max48p":          27065,   # 48-port PoE++ switch
    "dac_cable_10gbps":             421,   # per switch interconnect
    "ap_u7_pro_xg":                5050,   # U7-Pro-XG-W indoor (Mid)
    "ap_u7_pro_outdoor":           7851,   # U7-Pro-Outdoor
    "ap_u7_pro_xgs":               6818,   # U7-Pro-XGS indoor (Premium, est.)
    "ap_u7_pro":                   4040,   # U7-Pro indoor (Entry, est.)
    # Access Control
    "intercom_2n_ip_base":        30167,   # 2N IP Base door station (Entry — audio/video, fewer features; ~70% of IP One)
    "intercom_2n_ip_one":         43096,   # 2N IP One door station (Mid)
    "intercom_2n_ip_verso":       68954,   # 2N IP Verso door station (Premium — larger touchscreen, higher-res video; ~1.6x IP One)
    "intercom_surface_mount":      1845,   # surface mount box per station
    "touch_panel_savant_8":       56670,   # Savant Touch 8" (Premium)
    # Audio
    "speaker_sonance_is8_pair":   41974,   # Sonance IS8 stereo pair (Premium)
    "amp_sonos":                  17390,   # Sonos Amp per zone
    "speaker_cable_point":         1200,   # cabling termination per zone
}

# ─── LABOUR RATES (ex-VAT, ZAR) ───────────────────────────────────────────────
LABOUR = {
    # Lighting (per circuit = dim + sw + dali combined)
    "lighting_first_fix_per_circuit":    346,
    "lighting_second_fix_per_circuit":   355,
    "lighting_programming_base":       50000,
    "lighting_programming_per_circuit": 2670,   # (325000-50000)/103 circuits
    # CCTV
    "cctv_first_fix_per_camera":        1425,
    "cctv_second_fix_per_camera":       4869,
    "cctv_programming_base":           20000,
    "cctv_programming_per_camera":      3125,
    # Network
    "network_first_fix_per_ap":           79,
    "network_second_fix_per_ap":         238,
    "network_programming":             17500,
    # Audio
    "audio_first_fix_per_zone":         1900,
    "audio_second_fix_per_zone":        1900,
    "audio_programming_per_zone":       1250,
    # Access Control
    "ac_first_fix":                     1900,
    "ac_second_fix_per_panel":          1900,
    "ac_programming_base":              6250,
    # System Integration (fixed per tier, not per device)
    "si_programming":                  37500,
}

# System Integration — fixed net ex-VAT per tier (from WeQuote REF:0011)
SI_TIERS = {
    "Entry":   80970,
    "Mid":    172970,
    "Premium": 261274,
}

# Home Theatre — fixed net ex-VAT per tier (from WeQuote REF:0011)
HT_TIERS = {
    "Entry":   389217,
    "Mid":     572524,
    "Premium": 822609,
}


def modules_needed(circuits, channels_per_module):
    """Round UP to whole modules — cannot buy half a module."""
    if circuits <= 0:
        return 0
    return math.ceil(circuits / channels_per_module)


def calc_lighting(dimming_circuits, switched_circuits, dali_circuits, keypads, motion_sensors, tier):
    """Lutron HomeWorks — module-aware pricing."""
    # Scale circuits by tier
    scale = {"Entry": 0.50, "Mid": 0.75, "Premium": 1.0}[tier]
    kp_scale = {"Entry": 10/30, "Mid": 20/30, "Premium": 1.0}[tier]

    dim_c  = math.ceil(dimming_circuits  * scale / 4) * 4
    sw_c   = math.ceil(switched_circuits * scale / 4) * 4
    dali_c = max(0, round(dali_circuits  * scale))
    kp     = round(keypads * kp_scale)
    ms     = round(motion_sensors * scale)

    dim_m  = modules_needed(dim_c,  4)
    sw_m   = modules_needed(sw_c,   4)
    dali_m = modules_needed(dali_c, 2)
    total_m = dim_m + sw_m + dali_m

    ps_count = math.ceil(total_m / 12) if total_m > 0 else 1
    io_mod   = 1 if tier in ("Mid", "Premium") else 0

    total_circuits = dim_c + sw_c + dali_c
    wire_m  = total_circuits * 10 + 100
    reels   = math.ceil(wire_m / 304)

    hardware = (
        dim_m  * PRICES["lutron_4ch_dimmer_module"]
        + sw_m  * PRICES["lutron_4ch_switch_module"]
        + dali_m * PRICES["lutron_2ch_dali_module"]
        + dali_m * PRICES["lutron_dali_terminal_kit"]
        + dali_m * PRICES["lutron_dali_harness"]
        + PRICES["lutron_processor"]
        + ps_count * PRICES["lutron_link_ps"]
        + io_mod * PRICES["lutron_io_module"]
        + kp * PRICES["lutron_keypad"]
        + ms * PRICES["lutron_motion_sensor"]
        + reels * PRICES["lutron_wire_per_reel_304m"]
    )

    labour = (
        total_circuits * LABOUR["lighting_first_fix_per_circuit"]
        + total_circuits * LABOUR["lighting_second_fix_per_circuit"]
        + LABOUR["lighting_programming_base"]
        + total_circuits * LABOUR["lighting_programming_per_circuit"]
    )

    detail = {
        "dim_circuits": dim_c, "sw_circuits": sw_c, "dali_circuits": dali_c,
        "dim_modules": dim_m, "sw_modules": sw_m, "dali_modules": dali_m,
        "keypads": kp, "motion_sensors": ms, "reels": reels,
        "hardware": hardware, "labour": labour,
    }
    return hardware + labour, detail


def calc_cctv(cameras, poles, tier):
    """Ubiquiti UniFi Protect — NVR and HDD sizing."""
    nvr_count = math.ceil(cameras / 15) if cameras > 0 else 0
    hdd_count = math.ceil(cameras / 8)  if cameras > 0 else 0

    if tier == "Entry":
        cam_cost = cameras * PRICES["camera_g6_bullet"]
    elif tier == "Mid":
        cam_cost = cameras * (PRICES["camera_g6_bullet"] + PRICES["camera_enhancer"])
    else:  # Premium
        cam_cost = cameras * (PRICES["camera_g6_pro_bullet"] + PRICES["camera_enhancer"])

    hardware = (
        cam_cost
        + poles * (PRICES["camera_pole"] + PRICES["camera_cabcon"])
        + nvr_count * PRICES["nvr_unvr_g2"]
        + nvr_count * PRICES["nvr_monitor"]
        + hdd_count * PRICES["hdd_8tb"]
    )

    labour = (
        cameras * LABOUR["cctv_first_fix_per_camera"]
        + cameras * LABOUR["cctv_second_fix_per_camera"]
        + LABOUR["cctv_programming_base"]
        + cameras * LABOUR["cctv_programming_per_camera"]
    )

    detail = {
        "cameras": cameras, "poles": poles, "nvrs": nvr_count, "hdds": hdd_count,
        "hardware": hardware, "labour": labour,
    }
    return hardware + labour, detail


def calc_network(aps_indoor, aps_outdoor, cameras, tier):
    """Ubiquiti UniFi — switch port and AP tier sizing."""
    total_aps = aps_indoor + aps_outdoor
    poe_devices = total_aps + cameras
    poe_ports   = math.ceil(poe_devices * 1.2)
    poe_switches = math.ceil(poe_ports / 48) if poe_devices > 0 else 1

    ap_price_indoor = {
        "Entry": PRICES["ap_u7_pro"],
        "Mid":   PRICES["ap_u7_pro_xg"],
        "Premium": PRICES["ap_u7_pro_xgs"],
    }[tier]

    hardware = (
        PRICES["router_udm_max"]
        + PRICES["modem_5g"]
        + PRICES["switch_usw_max24"]
        + poe_switches * PRICES["switch_usw_max48p"]
        + (poe_switches) * PRICES["dac_cable_10gbps"]
        + aps_indoor  * ap_price_indoor
        + aps_outdoor * PRICES["ap_u7_pro_outdoor"]
    )

    labour = (
        total_aps * LABOUR["network_first_fix_per_ap"]
        + total_aps * LABOUR["network_second_fix_per_ap"]
        + LABOUR["network_programming"]
    )

    detail = {
        "aps_indoor": aps_indoor, "aps_outdoor": aps_outdoor,
        "poe_switches": poe_switches, "hardware": hardware, "labour": labour,
    }
    return hardware + labour, detail


def calc_audio(zones, tier):
    """Sonance/Sonos — per zone."""
    if zones == 0:
        return 0, {}

    spk_price = {
        "Entry":   round(PRICES["speaker_sonance_is8_pair"] * 0.75),
        "Mid":     round(PRICES["speaker_sonance_is8_pair"] * 0.88),
        "Premium": PRICES["speaker_sonance_is8_pair"],
    }[tier]

    hardware = zones * (spk_price + PRICES["amp_sonos"] + PRICES["speaker_cable_point"])
    labour   = zones * (
        LABOUR["audio_first_fix_per_zone"]
        + LABOUR["audio_second_fix_per_zone"]
        + LABOUR["audio_programming_per_zone"]
    )

    detail = {"zones": zones, "hardware": hardware, "labour": labour}
    return hardware + labour, detail


def calc_access_control(door_stations, tier):
    """2N — door stations only. Touch panels moved to system integration.

    BUGFIX: previously this always priced the door station at the flat
    'intercom_2n_ip_one' rate regardless of tier, so Entry/Mid/Premium came
    out identical. Now each tier uses a distinct 2N model, and Premium adds
    a dedicated Savant touch reader per door (matching the 'Touch Panel —
    Premium only' note in unit_prices.md).
    """
    door_unit_price = {
        "Entry":   PRICES["intercom_2n_ip_base"],
        "Mid":     PRICES["intercom_2n_ip_one"],
        "Premium": PRICES["intercom_2n_ip_verso"] + PRICES["touch_panel_savant_8"],
    }[tier]

    hw_doors = door_stations * (door_unit_price + PRICES["intercom_surface_mount"])
    labour   = (
        LABOUR["ac_first_fix"]
        + door_stations * LABOUR["ac_second_fix_per_panel"]
        + LABOUR["ac_programming_base"]
    )

    detail = {
        "door_stations": door_stations, "tier": tier,
        "unit_price": door_unit_price,
        "hardware": hw_doors, "labour": labour,
    }
    return hw_doors + labour, detail


def calc_system_integration(tier, touch_panels=0):
    """Savant S12 + touch panels — fixed base per tier, panels added on top."""
    base = SI_TIERS[tier]

    # Touch panels are supplied and installed as part of system integration
    hw_panels = touch_panels * PRICES["touch_panel_savant_8"]
    labour_panels = touch_panels * LABOUR["ac_second_fix_per_panel"]

    total = base + hw_panels + labour_panels
    detail = {
        "tier": tier,
        "touch_panels": touch_panels,
        "hw_panels": hw_panels,
        "labour_panels": labour_panels,
    }
    return total, detail


def calc_home_theatre(tier):
    """Dolby Atmos home theatre — fixed per tier."""
    return HT_TIERS[tier], {"tier": tier}


def spec_from_icon_counts(icon_counts):
    """
    Map floorplan icon dict → project spec dict.
    Estimates lighting circuits from keypad count (De Klerk ratio).
    """
    cameras = icon_counts.get("cctv_dome", 0) + icon_counts.get("cctv_bullet", 0)
    poles   = round(icon_counts.get("cctv_bullet", 0) * 0.5)

    total_aps = icon_counts.get("wireless_access_point", 0)
    aps_indoor  = round(total_aps * 0.85)
    aps_outdoor = total_aps - aps_indoor

    keypads = icon_counts.get("light_switch_keypad", 0)
    # De Klerk ratio: 30 keypads → 79 dim (2.63/kp) + 22 sw (0.73/kp)
    # Use ceil-to-module to keep module accuracy
    dim_c  = math.ceil(keypads * 2.5 / 4) * 4
    sw_c   = math.ceil(keypads * 0.7 / 4) * 4
    dali_c = keypads // 10

    ceiling_sp = icon_counts.get("ceiling_speaker", 0)
    wall_sp    = icon_counts.get("wall_speaker", 0)
    audio_zones = math.ceil((ceiling_sp + wall_sp) / 2)

    door_stations = max(
        icon_counts.get("facial_recognition_reader", 0),
        icon_counts.get("intercom_door_station", 0),
    )
    touch_panels  = icon_counts.get("touch_panel", 0)
    motion_sensors = icon_counts.get("motion_sensor", 0)

    spec = {
        "_source":          "icon_counts",
        "cctv_cameras":     cameras,
        "cctv_poles":       poles,
        "aps_indoor":       aps_indoor,
        "aps_outdoor":      aps_outdoor,
        "dimming_circuits": dim_c,
        "switched_circuits":sw_c,
        "dali_circuits":    dali_c,
        "keypads":          keypads,
        "motion_sensors":   motion_sensors,
        "audio_zones":      audio_zones,
        "door_stations":    door_stations,
        "touch_panels":     touch_panels,
    }

    print("  Derived spec from icon counts:")
    for k, v in spec.items():
        if not k.startswith("_"):
            print(f"    {k}: {v}")
    return spec


def calculate_all_systems(spec):
    """
    Run all calculators for Entry/Mid/Premium.
    Returns {tier_budgets, zone_prices, _detail}
    """
    tiers = ["Entry", "Mid", "Premium"]
    tier_budgets = {
        "cctv": {}, "access-control": {}, "network": {},
        "audio": {}, "home-theatre": {}, "lighting": {}, "system-integration": {},
    }
    detail_all = {}

    for tier in tiers:
        t, d = calc_lighting(
            spec.get("dimming_circuits", 0),
            spec.get("switched_circuits", 0),
            spec.get("dali_circuits", 0),
            spec.get("keypads", 0),
            spec.get("motion_sensors", 0),
            tier,
        )
        tier_budgets["lighting"][tier] = round(t)
        detail_all.setdefault("lighting", {})[tier] = d

        t, d = calc_cctv(spec.get("cctv_cameras", 0), spec.get("cctv_poles", 0), tier)
        tier_budgets["cctv"][tier] = round(t)
        detail_all.setdefault("cctv", {})[tier] = d

        t, d = calc_network(
            spec.get("aps_indoor", 0), spec.get("aps_outdoor", 0),
            spec.get("cctv_cameras", 0), tier,
        )
        tier_budgets["network"][tier] = round(t)
        detail_all.setdefault("network", {})[tier] = d

        # BUGFIX: this used to price the card at calc_audio(audio_zones, tier) --
        # i.e. the FULL system cost for every zone found on the drawings baked
        # straight into the option card, shown in full before the client ticks
        # a single room checkbox. The proposal's audio zone panel is meant to be
        # the thing that grows the total as rooms are selected (see zone_prices
        # below) -- the card itself should show a modest "from" price for one
        # zone at this tier's quality level, exactly like the zone panel's own
        # per-zone increment. Full multi-zone total (all rooms selected) is kept
        # in `detail_all` for internal reference only, not shown to the client
        # until they actually select rooms.
        t, d = calc_audio(1, tier)
        tier_budgets["audio"][tier] = round(t)
        full_t, _ = calc_audio(spec.get("audio_zones", 0), tier)
        d["zones_if_all_selected"] = spec.get("audio_zones", 0)
        d["total_if_all_zones_selected"] = round(full_t)
        detail_all.setdefault("audio", {})[tier] = d

        t, d = calc_access_control(spec.get("door_stations", 0), tier)
        tier_budgets["access-control"][tier] = round(t)
        detail_all.setdefault("access-control", {})[tier] = d

        t, d = calc_system_integration(tier, touch_panels=spec.get("touch_panels", 0))
        tier_budgets["system-integration"][tier] = round(t)
        detail_all.setdefault("system-integration", {})[tier] = d

        t, d = calc_home_theatre(tier)
        tier_budgets["home-theatre"][tier] = round(t)
        detail_all.setdefault("home-theatre", {})[tier] = d

    # Zone prices — per-unit cost for additional zones selected in the proposal.
    # Audio is always calculated from 1-zone cost at Entry tier so the Sonos Amp
    # is included regardless of whether the current spec has any audio zones.
    audio_1z, _ = calc_audio(1, "Entry")
    zone_prices = {
        "cctv":               round(tier_budgets["cctv"]["Entry"] / max(spec.get("cctv_cameras", 1), 1)),
        "access-control":     round(tier_budgets["access-control"]["Entry"] / max(spec.get("door_stations", 1) + spec.get("touch_panels", 1), 1)),
        "network":            round(tier_budgets["network"]["Entry"] / max(spec.get("aps_indoor", 0) + spec.get("aps_outdoor", 0), 1)),
        "audio":              round(audio_1z),   # 1 zone = speakers + Sonos Amp + cable + labour
        "lighting":           round(tier_budgets["lighting"]["Entry"] / max(spec.get("keypads", 1), 1)),
        "system-integration": tier_budgets["system-integration"]["Entry"],
    }

    return {"tier_budgets": tier_budgets, "zone_prices": zone_prices, "_detail": detail_all}


def main():
    parser = argparse.ArgumentParser(description="D-One Budget Calculator")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--spec",  help="Path to project spec JSON")
    group.add_argument("--icons", help="Path to floorplan icon counts JSON")
    parser.add_argument("--output", default=".", help="Output directory")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if args.spec:
        with open(args.spec) as f:
            spec = json.load(f)
        print(f"Loaded spec: {args.spec}")
    else:
        with open(args.icons) as f:
            icons = json.load(f)
        print(f"Loaded icon counts: {args.icons}")
        spec = spec_from_icon_counts(icons)

    print("\nCalculating budgets...")
    result = calculate_all_systems(spec)

    Path(args.output).mkdir(parents=True, exist_ok=True)

    # Write proposal_budgets.json
    out = {k: v for k, v in result.items() if not k.startswith("_")}
    budget_path = os.path.join(args.output, "proposal_budgets.json")
    with open(budget_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved: {budget_path}")

    # Print summary
    print("\n─── Budget Summary (net ex-VAT) ─────────────────────────────")
    for system, tiers in result["tier_budgets"].items():
        e, m, p = tiers["Entry"], tiers["Mid"], tiers["Premium"]
        print(f"  {system:<22} Entry R{e:>10,}  Mid R{m:>10,}  Premium R{p:>10,}")

    if args.verbose:
        print("\n─── Detail ──────────────────────────────────────────────────")
        print(json.dumps(result["_detail"], indent=2))

    # Write spec used (for audit)
    spec_path = os.path.join(args.output, "spec_used.json")
    with open(spec_path, "w") as f:
        json.dump(spec, f, indent=2)

    print(f"\nDone. Files saved to {args.output}")


if __name__ == "__main__":
    main()
