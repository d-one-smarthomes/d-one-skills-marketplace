#!/usr/bin/env python3
"""
build_proposal_contract.py — turn wequote-budget's budget_detail.json into the
SPLIT proposal contract consumed by the d-one-proposal generator.

Why this exists
---------------
The interactive proposal no longer treats every system as a single flat tier
price. Two systems are baseline + per-unit:

  * AUDIO           — baseline R0; each selected zone adds a TIER-SPECIFIC
                      per-zone price. Sum of all zones == that tier's audio total.
  * ACCESS CONTROL  — baseline covers the minimum (Entry/Mid: 1 reader + 1
                      viewer at the gate; Premium: 1 Savant gate intercom).
                      Additional viewers / readers / intercoms are per-unit,
                      tier-specific, and only move the subtotal (price hidden).

It also derives the NETWORK switch/PoE/LAN sizing with spares so the counts
that get priced are the real, buildable bill (design methodology, not a symbol
tally): total IP devices + ~25% spare ports (rounded to the next 24/48-port
unit), plus one spare LAN drop per TV.

Output: proposal_budgets.json (v2) with tier_budgets, per_unit, takeoff,
network_sizing and options — fed straight to generate.py --budgets-file.

NOTE (flagged for Darren): the current engine prices Access Control on UniFi
hardware. Your model describes a Savant gate intercom baseline for Premium and
an explicit reader/viewer split for Entry/Mid. The per-unit numbers below are
computed all-inclusive from whatever device lines the detail actually contains,
with documented assumptions; confirm the SKU/product model (Savant intercom,
Entry/Mid tag-reader) and the tier_definitions will follow.
"""
import os, sys, json, math, argparse

NETWORK_POINT = 1650  # all-in per network drop, matches price_overrides.json


def overhead_ratio(t):
    base = (t.get('hardware', 0) or 0) + (t.get('install', 0) or 0) + (t.get('programming', 0) or 0)
    return ((t.get('design', 0) or 0) + (t.get('pm', 0) or 0)) / base if base else 0.0


def line_allin(line, ratio, add_network_point=True):
    """All-inclusive cost for ONE unit of a device line:
    equipment + labour, grossed up by that tier's design+PM ratio, + a network point."""
    qty = max(1, int(line.get('qty', 1)))
    per_equip  = float(line.get('unit', 0) or 0)
    per_labour = (float(line.get('inst_r', 0) or 0) + float(line.get('prog_r', 0) or 0)) / qty
    np = NETWORK_POINT if add_network_point else 0
    return round((per_equip + per_labour) * (1 + ratio) + np)


def find_line(tier_detail, needles):
    """First non-accessory line whose role contains any of the needles."""
    for ln in tier_detail.get('lines', []):
        if ln.get('accessory'):
            continue
        role = (ln.get('role') or '').lower()
        if any(n in role for n in needles):
            return ln
    return None


def build_audio(detail, zones):
    """Audio: baseline 0; per-zone price per tier = tier total / zone count."""
    per_zone = {}
    for tier in ('Entry', 'Mid', 'Premium'):
        t = detail['audio'][tier]
        n = max(1, int(zones))
        per_zone[tier] = round(t['total'] / n)
    baseline = {'Entry': 0, 'Mid': 0, 'Premium': 0}
    return baseline, per_zone


def build_access(detail):
    """Access Control: baseline (min config) + per-unit viewer/reader/intercom per tier.
    Derives all-in unit costs from the detail lines that exist in each tier."""
    baseline = {}
    viewer, reader, intercom = {}, {}, {}
    for tier in ('Entry', 'Mid', 'Premium'):
        t = detail['access-control'][tier]
        r = overhead_ratio(t)
        v_line  = find_line(t, ['monitor', 'viewer'])
        ic_line = find_line(t, ['door station', 'intercom'])
        tr_line = find_line(t, ['tag reader', 'reader'])
        v_unit  = line_allin(v_line, r)  if v_line  else None
        ic_unit = line_allin(ic_line, r) if ic_line else None
        tr_unit = line_allin(tr_line, r) if tr_line else None
        if tier in ('Entry', 'Mid'):
            # baseline = 1 reader (mapped to the door-intercom/reader device) + 1 viewer
            if v_unit is not None:
                viewer[tier] = v_unit
            if ic_unit is not None:
                reader[tier] = ic_unit          # "additional readers" priced off the door device
            base = (ic_unit or 0) + (v_unit or 0)
            baseline[tier] = base
        else:  # Premium
            if ic_unit is not None:
                intercom[tier] = ic_unit         # additional Savant gate intercoms
            if tr_unit is not None:
                reader[tier] = tr_unit           # optional tag readers
            baseline[tier] = ic_unit or 0        # baseline = one gate intercom
    per_unit = {}
    if viewer:   per_unit['access_viewer']   = viewer
    if reader:   per_unit['access_reader']   = reader
    if intercom: per_unit['access_intercom'] = intercom
    return baseline, per_unit


