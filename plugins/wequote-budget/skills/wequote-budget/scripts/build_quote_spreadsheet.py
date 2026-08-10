#!/usr/bin/env python3
"""
Build the per-project line-item quote spreadsheet from budget_detail.json.
Every proposal gets one: every component, qty, live retail price, its markup vs
cost, and the labour (installation / programming / design / PM) per tier.

Usage:
  python3 build_quote_spreadsheet.py --detail out/budget_detail.json \
      --project "Mountain House" --output out/quote.xlsx
"""
import argparse, json
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

NAVY="17314A"; BLUE="1379C9"; LIGHT="EAF3FB"; GREY="E8E8E8"; RED="F4CCCC"
def F(**k): return Font(name="Arial", **k)
thin=Side(style="thin", color="CCCCCC"); box=Border(left=thin,right=thin,top=thin,bottom=thin)
CUR='R #,##0;(R #,##0);-'; PCT='0%'
TIERS=["Entry","Mid","Premium"]
FALLBACK_MARKUP=1.45

def load_costs():
    roots=[Path.home()/".claude"/"plugins"/"synced", Path("/root/.claude/plugins/synced")]
    for r in roots:
        for p in r.rglob("equip_cost_by_sku.json") if r.exists() else []:
            try: return {k.upper():v.get("unit_cost") for k,v in json.load(open(p)).items() if v.get("unit_cost")}
            except Exception: pass
    return {}

