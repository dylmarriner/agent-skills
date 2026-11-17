#!/usr/bin/env python3
"""
NZ Business Quote Generator — reportlab
=========================================
Build a professional A4 NZ quote/invoice PDF.

Usage:
  python3 nz_quote_builder.py

Edit the DATA dict below with your content, then run.
Columns and styling are set for a typical quote (labour + parts + misc + summary).
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

# ── CONFIG ─────────────────────────────────────────────────────────────
OUTPUT = "/tmp/Quote_Output.pdf"

# ── DATA — EDIT THIS ──────────────────────────────────────────────────
DATA = {
    "company_name": "YOUR COMPANY LTD",
    "address": "123 Street, Suburb 1234",
    "phone": "09 000 0000",
    "fax": "09 000 0001",
    "email": "you@company.co.nz",
    "gst_no": "000-000-000",

    "quote_no": "20250630123456",
    "quote_date": "30 June 2026",       # NZ format

    # Vehicle / customer fields
    "details": [
        ("Make:", "Mazda",             "Quote Number:", "20250630123456"),
        ("Model:", "Model Name",       "Quote Date:",   "30 June 2026"),
        ("Year:",  "2011",             "Client Name:",  "CLIENT NAME"),
        ("Rego:",  "ABC123",           "Home Phone:",   ""),
        ("VIN:",   "VINNUMBER",        "Work Phone:",   ""),
        ("Odometer:", "120,000 Kms",   "Mobile Phone:", ""),
        ("Colour:", "Red",             "Insurer:",      ""),
        ("Body Style:", "Hatchback",   "Claim No:",     ""),
        ("",       "",                 "Excess:",       "$0.00"),
    ],

    "labour": {
        "rate": 70.00,
        "items": [
            ("Description of work 1", 1.50),
            ("Description of work 2", 0.80),
        ],
    },

    "parts": {
        "margin_pct": 10,
        "items": [
            ("Part Name", "Parts Trader", "PART-001", 1, 250.00),
            ("Another Part", "Parts Trader", "PART-002", 1, 300.00),
        ],
    },

    "misc": [
        ("Materials & sundries", 85.00),
        ("Diagnostic fee", 75.00),
    ],

    "excess": 0.00,
}


# ── BUILD ──────────────────────────────────────────────────────────────

def build_quote(data):
    doc = SimpleDocTemplate(
        OUTPUT, pagesize=A4,
        rightMargin=15*mm, leftMargin=15*mm,
        topMargin=15*mm, bottomMargin=15*mm,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("HdrTitle", fontSize=14, fontName="Helvetica-Bold",
                              alignment=TA_CENTER, spaceAfter=2))
    styles.add(ParagraphStyle("HdrSub", fontSize=9, fontName="Helvetica",
                              alignment=TA_CENTER, spaceAfter=1))
    styles.add(ParagraphStyle("SmB", fontSize=9, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle("Sm", fontSize=9, fontName="Helvetica"))
    styles.add(ParagraphStyle("SecT", fontSize=10, fontName="Helvetica-Bold",
                              spaceBefore=8, spaceAfter=4, textColor=colors.HexColor("#333")))
    styles.add(ParagraphStyle("Tot", fontSize=11, fontName="Helvetica-Bold",
                              alignment=TA_RIGHT))
    styles.add(ParagraphStyle("BigT", fontSize=13, fontName="Helvetica-Bold",
                              alignment=TA_RIGHT))
    E = []

    # ── Header ──
    hdr = Table([
        [Paragraph(data["company_name"].upper(), styles["HdrTitle"])],
        [Paragraph(f'{data["address"]}', styles["HdrSub"])],
        [Paragraph(f'Phone: {data["phone"]}  Fax: {data["fax"]}  Email: {data["email"]}', styles["HdrSub"])],
        [Paragraph(f'GST: {data["gst_no"]}', styles["HdrSub"])],
    ], colWidths=[540])
    hdr.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 1, colors.black),
        ("TOPPADDING", (0,1), (0,1), 2),
        ("BOTTOMPADDING", (0,-1), (0,-1), 8),
        ("BACKGROUND", (0,0), (0,0), colors.HexColor("#2B2B2B")),
        ("TEXTCOLOR", (0,0), (0,0), colors.white),
    ]))
    E.append(hdr)
    E.append(Spacer(1, 6*mm))

    # ── Details ──
    d_rows = []
    for row in data["details"]:
        d_rows.append([
            Paragraph(f'<b>{row[0]}</b>', styles["Sm"]),
            Paragraph(row[1], styles["Sm"]),
            Paragraph(f'<b>{row[2]}</b>', styles["Sm"]),
            Paragraph(row[3], styles["Sm"]),
        ])
    dt = Table(d_rows, colWidths=[32*mm, 68*mm, 32*mm, 68*mm])
    dt.setStyle(TableStyle([
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("TOPPADDING", (0,0), (-1,-1), 2),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
        ("BOX", (0,0), (1,-1), 0.5, colors.grey),
        ("BOX", (2,0), (3,-1), 0.5, colors.grey),
    ]))
    E.append(dt)
    E.append(Spacer(1, 6*mm))

    # ── Labour (Remove & Refit) ──
    E.append(Paragraph("REMOVE & REFIT", styles["SecT"]))
    lbr_items = data["labour"]["items"]
    lbr_rate = data["labour"]["rate"]
    lbr_rows = [["", "Description", "Auth Hrs", "Rate", "Total"]]
    total_hrs = 0.0
    total_lbr = 0.0
    for desc, hrs in lbr_items:
        amt = hrs * lbr_rate
        total_hrs += hrs
        total_lbr += amt
        lbr_rows.append(["", desc,
                         f"{hrs:.2f}", f"${lbr_rate:.2f}", f"${amt:.2f}"])
    lbr_rows.append(["", Paragraph("<b>TOTAL — Remove & Refit</b>", styles["SmB"]),
                      Paragraph(f"<b>{total_hrs:.2f}</b>", styles["SmB"]),
                      Paragraph(f"<b>${lbr_rate:.2f}</b>", styles["SmB"]),
                      Paragraph(f"<b>${total_lbr:.2f}</b>", styles["SmB"])])
    lt = Table(lbr_rows, colWidths=[8*mm, 210*mm, 22*mm, 22*mm, 28*mm])
    lt.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ALIGN", (2,0), (-1,-1), "RIGHT"),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("GRID", (0,0), (-1,-2), 0.5, colors.grey),
        ("LINEBELOW", (0,-1), (-1,-1), 1, colors.black),
        ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#E8E8E8")),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#444")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
    ]))
    E.append(lt)
    E.append(Spacer(1, 3*mm))

    # ── Parts ──
    E.append(Paragraph("PARTS", styles["SecT"]))
    p_items = data["parts"]["items"]
    margin_pct = data["parts"]["margin_pct"]
    p_rows = [["", "Description", "Source", "Part #", "Qty", "Unit Price", "Total"]]
    p_sub = 0.0
    for desc, src, pn, qty, up in p_items:
        tot = qty * up
        p_sub += tot
        p_rows.append(["", desc, src, pn, f"{qty:.2f}",
                        f"${up:.2f}", f"${tot:.2f}"])
    p_margin = round(p_sub * margin_pct / 100, 2)
    p_total = p_sub + p_margin
    p_rows.append(["", "", "", "", "",
                    Paragraph("<b>Subtotal</b>", styles["SmB"]),
                    Paragraph(f"<b>${p_sub:.2f}</b>", styles["SmB"])])
    p_rows.append(["", "", "", "", "",
                    Paragraph(f"<b>Margin ({margin_pct}%)</b>", styles["SmB"]),
                    Paragraph(f"<b>${p_margin:.2f}</b>", styles["SmB"])])
    p_rows.append(["", "", "", "", "",
                    Paragraph("<b>Total Parts</b>", styles["SmB"]),
                    Paragraph(f"<b>${p_total:.2f}</b>", styles["SmB"])])
    pt = Table(p_rows, colWidths=[8*mm, 100*mm, 28*mm, 32*mm, 16*mm, 26*mm, 26*mm])
    pt.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ALIGN", (4,0), (-1,-1), "RIGHT"),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("GRID", (0,0), (-1,-4), 0.5, colors.grey),
        ("LINEBELOW", (0,-1), (-1,-1), 1, colors.black),
        ("LINEBELOW", (0,-2), (-1,-2), 0.5, colors.grey),
        ("LINEBELOW", (0,-3), (-1,-3), 0.5, colors.grey),
        ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#E8E8E8")),
        ("BACKGROUND", (0,-3), (-1,-3), colors.HexColor("#F5F5F5")),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#444")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
    ]))
    E.append(pt)
    E.append(Spacer(1, 3*mm))

    # ── Misc ──
    E.append(Paragraph("MISCELLANEOUS", styles["SecT"]))
    m_rows = [["Description", "Total"]]
    m_total = 0.0
    for desc, amt in data["misc"]:
        m_total += amt
        m_rows.append([desc, f"${amt:.2f}"])
    m_rows.append([Paragraph("<b>Total Miscellaneous</b>", styles["SmB"]),
                    Paragraph(f"<b>${m_total:.2f}</b>", styles["SmB"])])
    mt = Table(m_rows, colWidths=[268*mm, 28*mm])
    mt.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ALIGN", (1,0), (-1,-1), "RIGHT"),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("GRID", (0,0), (-1,-2), 0.5, colors.grey),
        ("LINEBELOW", (0,-1), (-1,-1), 1, colors.black),
        ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#E8E8E8")),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#444")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
    ]))
    E.append(mt)
    E.append(Spacer(1, 8*mm))

    # ── Summary ──
    E.append(HRFlowable(width="100%", thickness=1, color=colors.black))
    E.append(Spacer(1, 4*mm))

    total_excl = total_lbr + p_total + m_total
    gst = round(total_excl * 0.15, 2)
    total_incl = total_excl + gst
    excess = data["excess"]

    s_rows = [
        [Paragraph("<b>QUOTATION SUMMARY</b>", styles["SmB"]), "", ""],
        ["Remove & Refit (Labour):", "", f"${total_lbr:.2f}"],
        ["Parts:", "", f"${p_total:.2f}"],
        ["Miscellaneous:", "", f"${m_total:.2f}"],
        [Paragraph("<b>Total excl. GST:</b>", styles["SmB"]), "",
         Paragraph(f"<b>${total_excl:,.2f}</b>", styles["SmB"])],
        ["GST (15%):", "", f"${gst:.2f}"],
        [Paragraph("<b>TOTAL QUOTE incl. GST:</b>", styles["SmB"]), "",
         Paragraph(f"<b>${total_incl:,.2f}</b>", styles["SmB"])],
        [Paragraph("<b>Less Excess to be Collected:</b>", styles["SmB"]), "",
         Paragraph(f"<b>${excess:.2f}</b>", styles["SmB"])],
        [Paragraph("<b>Total Payable to Repairer:</b>", styles["BigT"]), "",
         Paragraph(f"<b>${total_incl:,.2f}</b>", styles["BigT"])],
    ]
    st = Table(s_rows, colWidths=[160*mm, 100*mm, 28*mm])
    st.setStyle(TableStyle([
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ALIGN", (2,0), (-1,-1), "RIGHT"),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("LINEBELOW", (0,0), (-1,0), 1, colors.black),
        ("LINEBELOW", (0,1), (-1,3), 0.5, colors.grey),
        ("LINEBELOW", (0,4), (-1,4), 0.5, colors.grey),
        ("LINEBELOW", (0,6), (-1,6), 1, colors.black),
        ("LINEBELOW", (0,7), (-1,7), 0.5, colors.grey),
        ("LINEBELOW", (0,8), (-1,8), 2, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#E8E8E8")),
        ("BACKGROUND", (0,4), (-1,4), colors.HexColor("#F5F5F5")),
        ("BACKGROUND", (0,6), (-1,7), colors.HexColor("#F5F5F5")),
        ("BACKGROUND", (0,8), (-1,8), colors.HexColor("#CCC")),
    ]))
    E.append(st)
    E.append(Spacer(1, 8*mm))

    # ── Footer ──
    from datetime import datetime
    today = datetime.now().strftime("%A %d %B %Y")
    ft = Table([
        [Paragraph(f"Created {today} &nbsp;&nbsp; Page 1 of 1",
                   ParagraphStyle("Ft", fontSize=8, fontName="Helvetica",
                                  alignment=TA_CENTER, textColor=colors.grey))],
    ], colWidths=[290*mm])
    E.append(ft)

    doc.build(E)
    return total_excl, gst, total_incl


if __name__ == "__main__":
    excl, gst, incl = build_quote(DATA)
    print(f"PDF → {OUTPUT}")
    print(f"Total excl GST: ${excl:,.2f}")
    print(f"GST: ${gst:.2f}")
    print(f"Total incl GST: ${incl:,.2f}")
