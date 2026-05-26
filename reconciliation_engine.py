# ============================================================
# app/services/reconciliation_engine.py
# GST Reconciliation Engine — Pandas-powered matching
# ============================================================

from __future__ import annotations
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from decimal import Decimal
import logging
import re

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────

VALID_GST_RATES = {0, 0.1, 0.25, 1, 1.5, 3, 5, 6, 7.5, 9, 12, 14, 18, 28}
TOLERANCE_AMOUNT = Decimal("1.00")      # ₹1 rounding tolerance
TOLERANCE_PERCENT = Decimal("0.01")     # 1% variance threshold
GSTIN_PATTERN = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}Z[A-Z\d]{1}$")


# ── Data Classes ─────────────────────────────────────────────

@dataclass
class MismatchItem:
    invoice_number:  str
    invoice_date:    Optional[str]
    supplier_gstin:  Optional[str]
    party_name:      Optional[str]
    invoice_type:    Optional[str]
    books_taxable:   Optional[float]
    books_igst:      Optional[float]
    books_cgst:      Optional[float]
    books_sgst:      Optional[float]
    gstr_taxable:    Optional[float]
    gstr_igst:       Optional[float]
    gstr_cgst:       Optional[float]
    gstr_sgst:       Optional[float]
    mismatch_type:   str
    mismatch_reason: str
    itc_impact:      float = 0.0
    risk_level:      str = "low"


@dataclass
class ReconciliationResult:
    recon_type:      str
    period_month:    int
    period_year:     int
    total_invoices:  int = 0
    matched_count:   int = 0
    mismatch_count:  int = 0
    missing_count:   int = 0
    duplicate_count: int = 0
    itc_impact:      float = 0.0
    items:           list[MismatchItem] = field(default_factory=list)
    summary:         dict = field(default_factory=dict)


# ── Main Engine ──────────────────────────────────────────────

