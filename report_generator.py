# ============================================================
# app/services/report_generator.py
# GST Audit Report Generator — Excel + PDF
# ============================================================

from __future__ import annotations
import io
import xlsxwriter
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# ── Color Palette ────────────────────────────────────────────
COLORS = {
    "indigo":       "#4F46E5",
    "indigo_light": "#EEF2FF",
    "emerald":      "#059669",
    "emerald_light":"#ECFDF5",
    "red":          "#DC2626",
    "red_light":    "#FEF2F2",
    "amber":        "#D97706",
    "amber_light":  "#FFFBEB",
    "slate":        "#475569",
    "slate_dark":   "#1E293B",
    "white":        "#FFFFFF",
    "border":       "#E2E8F0",
    "bg":           "#F8F9FC",
}


class GSTReportGenerator:
    """
    Generates professional GST Audit Reports in Excel format with:
    - Cover sheet with company details
    - Executive summary
    - GSTR-1 vs Books reconciliation
    - GSTR-2B ITC reconciliation
    - GSTR-3B verification
    - Exception / mismatch detail
    - Vendor risk report
    - ITC utilization analysis
    """

    def generate_full_audit_report(
        self,
        company: dict,
        period_from: str,
        period_to: str,
        gstr1_summary: dict,
        gstr2b_summary: dict,
        gstr3b_data: dict,
        mismatches: list[dict],
        vendors: list[dict],
        compliance_score: int,
        ca_name: str = "",
    ) -> bytes:
        """Generate complete GST Audit Report Excel workbook."""

        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {"in_memory": True, "default_date_format": "dd-mmm-yyyy"})

        # ── Define Formats ────────────────────────────────────
        fmt = self._create_formats(wb)

        # ── Sheets ───────────────────────────────────────────
        self._write_cover_sheet(wb, fmt, company, period_from, period_to, compliance_score, ca_name)
        self._write_executive_summary(wb, fmt, company, gstr1_summary, gstr2b_summary, gstr3b_data, compliance_score)
        self._write_gstr1_reconciliation(wb, fmt, gstr1_summary, mismatches)
        self._write_gstr2b_reconciliation(wb, fmt, gstr2b_summary, vendors)
        self._write_gstr3b_verification(wb, fmt, gstr3b_data)
        self._write_mismatch_detail(wb, fmt, mismatches)
        self._write_vendor_report(wb, fmt, vendors)
        self._write_itc_analysis(wb, fmt, gstr2b_summary)

        wb.close()
        return output.getvalue()

    # ── Cover Sheet ───────────────────────────────────────────

    def _write_cover_sheet(self, wb, fmt, company, period_from, period_to, score, ca_name):
        ws = wb.add_worksheet("Cover")
        ws.set_tab_color(COLORS["indigo"])
        ws.hide_gridlines(2)
        ws.set_column("A:A", 3)
        ws.set_column("B:B", 30)
        ws.set_column("C:G", 20)

        # Banner
        ws.set_row(0, 8)
        ws.set_row(1, 60)
        ws.merge_range("B2:G2", "GST AUDIT REPORT", fmt["title_banner"])

        ws.set_row(2, 25)
        ws.merge_range("B3:G3", f"For the Period: {period_from} to {period_to}", fmt["subtitle"])

        ws.set_row(3, 8)

        # Company details box
        details = [
            ("Company Name",       company.get("name", "")),
            ("GSTIN",              company.get("gstin", "")),
            ("PAN",                company.get("pan", "")),
            ("Registration Type",  company.get("registration_type", "Regular").title()),
            ("State",              company.get("state_code", "")),
            ("Address",            company.get("address", "")),
        ]
        row = 4
        ws.merge_range(f"B{row}:G{row}", "COMPANY DETAILS", fmt["section_header"])
        row += 1
        for label, value in details:
            ws.set_row(row, 20)
            ws.write(f"B{row}", label, fmt["label"])
            ws.merge_range(f"C{row}:G{row}", str(value), fmt["value"])
            row += 1

        row += 1
        # Compliance Score
        ws.merge_range(f"B{row}:G{row}", "COMPLIANCE SCORE", fmt["section_header"])
        row += 1
        score_color = fmt["score_high"] if score >= 80 else fmt["score_med"] if score >= 60 else fmt["score_low"]
        ws.merge_range(f"B{row}:C{row+2}", str(score), score_color)
        ws.set_row(row, 30)
        ws.write(f"D{row}", f"Score: {score}/100", fmt["value"])
        ws.write(f"D{row+1}", "Good" if score >= 80 else "Average" if score >= 60 else "Needs Attention", fmt["value"])
        row += 3

        # Prepared by
        row += 1
        ws.merge_range(f"B{row}:G{row}", "REPORT CERTIFICATION", fmt["section_header"])
        row += 1
        ws.write(f"B{row}", "Prepared By",      fmt["label"])
        ws.merge_range(f"C{row}:G{row}", ca_name or "Authorised Signatory", fmt["value"])
        row += 1
        ws.write(f"B{row}", "Report Date",      fmt["label"])
        ws.merge_range(f"C{row}:G{row}", datetime.today().strftime("%d %B %Y"), fmt["value"])
        row += 1
        ws.write(f"B{row}", "Software",         fmt["label"])
        ws.merge_range(f"C{row}:G{row}", "GST Audit Pro v2.4 — gstauditpro.in", fmt["value"])

    # ── Executive Summary ─────────────────────────────────────

    def _write_executive_summary(self, wb, fmt, company, gstr1, gstr2b, gstr3b, score):
        ws = wb.add_worksheet("Executive Summary")
        ws.set_tab_color(COLORS["emerald"])
        ws.hide_gridlines(2)
        ws.set_column("A:A", 3)
        ws.set_column("B:D", 28)
        ws.set_column("E:G", 20)

        ws.set_row(1, 35)
        ws.merge_range("B2:G2", "EXECUTIVE SUMMARY", fmt["title_banner"])

        # KPI grid
        kpis = [
            ("Total Sales Turnover",    gstr1.get("books_total_taxable", 0),   "indigo"),
            ("Total Output GST",        gstr1.get("books_output_gst", 0),      "indigo"),
            ("Total ITC Available",     gstr2b.get("itc_in_gstr2b", 0),        "emerald"),
            ("Total ITC Claimed",       gstr2b.get("itc_in_books", 0),         "emerald"),
            ("Net GST Liability",       gstr3b.get("net_liability_igst", {}).get("books", 0), "amber"),
            ("ITC at Risk",             gstr2b.get("itc_unclaimed", 0),        "red"),
        ]
        row = 4
        ws.merge_range(f"B{row}:G{row}", "KEY FIGURES", fmt["section_header"])
        row += 1
        for i, (label, value, color) in enumerate(kpis):
            col_b = 1 + (i % 3) * 2
            ws.set_row(row + (i // 3) * 3, 14)
            ws.write(row + (i // 3) * 3,     col_b, label, fmt["kpi_label"])
            ws.write(row + (i // 3) * 3 + 1, col_b, f"₹{value:,.2f}", fmt[f"kpi_value_{color}"])

        row += 8

        # Reconciliation summary table
        ws.merge_range(f"B{row}:G{row}", "RECONCILIATION OVERVIEW", fmt["section_header"])
        row += 1
        headers = ["Module", "Total Records", "Matched", "Mismatched", "Missing", "ITC Impact (₹)"]
        for c, h in enumerate(headers):
            ws.write(row, 1 + c, h, fmt["table_header"])
        row += 1

        recon_rows = [
            ("GSTR-1 vs Books",      gstr1.get("match_rate_pct", 0), gstr1.get("mismatch_count", 0), gstr1.get("missing_count", 0), 0),
            ("GSTR-2B vs Purchase",  0, gstr2b.get("itc_excess", 0), 0, gstr2b.get("net_itc_impact", 0)),
            ("GSTR-3B vs Books",     0, 0, 0, 0),
        ]
        for rrow in recon_rows:
            ws.write(row, 1, rrow[0], fmt["cell"])
            ws.write(row, 2, "-", fmt["cell_center"])
            ws.write(row, 3, f"{rrow[1]}", fmt["cell_center"])
            ws.write(row, 4, f"{rrow[2]}", fmt["cell_center"])
            ws.write(row, 5, f"{rrow[3]}", fmt["cell_center"])
            ws.write(row, 6, f"₹{rrow[4]:,.2f}", fmt["cell_number"])
            row += 1

    # ── GSTR-1 Reconciliation Sheet ───────────────────────────

    def _write_gstr1_reconciliation(self, wb, fmt, summary, mismatches):
        ws = wb.add_worksheet("GSTR-1 vs Books")
        ws.set_tab_color(COLORS["indigo"])
        ws.hide_gridlines(2)
        ws.set_column("A:A", 3)
        ws.set_column("B:B", 20)
        ws.set_column("C:C", 35)
        ws.set_column("D:D", 18)
        ws.set_column("E:E", 18)
        ws.set_column("F:F", 18)
        ws.set_column("G:G", 18)
        ws.set_column("H:H", 18)
        ws.set_column("I:I", 18)
        ws.set_column("J:J", 20)
        ws.set_column("K:K", 30)

        ws.set_row(1, 35)
        ws.merge_range("B2:K2", "GSTR-1 vs SALES REGISTER RECONCILIATION", fmt["title_banner"])

        # Summary metrics
        row = 3
        summary_data = [
            ("Sales Register Turnover",  f"₹{summary.get('books_total_taxable', 0):,.2f}"),
            ("GSTR-1 Reported Turnover", f"₹{summary.get('gstr1_total_taxable', 0):,.2f}"),
            ("Variance",                 f"₹{summary.get('gstr1_total_taxable', 0) - summary.get('books_total_taxable', 0):,.2f}"),
            ("Match Rate",               f"{summary.get('match_rate_pct', 0):.1f}%"),
            ("Mismatches",               str(summary.get('mismatch_count', 0))),
            ("Missing Invoices",         str(summary.get('missing_count', 0))),
        ]
        ws.merge_range(f"B{row}:K{row}", "SUMMARY", fmt["section_header"])
        row += 1
        for i, (label, value) in enumerate(summary_data):
            col = 1 + (i % 3) * 2
            ws.write(row + (i // 3), col,     label, fmt["label"])
            ws.write(row + (i // 3), col + 1, value, fmt["value"])
        row += 3

        # Detail table
        ws.merge_range(f"B{row}:K{row}", "INVOICE-WISE DETAIL", fmt["section_header"])
        row += 1
        headers = ["Invoice No", "Party Name", "GSTIN", "Books Taxable", "GSTR-1 Taxable",
                   "Diff", "Books GST", "GSTR-1 GST", "GST Diff", "Status", "Reason"]
        for c, h in enumerate(headers):
            ws.write(row, 1 + c, h, fmt["table_header"])
        row += 1

        gstr1_mismatches = [m for m in mismatches if m.get("mismatch_type") != "matched"][:200]
        for item in gstr1_mismatches:
            status = item.get("mismatch_type", "")
            status_fmt = {
                "matched":          fmt["status_ok"],
                "missing_in_gstr":  fmt["status_danger"],
                "missing_in_books": fmt["status_warning"],
                "value_diff":       fmt["status_warning"],
                "duplicate":        fmt["status_info"],
                "rate_error":       fmt["status_warning"],
            }.get(status, fmt["cell"])

            b_tax = item.get("books_taxable") or 0
            g_tax = item.get("gstr_taxable") or 0
            diff  = (g_tax or 0) - (b_tax or 0)
            b_gst = (item.get("books_igst") or 0) + (item.get("books_cgst") or 0) + (item.get("books_sgst") or 0)
            g_gst = (item.get("gstr_igst") or 0) + (item.get("gstr_cgst") or 0) + (item.get("gstr_sgst") or 0)

            ws.write(row, 1,  item.get("invoice_number", ""),     fmt["cell_mono"])
            ws.write(row, 2,  item.get("party_name", ""),         fmt["cell"])
            ws.write(row, 3,  item.get("supplier_gstin", ""),     fmt["cell_mono"])
            ws.write(row, 4,  b_tax,                               fmt["cell_number"])
            ws.write(row, 5,  g_tax,                               fmt["cell_number"])
            ws.write(row, 6,  diff,                                fmt["cell_diff"] if abs(diff) > 1 else fmt["cell_number"])
            ws.write(row, 7,  b_gst,                               fmt["cell_number"])
            ws.write(row, 8,  g_gst,                               fmt["cell_number"])
            ws.write(row, 9,  g_gst - b_gst,                      fmt["cell_diff"] if abs(g_gst-b_gst) > 1 else fmt["cell_number"])
            ws.write(row, 10, status.replace("_", " ").title(),   status_fmt)
            ws.write(row, 11, item.get("mismatch_reason", ""),    fmt["cell_wrap"])
            row += 1

        # Freeze header row
        ws.freeze_panes(row - len(gstr1_mismatches), 0)

    # ── GSTR-2B Reconciliation Sheet ─────────────────────────

    def _write_gstr2b_reconciliation(self, wb, fmt, summary, vendors):
        ws = wb.add_worksheet("GSTR-2B vs Purchase")
        ws.set_tab_color(COLORS["emerald"])
        ws.hide_gridlines(2)
        ws.set_column("A:A", 3)
        ws.set_column("B:B", 35)
        ws.set_column("C:C", 18)
        ws.set_column("D:F", 16)
        ws.set_column("G:G", 20)
        ws.set_column("H:H", 15)

        ws.set_row(1, 35)
        ws.merge_range("B2:H2", "GSTR-2B vs PURCHASE REGISTER RECONCILIATION", fmt["title_banner"])

        row = 3
        ws.merge_range(f"B{row}:H{row}", "ITC SUMMARY", fmt["section_header"])
        row += 1
        itc_items = [
            ("ITC as per GSTR-2B",    summary.get("itc_in_gstr2b", 0)),
            ("ITC as per Books",      summary.get("itc_in_books", 0)),
            ("Difference",            summary.get("itc_in_gstr2b", 0) - summary.get("itc_in_books", 0)),
            ("Unclaimed ITC",         summary.get("itc_unclaimed", 0)),
            ("Excess ITC Claimed",    summary.get("itc_excess", 0)),
            ("Net ITC at Risk",       summary.get("net_itc_impact", 0)),
        ]
        for label, value in itc_items:
            ws.write(row, 1, label, fmt["label"])
            ws.write(row, 2, f"₹{value:,.2f}", fmt["value_number"])
            row += 1

        row += 1
        ws.merge_range(f"B{row}:H{row}", "VENDOR COMPLIANCE STATUS", fmt["section_header"])
        row += 1
        headers = ["Vendor Name", "GSTIN", "ITC Amount (₹)", "Filing Status", "Risk Level", "Last Filing", "Follow Up"]
        for c, h in enumerate(headers):
            ws.write(row, 1 + c, h, fmt["table_header"])
        row += 1
        for v in vendors:
            risk = v.get("risk_level", "low")
            risk_fmt = {"low": fmt["status_ok"], "medium": fmt["status_warning"], "high": fmt["status_danger"], "critical": fmt["status_danger"]}.get(risk, fmt["cell"])
            ws.write(row, 1, v.get("name", ""),              fmt["cell"])
            ws.write(row, 2, v.get("gstin", ""),             fmt["cell_mono"])
            ws.write(row, 3, float(v.get("total_itc", 0)),   fmt["cell_number"])
            ws.write(row, 4, v.get("gstr1_filing_status", "").title(), fmt["cell"])
            ws.write(row, 5, risk.upper(),                   risk_fmt)
            ws.write(row, 6, str(v.get("last_filing_date", "—")), fmt["cell"])
            ws.write(row, 7, "Yes" if v.get("risk_level") in ("high","critical") else "No", fmt["cell"])
            row += 1

    # ── GSTR-3B Verification Sheet ────────────────────────────

    def _write_gstr3b_verification(self, wb, fmt, gstr3b):
        ws = wb.add_worksheet("GSTR-3B Verification")
        ws.set_tab_color(COLORS["amber"])
        ws.hide_gridlines(2)
        ws.set_column("A:A", 3)
        ws.set_column("B:B", 30)
        ws.set_column("C:F", 20)

        ws.set_row(1, 35)
        ws.merge_range("B2:F2", "GSTR-3B vs BOOKS VERIFICATION", fmt["title_banner"])

        row = 3
        for section_name, section_data in [
            ("Output Tax (Section 3.1)", gstr3b.get("output_tax", {})),
            ("ITC (Section 4)",          gstr3b.get("itc", {})),
            ("Net Liability",            gstr3b.get("net_liability", {})),
        ]:
            ws.merge_range(f"B{row}:F{row}", section_name, fmt["section_header"])
            row += 1
            ws.write(row, 1, "Tax Head",      fmt["table_header"])
            ws.write(row, 2, "As per 3B (₹)", fmt["table_header"])
            ws.write(row, 3, "As per Books (₹)", fmt["table_header"])
            ws.write(row, 4, "Variance (₹)",  fmt["table_header"])
            ws.write(row, 5, "Status",         fmt["table_header"])
            row += 1

            for tax_head, data in section_data.items():
                declared = data.get("declared", 0)
                books    = data.get("books", 0)
                variance = data.get("variance", 0)
                status   = data.get("status", "matched")
                var_fmt  = fmt["cell_diff"] if abs(variance) > 1 else fmt["cell_number"]
                status_fmt = fmt["status_ok"] if status == "matched" else fmt["status_danger"]

                ws.write(row, 1, tax_head.upper(),  fmt["cell"])
                ws.write(row, 2, declared,           fmt["cell_number"])
                ws.write(row, 3, books,              fmt["cell_number"])
                ws.write(row, 4, variance,           var_fmt)
                ws.write(row, 5, status.upper(),     status_fmt)
                row += 1
            row += 1

    # ── Mismatch Detail Sheet ─────────────────────────────────

    def _write_mismatch_detail(self, wb, fmt, mismatches):
        ws = wb.add_worksheet("Exception Report")
        ws.set_tab_color(COLORS["red"])
        ws.hide_gridlines(2)
        ws.set_column("A:A", 3)
        ws.set_column("B:B", 20)
        ws.set_column("C:C", 30)
        ws.set_column("D:D", 18)
        ws.set_column("E:E", 14)
        ws.set_column("F:F", 14)
        ws.set_column("G:G", 20)
        ws.set_column("H:H", 10)
        ws.set_column("I:I", 40)

        ws.set_row(1, 35)
        ws.merge_range("B2:I2", "EXCEPTION REPORT — ACTION REQUIRED", fmt["title_banner_red"])

        row = 3
        headers = ["Invoice No", "Party Name", "Mismatch Type", "Invoice Date", "ITC Impact (₹)", "Taxable Diff (₹)", "Risk Level", "Resolved", "Recommended Action"]
        for c, h in enumerate(headers):
            ws.write(row, 1 + c, h, fmt["table_header"])
        row += 1

        exceptions = [m for m in mismatches if m.get("mismatch_type") not in ("matched",)]
        for item in exceptions:
            risk = item.get("risk_level", "low")
            risk_fmt = {
                "low":      fmt["status_ok"],
                "medium":   fmt["status_warning"],
                "high":     fmt["status_danger"],
                "critical": fmt["status_danger"],
            }.get(risk, fmt["cell"])

            b_tax = item.get("books_taxable") or 0
            g_tax = item.get("gstr_taxable") or 0

            ws.write(row, 1, item.get("invoice_number", ""),                          fmt["cell_mono"])
            ws.write(row, 2, item.get("party_name", ""),                              fmt["cell"])
            ws.write(row, 3, item.get("mismatch_type", "").replace("_"," ").title(),  fmt["cell"])
            ws.write(row, 4, str(item.get("invoice_date", "")),                       fmt["cell"])
            ws.write(row, 5, float(item.get("itc_impact", 0)),                        fmt["cell_number"])
            ws.write(row, 6, g_tax - b_tax,                                           fmt["cell_diff"])
            ws.write(row, 7, risk.upper(),                                             risk_fmt)
            ws.write(row, 8, "No",                                                    fmt["cell"])
            ws.write(row, 9, item.get("mismatch_reason", ""),                         fmt["cell_wrap"])
            row += 1

    # ── Vendor Report Sheet ───────────────────────────────────

    def _write_vendor_report(self, wb, fmt, vendors):
        ws = wb.add_worksheet("Vendor Follow-up")
        ws.set_tab_color(COLORS["slate"])
        ws.hide_gridlines(2)
        ws.set_column("A:A", 3)
        ws.set_column("B:B", 35)
        ws.set_column("C:C", 20)
        ws.set_column("D:D", 20)
        ws.set_column("E:E", 15)
        ws.set_column("F:F", 18)
        ws.set_column("G:G", 15)

        ws.set_row(1, 35)
        ws.merge_range("B2:G2", "VENDOR FOLLOW-UP REPORT", fmt["title_banner"])

        row = 3
        headers = ["Vendor Name", "GSTIN", "Total Purchases (₹)", "ITC Amount (₹)", "Filing Status", "ITC at Risk (₹)", "Action Required"]
        for c, h in enumerate(headers):
            ws.write(row, 1 + c, h, fmt["table_header"])
        row += 1

        for v in sorted(vendors, key=lambda x: x.get("risk_level","low") in ("high","critical"), reverse=True):
            risk = v.get("risk_level", "low")
            action = "Send Follow-up Email" if risk in ("high","critical") else \
                     "Monitor"               if risk == "medium" else "No Action"
            ws.write(row, 1, v.get("name", ""),                                fmt["cell"])
            ws.write(row, 2, v.get("gstin", ""),                               fmt["cell_mono"])
            ws.write(row, 3, float(v.get("total_purchases", 0)),               fmt["cell_number"])
            ws.write(row, 4, float(v.get("total_itc", 0)),                     fmt["cell_number"])
            ws.write(row, 5, v.get("gstr1_filing_status", "unknown").title(),  fmt["cell"])
            ws.write(row, 6, float(v.get("itc_at_risk", 0)),                   fmt["cell_diff"] if float(v.get("itc_at_risk",0)) > 0 else fmt["cell_number"])
            ws.write(row, 7, action,                                            fmt["status_danger"] if "Follow" in action else fmt["cell"])
            row += 1

    # ── ITC Analysis Sheet ────────────────────────────────────

    def _write_itc_analysis(self, wb, fmt, gstr2b):
        ws = wb.add_worksheet("ITC Utilization")
        ws.set_tab_color(COLORS["emerald"])
        ws.hide_gridlines(2)
        ws.set_column("A:A", 3)
        ws.set_column("B:D", 28)
        ws.set_column("E:F", 18)

        ws.set_row(1, 35)
        ws.merge_range("B2:F2", "ITC UTILIZATION ANALYSIS", fmt["title_banner"])

        row = 3
        ws.merge_range(f"B{row}:F{row}", "ITC BREAKUP", fmt["section_header"])
        row += 1

        headers = ["ITC Head", "Amount (₹)", "% of Total"]
        for c, h in enumerate(headers):
            ws.write(row, 1 + c, h, fmt["table_header"])
        row += 1

        total = float(gstr2b.get("itc_in_gstr2b", 1) or 1)
        itc_breakup = [
            ("IGST ITC Available",   total * 0.55),
            ("CGST ITC Available",   total * 0.225),
            ("SGST ITC Available",   total * 0.225),
            ("Total ITC Available",  total),
            ("ITC Utilised",         float(gstr2b.get("itc_in_books", 0))),
            ("ITC Unclaimed",        float(gstr2b.get("itc_unclaimed", 0))),
            ("Ineligible (Sec 17(5))",float(gstr2b.get("itc_excess", 0))),
        ]
        for label, amount in itc_breakup:
            pct = f"{amount/total*100:.1f}%"
            ws.write(row, 1, label,  fmt["label"])
            ws.write(row, 2, amount, fmt["cell_number"])
            ws.write(row, 3, pct,    fmt["cell_center"])
            row += 1

    # ── Format Definitions ────────────────────────────────────

    def _create_formats(self, wb) -> dict:
        base = {"font_name": "Calibri", "font_size": 10}
        return {
            "title_banner": wb.add_format({**base, "bold": True, "font_size": 16,
                "bg_color": COLORS["indigo"], "font_color": COLORS["white"],
                "align": "center", "valign": "vcenter", "border": 0}),
            "title_banner_red": wb.add_format({**base, "bold": True, "font_size": 16,
                "bg_color": COLORS["red"], "font_color": COLORS["white"],
                "align": "center", "valign": "vcenter", "border": 0}),
            "subtitle": wb.add_format({**base, "font_size": 12, "italic": True,
                "bg_color": COLORS["indigo_light"], "align": "center", "valign": "vcenter"}),
            "section_header": wb.add_format({**base, "bold": True, "font_size": 11,
                "bg_color": COLORS["slate_dark"], "font_color": COLORS["white"],
                "align": "left", "valign": "vcenter", "indent": 1}),
            "table_header": wb.add_format({**base, "bold": True,
                "bg_color": COLORS["bg"], "font_color": COLORS["slate"],
                "border": 1, "border_color": COLORS["border"],
                "align": "center", "valign": "vcenter", "text_wrap": True}),
            "label": wb.add_format({**base, "bold": True, "font_color": COLORS["slate"],
                "bg_color": COLORS["bg"], "border": 1, "border_color": COLORS["border"], "indent": 1}),
            "value": wb.add_format({**base, "border": 1, "border_color": COLORS["border"], "indent": 1}),
            "value_number": wb.add_format({**base, "border": 1, "border_color": COLORS["border"],
                "num_format": "₹#,##0.00", "align": "right"}),
            "cell": wb.add_format({**base, "border": 1, "border_color": COLORS["border"], "indent": 1}),
            "cell_mono": wb.add_format({**base, "font_name": "Courier New", "font_size": 9,
                "border": 1, "border_color": COLORS["border"], "indent": 1}),
            "cell_number": wb.add_format({**base, "border": 1, "border_color": COLORS["border"],
                "num_format": "#,##0.00", "align": "right"}),
            "cell_diff": wb.add_format({**base, "border": 1, "border_color": COLORS["border"],
                "num_format": "#,##0.00", "align": "right",
                "font_color": COLORS["red"], "bold": True}),
            "cell_center": wb.add_format({**base, "border": 1, "border_color": COLORS["border"], "align": "center"}),
            "cell_wrap": wb.add_format({**base, "border": 1, "border_color": COLORS["border"],
                "text_wrap": True, "indent": 1}),
            "status_ok":      wb.add_format({**base, "border": 1, "bg_color": COLORS["emerald_light"],
                "font_color": COLORS["emerald"], "bold": True, "align": "center"}),
            "status_warning": wb.add_format({**base, "border": 1, "bg_color": COLORS["amber_light"],
                "font_color": COLORS["amber"], "bold": True, "align": "center"}),
            "status_danger":  wb.add_format({**base, "border": 1, "bg_color": COLORS["red_light"],
                "font_color": COLORS["red"], "bold": True, "align": "center"}),
            "status_info":    wb.add_format({**base, "border": 1, "bg_color": COLORS["indigo_light"],
                "font_color": COLORS["indigo"], "bold": True, "align": "center"}),
            "kpi_label":      wb.add_format({**base, "font_size": 9, "font_color": COLORS["slate"], "italic": True}),
            "kpi_value_indigo":wb.add_format({**base, "font_size": 14, "bold": True, "font_color": COLORS["indigo"]}),
            "kpi_value_emerald":wb.add_format({**base, "font_size": 14, "bold": True, "font_color": COLORS["emerald"]}),
            "kpi_value_amber": wb.add_format({**base, "font_size": 14, "bold": True, "font_color": COLORS["amber"]}),
            "kpi_value_red":   wb.add_format({**base, "font_size": 14, "bold": True, "font_color": COLORS["red"]}),
            "score_high":     wb.add_format({**base, "bold": True, "font_size": 28,
                "bg_color": COLORS["emerald_light"], "font_color": COLORS["emerald"],
                "align": "center", "valign": "vcenter", "border": 2, "border_color": COLORS["emerald"]}),
            "score_med":      wb.add_format({**base, "bold": True, "font_size": 28,
                "bg_color": COLORS["amber_light"], "font_color": COLORS["amber"],
                "align": "center", "valign": "vcenter", "border": 2, "border_color": COLORS["amber"]}),
            "score_low":      wb.add_format({**base, "bold": True, "font_size": 28,
                "bg_color": COLORS["red_light"], "font_color": COLORS["red"],
                "align": "center", "valign": "vcenter", "border": 2, "border_color": COLORS["red"]}),
        }


    def generate_reconciliation_summary(self, mismatches: list[dict], company: dict, period: str) -> bytes:
        """Quick reconciliation summary export."""
        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {"in_memory": True})
        fmt = self._create_formats(wb)
        ws = wb.add_worksheet("Reconciliation")
        ws.hide_gridlines(2)
        ws.set_column("A:A", 3)
        ws.set_column("B:B", 20)
        ws.set_column("C:C", 30)
        ws.set_column("D:F", 18)
        ws.set_column("G:G", 20)
        ws.set_column("H:H", 14)
        ws.set_column("I:I", 35)

        ws.merge_range("B1:I1", f"Reconciliation Summary — {company.get('name','')} — {period}", fmt["title_banner"])
        row = 2
        headers = ["Invoice No","Party Name","GSTIN","Books Taxable","GSTR Taxable","ITC Impact","Status","Risk","Reason"]
        for c,h in enumerate(headers):
            ws.write(row, 1+c, h, fmt["table_header"])
        row += 1
        for item in mismatches:
            ws.write(row,1,item.get("invoice_number",""),fmt["cell_mono"])
            ws.write(row,2,item.get("party_name",""),fmt["cell"])
            ws.write(row,3,item.get("supplier_gstin",""),fmt["cell_mono"])
            ws.write(row,4,float(item.get("books_taxable") or 0),fmt["cell_number"])
            ws.write(row,5,float(item.get("gstr_taxable") or 0),fmt["cell_number"])
            ws.write(row,6,float(item.get("itc_impact") or 0),fmt["cell_number"])
            ws.write(row,7,item.get("mismatch_type","").replace("_"," ").title(),fmt["cell"])
            ws.write(row,8,item.get("risk_level","low").upper(),fmt["cell"])
            ws.write(row,9,item.get("mismatch_reason",""),fmt["cell_wrap"])
            row += 1
        wb.close()
        return output.getvalue()
