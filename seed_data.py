#!/usr/bin/env python3
# ============================================================
# scripts/seed_data.py
# Seed realistic Indian GST dummy data for development
# ============================================================

import asyncio
import uuid
from datetime import date, timedelta
from decimal import Decimal
import random
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models import (
    Tenant, Company, User, Vendor,
    GSTR1Invoice, GSTR2BInvoice,
    SalesRegister, PurchaseRegister,
    GSTR3BData,
)

# ── Sample Indian Companies ──────────────────────────────────
COMPANIES_DATA = [
    {"name": "Tech Mahindra Ltd",    "gstin": "27AABCT0898L1ZB", "pan": "AABCT0898L", "state": "27"},
    {"name": "Infosys Ltd",          "gstin": "29AAACI1681G2Z7", "pan": "AAACI1681G", "state": "29"},
]

# ── Sample Vendors (Suppliers) ───────────────────────────────
VENDORS_DATA = [
    {"name": "Infosys Ltd",        "gstin": "27AAPFU0939F1ZV", "state": "27", "itc": 864000,  "filed": True},
    {"name": "TCS Pvt Ltd",        "gstin": "29AADCI0859A1ZP", "state": "29", "itc": 396000,  "filed": True},
    {"name": "Wipro Ltd",          "gstin": "33AAACV0209R1Z1", "state": "33", "itc": 279000,  "filed": False},
    {"name": "HCL Technologies",   "gstin": "07AABCS1429B1Z1", "state": "07", "itc": 558000,  "filed": True},
    {"name": "Cognizant India",    "gstin": "27AAFCS8865R1Z7", "state": "27", "itc": 1206000, "filed": True},
    {"name": "Mphasis Ltd",        "gstin": "29AADCS2649N1Z1", "state": "29", "itc": 162000,  "filed": False},
    {"name": "Oracle India Pvt",   "gstin": "27AAACO0326F1ZR", "state": "27", "itc": 576000,  "filed": True},
    {"name": "SAP India Pvt Ltd",  "gstin": "29AABCS4702G1ZC", "state": "29", "itc": 432000,  "filed": True},
    {"name": "Adobe Systems India","gstin": "29AABCA3818Q1Z2", "state": "29", "itc": 324000,  "filed": True},
    {"name": "Microsoft India",    "gstin": "27AAACM4487P1ZJ", "state": "27", "itc": 720000,  "filed": True},
    {"name": "AWS India (Amazon)", "gstin": "29AABCA0781A1ZJ", "state": "29", "itc": 900000,  "filed": True},
    {"name": "Tata Consultancy",   "gstin": "27AAACT2727Q1ZN", "state": "27", "itc": 648000,  "filed": True},
]

# ── Invoice generators ───────────────────────────────────────
GST_RATES = [5, 12, 18, 28]

def random_amount(min_val: float, max_val: float) -> Decimal:
    return Decimal(str(round(random.uniform(min_val, max_val), 2)))

def gst_components(taxable: Decimal, rate: float, inter_state: bool = True) -> tuple:
    gst = taxable * Decimal(str(rate)) / Decimal("100")
    if inter_state:
        return gst, Decimal("0"), Decimal("0")
    half = (gst / 2).quantize(Decimal("0.01"))
    return Decimal("0"), half, half

def generate_invoice_number(prefix: str, year: int, month: int, seq: int) -> str:
    return f"{prefix}/{year}-{str(year+1)[-2:]}/{month:02d}/{seq:04d}"


