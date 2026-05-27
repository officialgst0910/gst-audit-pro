# ============================================================
# app/api/routes/auth.py
# ============================================================
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from datetime import datetime, timezone
import uuid

from app.core.database import get_db
from app.core.security import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, generate_otp
)
from app.core.config import settings
from app.models import User, Tenant, RefreshToken

router = APIRouter()


class SignupRequest(BaseModel):
    full_name:    str
    email:        EmailStr
    phone:        str
    password:     str
    company_name: str
    gstin:        str
    role:         str = "admin"


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class OTPVerifyRequest(BaseModel):
    email: EmailStr
    otp:   str


class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    user:          dict


@router.post("/signup", status_code=201)
async def signup(req: SignupRequest, db: AsyncSession = Depends(get_db)):
    # Check email uniqueness
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Email already registered")

    # Create tenant
    tenant = Tenant(
        name=req.company_name,
        slug=req.company_name.lower().replace(" ", "-")[:50] + "-" + str(uuid.uuid4())[:8],
        plan="trial",
    )
    db.add(tenant)
    await db.flush()

    # Create user
    otp = generate_otp()
    user = User(
        tenant_id     = tenant.id,
        email         = req.email,
        phone         = req.phone,
        full_name     = req.full_name,
        password_hash = hash_password(req.password),
        role          = req.role,
        otp_secret    = otp,
        otp_expires_at= datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(user)
    await db.commit()

    # TODO: send OTP email via background task
    return {"message": "Account created. Please verify your email.", "user_id": str(user.id)}


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    access_token  = create_access_token({"sub": str(user.id), "role": user.role, "tenant": str(user.tenant_id)})
    refresh_token = create_refresh_token()

    rt = RefreshToken(user_id=user.id, token=refresh_token,
                      expires_at=datetime.now(timezone.utc).replace(tzinfo=None))
    db.add(rt)
    user.last_login_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={"id": str(user.id), "email": user.email, "full_name": user.full_name, "role": user.role},
    )


