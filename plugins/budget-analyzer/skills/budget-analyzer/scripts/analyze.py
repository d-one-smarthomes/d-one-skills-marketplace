#!/usr/bin/env python3
"""
D-One Budget Analyzer
Reads structured quote data (JSON), calculates per-unit averages by system,
and outputs an Excel breakdown + zone_prices.json for the proposal skill.

Usage:
    python3 analyze.py --data /tmp/quote_data.json --output /tmp/budget-analysis/
"""

import os
import sys
import json
import argparse
from collections import defaultdict

try:
    import openpyxl
    from openpyxl.styles import (Font, PatternFill, Alignment, Border, Side,
                                  GradientFill)
    from openpyxl.utils import get_column_letter
except ImportError:
    print("Installing openpyxl...")
    os.system(f"{sys.executable} -m pip install openpyxl --break-system-packages -q")
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

# ── D-One brand colours ──────────────────────────────────────────────────────
DARK    = "17140F"
GOLD    = "B8944A"
GOLD_LT = "D4AE6A"
CREAM   = "F3EDE2"
STONE   = "8C7E6B"
WHITE   = "F8F3EB"
MID_BG  = "211D16"
RED_FLAG = "C0392B"

SYSTEM_LABELS = {
    "cctv":               "CCTV",
    "access-control":     "Access Control",
    "network":            "Network & Wi-Fi",
    "audio":              "Audio",
    "home-theatre":       "Home Theatre",
    "lighting":           "Lighting Control",
    "system-integration": "System Integration",
}

SYSTEM_UNIT_LABELS = {
    "cctv":               "per camera",
    "access-control":     "per reader / point",
    "network":            "per access point",
    "audio":              "per zone / room",
    "home-theatre":       "per room",
    "lighting":           "per circuit / zone",
    "system-integration": "per system",
}

TIER_ORDER = ["Entry", "Mid", "Premium"]
SYSTEM_ORDER = ["cctv", "access-control", "network", "audio",
                 "home-theatre", "lighting", "system-integration"]


def fmt_zar(val):
    if val is None:
        return "—"
    return f"R {val:,.0f}"


def cell_style(ws, row, col, value=None, bold=False, bg=None, fg=None,
               align="left", number_format=None, border=None, size=10, italic=False):
    c = ws.cell(row=row, column=col)
    if value is not None:
        c.value = value
    if bold:
        c.font = Font(bold=True, color=fg or "000000", size=size, italic=italic,
                      name="Calibri")
    else:
        c.font = Font(color=fg or "000000", size=size, italic=italic, name="Calibri")
    if bg:
        c.fill = PatternFill("solid", fgColor=bg)
    c.alignment = Alignment(horizontal=align, vertical="center", wrap_text=True)
    if number_format:
        c.number_format = number_format
    if border:
        thin = Side(style="thin", color="CCCCCC")
        c.border = Border(bottom=thin)
    return c


def auto_width(ws, col, min_w=10, max_w=50):
    col_letter = get_column_letter(col)
    max_len = 0
    for cell in ws[col_letter]:
        try:
            if cell.value:
                max_len = max(max_len, len(str(cell.value)))
        except Exception:
            pass
    ws.column_dimensions[col_letter].width = min(max_w, max(min_w, max_len + 2))


