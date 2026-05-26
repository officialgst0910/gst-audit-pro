# ============================================================
# app/models/__init__.py — All SQLAlchemy ORM Models
# ============================================================

from __future__ import annotations
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
import uuid

from sqlalchemy import (
    String, Boolean, Integer, BigInteger, Numeric, Text,
    DateTime, Date, ForeignKey, UniqueConstraint, CheckConstraint,
    func, JSON
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


# ── Mixins ──────────────────────────────────────────────────

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


# ── Tenant ──────────────────────────────────────────────────

class Tenant(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "tenants"

    name:           Mapped[str]           = mapped_column(String(200), nullable=False)
    slug:           Mapped[str]           = mapped_column(String(100), unique=True, nullable=False)
    plan:           Mapped[str]           = mapped_column(String(50), default="trial")
    plan_expires_at:Mapped[Optional[datetime]] = mapped_column(DateTime)
    max_gstins:     Mapped[int]           = mapped_column(Integer, default=1)
    max_users:      Mapped[int]           = mapped_column(Integer, default=5)
    max_invoices:   Mapped[int]           = mapped_column(Integer, default=500)
    is_active:      Mapped[bool]          = mapped_column(Boolean, default=True)

    companies:      Mapped[List["Company"]] = relationship("Company", back_populates="tenant")
    users:          Mapped[List["User"]]    = relationship("User", back_populates="tenant")


# ── Company ──────────────────────────────────────────────────

class Company(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "companies"
    __table_args__ = (UniqueConstraint("tenant_id", "gstin"),)

    tenant_id:          Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name:               Mapped[str]           = mapped_column(String(200), nullable=False)
    gstin:              Mapped[str]           = mapped_column(String(15), nullable=False, index=True)
    pan:                Mapped[str]           = mapped_column(String(10), nullable=False)
    trade_name:         Mapped[Optional[str]] = mapped_column(String(200))
    address:            Mapped[Optional[str]] = mapped_column(Text)
    state_code:         Mapped[str]           = mapped_column(String(2), nullable=False)
    email:              Mapped[Optional[str]] = mapped_column(String(200))
    phone:              Mapped[Optional[str]] = mapped_column(String(15))
    registration_type:  Mapped[str]           = mapped_column(String(50), default="regular")
    is_active:          Mapped[bool]          = mapped_column(Boolean, default=True)

    tenant:             Mapped["Tenant"]                  = relationship("Tenant", back_populates="companies")
    vendors:            Mapped[List["Vendor"]]            = relationship("Vendor", back_populates="company")
    file_uploads:       Mapped[List["FileUpload"]]        = relationship("FileUpload", back_populates="company")
    gstr1_invoices:     Mapped[List["GSTR1Invoice"]]      = relationship("GSTR1Invoice", back_populates="company")
    gstr2b_invoices:    Mapped[List["GSTR2BInvoice"]]     = relationship("GSTR2BInvoice", back_populates="company")
    purchase_register:  Mapped[List["PurchaseRegister"]]  = relationship("PurchaseRegister", back_populates="company")
    sales_register:     Mapped[List["SalesRegister"]]     = relationship("SalesRegister", back_populates="company")
    recon_runs:         Mapped[List["ReconciliationRun"]] = relationship("ReconciliationRun", back_populates="company")


# ── User ──────────────────────────────────────────────────────

class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("tenant_id", "email"),)

    tenant_id:      Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    email:          Mapped[str]           = mapped_column(String(200), nullable=False)
    phone:          Mapped[Optional[str]] = mapped_column(String(15))
    full_name:      Mapped[str]           = mapped_column(String(200), nullable=False)
    password_hash:  Mapped[str]           = mapped_column(String(255), nullable=False)
    role:           Mapped[str]           = mapped_column(String(50), default="user")
    is_active:      Mapped[bool]          = mapped_column(Boolean, default=True)
    is_verified:    Mapped[bool]          = mapped_column(Boolean, default=False)
    last_login_at:  Mapped[Optional[datetime]] = mapped_column(DateTime)
    otp_secret:     Mapped[Optional[str]] = mapped_column(String(100))
    otp_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    tenant:         Mapped["Tenant"] = relationship("Tenant", back_populates="users")


# ── File Upload ───────────────────────────────────────────────

class FileUpload(UUIDMixin, Base):
    __tablename__ = "file_uploads"

    company_id:     Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    uploaded_by:    Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    file_name:      Mapped[str]           = mapped_column(String(300), nullable=False)
    original_name:  Mapped[str]           = mapped_column(String(300), nullable=False)
    file_type:      Mapped[str]           = mapped_column(String(50), nullable=False)
    file_format:    Mapped[str]           = mapped_column(String(10), nullable=False)
    file_size:      Mapped[int]           = mapped_column(BigInteger, nullable=False)
    s3_key:         Mapped[str]           = mapped_column(String(500), nullable=False)
    period_month:   Mapped[Optional[int]] = mapped_column(Integer)
    period_year:    Mapped[Optional[int]] = mapped_column(Integer)
    row_count:      Mapped[Optional[int]] = mapped_column(Integer)
    status:         Mapped[str]           = mapped_column(String(50), default="pending")
    error_message:  Mapped[Optional[str]] = mapped_column(Text)
    processed_at:   Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at:     Mapped[datetime]      = mapped_column(DateTime, default=func.now())

    company: Mapped["Company"] = relationship("Company", back_populates="file_uploads")


# ── GSTR-1 Invoice ────────────────────────────────────────────

class GSTR1Invoice(UUIDMixin, Base):
    __tablename__ = "gstr1_invoices"

    company_id:     Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    upload_id:      Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("file_uploads.id"))
    period_month:   Mapped[int]           = mapped_column(Integer, nullable=False)
    period_year:    Mapped[int]           = mapped_column(Integer, nullable=False)
    invoice_type:   Mapped[str]           = mapped_column(String(20), nullable=False)
    invoice_number: Mapped[str]           = mapped_column(String(50), nullable=False, index=True)
    invoice_date:   Mapped[date]          = mapped_column(Date, nullable=False)
    supplier_gstin: Mapped[str]           = mapped_column(String(15), nullable=False)
    receiver_gstin: Mapped[Optional[str]] = mapped_column(String(15), index=True)
    receiver_name:  Mapped[Optional[str]] = mapped_column(String(200))
    place_of_supply:Mapped[Optional[str]] = mapped_column(String(2))
    hsn_code:       Mapped[Optional[str]] = mapped_column(String(10))
    taxable_value:  Mapped[Decimal]       = mapped_column(Numeric(15,2), default=0)
    igst:           Mapped[Decimal]       = mapped_column(Numeric(15,2), default=0)
    cgst:           Mapped[Decimal]       = mapped_column(Numeric(15,2), default=0)
    sgst:           Mapped[Decimal]       = mapped_column(Numeric(15,2), default=0)
    cess:           Mapped[Decimal]       = mapped_column(Numeric(15,2), default=0)
    total_value:    Mapped[Decimal]       = mapped_column(Numeric(15,2), default=0)
    gst_rate:       Mapped[Optional[Decimal]] = mapped_column(Numeric(5,2))
    is_amended:     Mapped[bool]          = mapped_column(Boolean, default=False)
    source:         Mapped[str]           = mapped_column(String(20), default="gstr1")
    created_at:     Mapped[datetime]      = mapped_column(DateTime, default=func.now())

    company: Mapped["Company"] = relationship("Company", back_populates="gstr1_invoices")


# ── GSTR-2B Invoice ───────────────────────────────────────────

class GSTR2BInvoice(UUIDMixin, Base):
    __tablename__ = "gstr2b_invoices"

    company_id:         Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    upload_id:          Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("file_uploads.id"))
    period_month:       Mapped[int]           = mapped_column(Integer, nullable=False)
    period_year:        Mapped[int]           = mapped_column(Integer, nullable=False)
    record_type:        Mapped[str]           = mapped_column(String(20), nullable=False)
    supplier_gstin:     Mapped[str]           = mapped_column(String(15), nullable=False, index=True)
    supplier_name:      Mapped[Optional[str]] = mapped_column(String(200))
    invoice_number:     Mapped[str]           = mapped_column(String(50), nullable=False)
    invoice_date:       Mapped[date]          = mapped_column(Date, nullable=False)
    taxable_value:      Mapped[Decimal]       = mapped_column(Numeric(15,2), default=0)
    igst:               Mapped[Decimal]       = mapped_column(Numeric(15,2), default=0)
    cgst:               Mapped[Decimal]       = mapped_column(Numeric(15,2), default=0)
    sgst:               Mapped[Decimal]       = mapped_column(Numeric(15,2), default=0)
    cess:               Mapped[Decimal]       = mapped_column(Numeric(15,2), default=0)
    itc_availability:   Mapped[str]           = mapped_column(String(30), default="available")
    is_reverse_charge:  Mapped[bool]          = mapped_column(Boolean, default=False)
    gstr1_filing_date:  Mapped[Optional[date]] = mapped_column(Date)
    created_at:         Mapped[datetime]      = mapped_column(DateTime, default=func.now())

    company: Mapped["Company"] = relationship("Company", back_populates="gstr2b_invoices")