def build(detail_path, project, out_path):
    D=json.load(open(detail_path))
    labels=D["modules"]; groups=D["category_group"]; detail=D["detail"]
    order=list(detail)
    costs=load_costs()
    flags=[]  # (system, sku, unit, markup) for near-cost items

    def markup(sku, unit):
        """Return (markup_fraction, estimated_bool). markup 0.45 == +45%."""
        c=costs.get(sku.upper())
        if c and c>0:
            return unit/c-1.0, False
        return FALLBACK_MARKUP-1.0, True   # est

    wb=Workbook()
    sw=wb.active; sw.title="Summary"
    sw.merge_cells("A1:E1")
    c=sw.cell(1,1,f"D-One Quote — {project}   (net ex-VAT, ZAR)"); c.font=F(bold=True,size=14,color="FFFFFF")
    c.fill=PatternFill("solid",fgColor=NAVY); c.alignment=Alignment(vertical="center",indent=1); sw.row_dimensions[1].height=26
    sw.cell(3,1,"Live retail prices from the estimator inventory; markup column = retail ÷ cost. Labour per standards (install/programming per component, design 10%, PM 12.5%).").font=F(italic=True,size=9,color="555555")
    sw.merge_cells("A3:E3")
    for i,h in enumerate(["System","Category","Entry","Mid","Premium"],1):
        cc=sw.cell(5,i,h); cc.font=F(bold=True,color="FFFFFF"); cc.fill=PatternFill("solid",fgColor=BLUE); cc.border=box
    for i,w in enumerate([24,18,15,15,15],1): sw.column_dimensions[get_column_letter(i)].width=w
    r=6
    for m in order:
        sw.cell(r,1,labels[m]); sw.cell(r,2,groups[m])
        for ci,t in zip([3,4,5],TIERS):
            cell=sw.cell(r,ci, detail[m][t]["total"]); cell.number_format=CUR
        for cc in range(1,6): sw.cell(r,cc).border=box
        r+=1
    sw.cell(r,1,"(No grand total — each category quoted independently)").font=F(italic=True,size=9,color="777777")
    sw.merge_cells(start_row=r,start_column=1,end_row=r,end_column=5)
    r+=2
    # project-wide labour & hardware-margin totals by tier
    agg={t:{"margin":0.0,"mext":0.0,"ih":0.0,"ph":0.0,"lab":0.0} for t in TIERS}
    for mm in order:
        for t in TIERS:
            rs=detail[mm][t]
            agg[t]["margin"]+=rs.get("hw_margin_R",0) or 0
            agg[t]["mext"]+=rs.get("hw_matched_ext",0) or 0
            agg[t]["ih"]+=rs.get("inst_hours",0) or 0
            agg[t]["ph"]+=rs.get("prog_hours",0) or 0
            agg[t]["lab"]+=rs.get("labour_total",0) or 0
    for i,h in enumerate(["Whole-project totals","","Entry","Mid","Premium"],1):
        c=sw.cell(r,i,h); c.font=F(bold=True,color="FFFFFF"); c.fill=PatternFill("solid",fgColor=NAVY); c.border=box
    r+=1
    def trow(label, vals, fmt):
        sw.cell(r,1,label).font=F(bold=True)
        for ci,t in zip([3,4,5],TIERS):
            c=sw.cell(r,ci,vals[t]); c.number_format=fmt
        for cc in range(1,6): sw.cell(r,cc).border=box
    trow("Total hardware margin (matched items)", {t:round(agg[t]["margin"]) for t in TIERS}, CUR); r+=1
    trow("Hardware margin %", {t:(agg[t]["margin"]/agg[t]["mext"] if agg[t]["mext"] else 0) for t in TIERS}, PCT); r+=1
    trow("Total labour (hours)", {t:round(agg[t]["ih"]+agg[t]["ph"],1) for t in TIERS}, '0.0"h"'); r+=1
    trow("Total labour (Rands)", {t:round(agg[t]["lab"]) for t in TIERS}, CUR); r+=1
    sw.cell(r,1,"Margin % is on matched-price items only (items without a matched cost+retail are excluded).").font=F(italic=True,size=8,color="777777")
    sw.merge_cells(start_row=r,start_column=1,end_row=r,end_column=5)
    sw.freeze_panes="A6"

    cols=["Item","SKU","Qty","Unit price (retail)","Markup","Equipment","Installation","Programming","Design","Project mgmt"]
    widths=[34,20,5,16,9,13,12,12,11,11]
    checks=[]
    for m in order:
        ws=wb.create_sheet(labels[m][:31])
        ws.merge_cells("A1:J1")
        c=ws.cell(1,1,f"{labels[m]} — line-item build-up (net ex-VAT)"); c.font=F(bold=True,size=13,color="FFFFFF")
        c.fill=PatternFill("solid",fgColor=NAVY); c.alignment=Alignment(vertical="center",indent=1); ws.row_dimensions[1].height=24
        for i,w in enumerate(widths,1): ws.column_dimensions[get_column_letter(i)].width=w
        r=3
        for t in TIERS:
            res=detail[m][t]
            for i in range(1,11): ws.cell(r,i).fill=PatternFill("solid",fgColor=BLUE)
            ws.cell(r,1,f"{t} tier").font=F(bold=True,color="FFFFFF")
            for i,h in enumerate(cols,1):
                if i>=3: ws.cell(r,i,h).font=F(bold=True,color="FFFFFF")
            r+=1
            eq=ins=prg=0.0
            for ln in res["lines"]:
                ws.cell(r,1,("   " if not ln["accessory"] else "   · ")+ln["role"])
                ws.cell(r,2,ln["sku"]).font=F(size=9,color="666666")
                ws.cell(r,3,ln["qty"])
                uc=ws.cell(r,4,ln["unit"]); uc.number_format=CUR
                mk = ln.get("markup")   # only set when retail+cost are a matched pricelist pair
                if mk is not None:
                    mc=ws.cell(r,5,round(mk,2)); mc.number_format=PCT
                    if mk < 0.10:
                        mc.fill=PatternFill("solid",fgColor=RED)
                        flags.append((labels[m],ln["role"],ln["sku"],ln["unit"],round(mk*100)))
                # else: leave the Markup cell blank (no cost/retail matched pair)
                ec=ws.cell(r,6,ln["ext"]); ec.number_format=CUR; eq+=ln["ext"]
                if ln["inst_r"]:
                    ic=ws.cell(r,7,ln["inst_r"]); ic.number_format=CUR; ins+=ln["inst_r"]
                if ln["prog_r"]:
                    pc=ws.cell(r,8,ln["prog_r"]); pc.number_format=CUR; prg+=ln["prog_r"]
                r+=1
            for lab in res.get("labour_lines",[]):
                ws.cell(r,1,"   "+lab["desc"]).font=F(italic=True)
                col=7 if lab["kind"]=="install" else 8
                cc=ws.cell(r,col,lab["cost"]); cc.number_format=CUR
                if lab["kind"]=="install": ins+=lab["cost"]
                else: prg+=lab["cost"]
                r+=1
            ws.cell(r,1,"   Design (10% of equipment + install)").font=F(italic=True)
            ws.cell(r,9,res["design"]).number_format=CUR; r+=1
            ws.cell(r,1,"   Project management (12.5% of labour)").font=F(italic=True)
            ws.cell(r,10,res["pm"]).number_format=CUR; r+=1
            for i in range(1,11): ws.cell(r,i).fill=PatternFill("solid",fgColor=LIGHT)
            ws.cell(r,1,f"{t} — subtotals").font=F(bold=True)
            for col,val in [(6,eq),(7,ins),(8,prg),(9,res["design"]),(10,res["pm"])]:
                cc=ws.cell(r,col,round(val,2)); cc.number_format=CUR; cc.font=F(bold=True)
            r+=1
            for i in range(1,11): ws.cell(r,i).fill=PatternFill("solid",fgColor=GREY)
            ws.cell(r,1,f"{t} TOTAL").font=F(bold=True,size=12)
            tot=ws.cell(r,10,res["total"]); tot.number_format=CUR; tot.font=F(bold=True,size=12)
            checks.append((labels[m],t,round(eq+ins+prg+res["design"]+res["pm"],2),res["total"]))
            r+=1
            # hardware margin + labour totals (always shown)
            mR=res.get("hw_margin_R"); mp=res.get("hw_margin_pct")
            ws.cell(r,1,"   Hardware margin (matched-price items)").font=F(italic=True,color="555555")
            mc=ws.cell(r,6,mR); mc.number_format=CUR; mc.font=F(italic=True,color="555555")
            if mp is not None:
                pcc=ws.cell(r,5,round(mp,2)); pcc.number_format=PCT; pcc.font=F(italic=True,color="555555")
            r+=1
            lh=res.get("inst_hours",0)+res.get("prog_hours",0)
            ws.cell(r,1,f"   Labour — {res.get('inst_hours',0):g} install h + {res.get('prog_hours',0):g} prog h = {lh:g} h").font=F(italic=True,color="555555")
            lc=ws.cell(r,7,res.get("labour_total")); lc.number_format=CUR; lc.font=F(italic=True,color="555555")
            r+=2
        ws.freeze_panes="A3"

    wb.save(out_path)
    bad=[c for c in checks if abs(c[2]-c[3])>1]
    print(f"Saved {out_path}")
    print("Reconciliation:", "ALL OK" if not bad else f"MISMATCH {bad[:5]}")
    if flags:
        print(f"\n⚠ Items with <10% markup (check they're at retail, not cost):")
        seen=set()
        for s,role,sku,unit,mk in flags:
            if sku in seen: continue
            seen.add(sku); print(f"   {sku:22s} {role[:28]:28s} R{unit:>10,.0f}  markup {mk}%")

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--detail",required=True); ap.add_argument("--project",default="Project")
    ap.add_argument("--output",required=True)
    a=ap.parse_args()
    build(a.detail,a.project,a.output)