def build_raw_sheet(wb, entries):
    ws = wb.create_sheet("Quote Data")
    ws.sheet_view.showGridLines = False

    headers = [
        "Source File", "System", "Tier", "Unit Type", "Qty",
        "Supply (ex VAT)", "Install (ex VAT)", "Total (ex VAT)",
        "Per Unit Rate", "Notes"
    ]

    # Header row
    ws.row_dimensions[1].height = 32
    for i, h in enumerate(headers, 1):
        cell_style(ws, 1, i, h, bold=True, bg=DARK, fg=GOLD_LT,
                   align="center", size=9)

    # Compute outlier thresholds per system
    rates_by_system = defaultdict(list)
    for e in entries:
        if e.get("per_unit_rate") and e.get("quantity"):
            rates_by_system[e["system"]].append(e["per_unit_rate"])

    def is_outlier(system, rate):
        rates = rates_by_system.get(system, [])
        if len(rates) < 2 or not rate:
            return False
        avg = sum(rates) / len(rates)
        return abs(rate - avg) / avg > 0.40

    # Data rows
    for row_i, e in enumerate(entries, 2):
        bg = "FFFFFF" if row_i % 2 == 0 else "F9F6F1"
        rate = e.get("per_unit_rate")
        outlier = is_outlier(e.get("system", ""), rate)

        cell_style(ws, row_i, 1,  e.get("source", ""),           bg=bg, size=9, border=True)
        cell_style(ws, row_i, 2,  SYSTEM_LABELS.get(e.get("system",""), e.get("system","")),
                   bg=bg, bold=True, size=9, border=True)
        cell_style(ws, row_i, 3,  e.get("tier", "—"),             bg=bg, size=9, border=True)
        cell_style(ws, row_i, 4,  e.get("unit_type", ""),         bg=bg, size=9, border=True)
        cell_style(ws, row_i, 5,  e.get("quantity"),              bg=bg, align="center", size=9, border=True)
        cell_style(ws, row_i, 6,  e.get("supply_price"),          bg=bg, align="right",
                   number_format='R #,##0', size=9, border=True)
        cell_style(ws, row_i, 7,  e.get("install_price"),         bg=bg, align="right",
                   number_format='R #,##0', size=9, border=True)
        cell_style(ws, row_i, 8,  e.get("total_price"),           bg=bg, align="right",
                   number_format='R #,##0', size=9, border=True)

        rate_cell = cell_style(ws, row_i, 9, rate, bg=bg, align="right",
                               number_format='R #,##0', size=9, bold=True, border=True)
        if outlier:
            rate_cell.fill = PatternFill("solid", fgColor="FDECEA")
            rate_cell.font = Font(color=RED_FLAG, bold=True, size=9, name="Calibri")
            ws.cell(row_i, 9).comment = None  # could add comment

        cell_style(ws, row_i, 10, e.get("notes", ""),             bg=bg, size=9, border=True)

    # Column widths
    widths = [28, 20, 10, 18, 6, 16, 16, 16, 16, 40]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # Freeze header
    ws.freeze_panes = "A2"
    return ws