# ── Purchase Register ─────────────────────────────────────────

class PurchaseRegister(UUIDMixin, Base):
    __tablename__ = "purchase_register"

    company_id:     Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    upload_id:      Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("file_uploads.id"))
    period_month:   Mapped[int]           = mapped_column(Integer, nullable=False)
    period_year:    Mapped[int]           = mapped_column(Integer, nullable=False)
    invoice_number: Mapped[str]           = mapped_column(String(50), nullable=False)
    invoice_date:   Mapped[date]          = mapped_column(Date, nullable=False)
    supplier_gstin: Mapped[Optional[str]] = mapped_column(String(15), index=True)
    supplier_name:  Mapped[str]           = mapped_column(String(200), nullable=False)
    hsn_code:       Mapped[Optional[str]] = mapped_column(String(10))
    description:    Mapped[Optional[str]] = mapped_column(Text)
    taxable_value:  Mapped[Decimal]       = mapped_column(Numeric(15,2), default=0)
    igst:           Mapped[Decimal]       = mapped_column(Numeric(15,2), default=0)
    cgst:           Mapped[Decimal]       = mapped_column(Numeric(15,2), default=0)
    sgst:           Mapped[Decimal]       = mapped_column(Numeric(15,2), default=0)
    cess:           Mapped[Decimal]       = mapped_column(Numeric(15,2), default=0)
    total_value:    Mapped[Decimal]       = mapped_column(Numeric(15,2), default=0)
    gst_rate:       Mapped[Optional[Decimal]] = mapped_column(Numeric(5,2))
    itc_eligible:   Mapped[bool]          = mapped_column(Boolean, default=True)
    itc_claimed:    Mapped[Decimal]       = mapped_column(Numeric(15,2), default=0)
    expense_head:   Mapped[Optional[str]] = mapped_column(String(100))
    voucher_number: Mapped[Optional[str]] = mapped_column(String(50))
    created_at:     Mapped[datetime]      = mapped_column(DateTime, default=func.now())

    company: Mapped["Company"] = relationship("Company", back_populates="purchase_register")