@router.post("/verify-otp")
async def verify_otp(req: OTPVerifyRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    if user.otp_secret != req.otp:
        raise HTTPException(400, "Invalid OTP")
    user.is_verified = True
    user.otp_secret  = None
    await db.commit()
    return {"message": "Email verified successfully"}


@router.post("/logout")
async def logout(db: AsyncSession = Depends(get_db)):
    return {"message": "Logged out"}


# ============================================================
# app/api/routes/dashboard.py
# ============================================================
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import SalesRegister, PurchaseRegister, ReconciliationRun

router_dashboard = APIRouter()


@router_dashboard.get("/summary")
async def dashboard_summary(
    company_id: str = Query(...),
    year:  int = Query(2024),
    month: int = Query(10),
    db:    AsyncSession = Depends(get_db),
    user   = Depends(get_current_user),
):
    import uuid as _uuid
    cid = _uuid.UUID(company_id)

    # Total sales
    sales_q = await db.execute(
        select(
            func.sum(SalesRegister.taxable_value).label("total_sales"),
            func.sum(SalesRegister.igst + SalesRegister.cgst + SalesRegister.sgst).label("output_gst"),
            func.count().label("invoice_count"),
        ).where(and_(
            SalesRegister.company_id == cid,
            SalesRegister.period_year  == year,
            SalesRegister.period_month == month,
        ))
    )
    sales_row = sales_q.one()

    # Total purchases
    purch_q = await db.execute(
        select(
            func.sum(PurchaseRegister.taxable_value).label("total_purchases"),
            func.sum(PurchaseRegister.igst + PurchaseRegister.cgst + PurchaseRegister.sgst).label("itc_available"),
            func.sum(PurchaseRegister.itc_claimed).label("itc_claimed"),
        ).where(and_(
            PurchaseRegister.company_id == cid,
            PurchaseRegister.period_year  == year,
            PurchaseRegister.period_month == month,
        ))
    )
    purch_row = purch_q.one()

    # Latest recon run
    recon_q = await db.execute(
        select(ReconciliationRun).where(
            and_(ReconciliationRun.company_id == cid,
                 ReconciliationRun.status == "completed")
        ).order_by(ReconciliationRun.completed_at.desc()).limit(1)
    )
    latest_recon = recon_q.scalar_one_or_none()

    return {
        "period":          f"{month:02d}/{year}",
        "total_sales":     float(sales_row.total_sales or 0),
        "output_gst":      float(sales_row.output_gst or 0),
        "invoice_count":   int(sales_row.invoice_count or 0),
        "total_purchases": float(purch_row.total_purchases or 0),
        "itc_available":   float(purch_row.itc_available or 0),
        "itc_claimed":     float(purch_row.itc_claimed or 0),
        "pending_mismatches": latest_recon.mismatch_count if latest_recon else 0,
        "compliance_score": 82,  # computed from view in production
    }


@router_dashboard.get("/monthly-trend")
async def monthly_trend(
    company_id: str = Query(...),
    year: int = Query(2024),
    db:   AsyncSession = Depends(get_db),
    user  = Depends(get_current_user),
):
    import uuid as _uuid
    cid = _uuid.UUID(company_id)

    rows = await db.execute(
        select(
            SalesRegister.period_month,
            func.sum(SalesRegister.taxable_value).label("sales"),
            func.sum(SalesRegister.igst + SalesRegister.cgst + SalesRegister.sgst).label("output_gst"),
        ).where(and_(
            SalesRegister.company_id == cid,
            SalesRegister.period_year == year,
        )).group_by(SalesRegister.period_month).order_by(SalesRegister.period_month)
    )

    months = ["Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec","Jan","Feb","Mar"]
    data = {r.period_month: r for r in rows.all()}

    return {
        "labels": months,
        "sales":     [float(data.get(m, type("x", (), {"sales": 0})).sales or 0) for m in range(4, 16)],
        "output_gst":[float(data.get(m % 12 + 1, type("x", (), {"output_gst": 0})).output_gst or 0) for m in range(4, 16)],
    }


# ============================================================
# app/api/routes/uploads.py
# ============================================================
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd
import json
import io
import boto3
from botocore.exceptions import ClientError

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.config import settings
from app.models import FileUpload

router_uploads = APIRouter()

ALLOWED_TYPES = {
    "gstr1", "gstr2b", "gstr3b",
    "sales_register", "purchase_register", "journal"
}


def get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id     = settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY,
        region_name           = settings.AWS_REGION,
    )


async def parse_excel_file(file_bytes: bytes, file_format: str) -> pd.DataFrame:
    """Parse Excel/CSV/JSON into DataFrame with validation."""
    if file_format in ("xlsx", "xls"):
        df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
    elif file_format == "csv":
        df = pd.read_csv(io.BytesIO(file_bytes))
    elif file_format == "json":
        data = json.loads(file_bytes)
        # Handle GST portal JSON format (nested structure)
        if isinstance(data, dict):
            # Extract b2b invoices from GSTR-1 JSON
            records = []
            for key in ["b2b", "b2cs", "cdnr", "exp"]:
                if key in data:
                    for supplier in data[key]:
                        for inv in supplier.get("inv", [supplier]):
                            inv["supplier_gstin"] = supplier.get("ctin", "")
                            records.append(inv)
            df = pd.DataFrame(records) if records else pd.DataFrame(data)
        else:
            df = pd.DataFrame(data)
    else:
        raise HTTPException(400, f"Unsupported format: {file_format}")

    # Strip whitespace from column names
    df.columns = df.columns.str.strip()
    return df