def build_summary_sheet(wb, entries):
    ws = wb.create_sheet("Averages", 0)
    ws.sheet_view.showGridLines = False

    row = 1

    # Title
    ws.row_dimensions[row].height = 40
    c = ws.cell(row=row, column=1, value="D-One  ·  Budget Averages")
    c.font = Font(name="Calibri", bold=True, size=16, color=GOLD)
    c.fill = PatternFill("solid", fgColor=DARK)
    c.alignment = Alignment(horizontal="left", vertical="center")
    ws.merge_cells(f"A{row}:I{row}")
    row += 1

    # Subtitle
    ws.row_dimensions[row].height = 20
    c = ws.cell(row=row, column=1, value="Per-unit averages derived from uploaded quotes")
    c.font = Font(name="Calibri", size=9, color=STONE, italic=True)
    c.fill = PatternFill("solid", fgColor=DARK)
    c.alignment = Alignment(horizontal="left", vertical="center")
    ws.merge_cells(f"A{row}:I{row}")
    row += 2

    # Column headers
    ws.row_dimensions[row].height = 28
    hdrs = ["System", "Tier", "# Quotes", "# Units", "Min Rate", "Max Rate",
            "Avg Rate", "Unit", "Proposal Arg"]
    for i, h in enumerate(hdrs, 1):
        cell_style(ws, row, i, h, bold=True, bg=MID_BG, fg=GOLD_LT,
                   align="center", size=9)
    row += 1

    # Group entries by system+tier
    groups = defaultdict(list)
    for e in entries:
        sys_key = e.get("system", "unknown")
        tier_key = e.get("tier") or "Unknown"
        if e.get("per_unit_rate") and e.get("quantity"):
            groups[(sys_key, tier_key)].append(e)

    # Also group by system only (across all tiers) for per-unit pricing
    by_system = defaultdict(list)
    for e in entries:
        if e.get("per_unit_rate") and e.get("quantity"):
            by_system[e.get("system", "unknown")].append(e)

    # Write rows ordered by system then tier
    written_systems = set()
    for sys_slug in SYSTEM_ORDER:
        sys_entries = [(k, v) for k, v in groups.items() if k[0] == sys_slug]
        if not sys_entries:
            continue

        first_in_sys = True
        for tier in TIER_ORDER + ["Unknown"]:
            key = (sys_slug, tier)
            if key not in groups:
                continue

            grp = groups[key]
            rates = [e["per_unit_rate"] for e in grp]
            quantities = [e.get("quantity", 0) for e in grp]
            avg_rate = sum(rates) / len(rates)
            min_rate = min(rates)
            max_rate = max(rates)
            total_units = sum(quantities)
            unit_label = SYSTEM_UNIT_LABELS.get(sys_slug, "per unit")

            bg = "FFFFFF" if row % 2 == 0 else "F9F6F1"
            sys_label = SYSTEM_LABELS.get(sys_slug, sys_slug) if first_in_sys else ""
            first_in_sys = False

            cell_style(ws, row, 1, sys_label, bold=True, bg=bg, size=9, border=True)
            cell_style(ws, row, 2, tier, bg=bg, size=9, border=True)
            cell_style(ws, row, 3, len(grp), bg=bg, align="center", size=9, border=True)
            cell_style(ws, row, 4, total_units, bg=bg, align="center", size=9, border=True)
            cell_style(ws, row, 5, min_rate, bg=bg, align="right",
                       number_format='R #,##0', size=9, border=True)
            cell_style(ws, row, 6, max_rate, bg=bg, align="right",
                       number_format='R #,##0', size=9, border=True)
            avg_c = cell_style(ws, row, 7, avg_rate, bg=bg, align="right",
                               number_format='R #,##0', bold=True, size=10,
                               fg=DARK, border=True)
            cell_style(ws, row, 8, unit_label, bg=bg, size=9,
                       fg=STONE, italic=True, border=True)

            # Proposal arg hint
            prop_arg = f'"audio": {int(avg_rate)}' if sys_slug == "audio" else \
                       f'"access-control": {int(avg_rate)}' if sys_slug == "access-control" else ""
            cell_style(ws, row, 9, prop_arg, bg=bg, size=8, fg=STONE,
                       italic=True, border=True)

            row += 1

        written_systems.add(sys_slug)

    row += 1

    # ── Per-system overall average (for zone_prices.json) ──
    ws.row_dimensions[row].height = 24
    c = ws.cell(row=row, column=1, value="Overall Per-Unit Averages  (all tiers combined)")
    c.font = Font(name="Calibri", bold=True, size=10, color=WHITE)
    c.fill = PatternFill("solid", fgColor=DARK)
    c.alignment = Alignment(horizontal="left", vertical="center")
    ws.merge_cells(f"A{row}:I{row}")
    row += 1

    zone_prices = {}
    for sys_slug in SYSTEM_ORDER:
        sys_entries_all = by_system.get(sys_slug, [])
        if not sys_entries_all:
            continue
        rates = [e["per_unit_rate"] for e in sys_entries_all]
        avg = round(sum(rates) / len(rates))
        zone_prices[sys_slug] = avg
        unit_label = SYSTEM_UNIT_LABELS.get(sys_slug, "per unit")

        bg = "FFFFFF" if row % 2 == 0 else "F9F6F1"
        cell_style(ws, row, 1, SYSTEM_LABELS.get(sys_slug, sys_slug),
                   bold=True, bg=bg, size=9, border=True)
        cell_style(ws, row, 2, "All", bg=bg, size=9, fg=STONE, border=True)
        cell_style(ws, row, 3, len(sys_entries_all), bg=bg, align="center", size=9, border=True)
        total_u = sum(e.get("quantity", 0) for e in sys_entries_all)
        cell_style(ws, row, 4, total_u, bg=bg, align="center", size=9, border=True)
        cell_style(ws, row, 7, avg, bg="FDF6E8", align="right",
                   number_format='R #,##0', bold=True, size=11, fg="17140F", border=True)
        cell_style(ws, row, 8, unit_label, bg=bg, size=9, fg=STONE, italic=True, border=True)
        row += 1

    # Column widths
    col_widths = [22, 10, 10, 10, 14, 14, 14, 22, 32]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws.freeze_panes = "A4"
    return ws, zone_prices


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data",   required=True,
                        help="Path to JSON file with extracted quote entries")
    parser.add_argument("--output", required=True,
                        help="Output directory for Excel and JSON files")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    with open(args.data, "r", encoding="utf-8") as f:
        entries = json.load(f)

    # Calculate per_unit_rate for any entries missing it
    for e in entries:
        if not e.get("per_unit_rate"):
            total = e.get("total_price") or (
                (e.get("supply_price") or 0) + (e.get("install_price") or 0)
            )
            qty = e.get("quantity")
            if total and qty and qty > 0:
                e["per_unit_rate"] = round(total / qty)

    # Build workbook
    wb = openpyxl.Workbook()
    if "Sheet" in wb.sheetnames:
        del wb["Sheet"]

    summary_ws, zone_prices = build_summary_sheet(wb, entries)
    raw_ws = build_raw_sheet(wb, entries)

    # Save Excel
    xlsx_path = os.path.join(args.output, "budget_analysis.xlsx")
    wb.save(xlsx_path)
    print(f"Excel saved: {xlsx_path}")

    # ── Compute tier budgets: average total_price per system+tier ──────────
    tier_budgets = {}
    tier_groups = defaultdict(list)
    for e in entries:
        total = e.get("total_price") or (
            (e.get("supply_price") or 0) + (e.get("install_price") or 0)
        )
        tier = e.get("tier")
        sys_slug = e.get("system")
        if total and tier and sys_slug and tier in TIER_ORDER:
            tier_groups[(sys_slug, tier)].append(total)

    for sys_slug in SYSTEM_ORDER:
        sys_tiers = {}
        for tier in TIER_ORDER:
            vals = tier_groups.get((sys_slug, tier), [])
            if vals:
                sys_tiers[tier] = round(sum(vals) / len(vals))
        if sys_tiers:
            tier_budgets[sys_slug] = sys_tiers

    # ── Save combined proposal_budgets.json ─────────────────────────────────
    proposal_budgets = {
        "tier_budgets": tier_budgets,
        "zone_prices":  zone_prices,
    }
    budgets_path = os.path.join(args.output, "proposal_budgets.json")
    with open(budgets_path, "w", encoding="utf-8") as f:
        json.dump(proposal_budgets, f, indent=2)
    print(f"Budgets saved: {budgets_path}")

    # ── Print summary ────────────────────────────────────────────────────────
    print("\n── Tier Budgets (card prices) ──────────────────")
    for sys_slug in SYSTEM_ORDER:
        tiers = tier_budgets.get(sys_slug, {})
        if not tiers:
            continue
        label = SYSTEM_LABELS.get(sys_slug, sys_slug)
        tier_str = "   ".join(
            f"{t}: R {tiers[t]:,.0f}" for t in TIER_ORDER if t in tiers
        )
        print(f"  {label:<24} {tier_str}")

    print("\n── Per-Unit Add-on Rates (zone checkboxes) ─────")
    for sys_slug, avg in zone_prices.items():
        label = SYSTEM_LABELS.get(sys_slug, sys_slug)
        unit  = SYSTEM_UNIT_LABELS.get(sys_slug, "per unit")
        print(f"  {label:<24} R {avg:>8,.0f}  {unit}")

    print("\n── Pass to generate.py ─────────────────────────")
    print(f"  --budgets-file '{budgets_path}'")
    print("────────────────────────────────────────────────")


if __name__ == "__main__":
    main()