# ── Sales Register ────────────────────────────────────────────

class SalesRegister(UUIDMixin, Base):
    __tablename__ = "sales_register"

    company_id:     Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    upload_id:      Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("file_uploads.id"))
    period_month:   Mapped[int]           = mapped_column(Integer, nullable=False)
    period_year:    Mapped[int]           = mapped_column(Integer, nullable=False)
    invoice_number: Mapped[str]           = mapped_column(String(50), nullable=False)
    invoice_date:   Mapped[date]          = mapped_column(Date, nullable=False)
    customer_gstin: Mapped[Optional[str]] = mapped_column(String(15))
    customer_name:  Mapped[str]           = mapped_column(String(200), nullable=False)
    place_of_supply:Mapped[Optional[str]] = mapped_column(String(2))
    hsn_code:       Mapped[Optional[str]] = mapped_column(String(10))
    description:    Mapped[Optional[str]] = mapped_column(Text)
    taxable_value:  Mapped[Decimal]       = mapped_column(Numeric(15,2), default=0)
    igst:           Mapped[Decimal]       = mapped_column(Numeric(15,2), default=0)
    cgst:           Mapped[Decimal]       = mapped_column(Numeric(15,2), default=0)
    sgst:           Mapped[Decimal]       = mapped_column(Numeric(15,2), default=0)
    cess:           Mapped[Decimal]       = mapped_column(Numeric(15,2), default=0)
    total_value:    Mapped[Decimal]       = mapped_column(Numeric(15,2), default=0)
    gst_rate:       Mapped[Optional[Decimal]] = mapped_column(Numeric(5,2))
    invoice_type:   Mapped[str]           = mapped_column(String(20), default="B2B")
    is_export:      Mapped[bool]          = mapped_column(Boolean, default=False)
    voucher_number: Mapped[Optional[str]] = mapped_column(String(50))
    created_at:     Mapped[datetime]      = mapped_column(DateTime, default=func.now())

    company: Mapped["Company"] = relationship("Company", back_populates="sales_register")