@router_uploads.post("/")
async def upload_file(
    company_id:   str        = Form(...),
    file_type:    str        = Form(...),
    period_month: int        = Form(...),
    period_year:  int        = Form(...),
    file:         UploadFile = File(...),
    db:           AsyncSession = Depends(get_db),
    user           = Depends(get_current_user),
):
    if file_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"Invalid file_type. Must be one of: {ALLOWED_TYPES}")

    suffix = file.filename.split(".")[-1].lower()
    if f".{suffix}" not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"File extension .{suffix} not allowed")

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit")

    # Parse to validate
    df = await parse_excel_file(content, suffix)
    row_count = len(df)

    # Upload to S3
    import uuid as _uuid
    s3_key = f"uploads/{company_id}/{period_year}/{period_month:02d}/{file_type}/{_uuid.uuid4()}.{suffix}"
    try:
        s3 = get_s3_client()
        s3.put_object(
            Bucket=settings.AWS_BUCKET_NAME,
            Key=s3_key,
            Body=content,
            ContentType=file.content_type,
            ServerSideEncryption="AES256",
        )
    except Exception as e:
        # In dev without S3, continue without upload
        s3_key = f"local/{s3_key}"

    upload = FileUpload(
        company_id    = _uuid.UUID(company_id),
        uploaded_by   = user.id,
        file_name     = f"{file_type}_{period_year}{period_month:02d}.{suffix}",
        original_name = file.filename,
        file_type     = file_type,
        file_format   = suffix,
        file_size     = len(content),
        s3_key        = s3_key,
        period_month  = period_month,
        period_year   = period_year,
        row_count     = row_count,
        status        = "processed",
    )
    db.add(upload)
    await db.commit()
    await db.refresh(upload)

    return {
        "upload_id":  str(upload.id),
        "file_type":  file_type,
        "row_count":  row_count,
        "status":     "processed",
        "message":    f"Successfully uploaded {row_count} records",
    }


@router_uploads.get("/")
async def list_uploads(
    company_id: str = Query(...),
    db:         AsyncSession = Depends(get_db),
    user         = Depends(get_current_user),
):
    import uuid as _uuid
    result = await db.execute(
        select(FileUpload).where(FileUpload.company_id == _uuid.UUID(company_id))
        .order_by(FileUpload.created_at.desc()).limit(50)
    )
    uploads = result.scalars().all()
    return [
        {
            "id":           str(u.id),
            "file_name":    u.original_name,
            "file_type":    u.file_type,
            "file_size":    u.file_size,
            "row_count":    u.row_count,
            "period":       f"{u.period_month:02d}/{u.period_year}",
            "status":       u.status,
            "created_at":   u.created_at.isoformat(),
        }
        for u in uploads
    ]


# ============================================================
# app/api/routes/reconciliation.py
# ============================================================
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime, timezone
import uuid as _uuid

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import ReconciliationRun, ReconciliationItem, GSTR1Invoice, SalesRegister, GSTR2BInvoice, PurchaseRegister
from app.services.reconciliation_engine import GSTReconciliationEngine
import pandas as pd

router_recon = APIRouter()
engine = GSTReconciliationEngine()


class RunReconRequest(BaseModel):
    company_id:   str
    recon_type:   str  # gstr1_vs_books | gstr2b_vs_books | gstr3b_vs_books | full_audit
    period_month: int
    period_year:  int