def network_sizing(spec):
    """Design-methodology switch sizing. Returns a dict for the counts checkpoint."""
    net = (spec or {}).get('network', {})
    cctv = (spec or {}).get('cctv', {})
    acc  = (spec or {}).get('access-control', {})
    light = (spec or {}).get('lighting', {})
    si   = (spec or {}).get('system-integration', {})

    poe = 0
    poe += int(cctv.get('cctv_building_cameras', 0)) + int(cctv.get('cctv_perimeter_cameras', 0))
    poe += int(net.get('aps_indoor', 0)) + int(net.get('aps_outdoor', 0))
    poe += int(net.get('poe_devices_other', 0))
    poe += int(acc.get('door_intercoms', 0)) + int(acc.get('intercom_viewers', 0))
    poe += int(light.get('motion_sensors', 0))
    poe += int(si.get('touch_panels', 0))

    tvs = int(net.get('non_poe_devices', 0))
    lan = tvs                                   # non-PoE IP devices (TVs, etc.)
    spare_tv_drops = tvs                        # +1 spare LAN drop per TV
    subtotal = poe + lan + spare_tv_drops
    with_spare = math.ceil(subtotal * 1.25)     # +25% spare ports
    # round switch capacity up to the next 24/48-port unit
    unit = 48 if with_spare > 24 else 24
    switch_ports = unit * math.ceil(with_spare / unit)
    return {
        'poe_ports_needed': poe,
        'lan_ports_needed': lan + spare_tv_drops,
        'spare_lan_drops_for_tvs': spare_tv_drops,
        'ports_with_25pct_spare': with_spare,
        'recommended_switch_ports': switch_ports,
        'note': 'total IP devices + 25% spare, rounded to next 24/48-port switch; +1 LAN drop per TV',
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--detail', required=True, help='budget_detail.json from calculate_budget.py')
    ap.add_argument('--spec', default=None, help='the project spec JSON (for network sizing / zone count)')
    ap.add_argument('--takeoff', default=None, help='optional takeoff.json: audio_zones, access_viewer_locations, access_intercom_locations, access_reader_max')
    ap.add_argument('--output', required=True, help='path to write proposal_budgets.json')
    args = ap.parse_args()

    detail = json.load(open(args.detail, encoding='utf-8'))['detail']
    spec = json.load(open(args.spec, encoding='utf-8')) if args.spec and os.path.exists(args.spec) else {}
    takeoff = json.load(open(args.takeoff, encoding='utf-8')) if args.takeoff and os.path.exists(args.takeoff) else {}

    zones = int((spec.get('audio', {}) or {}).get('audio_zones', 0)) or len(takeoff.get('audio_zones', [])) or 12

    tier_budgets = {}
    for sysk in ('cctv', 'access-control', 'network', 'audio', 'home-theatre', 'lighting', 'system-integration'):
        tier_budgets[sysk] = {tier: round(detail[sysk][tier]['total']) for tier in ('Entry', 'Mid', 'Premium')}

    # audio → baseline 0 + per-zone
    au_base, au_perzone = build_audio(detail, zones)
    tier_budgets['audio'] = au_base

    # access → baseline (min config) + per-unit
    ac_base, ac_per_unit = build_access(detail)
    tier_budgets['access-control'] = ac_base

    per_unit = {'audio_zone': au_perzone}
    per_unit.update(ac_per_unit)

    contract = {
        '_note': 'Split proposal contract (v2). Net ex-VAT ZAR. audio baseline 0 + per-zone; access baseline + per-unit.',
        'tier_budgets': tier_budgets,
        'per_unit': per_unit,
        'takeoff': takeoff,
        'network_sizing': network_sizing(spec),
        'options': {},   # merged in by the caller from the original proposal_budgets.json if desired
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    json.dump(contract, open(args.output, 'w', encoding='utf-8'), indent=2)
    print('Wrote', args.output)
    print(json.dumps({'audio_per_zone': au_perzone, 'access_baseline': ac_base,
                      'access_per_unit': ac_per_unit, 'network_sizing': contract['network_sizing']}, indent=2))


if __name__ == '__main__':
    main()