# ── Reconciliation Run ────────────────────────────────────────

class ReconciliationRun(UUIDMixin, Base):
    __tablename__ = "reconciliation_runs"

    company_id:     Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    run_by:         Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    recon_type:     Mapped[str]           = mapped_column(String(30), nullable=False)
    period_month:   Mapped[int]           = mapped_column(Integer, nullable=False)
    period_year:    Mapped[int]           = mapped_column(Integer, nullable=False)
    status:         Mapped[str]           = mapped_column(String(20), default="running")
    total_invoices: Mapped[int]           = mapped_column(Integer, default=0)
    matched_count:  Mapped[int]           = mapped_column(Integer, default=0)
    mismatch_count: Mapped[int]           = mapped_column(Integer, default=0)
    missing_count:  Mapped[int]           = mapped_column(Integer, default=0)
    duplicate_count:Mapped[int]           = mapped_column(Integer, default=0)
    itc_impact:     Mapped[Decimal]       = mapped_column(Numeric(15,2), default=0)
    summary_json:   Mapped[Optional[dict]]= mapped_column(JSONB)
    error_log:      Mapped[Optional[str]] = mapped_column(Text)
    started_at:     Mapped[datetime]      = mapped_column(DateTime, default=func.now())
    completed_at:   Mapped[Optional[datetime]] = mapped_column(DateTime)

    company: Mapped["Company"]                  = relationship("Company", back_populates="recon_runs")
    items:   Mapped[List["ReconciliationItem"]]  = relationship("ReconciliationItem", back_populates="run")


# ── Reconciliation Item ───────────────────────────────────────

class ReconciliationItem(UUIDMixin, Base):
    __tablename__ = "reconciliation_items"

    run_id:         Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), ForeignKey("reconciliation_runs.id"), nullable=False, index=True)
    company_id:     Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    invoice_number: Mapped[Optional[str]] = mapped_column(String(50))
    invoice_date:   Mapped[Optional[date]] = mapped_column(Date)
    supplier_gstin: Mapped[Optional[str]] = mapped_column(String(15))
    party_name:     Mapped[Optional[str]] = mapped_column(String(200))
    invoice_type:   Mapped[Optional[str]] = mapped_column(String(20))
    books_taxable:  Mapped[Optional[Decimal]] = mapped_column(Numeric(15,2))
    books_igst:     Mapped[Optional[Decimal]] = mapped_column(Numeric(15,2))
    books_cgst:     Mapped[Optional[Decimal]] = mapped_column(Numeric(15,2))
    books_sgst:     Mapped[Optional[Decimal]] = mapped_column(Numeric(15,2))
    gstr_taxable:   Mapped[Optional[Decimal]] = mapped_column(Numeric(15,2))
    gstr_igst:      Mapped[Optional[Decimal]] = mapped_column(Numeric(15,2))
    gstr_cgst:      Mapped[Optional[Decimal]] = mapped_column(Numeric(15,2))
    gstr_sgst:      Mapped[Optional[Decimal]] = mapped_column(Numeric(15,2))
    mismatch_type:  Mapped[Optional[str]] = mapped_column(String(30), index=True)
    mismatch_reason:Mapped[Optional[str]] = mapped_column(Text)
    itc_impact:     Mapped[Decimal]       = mapped_column(Numeric(15,2), default=0)
    risk_level:     Mapped[str]           = mapped_column(String(10), default="low")
    is_resolved:    Mapped[bool]          = mapped_column(Boolean, default=False)
    resolution_note:Mapped[Optional[str]] = mapped_column(Text)
    resolved_by:    Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    resolved_at:    Mapped[Optional[datetime]]  = mapped_column(DateTime)
    created_at:     Mapped[datetime]      = mapped_column(DateTime, default=func.now())

    run: Mapped["ReconciliationRun"] = relationship("ReconciliationRun", back_populates="items")