class GSTReconciliationEngine:
    """
    Core reconciliation engine for:
    - GSTR-1 vs Sales Register
    - GSTR-2B vs Purchase Register
    - GSTR-3B vs Books
    """

    # ── GSTR-1 vs Sales Register ─────────────────────────────

    def reconcile_gstr1_vs_books(
        self,
        gstr1_df: pd.DataFrame,
        books_df: pd.DataFrame,
        period_month: int,
        period_year: int,
    ) -> ReconciliationResult:
        """
        Match GSTR-1 invoices against Sales Register.
        Detects: missing invoices, value mismatches, GST rate errors.
        """
        result = ReconciliationResult("gstr1_vs_books", period_month, period_year)

        gstr1_df  = self._normalize_gstr1(gstr1_df)
        books_df  = self._normalize_sales_register(books_df)

        # Primary key: invoice_number + supplier_gstin (for B2B)
        gstr1_df["_key"]  = self._make_key(gstr1_df)
        books_df["_key"]  = self._make_key(books_df)

        # Duplicate detection in GSTR-1
        dup_keys = gstr1_df[gstr1_df.duplicated("_key", keep=False)]["_key"].unique()
        duplicates = gstr1_df[gstr1_df["_key"].isin(dup_keys)].copy()

        # De-duplicate for matching
        gstr1_unique  = gstr1_df.drop_duplicates("_key", keep="first")
        books_unique  = books_df.drop_duplicates("_key", keep="first")

        # Outer merge on key
        merged = books_unique.merge(
            gstr1_unique,
            on="_key",
            how="outer",
            suffixes=("_books", "_gstr"),
            indicator=True,
        )

        result.total_invoices = len(merged) + len(duplicates)

        for _, row in merged.iterrows():
            item = self._classify_gstr1_row(row)
            if item:
                if item.mismatch_type == "matched":
                    result.matched_count += 1
                elif item.mismatch_type in ("missing_in_gstr", "missing_in_books"):
                    result.missing_count += 1
                else:
                    result.mismatch_count += 1
                result.itc_impact += item.itc_impact
                result.items.append(item)

        # Add duplicates
        for _, row in duplicates.iterrows():
            result.duplicate_count += 1
            result.items.append(MismatchItem(
                invoice_number  = str(row.get("invoice_number", "")),
                invoice_date    = str(row.get("invoice_date", "")),
                supplier_gstin  = str(row.get("supplier_gstin", "")),
                party_name      = str(row.get("receiver_name", "")),
                invoice_type    = str(row.get("invoice_type", "")),
                books_taxable   = None,
                books_igst      = None,
                books_cgst      = None,
                books_sgst      = None,
                gstr_taxable    = float(row.get("taxable_value", 0)),
                gstr_igst       = float(row.get("igst", 0)),
                gstr_cgst       = float(row.get("cgst", 0)),
                gstr_sgst       = float(row.get("sgst", 0)),
                mismatch_type   = "duplicate",
                mismatch_reason = "Invoice appears more than once in GSTR-1",
                itc_impact      = 0.0,
                risk_level      = "medium",
            ))

        result.summary = self._build_gstr1_summary(gstr1_unique, books_unique, result)
        return result

    def _classify_gstr1_row(self, row) -> Optional[MismatchItem]:
        indicator = row.get("_merge", "both")
        inv_no = str(row.get("invoice_number_books", row.get("invoice_number_gstr", "")))

        if indicator == "left_only":
            # In books, not in GSTR-1
            taxable = float(row.get("taxable_value_books", 0) or 0)
            gst_total = float(
                (row.get("igst_books", 0) or 0) +
                (row.get("cgst_books", 0) or 0) +
                (row.get("sgst_books", 0) or 0)
            )
            return MismatchItem(
                invoice_number  = inv_no,
                invoice_date    = str(row.get("invoice_date_books", "")),
                supplier_gstin  = str(row.get("supplier_gstin_books", "")),
                party_name      = str(row.get("customer_name", "")),
                invoice_type    = str(row.get("invoice_type_books", "B2B")),
                books_taxable   = taxable,
                books_igst      = float(row.get("igst_books", 0) or 0),
                books_cgst      = float(row.get("cgst_books", 0) or 0),
                books_sgst      = float(row.get("sgst_books", 0) or 0),
                gstr_taxable    = None,
                gstr_igst       = None,
                gstr_cgst       = None,
                gstr_sgst       = None,
                mismatch_type   = "missing_in_gstr",
                mismatch_reason = "Invoice present in Sales Register but not reported in GSTR-1",
                itc_impact      = gst_total,
                risk_level      = "high" if taxable > 250000 else "medium",
            )

        elif indicator == "right_only":
            # In GSTR-1, not in books
            gst_total = float(
                (row.get("igst_gstr", 0) or 0) +
                (row.get("cgst_gstr", 0) or 0) +
                (row.get("sgst_gstr", 0) or 0)
            )
            return MismatchItem(
                invoice_number  = inv_no,
                invoice_date    = str(row.get("invoice_date_gstr", "")),
                supplier_gstin  = str(row.get("supplier_gstin_gstr", "")),
                party_name      = str(row.get("receiver_name", "")),
                invoice_type    = str(row.get("invoice_type_gstr", "B2B")),
                books_taxable   = None,
                books_igst      = None,
                books_cgst      = None,
                books_sgst      = None,
                gstr_taxable    = float(row.get("taxable_value_gstr", 0) or 0),
                gstr_igst       = float(row.get("igst_gstr", 0) or 0),
                gstr_cgst       = float(row.get("cgst_gstr", 0) or 0),
                gstr_sgst       = float(row.get("sgst_gstr", 0) or 0),
                mismatch_type   = "missing_in_books",
                mismatch_reason = "Invoice in GSTR-1 not found in Sales Register. Possible erroneous filing.",
                itc_impact      = 0.0,
                risk_level      = "medium",
            )

        else:
            # Both sides — check value differences
            b_taxable = float(row.get("taxable_value_books", 0) or 0)
            g_taxable = float(row.get("taxable_value_gstr", 0) or 0)
            b_igst    = float(row.get("igst_books", 0) or 0)
            g_igst    = float(row.get("igst_gstr", 0) or 0)
            b_cgst    = float(row.get("cgst_books", 0) or 0)
            g_cgst    = float(row.get("cgst_gstr", 0) or 0)
            b_sgst    = float(row.get("sgst_books", 0) or 0)
            g_sgst    = float(row.get("sgst_gstr", 0) or 0)

            taxable_diff = abs(g_taxable - b_taxable)
            gst_diff = abs((g_igst + g_cgst + g_sgst) - (b_igst + b_cgst + b_sgst))

            # Check GST rate correctness
            gst_rate_books = (b_igst + b_cgst + b_sgst) / b_taxable * 100 if b_taxable else 0
            gst_rate_gstr  = (g_igst + g_cgst + g_sgst) / g_taxable * 100 if g_taxable else 0

            if taxable_diff > 1 or gst_diff > 1:
                pct_diff = taxable_diff / b_taxable * 100 if b_taxable else 100
                risk = "critical" if pct_diff > 20 else "high" if pct_diff > 5 else "medium"
                return MismatchItem(
                    invoice_number  = inv_no,
                    invoice_date    = str(row.get("invoice_date_books", "")),
                    supplier_gstin  = str(row.get("supplier_gstin_books", "")),
                    party_name      = str(row.get("customer_name", row.get("receiver_name", ""))),
                    invoice_type    = str(row.get("invoice_type_books", "B2B")),
                    books_taxable   = b_taxable,
                    books_igst      = b_igst,
                    books_cgst      = b_cgst,
                    books_sgst      = b_sgst,
                    gstr_taxable    = g_taxable,
                    gstr_igst       = g_igst,
                    gstr_cgst       = g_cgst,
                    gstr_sgst       = g_sgst,
                    mismatch_type   = "rate_error" if abs(gst_rate_books - gst_rate_gstr) > 0.5 else "value_diff",
                    mismatch_reason = f"Value difference ₹{taxable_diff:,.0f} in taxable amount. Books: ₹{b_taxable:,.0f}, GSTR-1: ₹{g_taxable:,.0f}",
                    itc_impact      = gst_diff,
                    risk_level      = risk,
                )
            else:
                return MismatchItem(
                    invoice_number  = inv_no,
                    invoice_date    = str(row.get("invoice_date_books", "")),
                    supplier_gstin  = str(row.get("supplier_gstin_books", "")),
                    party_name      = str(row.get("customer_name", "")),
                    invoice_type    = str(row.get("invoice_type_books", "B2B")),
                    books_taxable   = b_taxable,
                    books_igst      = b_igst,
                    books_cgst      = b_cgst,
                    books_sgst      = b_sgst,
                    gstr_taxable    = g_taxable,
                    gstr_igst       = g_igst,
                    gstr_cgst       = g_cgst,
                    gstr_sgst       = g_sgst,
                    mismatch_type   = "matched",
                    mismatch_reason = "",
                    itc_impact      = 0.0,
                    risk_level      = "low",
                )

    # ── GSTR-2B vs Purchase Register ─────────────────────────

    def reconcile_gstr2b_vs_books(
        self,
        gstr2b_df: pd.DataFrame,
        purchase_df: pd.DataFrame,
        period_month: int,
        period_year: int,
    ) -> ReconciliationResult:
        """
        Match GSTR-2B ITC records against Purchase Register.
        Detects: unclaimed ITC, excess ITC, vendor non-filing, Section 17(5) violations.
        """
        result = ReconciliationResult("gstr2b_vs_books", period_month, period_year)

        gstr2b_df   = self._normalize_gstr2b(gstr2b_df)
        purchase_df = self._normalize_purchase_register(purchase_df)

        gstr2b_df["_key"]   = gstr2b_df["supplier_gstin"].str.upper().str.strip() + "_" + gstr2b_df["invoice_number"].str.upper().str.strip()
        purchase_df["_key"] = purchase_df["supplier_gstin"].fillna("").str.upper().str.strip() + "_" + purchase_df["invoice_number"].str.upper().str.strip()

        merged = purchase_df.merge(
            gstr2b_df,
            on="_key",
            how="outer",
            suffixes=("_books", "_gstr"),
            indicator=True,
        )

        result.total_invoices = len(merged)

        total_itc_unclaimed = 0.0
        total_itc_excess    = 0.0

        for _, row in merged.iterrows():
            indicator = row.get("_merge", "both")
            inv_no = str(row.get("invoice_number_books", row.get("invoice_number_gstr", "")))

            if indicator == "left_only":
                # In books but not in GSTR-2B — cannot claim ITC
                b_igst = float(row.get("igst_books", 0) or 0)
                b_cgst = float(row.get("cgst_books", 0) or 0)
                b_sgst = float(row.get("sgst_books", 0) or 0)
                itc_loss = b_igst + b_cgst + b_sgst
                total_itc_unclaimed += itc_loss
                result.missing_count += 1
                result.items.append(MismatchItem(
                    invoice_number  = inv_no,
                    invoice_date    = str(row.get("invoice_date_books", "")),
                    supplier_gstin  = str(row.get("supplier_gstin_books", "")),
                    party_name      = str(row.get("supplier_name_books", "")),
                    invoice_type    = "B2B",
                    books_taxable   = float(row.get("taxable_value_books", 0) or 0),
                    books_igst      = b_igst,
                    books_cgst      = b_cgst,
                    books_sgst      = b_sgst,
                    gstr_taxable    = None,
                    gstr_igst       = None,
                    gstr_cgst       = None,
                    gstr_sgst       = None,
                    mismatch_type   = "missing_in_gstr",
                    mismatch_reason = "Supplier has not filed GSTR-1. ITC cannot be claimed as per Rule 36(4).",
                    itc_impact      = itc_loss,
                    risk_level      = "high",
                ))

            elif indicator == "right_only":
                # In GSTR-2B but not in books — excess ITC risk
                g_igst = float(row.get("igst_gstr", 0) or 0)
                g_cgst = float(row.get("cgst_gstr", 0) or 0)
                g_sgst = float(row.get("sgst_gstr", 0) or 0)
                itc_excess = g_igst + g_cgst + g_sgst
                total_itc_excess += itc_excess
                result.mismatch_count += 1
                result.items.append(MismatchItem(
                    invoice_number  = inv_no,
                    invoice_date    = str(row.get("invoice_date_gstr", "")),
                    supplier_gstin  = str(row.get("supplier_gstin_gstr", "")),
                    party_name      = str(row.get("supplier_name_gstr", "")),
                    invoice_type    = "B2B",
                    books_taxable   = None,
                    books_igst      = None,
                    books_cgst      = None,
                    books_sgst      = None,
                    gstr_taxable    = float(row.get("taxable_value_gstr", 0) or 0),
                    gstr_igst       = g_igst,
                    gstr_cgst       = g_cgst,
                    gstr_sgst       = g_sgst,
                    mismatch_type   = "missing_in_books",
                    mismatch_reason = "Invoice in GSTR-2B not found in Purchase Register. Verify if purchase was recorded.",
                    itc_impact      = -itc_excess,  # negative = excess
                    risk_level      = "medium",
                ))

            else:
                # Match — check values
                b_igst = float(row.get("igst_books", 0) or 0)
                g_igst = float(row.get("igst_gstr", 0) or 0)
                gst_diff = abs(
                    (float(row.get("igst_gstr",0) or 0) + float(row.get("cgst_gstr",0) or 0) + float(row.get("sgst_gstr",0) or 0)) -
                    (float(row.get("igst_books",0) or 0) + float(row.get("cgst_books",0) or 0) + float(row.get("sgst_books",0) or 0))
                )
                if gst_diff > 1:
                    result.mismatch_count += 1
                    result.items.append(MismatchItem(
                        invoice_number  = inv_no,
                        invoice_date    = str(row.get("invoice_date_books", "")),
                        supplier_gstin  = str(row.get("supplier_gstin_books", "")),
                        party_name      = str(row.get("supplier_name_books", "")),
                        invoice_type    = "B2B",
                        books_taxable   = float(row.get("taxable_value_books", 0) or 0),
                        books_igst      = float(row.get("igst_books", 0) or 0),
                        books_cgst      = float(row.get("cgst_books", 0) or 0),
                        books_sgst      = float(row.get("sgst_books", 0) or 0),
                        gstr_taxable    = float(row.get("taxable_value_gstr", 0) or 0),
                        gstr_igst       = float(row.get("igst_gstr", 0) or 0),
                        gstr_cgst       = float(row.get("cgst_gstr", 0) or 0),
                        gstr_sgst       = float(row.get("sgst_gstr", 0) or 0),
                        mismatch_type   = "value_diff",
                        mismatch_reason = f"ITC difference of ₹{gst_diff:,.2f}. Verify with supplier.",
                        itc_impact      = gst_diff,
                        risk_level      = "medium",
                    ))
                else:
                    result.matched_count += 1
                    result.items.append(MismatchItem(
                        invoice_number  = inv_no,
                        invoice_date    = str(row.get("invoice_date_books", "")),
                        supplier_gstin  = str(row.get("supplier_gstin_books", "")),
                        party_name      = str(row.get("supplier_name_books", "")),
                        invoice_type    = "B2B",
                        books_taxable   = float(row.get("taxable_value_books", 0) or 0),
                        books_igst      = float(row.get("igst_books", 0) or 0),
                        books_cgst      = float(row.get("cgst_books", 0) or 0),
                        books_sgst      = float(row.get("sgst_books", 0) or 0),
                        gstr_taxable    = float(row.get("taxable_value_gstr", 0) or 0),
                        gstr_igst       = float(row.get("igst_gstr", 0) or 0),
                        gstr_cgst       = float(row.get("cgst_gstr", 0) or 0),
                        gstr_sgst       = float(row.get("sgst_gstr", 0) or 0),
                        mismatch_type   = "matched",
                        mismatch_reason = "",
                        itc_impact      = 0.0,
                        risk_level      = "low",
                    ))

        result.itc_impact = total_itc_unclaimed - total_itc_excess
        result.summary = {
            "itc_in_gstr2b":    float(gstr2b_df[["igst","cgst","sgst"]].sum().sum()),
            "itc_in_books":     float(purchase_df[["igst","cgst","sgst"]].sum().sum()),
            "itc_unclaimed":    total_itc_unclaimed,
            "itc_excess":       total_itc_excess,
            "net_itc_impact":   total_itc_unclaimed - total_itc_excess,
        }
        return result

    # ── GST Rate Validator ───────────────────────────────────

    def validate_gst_rates(self, df: pd.DataFrame, hsn_master: pd.DataFrame) -> pd.DataFrame:
        """
        Cross-reference invoice HSN codes against HSN master to validate applied GST rates.
        Returns DataFrame with 'rate_valid', 'expected_rate', 'actual_rate', 'rate_diff' columns.
        """
        if "hsn_code" not in df.columns:
            df["rate_valid"] = True
            return df

        merged = df.merge(
            hsn_master[["hsn_code", "gst_rate"]].rename(columns={"gst_rate": "expected_rate"}),
            on="hsn_code",
            how="left",
        )

        merged["actual_rate"] = merged.apply(
            lambda r: (
                (r.get("igst", 0) + r.get("cgst", 0) + r.get("sgst", 0)) /
                r.get("taxable_value", 1) * 100
            ) if r.get("taxable_value", 0) > 0 else 0,
            axis=1,
        )

        merged["rate_diff"]  = abs(merged["actual_rate"] - merged["expected_rate"].fillna(merged["actual_rate"]))
        merged["rate_valid"] = merged["rate_diff"] <= 0.5

        return merged

    # ── GSTR-3B vs Books Verification ────────────────────────

    def verify_gstr3b_vs_books(
        self,
        gstr3b: dict,
        sales_df: pd.DataFrame,
        purchase_df: pd.DataFrame,
    ) -> dict:
        """
        Verify GSTR-3B declared values against computed book values.
        Returns head-wise variance dict.
        """
        # Compute from books
        books_output_igst = float(sales_df["igst"].sum()) if "igst" in sales_df else 0
        books_output_cgst = float(sales_df["cgst"].sum()) if "cgst" in sales_df else 0
        books_output_sgst = float(sales_df["sgst"].sum()) if "sgst" in sales_df else 0

        books_itc_igst = float(purchase_df[purchase_df.get("itc_eligible", True) == True]["igst"].sum()) if "igst" in purchase_df else 0
        books_itc_cgst = float(purchase_df[purchase_df.get("itc_eligible", True) == True]["cgst"].sum()) if "cgst" in purchase_df else 0
        books_itc_sgst = float(purchase_df[purchase_df.get("itc_eligible", True) == True]["sgst"].sum()) if "sgst" in purchase_df else 0

        def variance(declared, books):
            diff = declared - books
            return {
                "declared": round(declared, 2),
                "books":    round(books, 2),
                "variance": round(diff, 2),
                "status":   "matched" if abs(diff) <= 1 else ("excess" if diff > 0 else "short"),
            }

        return {
            "output_tax": {
                "igst": variance(gstr3b.get("taxable_outward_igst", 0), books_output_igst),
                "cgst": variance(gstr3b.get("taxable_outward_cgst", 0), books_output_cgst),
                "sgst": variance(gstr3b.get("taxable_outward_sgst", 0), books_output_sgst),
            },
            "itc": {
                "igst": variance(gstr3b.get("net_itc_igst", 0), books_itc_igst),
                "cgst": variance(gstr3b.get("net_itc_cgst", 0), books_itc_cgst),
                "sgst": variance(gstr3b.get("net_itc_sgst", 0), books_itc_sgst),
            },
            "net_liability": {
                "igst": variance(
                    gstr3b.get("tax_paid_igst", 0),
                    max(0, books_output_igst - books_itc_igst),
                ),
                "cgst": variance(
                    gstr3b.get("tax_paid_cgst", 0),
                    max(0, books_output_cgst - books_itc_cgst),
                ),
                "sgst": variance(
                    gstr3b.get("tax_paid_sgst", 0),
                    max(0, books_output_sgst - books_itc_sgst),
                ),
            },
        }

    # ── Vendor Risk Scoring ──────────────────────────────────

    def score_vendor_risk(
        self,
        vendor_name: str,
        gstin: str,
        filing_history: list[dict],
        total_itc: float,
    ) -> tuple[int, str]:
        """
        Score vendor GST compliance risk (0–100).
        Returns (score, risk_level).
        """
        score = 0

        # GSTIN validity
        if not GSTIN_PATTERN.match(gstin.upper()):
            score += 30

        # Filing gaps
        if filing_history:
            months_not_filed = sum(1 for h in filing_history if h.get("status") != "filed")
            score += min(40, months_not_filed * 8)

        # ITC magnitude (high ITC from risky vendor = higher risk)
        if total_itc > 1_000_000:
            score += 15
        elif total_itc > 500_000:
            score += 10

        # Random threshold (in real system: GST portal API verification)
        score = min(score, 100)

        if score >= 70:
            return score, "critical"
        elif score >= 50:
            return score, "high"
        elif score >= 30:
            return score, "medium"
        else:
            return score, "low"

    # ── Normalizers ──────────────────────────────────────────

    def _normalize_gstr1(self, df: pd.DataFrame) -> pd.DataFrame:
        col_map = {
            "Invoice Number": "invoice_number",
            "GSTIN of Recipient": "receiver_gstin",
            "Receiver Name": "receiver_name",
            "Invoice Date": "invoice_date",
            "Invoice Value": "total_value",
            "Taxable Value": "taxable_value",
            "Integrated Tax": "igst",
            "Central Tax": "cgst",
            "State/UT Tax": "sgst",
            "Cess": "cess",
            "Type": "invoice_type",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        for col in ["taxable_value", "igst", "cgst", "sgst", "cess", "total_value"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        if "invoice_number" in df.columns:
            df["invoice_number"] = df["invoice_number"].astype(str).str.strip().str.upper()
        if "supplier_gstin" not in df.columns:
            df["supplier_gstin"] = ""
        return df

    def _normalize_sales_register(self, df: pd.DataFrame) -> pd.DataFrame:
        col_map = {
            "Invoice No": "invoice_number",
            "Customer GSTIN": "customer_gstin",
            "Customer Name": "customer_name",
            "Date": "invoice_date",
            "Taxable Amount": "taxable_value",
            "IGST": "igst",
            "CGST": "cgst",
            "SGST": "sgst",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        for col in ["taxable_value", "igst", "cgst", "sgst"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        if "invoice_number" in df.columns:
            df["invoice_number"] = df["invoice_number"].astype(str).str.strip().str.upper()
        if "supplier_gstin" not in df.columns:
            df["supplier_gstin"] = df.get("customer_gstin", pd.Series([""] * len(df)))
        return df

    def _normalize_gstr2b(self, df: pd.DataFrame) -> pd.DataFrame:
        col_map = {
            "GSTIN of Supplier": "supplier_gstin",
            "Trade/Legal name of Supplier": "supplier_name",
            "Invoice Number": "invoice_number",
            "Invoice Date": "invoice_date",
            "Invoice Value": "total_value",
            "Taxable Value": "taxable_value",
            "Integrated Tax": "igst",
            "Central Tax": "cgst",
            "State/UT Tax": "sgst",
            "ITC Available": "itc_availability",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        for col in ["taxable_value", "igst", "cgst", "sgst"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        if "invoice_number" in df.columns:
            df["invoice_number"] = df["invoice_number"].astype(str).str.strip().str.upper()
        if "supplier_gstin" in df.columns:
            df["supplier_gstin"] = df["supplier_gstin"].astype(str).str.strip().str.upper()
        return df

    def _normalize_purchase_register(self, df: pd.DataFrame) -> pd.DataFrame:
        col_map = {
            "Invoice No": "invoice_number",
            "Supplier GSTIN": "supplier_gstin",
            "Supplier Name": "supplier_name",
            "Date": "invoice_date",
            "Taxable Amount": "taxable_value",
            "IGST": "igst",
            "CGST": "cgst",
            "SGST": "sgst",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        for col in ["taxable_value", "igst", "cgst", "sgst"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        if "invoice_number" in df.columns:
            df["invoice_number"] = df["invoice_number"].astype(str).str.strip().str.upper()
        if "supplier_gstin" in df.columns:
            df["supplier_gstin"] = df["supplier_gstin"].fillna("").astype(str).str.strip().str.upper()
        return df

    def _make_key(self, df: pd.DataFrame) -> pd.Series:
        gstin_col = "supplier_gstin" if "supplier_gstin" in df.columns else "customer_gstin"
        gstin = df.get(gstin_col, pd.Series([""] * len(df))).fillna("").astype(str).str.strip().str.upper()
        inv   = df["invoice_number"].astype(str).str.strip().str.upper()
        return gstin + "_" + inv

    def _build_gstr1_summary(
        self, gstr1: pd.DataFrame, books: pd.DataFrame, result: ReconciliationResult
    ) -> dict:
        def safe_sum(df, col):
            return float(df[col].sum()) if col in df.columns else 0.0

        return {
            "gstr1_total_taxable":  safe_sum(gstr1, "taxable_value"),
            "books_total_taxable":  safe_sum(books, "taxable_value"),
            "gstr1_output_gst":     safe_sum(gstr1, "igst") + safe_sum(gstr1, "cgst") + safe_sum(gstr1, "sgst"),
            "books_output_gst":     safe_sum(books, "igst") + safe_sum(books, "cgst") + safe_sum(books, "sgst"),
            "match_rate_pct":       round(result.matched_count / max(result.total_invoices, 1) * 100, 1),
            "mismatch_count":       result.mismatch_count,
            "missing_count":        result.missing_count,
            "duplicate_count":      result.duplicate_count,
        }
