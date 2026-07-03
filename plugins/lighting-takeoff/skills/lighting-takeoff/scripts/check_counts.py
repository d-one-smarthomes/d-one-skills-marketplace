#!/usr/bin/env python3
"""
check_counts.py — validate a room-level lighting take-off BEFORE building the xlsx.

Visual counts are error-prone, so this is the safety net: it catches the mistakes
that have actually bitten us (phantom fittings with no room, LED circuits that
exceed runs, control-less rooms, empty columns) so they're fixed before a polished
spreadsheet hides them. Run it on your counts JSON; read EVERY line.

    python check_counts.py counts.json

- ERRORS are logical impossibilities — fix them (the script exits non-zero).
- WARNINGS are "look again" flags — most should be explained or corrected, but a
  few may be legitimately fine (e.g. a plant room with no sensor). Use judgement,
  but never ignore them silently.

The report also prints each floor's totals so you can eyeball them against the
plan before committing.
"""
import json, sys

LED_CIRCUIT_KEY = "led-strip circuit"   # matched case-insensitively / loosely


def is_led_circuit(name):
    n = name.lower()
    return "led" in n and "circuit" in n


def main():
    data = json.load(open(sys.argv[1]))
    errors, warns = [], []
    proj = data.get("project", "(unnamed)")
    print(f"== Validating take-off: {proj} ==\n")

    for fl in data.get("floors", []):
        fname = fl.get("name", "(unnamed floor)")
        rooms = fl.get("rooms")
        if not rooms:
            warns.append(f"[{fname}] no room-level breakdown (floor-level only) — "
                         "room-level is expected now.")
            rooms = []
        ftot = {"fittings": 0, "led": 0, "keypads": 0, "circuits": 0, "sensors": 0}
        led_circ_total = 0
        for i, rm in enumerate(rooms):
            rn = rm.get("name")
            tag = f"[{fname} / {rn or f'room #{i+1}'}]"
            if not rn:
                errors.append(f"{tag} room has no name — every count must name its room.")
            lights = rm.get("lights") or {}
            fittings = sum(v or 0 for v in lights.values())
            led = rm.get("led_strips", 0) or 0
            kp = rm.get("keypads", rm.get("switch_points", 0)) or 0
            circ = rm.get("circuits") or {}
            if not isinstance(circ, dict):
                errors.append(f"{tag} circuits must be a {{type: count}} object.")
                circ = {}
            led_circ = sum(v or 0 for k, v in circ.items() if is_led_circuit(k))
            ctot = sum(v or 0 for v in circ.values())

            for k, v in list(lights.items()) + list(circ.items()):
                if (v or 0) < 0:
                    errors.append(f"{tag} negative value for '{k}'.")
            # LED circuits can never exceed LED runs (a circuit groups runs)
            if led_circ > led:
                errors.append(f"{tag} {led_circ} LED-strip circuits but only {led} "
                              f"LED runs — circuits cannot exceed runs.")
            # rooms with fittings should have a control point
            if fittings and not kp:
                warns.append(f"{tag} has {fittings} fittings but 0 keypads/switch "
                             "points — does this room really have no control?")
            if kp and not fittings and not led:
                warns.append(f"{tag} has {kp} keypads but no fittings or LED — check.")
            # fittings but no circuit (or vice-versa)
            if fittings and ctot == 0:
                warns.append(f"{tag} has fittings but no circuits recorded.")
            if ctot and not fittings and not led:
                warns.append(f"{tag} has circuits but no fittings/LED to be on them.")

            ftot["fittings"] += fittings; ftot["led"] += led; ftot["keypads"] += kp
            ftot["circuits"] += ctot; ftot["sensors"] += rm.get("sensors", 0) or 0
            led_circ_total += led_circ

        if led_circ_total > ftot["led"]:
            errors.append(f"[{fname}] floor LED circuits ({led_circ_total}) exceed "
                          f"LED runs ({ftot['led']}).")
        print(f"{fname}: {len(rooms)} rooms | fittings {ftot['fittings']} | "
              f"LED runs {ftot['led']} | keypads {ftot['keypads']} | "
              f"circuits {ftot['circuits']} | sensors {ftot['sensors']}")

    print()
    for w in warns:
        print("  WARNING:", w)
    for e in errors:
        print("  ERROR:  ", e)
    print()
    if errors:
        print(f"FAILED — {len(errors)} error(s), {len(warns)} warning(s). "
              "Fix errors before building the spreadsheet.")
        sys.exit(1)
    print(f"PASSED — 0 errors, {len(warns)} warning(s). "
          "Review warnings, then build the spreadsheet.")


if __name__ == "__main__":
    main()
