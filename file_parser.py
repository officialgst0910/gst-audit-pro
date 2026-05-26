# ============================================================
# app/services/file_parser.py
# GST File Parser — Excel / JSON / CSV for all GSTR formats
# ============================================================

from __future__ import annotations
import pandas as pd
import numpy as np
import json
import io
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)

GSTIN_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]$")


@dataclass
class ParseResult:
    success:   bool
    records:   list[dict] = field(default_factory=list)
    row_count: int = 0
    errors:    list[str] = field(default_factory=list)
    warnings:  list[str] = field(default_factory=list)
    metadata:  dict = field(default_factory=dict)


class GSTFileParser:
    """
    Parser for all GST data files:
    - GSTR-1 (Excel export from GST portal / Tally / Busy)
    - GSTR-2B (Excel / JSON from GST portal)
    - GSTR-3B (Excel)
    - Sales Register (Tally/Busy/Zoho Books export)
    - Purchase Register
    """

    # ── GSTR-1 Parser ────────────────────────────────────────

    def parse_gstr1_excel(self, file_bytes: bytes) -> ParseResult:
        """
        Parse GSTR-1 Excel downloaded from GST portal.
        Handles multi-sheet format: B2B, B2CS, B2CL, CDNR, EXP sheets.
        """
        result = ParseResult(success=False)
        try:
            xf = pd.ExcelFile(io.BytesIO(file_bytes))
            all_records = []

            sheet_parsers = {
                "b2b":  self._parse_gstr1_b2b_sheet,
                "B2B":  self._parse_gstr1_b2b_sheet,
                "b2cs": self._parse_gstr1_b2cs_sheet,
                "B2CS": self._parse_gstr1_b2cs_sheet,
                "cdnr": self._parse_gstr1_cdnr_sheet,
                "CDNR": self._parse_gstr1_cdnr_sheet,
                "exp":  self._parse_gstr1_exp_sheet,
                "EXP":  self._parse_gstr1_exp_sheet,
            }

            for sheet_name in xf.sheet_names:
                parser = sheet_parsers.get(sheet_name)
                if parser:
                    df = xf.parse(sheet_name, skiprows=self._detect_header_row(xf, sheet_name))
                    df = df.dropna(how="all")
                    records = parser(df)
                    all_records.extend(records)
                    logger.info(f"Parsed {len(records)} records from sheet '{sheet_name}'")

            result.records   = all_records
            result.row_count = len(all_records)
            result.success   = True
            result.metadata  = {"sheets_parsed": list(xf.sheet_names)}

        except Exception as e:
            result.errors.append(f"GSTR-1 parse error: {str(e)}")
            logger.error(f"GSTR-1 parse failed: {e}")

        return result

    def _parse_gstr1_b2b_sheet(self, df: pd.DataFrame) -> list[dict]:
        records = []
        # GST portal B2B sheet columns
        col_map = {
            "GSTIN of Recipient":    "receiver_gstin",
            "Receiver Name":          "receiver_name",
            "Invoice Number":         "invoice_number",
            "Invoice Date":           "invoice_date",
            "Invoice Value":          "total_value",
            "Place Of Supply":        "place_of_supply",
            "Applicable % of Tax":    "tax_rate",
            "Invoice Type":           "invoice_sub_type",
            "E-Commerce GSTIN":       "ecom_gstin",
            "Rate":                   "gst_rate",
            "Taxable Value":          "taxable_value",
            "Cess Amount":            "cess",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

        for _, row in df.iterrows():
            if pd.isna(row.get("invoice_number")):
                continue
            igst, cgst, sgst = self._compute_gst_components(
                taxable = float(row.get("taxable_value", 0) or 0),
                rate    = float(row.get("gst_rate", 0) or 0),
                pos     = str(row.get("place_of_supply", "")),
            )
            records.append({
                "invoice_type":   "B2B",
                "invoice_number": str(row.get("invoice_number", "")).strip(),
                "invoice_date":   self._parse_date(row.get("invoice_date")),
                "receiver_gstin": str(row.get("receiver_gstin", "")).strip().upper(),
                "receiver_name":  str(row.get("receiver_name", "")).strip(),
                "place_of_supply":str(row.get("place_of_supply", "")).strip()[:2],
                "taxable_value":  float(row.get("taxable_value", 0) or 0),
                "gst_rate":       float(row.get("gst_rate", 0) or 0),
                "igst":           igst,
                "cgst":           cgst,
                "sgst":           sgst,
                "cess":           float(row.get("cess", 0) or 0),
                "total_value":    float(row.get("total_value", 0) or 0),
            })
        return records

    def _parse_gstr1_b2cs_sheet(self, df: pd.DataFrame) -> list[dict]:
        records = []
        col_map = {
            "Type":              "supply_type",
            "Place Of Supply":   "place_of_supply",
            "Rate":              "gst_rate",
            "Taxable Value":     "taxable_value",
            "Cess Amount":       "cess",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        for i, row in df.iterrows():
            if pd.isna(row.get("taxable_value")):
                continue
            taxable = float(row.get("taxable_value", 0) or 0)
            rate    = float(row.get("gst_rate", 0) or 0)
            igst    = round(taxable * rate / 100, 2)
            records.append({
                "invoice_type":   "B2CS",
                "invoice_number": f"B2CS-{i:04d}",
                "invoice_date":   None,
                "receiver_gstin": "",
                "receiver_name":  "Unregistered Customers",
                "place_of_supply":str(row.get("place_of_supply", "")).strip()[:2],
                "taxable_value":  taxable,
                "gst_rate":       rate,
                "igst":           igst,
                "cgst":           0.0,
                "sgst":           0.0,
                "cess":           float(row.get("cess", 0) or 0),
                "total_value":    taxable + igst,
            })
        return records

    def _parse_gstr1_cdnr_sheet(self, df: pd.DataFrame) -> list[dict]:
        col_map = {
            "GSTIN of Recipient":    "receiver_gstin",
            "Note/Refund Voucher Number": "invoice_number",
            "Note/Refund Voucher Date":   "invoice_date",
            "Note/Refund Voucher Value":  "total_value",
            "Note Type":             "note_type",
            "Rate":                  "gst_rate",
            "Taxable Value":         "taxable_value",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        records = []
        for _, row in df.iterrows():
            if pd.isna(row.get("invoice_number")):
                continue
            taxable = float(row.get("taxable_value", 0) or 0)
            rate    = float(row.get("gst_rate", 0) or 0)
            igst, cgst, sgst = self._compute_gst_components(taxable, rate, "")
            records.append({
                "invoice_type":   "CDNR",
                "invoice_number": str(row.get("invoice_number", "")).strip(),
                "invoice_date":   self._parse_date(row.get("invoice_date")),
                "receiver_gstin": str(row.get("receiver_gstin", "")).strip().upper(),
                "taxable_value":  -taxable,  # credit note = negative
                "gst_rate":       rate,
                "igst":           -igst,
                "cgst":           -cgst,
                "sgst":           -sgst,
                "cess":           0.0,
                "total_value":    float(row.get("total_value", 0) or 0),
            })
        return records

    def _parse_gstr1_exp_sheet(self, df: pd.DataFrame) -> list[dict]:
        col_map = {
            "Export Type":   "export_type",
            "Invoice Number":"invoice_number",
            "Invoice Date":  "invoice_date",
            "Invoice Value": "total_value",
            "Port Code":     "port_code",
            "Shipping Bill Number": "shipping_bill_no",
            "Rate":          "gst_rate",
            "Taxable Value": "taxable_value",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        records = []
        for _, row in df.iterrows():
            if pd.isna(row.get("invoice_number")):
                continue
            taxable = float(row.get("taxable_value", 0) or 0)
            records.append({
                "invoice_type":   "EXPORT",
                "invoice_number": str(row.get("invoice_number", "")).strip(),
                "invoice_date":   self._parse_date(row.get("invoice_date")),
                "receiver_gstin": "",
                "taxable_value":  taxable,
                "gst_rate":       0.0,
                "igst":           0.0,
                "cgst":           0.0,
                "sgst":           0.0,
                "cess":           0.0,
                "total_value":    float(row.get("total_value", 0) or 0),
                "is_export":      True,
            })
        return records

    # ── GSTR-1 JSON Parser (GST Portal Format) ───────────────

    def parse_gstr1_json(self, file_bytes: bytes) -> ParseResult:
        result = ParseResult(success=False)
        try:
            data = json.loads(file_bytes)
            records = []

            # B2B invoices
            for supplier in data.get("b2b", []):
                gstin = supplier.get("ctin", "")
                for inv in supplier.get("inv", []):
                    for item in inv.get("itms", [{}]):
                        det = item.get("itm_det", {})
                        records.append({
                            "invoice_type":   "B2B",
                            "invoice_number": inv.get("inum", ""),
                            "invoice_date":   inv.get("idt", ""),
                            "receiver_gstin": gstin,
                            "receiver_name":  supplier.get("trdnm", ""),
                            "taxable_value":  float(det.get("txval", 0)),
                            "gst_rate":       float(det.get("rt", 0)),
                            "igst":           float(det.get("iamt", 0)),
                            "cgst":           float(det.get("camt", 0)),
                            "sgst":           float(det.get("samt", 0)),
                            "cess":           float(det.get("csamt", 0)),
                            "total_value":    float(inv.get("val", 0)),
                            "place_of_supply":inv.get("pos", ""),
                        })

            # B2CS
            for item in data.get("b2cs", []):
                taxable = float(item.get("txval", 0))
                igst    = float(item.get("iamt", 0))
                records.append({
                    "invoice_type":   "B2CS",
                    "invoice_number": f"B2CS-{item.get('pos','')}",
                    "taxable_value":  taxable,
                    "gst_rate":       float(item.get("rt", 0)),
                    "igst":           igst,
                    "cgst":           float(item.get("camt", 0)),
                    "sgst":           float(item.get("samt", 0)),
                    "cess":           float(item.get("csamt", 0)),
                    "place_of_supply":item.get("pos", ""),
                    "total_value":    taxable + igst,
                })

            result.records   = records
            result.row_count = len(records)
            result.success   = True
            result.metadata  = {
                "gstin":  data.get("gstin", ""),
                "fp":     data.get("fp", ""),  # filing period MM-YYYY
            }
        except Exception as e:
            result.errors.append(str(e))
        return result

    # ── GSTR-2B Parser ────────────────────────────────────────

    def parse_gstr2b_excel(self, file_bytes: bytes) -> ParseResult:
        result = ParseResult(success=False)
        try:
            xf = pd.ExcelFile(io.BytesIO(file_bytes))
            # GSTR-2B has sheets: B2B, CDNR, ISD, IMPG
            records = []

            for sheet in ["B2B", "b2b"]:
                if sheet in xf.sheet_names:
                    df = xf.parse(sheet, skiprows=3)
                    df = df.dropna(how="all")
                    col_map = {
                        "GSTIN of Supplier":                "supplier_gstin",
                        "Trade/Legal name of the Supplier": "supplier_name",
                        "Invoice number":                   "invoice_number",
                        "Invoice Date":                     "invoice_date",
                        "Invoice Value(₹)":                 "total_value",
                        "Place of supply":                  "place_of_supply",
                        "Supply Type":                      "supply_type",
                        "Rate(%)":                          "gst_rate",
                        "Taxable value(₹)":                 "taxable_value",
                        "Integrated Tax(₹)":                "igst",
                        "Central Tax(₹)":                   "cgst",
                        "State/UT Tax(₹)":                  "sgst",
                        "Cess(₹)":                         "cess",
                        "ITC Availability":                 "itc_availability",
                        "Reason":                           "itc_reason",
                    }
                    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
                    for _, row in df.iterrows():
                        if pd.isna(row.get("invoice_number")):
                            continue
                        records.append({
                            "record_type":    "B2B",
                            "supplier_gstin": str(row.get("supplier_gstin", "")).strip().upper(),
                            "supplier_name":  str(row.get("supplier_name", "")).strip(),
                            "invoice_number": str(row.get("invoice_number", "")).strip(),
                            "invoice_date":   self._parse_date(row.get("invoice_date")),
                            "total_value":    float(row.get("total_value", 0) or 0),
                            "taxable_value":  float(row.get("taxable_value", 0) or 0),
                            "igst":           float(row.get("igst", 0) or 0),
                            "cgst":           float(row.get("cgst", 0) or 0),
                            "sgst":           float(row.get("sgst", 0) or 0),
                            "cess":           float(row.get("cess", 0) or 0),
                            "itc_availability":str(row.get("itc_availability", "Yes")).strip(),
                            "itc_reason":     str(row.get("itc_reason", "")).strip(),
                        })

            result.records   = records
            result.row_count = len(records)
            result.success   = True
        except Exception as e:
            result.errors.append(str(e))
        return result

    # ── Sales Register Parser ─────────────────────────────────

    def parse_sales_register(self, file_bytes: bytes, file_format: str = "xlsx") -> ParseResult:
        """
        Parse Sales Register from Tally/Busy/Zoho/custom Excel.
        Auto-detects column mapping.
        """
        result = ParseResult(success=False)
        try:
            if file_format in ("xlsx", "xls"):
                df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
            else:
                df = pd.read_csv(io.BytesIO(file_bytes))

            df = df.dropna(how="all")
            df.columns = df.columns.str.strip()

            # Auto-detect columns (handles Tally, Busy, custom formats)
            col_map = self._detect_sales_columns(df.columns.tolist())
            df = df.rename(columns=col_map)

            # Validate GSTIN column
            warnings = []
            if "customer_gstin" in df.columns:
                invalid_gstin = df[df["customer_gstin"].notna() & ~df["customer_gstin"].astype(str).str.match(GSTIN_RE.pattern)]["customer_gstin"].unique()
                if len(invalid_gstin) > 0:
                    warnings.append(f"{len(invalid_gstin)} invalid GSTINs found: {list(invalid_gstin[:3])}")

            records = []
            for _, row in df.iterrows():
                if pd.isna(row.get("invoice_number")):
                    continue
                taxable = float(row.get("taxable_value", 0) or 0)
                igst    = float(row.get("igst", 0) or 0)
                cgst    = float(row.get("cgst", 0) or 0)
                sgst    = float(row.get("sgst", 0) or 0)
                records.append({
                    "invoice_number": str(row.get("invoice_number", "")).strip(),
                    "invoice_date":   self._parse_date(row.get("invoice_date")),
                    "customer_gstin": str(row.get("customer_gstin", "")).strip().upper(),
                    "customer_name":  str(row.get("customer_name", "")).strip(),
                    "hsn_code":       str(row.get("hsn_code", "")).strip(),
                    "taxable_value":  taxable,
                    "igst":           igst,
                    "cgst":           cgst,
                    "sgst":           sgst,
                    "cess":           float(row.get("cess", 0) or 0),
                    "total_value":    float(row.get("total_value", taxable + igst + cgst + sgst) or 0),
                    "gst_rate":       float(row.get("gst_rate", 0) or 0),
                    "place_of_supply":str(row.get("place_of_supply", "")).strip()[:2],
                    "invoice_type":   "B2B" if row.get("customer_gstin") else "B2C",
                })

            result.records   = records
            result.row_count = len(records)
            result.success   = True
            result.warnings  = warnings

        except Exception as e:
            result.errors.append(str(e))
        return result

    # ── Purchase Register Parser ──────────────────────────────

    def parse_purchase_register(self, file_bytes: bytes, file_format: str = "xlsx") -> ParseResult:
        result = ParseResult(success=False)
        try:
            if file_format in ("xlsx", "xls"):
                df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
            else:
                df = pd.read_csv(io.BytesIO(file_bytes))

            df = df.dropna(how="all")
            df.columns = df.columns.str.strip()
            col_map = self._detect_purchase_columns(df.columns.tolist())
            df = df.rename(columns=col_map)

            records = []
            for _, row in df.iterrows():
                if pd.isna(row.get("invoice_number")):
                    continue
                records.append({
                    "invoice_number": str(row.get("invoice_number", "")).strip(),
                    "invoice_date":   self._parse_date(row.get("invoice_date")),
                    "supplier_gstin": str(row.get("supplier_gstin", "")).strip().upper(),
                    "supplier_name":  str(row.get("supplier_name", "")).strip(),
                    "hsn_code":       str(row.get("hsn_code", "")).strip(),
                    "description":    str(row.get("description", "")).strip(),
                    "taxable_value":  float(row.get("taxable_value", 0) or 0),
                    "igst":           float(row.get("igst", 0) or 0),
                    "cgst":           float(row.get("cgst", 0) or 0),
                    "sgst":           float(row.get("sgst", 0) or 0),
                    "cess":           float(row.get("cess", 0) or 0),
                    "total_value":    float(row.get("total_value", 0) or 0),
                    "gst_rate":       float(row.get("gst_rate", 0) or 0),
                    "itc_eligible":   str(row.get("itc_eligible", "Yes")).strip().lower() in ("yes","y","true","1"),
                    "itc_claimed":    float(row.get("itc_claimed", 0) or 0),
                    "expense_head":   str(row.get("expense_head", "")).strip(),
                    "voucher_number": str(row.get("voucher_number", "")).strip(),
                })

            result.records   = records
            result.row_count = len(records)
            result.success   = True
        except Exception as e:
            result.errors.append(str(e))
        return result

    # ── Helpers ───────────────────────────────────────────────

    def _detect_header_row(self, xf, sheet_name: str) -> int:
        """Detect the actual header row in GST portal exports (usually row 3-5)."""
        df_raw = xf.parse(sheet_name, header=None, nrows=10)
        for i, row in df_raw.iterrows():
            row_str = " ".join(str(v).lower() for v in row if pd.notna(v))
            if any(kw in row_str for kw in ["gstin", "invoice", "taxable", "cgst", "sgst"]):
                return i
        return 0

    def _detect_sales_columns(self, columns: list[str]) -> dict:
        """Fuzzy column mapping for common Sales Register formats."""
        mapping = {}
        known = {
            "invoice_number": ["invoice no", "inv no", "invoice number", "bill no", "voucher no", "invoice#"],
            "invoice_date":   ["invoice date", "inv date", "bill date", "date", "voucher date"],
            "customer_gstin": ["customer gstin", "buyer gstin", "gstin", "party gstin", "cust. gstin"],
            "customer_name":  ["customer name", "buyer name", "party name", "ledger name"],
            "taxable_value":  ["taxable value", "taxable amount", "taxable", "assessable value", "base amount"],
            "igst":           ["igst", "igst amount", "integrated tax", "igst amt"],
            "cgst":           ["cgst", "cgst amount", "central tax", "cgst amt"],
            "sgst":           ["sgst", "sgst amount", "state tax", "utgst", "sgst/utgst amt"],
            "cess":           ["cess", "cess amount"],
            "total_value":    ["invoice value", "total value", "total amount", "net amount", "grand total"],
            "gst_rate":       ["rate", "gst rate", "tax rate", "rate %"],
            "hsn_code":       ["hsn", "hsn code", "hsn/sac", "hsn/sac code"],
            "place_of_supply":["pos", "place of supply", "state"],
        }
        cols_lower = {c.lower().strip(): c for c in columns}
        for target, aliases in known.items():
            for alias in aliases:
                if alias in cols_lower:
                    mapping[cols_lower[alias]] = target
                    break
        return mapping

    def _detect_purchase_columns(self, columns: list[str]) -> dict:
        mapping = {}
        known = {
            "invoice_number": ["invoice no", "bill no", "purchase invoice no", "supplier invoice"],
            "invoice_date":   ["invoice date", "bill date", "date", "purchase date"],
            "supplier_gstin": ["supplier gstin", "vendor gstin", "party gstin", "gstin"],
            "supplier_name":  ["supplier name", "vendor name", "party name", "ledger name"],
            "taxable_value":  ["taxable value", "taxable amount", "taxable", "assessable value"],
            "igst":           ["igst", "igst amount", "integrated tax"],
            "cgst":           ["cgst", "cgst amount", "central tax"],
            "sgst":           ["sgst", "sgst amount", "state tax", "utgst"],
            "cess":           ["cess", "cess amount"],
            "total_value":    ["invoice value", "total value", "total amount", "bill value"],
            "gst_rate":       ["rate", "gst rate", "tax rate"],
            "hsn_code":       ["hsn", "hsn code", "hsn/sac"],
            "itc_eligible":   ["itc eligible", "eligible for itc", "itc availability"],
            "itc_claimed":    ["itc claimed", "itc availed", "input tax credit"],
            "expense_head":   ["expense head", "account head", "gl account", "cost head"],
            "voucher_number": ["voucher no", "voucher number", "journal no"],
        }
        cols_lower = {c.lower().strip(): c for c in columns}
        for target, aliases in known.items():
            for alias in aliases:
                if alias in cols_lower:
                    mapping[cols_lower[alias]] = target
                    break
        return mapping

    def _parse_date(self, val) -> Optional[str]:
        if pd.isna(val) if not isinstance(val, str) else not val:
            return None
        if isinstance(val, datetime):
            return val.strftime("%Y-%m-%d")
        val_str = str(val).strip()
        for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%b-%Y", "%d-%b-%y", "%m/%d/%Y"):
            try:
                return datetime.strptime(val_str, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return val_str

    def _compute_gst_components(self, taxable: float, rate: float, pos: str) -> tuple[float, float, float]:
        """
        Determine IGST vs CGST+SGST split based on Place of Supply.
        For same-state supply: CGST + SGST. For inter-state: IGST.
        """
        total_gst = round(taxable * rate / 100, 2)
        # If POS is different from supplier state → IGST
        # Simplified: if POS code matches supplier state code → CGST+SGST
        # In production, compare with company's state code from DB
        half = round(total_gst / 2, 2)
        # Default: IGST (inter-state) — actual split set by recon engine
        return total_gst, 0.0, 0.0

    def validate_records(self, records: list[dict], file_type: str) -> tuple[list[dict], list[str]]:
        """Validate parsed records and return (valid_records, error_messages)."""
        valid   = []
        errors  = []
        required = {
            "gstr1":            ["invoice_number", "taxable_value"],
            "gstr2b":           ["supplier_gstin", "invoice_number", "taxable_value"],
            "sales_register":   ["invoice_number", "invoice_date", "taxable_value"],
            "purchase_register":["invoice_number", "supplier_name", "taxable_value"],
        }
        req_cols = required.get(file_type, [])

        for i, rec in enumerate(records):
            row_errors = []
            for col in req_cols:
                if not rec.get(col):
                    row_errors.append(f"Row {i+1}: Missing '{col}'")

            # Validate amounts
            taxable = rec.get("taxable_value", 0)
            if taxable < 0:
                row_errors.append(f"Row {i+1}: Negative taxable value {taxable}")

            if row_errors:
                errors.extend(row_errors)
            else:
                valid.append(rec)

        return valid, errors