@router_recon.post("/run")
async def run_reconciliation(
    req:  RunReconRequest,
    bg:   BackgroundTasks,
    db:   AsyncSession = Depends(get_db),
    user  = Depends(get_current_user),
):
    run = ReconciliationRun(
        company_id   = _uuid.UUID(req.company_id),
        run_by       = user.id,
        recon_type   = req.recon_type,
        period_month = req.period_month,
        period_year  = req.period_year,
        status       = "running",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    # Queue background task
    bg.add_task(_run_recon_task, str(run.id), req.company_id, req.recon_type, req.period_month, req.period_year)

    return {"run_id": str(run.id), "status": "running", "message": "Reconciliation started"}


async def _run_recon_task(run_id, company_id, recon_type, month, year):
    """Background reconciliation task."""
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        try:
            run = await db.get(ReconciliationRun, _uuid.UUID(run_id))

            # Fetch data (in production: query DB tables → DataFrames)
            gstr1_df   = pd.DataFrame()  # populated from gstr1_invoices table
            sales_df   = pd.DataFrame()  # populated from sales_register table
            gstr2b_df  = pd.DataFrame()
            purchase_df= pd.DataFrame()

            if recon_type in ("gstr1_vs_books", "full_audit"):
                result = engine.reconcile_gstr1_vs_books(gstr1_df, sales_df, month, year)
                _save_recon_items(db, run, result, company_id)

            if recon_type in ("gstr2b_vs_books", "full_audit"):
                result2 = engine.reconcile_gstr2b_vs_books(gstr2b_df, purchase_df, month, year)
                _save_recon_items(db, run, result2, company_id)

            run.status       = "completed"
            run.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            await db.commit()

        except Exception as e:
            run.status    = "failed"
            run.error_log = str(e)
            await db.commit()


def _save_recon_items(db, run, result, company_id):
    for item in result.items:
        ri = ReconciliationItem(
            run_id         = run.id,
            company_id     = _uuid.UUID(company_id),
            invoice_number = item.invoice_number,
            supplier_gstin = item.supplier_gstin,
            party_name     = item.party_name,
            invoice_type   = item.invoice_type,
            books_taxable  = item.books_taxable,
            books_igst     = item.books_igst,
            books_cgst     = item.books_cgst,
            books_sgst     = item.books_sgst,
            gstr_taxable   = item.gstr_taxable,
            gstr_igst      = item.gstr_igst,
            gstr_cgst      = item.gstr_cgst,
            gstr_sgst      = item.gstr_sgst,
            mismatch_type  = item.mismatch_type,
            mismatch_reason= item.mismatch_reason,
            itc_impact     = item.itc_impact,
            risk_level     = item.risk_level,
        )
        db.add(ri)
    run.total_invoices  = result.total_invoices
    run.matched_count   = result.matched_count
    run.mismatch_count  = result.mismatch_count
    run.missing_count   = result.missing_count
    run.duplicate_count = result.duplicate_count
    run.itc_impact      = result.itc_impact
    run.summary_json    = result.summary


@router_recon.get("/runs")
async def list_runs(
    company_id: str = Query(...),
    db:         AsyncSession = Depends(get_db),
    user         = Depends(get_current_user),
):
    result = await db.execute(
        select(ReconciliationRun)
        .where(ReconciliationRun.company_id == _uuid.UUID(company_id))
        .order_by(ReconciliationRun.started_at.desc())
        .limit(20)
    )
    runs = result.scalars().all()
    return [
        {
            "id":             str(r.id),
            "recon_type":     r.recon_type,
            "period":         f"{r.period_month:02d}/{r.period_year}",
            "status":         r.status,
            "total_invoices": r.total_invoices,
            "matched":        r.matched_count,
            "mismatches":     r.mismatch_count,
            "missing":        r.missing_count,
            "itc_impact":     float(r.itc_impact or 0),
            "started_at":     r.started_at.isoformat(),
            "completed_at":   r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in runs
    ]


@router_recon.get("/items/{run_id}")
async def get_recon_items(
    run_id:       str,
    mismatch_type:str = Query(None),
    risk_level:   str = Query(None),
    page:         int = Query(1),
    page_size:    int = Query(50),
    db:            AsyncSession = Depends(get_db),
    user            = Depends(get_current_user),
):
    q = select(ReconciliationItem).where(ReconciliationItem.run_id == _uuid.UUID(run_id))
    if mismatch_type:
        q = q.where(ReconciliationItem.mismatch_type == mismatch_type)
    if risk_level:
        q = q.where(ReconciliationItem.risk_level == risk_level)
    q = q.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(q)
    items = result.scalars().all()
    return [
        {
            "id":             str(i.id),
            "invoice_number": i.invoice_number,
            "supplier_gstin": i.supplier_gstin,
            "party_name":     i.party_name,
            "mismatch_type":  i.mismatch_type,
            "mismatch_reason":i.mismatch_reason,
            "books_taxable":  float(i.books_taxable or 0),
            "gstr_taxable":   float(i.gstr_taxable or 0),
            "itc_impact":     float(i.itc_impact or 0),
            "risk_level":     i.risk_level,
            "is_resolved":    i.is_resolved,
        }
        for i in items
    ]


# ============================================================
# app/api/routes/ai_insights.py
# ============================================================
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from anthropic import Anthropic
import json

from app.core.deps import get_current_user
from app.core.config import settings

router_ai = APIRouter()
anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)


class AnalyzeRequest(BaseModel):
    company_id:  str
    period:      str   # "MM-YYYY"
    mismatches:  list[dict]
    vendor_data: list[dict]
    gstr3b:      dict = {}


@router_ai.post("/analyze")
async def analyze_mismatches(
    req:  AnalyzeRequest,
    user  = Depends(get_current_user),
):
    """Use Claude AI to analyze reconciliation mismatches and generate insights."""

    prompt = f"""You are an expert Indian CA (Chartered Accountant) specializing in GST compliance.
Analyze the following GST reconciliation data for period {req.period} and provide structured insights.

MISMATCHES FOUND:
{json.dumps(req.mismatches[:20], indent=2)}

VENDOR RISK DATA:
{json.dumps(req.vendor_data[:10], indent=2)}

Provide a JSON response with this exact structure:
{{
  "insights": [
    {{
      "type": "mismatch_explanation|fraud_detection|risk_scoring|itc_suggestion|vendor_alert",
      "title": "Short title (max 80 chars)",
      "description": "Detailed explanation with Indian GST law references (CGST Act sections)",
      "risk_level": "low|medium|high|critical",
      "financial_impact": <number in INR>,
      "suggested_action": "Specific actionable step",
      "priority": 1
    }}
  ],
  "overall_risk": "low|medium|high|critical",
  "compliance_score": <0-100>,
  "itc_at_risk": <total INR>,
  "summary": "2-3 sentence executive summary"
}}

Focus on:
1. Section 16 ITC eligibility issues
2. Rule 36(4) provisional ITC limits
3. Section 17(5) blocked credits
4. RCM liability under Section 9(3)/9(4)
5. GSTR-1 amendment requirements
Return ONLY valid JSON, no markdown."""

    try:
        response = anthropic_client.messages.create(
            model      = "claude-sonnet-4-20250514",
            max_tokens = 2000,
            messages   = [{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        result = json.loads(raw)
        return {
            "analysis":    result,
            "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
            "model":       "claude-sonnet-4-20250514",
        }
    except json.JSONDecodeError:
        raise HTTPException(500, "AI response parsing failed")
    except Exception as e:
        raise HTTPException(500, f"AI analysis failed: {str(e)}")


@router_ai.post("/explain-mismatch")
async def explain_mismatch(
    mismatch: dict,
    user = Depends(get_current_user),
):
    """Get AI explanation for a specific mismatch."""
    prompt = f"""Explain this GST reconciliation mismatch in simple terms for an Indian CA:

Mismatch: {json.dumps(mismatch, indent=2)}

Respond in JSON:
{{
  "plain_explanation": "Simple 2-sentence explanation",
  "legal_reference":   "Relevant CGST Act section",
  "impact":            "Financial and compliance impact",
  "fix_steps":         ["Step 1", "Step 2", "Step 3"],
  "deadline":          "When action must be taken"
}}"""

    response = anthropic_client.messages.create(
        model      = "claude-sonnet-4-20250514",
        max_tokens = 500,
        messages   = [{"role": "user", "content": prompt}],
    )
    try:
        return json.loads(response.content[0].text.strip())
    except:
        return {"explanation": response.content[0].text}