async def seed():
    print("🌱 Seeding GST Audit Pro database...")

    async with AsyncSessionLocal() as db:
        try:
            # ── 1. Tenant ─────────────────────────────────────
            tenant = Tenant(
                name       = "Demo CA Firm",
                slug       = "demo-ca-firm",
                plan       = "professional",
                max_gstins = 5,
                max_users  = 15,
            )
            db.add(tenant)
            await db.flush()
            print(f"  ✅ Tenant: {tenant.name} ({tenant.id})")

            # ── 2. Companies ──────────────────────────────────
            companies = []
            for cd in COMPANIES_DATA:
                company = Company(
                    tenant_id         = tenant.id,
                    name              = cd["name"],
                    gstin             = cd["gstin"],
                    pan               = cd["pan"],
                    state_code        = cd["state"],
                    registration_type = "regular",
                    address           = f"India — State {cd['state']}",
                )
                db.add(company)
                companies.append(company)
            await db.flush()
            print(f"  ✅ Companies: {len(companies)} created")

            company = companies[0]  # Tech Mahindra as primary

            # ── 3. Users ──────────────────────────────────────
            users_data = [
                ("Super Admin",    "admin@gstauditpro.in",  "Admin@123",  "super_admin"),
                ("CA Rajesh Mehta","ca@demo.in",            "Demo@123",   "ca"),
                ("Priya Sharma",   "user@demo.in",          "Demo@123",   "user"),
                ("CA Anita Gupta", "ca2@demo.in",           "Demo@123",   "ca"),
                ("Vikram Finance", "finance@demo.in",       "Demo@123",   "user"),
            ]
            for full_name, email, pwd, role in users_data:
                user = User(
                    tenant_id     = tenant.id,
                    full_name     = full_name,
                    email         = email,
                    password_hash = hash_password(pwd),
                    role          = role,
                    is_verified   = True,
                    is_active     = True,
                )
                db.add(user)
            await db.flush()
            print(f"  ✅ Users: {len(users_data)} created")

            # ── 4. Vendors ────────────────────────────────────
            vendors = []
            for i, vd in enumerate(VENDORS_DATA):
                risk = "low" if vd["filed"] and i < 8 else "high" if not vd["filed"] else "medium"
                vendor = Vendor(
                    company_id           = company.id,
                    gstin                = vd["gstin"],
                    name                 = vd["name"],
                    state_code           = vd["state"],
                    registration_status  = "active",
                    gstr1_filing_status  = "filed" if vd["filed"] else "pending",
                    last_filing_date     = date(2024, 10, 11) if vd["filed"] else None,
                    risk_score           = random.randint(5, 25) if vd["filed"] else random.randint(60, 85),
                    risk_level           = risk,
                    total_purchases      = Decimal(str(vd["itc"] * 5)),
                    total_itc            = Decimal(str(vd["itc"])),
                    itc_at_risk          = Decimal(str(vd["itc"])) if not vd["filed"] else Decimal("0"),
                )
                db.add(vendor)
                vendors.append(vendor)
            await db.flush()
            print(f"  ✅ Vendors: {len(vendors)} created")

            # ── 5. Generate 12 months of Sales Register data ──
            print("  📊 Generating Sales Register (12 months)...")
            sales_count = 0
            for year in [2024]:
                for month in range(4, 13):  # Apr-Dec 2024
                    base_sales = random.randint(200, 600)
                    for i in range(1, base_sales + 1):
                        is_b2b  = random.random() > 0.3
                        rate    = random.choice(GST_RATES)
                        taxable = random_amount(10000, 800000)
                        inter   = random.random() > 0.5
                        igst, cgst, sgst = gst_components(taxable, rate, inter)
                        cust_gstin = random.choice(VENDORS_DATA)["gstin"] if is_b2b else ""

                        sr = SalesRegister(
                            company_id      = company.id,
                            period_month    = month,
                            period_year     = year,
                            invoice_number  = generate_invoice_number("TM", year, month, i),
                            invoice_date    = date(year, month, random.randint(1, 28)),
                            customer_gstin  = cust_gstin,
                            customer_name   = random.choice(VENDORS_DATA)["name"] if is_b2b else "B2C Customer",
                            taxable_value   = taxable,
                            igst            = igst,
                            cgst            = cgst,
                            sgst            = sgst,
                            total_value     = taxable + igst + cgst + sgst,
                            gst_rate        = Decimal(str(rate)),
                            invoice_type    = "B2B" if is_b2b else "B2C",
                        )
                        db.add(sr)
                        sales_count += 1

            await db.flush()
            print(f"  ✅ Sales Register: {sales_count} invoices")

            # ── 6. GSTR-1 (slightly different from books = mismatches) ─
            print("  📊 Generating GSTR-1 data...")
            gstr1_count = 0
            for year in [2024]:
                for month in range(4, 13):
                    base = random.randint(180, 580)
                    for i in range(1, base + 1):
                        rate    = random.choice(GST_RATES)
                        # Introduce intentional mismatches (5% chance of value diff)
                        mismatch_factor = Decimal(str(random.uniform(0.97, 1.03))) if random.random() < 0.05 else Decimal("1.0")
                        taxable = random_amount(10000, 800000) * mismatch_factor
                        inter   = random.random() > 0.5
                        igst, cgst, sgst = gst_components(taxable, rate, inter)

                        g1 = GSTR1Invoice(
                            company_id      = company.id,
                            period_month    = month,
                            period_year     = year,
                            invoice_type    = "B2B",
                            invoice_number  = generate_invoice_number("TM", year, month, i),
                            invoice_date    = date(year, month, random.randint(1, 28)),
                            supplier_gstin  = company.gstin,
                            receiver_gstin  = random.choice(VENDORS_DATA)["gstin"],
                            receiver_name   = random.choice(VENDORS_DATA)["name"],
                            taxable_value   = taxable,
                            igst            = igst,
                            cgst            = cgst,
                            sgst            = sgst,
                            total_value     = taxable + igst + cgst + sgst,
                            gst_rate        = Decimal(str(rate)),
                            source          = "gstr1",
                        )
                        db.add(g1)
                        gstr1_count += 1

            await db.flush()
            print(f"  ✅ GSTR-1: {gstr1_count} invoices")

            # ── 7. Purchase Register ──────────────────────────
            print("  📊 Generating Purchase Register...")
            purch_count = 0
            for year in [2024]:
                for month in range(4, 13):
                    for j, vd in enumerate(VENDORS_DATA[:8]):
                        num_invoices = random.randint(2, 8)
                        for i in range(1, num_invoices + 1):
                            rate    = 18  # IT services = 18%
                            taxable = random_amount(50000, 500000)
                            igst, cgst, sgst = gst_components(taxable, rate, True)
                            eligible = random.random() > 0.1  # 10% ineligible

                            pr = PurchaseRegister(
                                company_id      = company.id,
                                period_month    = month,
                                period_year     = year,
                                invoice_number  = f"{vd['name'][:3].upper()}/2024/{month:02d}/{i:03d}",
                                invoice_date    = date(year, month, random.randint(1, 28)),
                                supplier_gstin  = vd["gstin"],
                                supplier_name   = vd["name"],
                                taxable_value   = taxable,
                                igst            = igst,
                                cgst            = cgst,
                                sgst            = sgst,
                                total_value     = taxable + igst,
                                gst_rate        = Decimal(str(rate)),
                                itc_eligible    = eligible,
                                itc_claimed     = igst if eligible else Decimal("0"),
                                expense_head    = "IT Services",
                            )
                            db.add(pr)
                            purch_count += 1

            await db.flush()
            print(f"  ✅ Purchase Register: {purch_count} invoices")

            # ── 8. GSTR-2B (matches purchase but with small diffs) ─
            print("  📊 Generating GSTR-2B...")
            gstr2b_count = 0
            for year in [2024]:
                for month in range(4, 13):
                    for vd in VENDORS_DATA[:10]:
                        if not vd["filed"] and month >= 10:
                            continue  # Unfiled vendors missing from GSTR-2B
                        num_inv = random.randint(2, 7)
                        for i in range(1, num_inv + 1):
                            taxable = random_amount(50000, 500000)
                            igst    = taxable * Decimal("0.18")

                            g2b = GSTR2BInvoice(
                                company_id        = company.id,
                                period_month      = month,
                                period_year       = year,
                                record_type       = "B2B",
                                supplier_gstin    = vd["gstin"],
                                supplier_name     = vd["name"],
                                invoice_number    = f"{vd['name'][:3].upper()}/2024/{month:02d}/{i:03d}",
                                invoice_date      = date(year, month, random.randint(1, 28)),
                                taxable_value     = taxable,
                                igst              = igst,
                                cgst              = Decimal("0"),
                                sgst              = Decimal("0"),
                                itc_availability  = "available" if vd["filed"] else "not_available",
                                gstr1_filing_date = date(year, month, 11) if vd["filed"] else None,
                            )
                            db.add(g2b)
                            gstr2b_count += 1

            await db.flush()
            print(f"  ✅ GSTR-2B: {gstr2b_count} records")

            # ── 9. GSTR-3B ────────────────────────────────────
            print("  📊 Generating GSTR-3B...")
            for year in [2024]:
                for month in range(4, 13):
                    output_igst = Decimal(str(random.randint(3000000, 8000000)))
                    output_cgst = output_igst * Decimal("0.25")
                    output_sgst = output_cgst
                    itc_igst    = Decimal(str(random.randint(1500000, 4000000)))
                    itc_cgst    = itc_igst * Decimal("0.25")
                    itc_sgst    = itc_cgst

                    g3b = GSTR3BData(
                        company_id           = company.id,
                        period_month         = month,
                        period_year          = year,
                        taxable_outward_igst = output_igst,
                        taxable_outward_cgst = output_cgst,
                        taxable_outward_sgst = output_sgst,
                        inward_rcm_igst      = Decimal(str(random.randint(50000, 200000))),
                        itc_available_igst   = itc_igst,
                        itc_available_cgst   = itc_cgst,
                        itc_available_sgst   = itc_sgst,
                        net_itc_igst         = itc_igst,
                        net_itc_cgst         = itc_cgst,
                        net_itc_sgst         = itc_sgst,
                        tax_paid_igst        = max(Decimal("0"), output_igst - itc_igst),
                        tax_paid_cgst        = max(Decimal("0"), output_cgst - itc_cgst),
                        tax_paid_sgst        = max(Decimal("0"), output_sgst - itc_sgst),
                        filing_date          = date(year, month, 20),
                        filing_status        = "filed",
                    )
                    db.add(g3b)

            await db.flush()
            print("  ✅ GSTR-3B: 9 months filed")

            await db.commit()
            print("\n🎉 Seed complete!")
            print("\n📋 Login credentials:")
            print("  Super Admin: admin@gstauditpro.in / Admin@123")
            print("  CA User:     ca@demo.in            / Demo@123")
            print("  Regular:     user@demo.in           / Demo@123")

        except Exception as e:
            await db.rollback()
            print(f"\n❌ Seed failed: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(seed())