# ── Vendor ────────────────────────────────────────────────────

class Vendor(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "vendors"
    __table_args__ = (UniqueConstraint("company_id", "gstin"),)

    company_id:             Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    gstin:                  Mapped[str]           = mapped_column(String(15), nullable=False, index=True)
    name:                   Mapped[str]           = mapped_column(String(200), nullable=False)
    pan:                    Mapped[Optional[str]] = mapped_column(String(10))
    email:                  Mapped[Optional[str]] = mapped_column(String(200))
    phone:                  Mapped[Optional[str]] = mapped_column(String(15))
    state_code:             Mapped[Optional[str]] = mapped_column(String(2))
    registration_status:    Mapped[str]           = mapped_column(String(30), default="active")
    gstr1_filing_status:    Mapped[str]           = mapped_column(String(20), default="unknown")
    last_filing_date:       Mapped[Optional[date]] = mapped_column(Date)
    risk_score:             Mapped[int]           = mapped_column(Integer, default=0)
    risk_level:             Mapped[str]           = mapped_column(String(10), default="low", index=True)
    total_purchases:        Mapped[Decimal]       = mapped_column(Numeric(15,2), default=0)
    total_itc:              Mapped[Decimal]       = mapped_column(Numeric(15,2), default=0)
    itc_at_risk:            Mapped[Decimal]       = mapped_column(Numeric(15,2), default=0)
    follow_up_sent:         Mapped[bool]          = mapped_column(Boolean, default=False)
    last_follow_up:         Mapped[Optional[datetime]] = mapped_column(DateTime)
    notes:                  Mapped[Optional[str]] = mapped_column(Text)

    company: Mapped["Company"] = relationship("Company", back_populates="vendors")


# ── AI Insight ────────────────────────────────────────────────

class AIInsight(UUIDMixin, Base):
    __tablename__ = "ai_insights"

    company_id:      Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    run_id:          Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("reconciliation_runs.id"))
    period_month:    Mapped[Optional[int]] = mapped_column(Integer)
    period_year:     Mapped[Optional[int]] = mapped_column(Integer)
    insight_type:    Mapped[str]           = mapped_column(String(50), nullable=False)
    title:           Mapped[str]           = mapped_column(String(300), nullable=False)
    description:     Mapped[str]           = mapped_column(Text, nullable=False)
    risk_level:      Mapped[Optional[str]] = mapped_column(String(10))
    financial_impact:Mapped[Decimal]       = mapped_column(Numeric(15,2), default=0)
    suggested_action:Mapped[Optional[str]] = mapped_column(Text)
    is_addressed:    Mapped[bool]          = mapped_column(Boolean, default=False)
    model_used:      Mapped[str]           = mapped_column(String(50), default="claude-3-5-sonnet")
    tokens_used:     Mapped[Optional[int]] = mapped_column(Integer)
    created_at:      Mapped[datetime]      = mapped_column(DateTime, default=func.now())


# ── AuditLog ──────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id:          Mapped[int]              = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id:   Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    user_id:     Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    company_id:  Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"))
    action:      Mapped[str]              = mapped_column(String(100), nullable=False)
    entity_type: Mapped[Optional[str]]    = mapped_column(String(50))
    entity_id:   Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    old_value:   Mapped[Optional[dict]]   = mapped_column(JSONB)
    new_value:   Mapped[Optional[dict]]   = mapped_column(JSONB)
    ip_address:  Mapped[Optional[str]]    = mapped_column(String(45))
    user_agent:  Mapped[Optional[str]]    = mapped_column(Text)
    created_at:  Mapped[datetime]         = mapped_column(DateTime, default=func.now(), index=True)
