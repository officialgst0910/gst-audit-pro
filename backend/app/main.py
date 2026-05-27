# ============================================================
# GST Audit Pro — FastAPI Main Application
# ============================================================

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import time
import logging

from app.core.config import settings
from app.core.database import engine, Base
from app.api.routes import (
    auth, companies, uploads, reconciliation,
    gstr1, gstr2b, gstr3b, reports, vendors,
    ai_insights, admin, dashboard
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 GST Audit Pro API starting up...")
    # Create tables (use Alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database connected")
    yield
    logger.info("🛑 GST Audit Pro API shutting down...")


app = FastAPI(
    title="GST Audit Pro API",
    description="""
## GST Audit Pro — Professional GST Reconciliation & Audit Platform

### Features
- 🔐 JWT Authentication with RBAC
- 📊 GSTR-1 vs Books Reconciliation
- 🔍 GSTR-2B ITC Matching
- ✅ GSTR-3B Verification
- 🤖 AI-Powered Mismatch Analysis
- 📄 Automated Audit Reports
- 🏢 Multi-tenant, Multi-company Support

### Authentication
All protected endpoints require: `Authorization: Bearer <token>`
    """,
    version="2.4.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    contact={"name": "GST Audit Pro Support", "email": "support@gstauditpro.in"},
)

# ── Middleware ──────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def add_process_time(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    response.headers["X-Process-Time"] = f"{(time.time()-start)*1000:.1f}ms"
    return response


@app.middleware("http")
async def tenant_middleware(request: Request, call_next):
    """Inject tenant context from subdomain or header."""
    tenant_slug = request.headers.get("X-Tenant-Slug", "default")
    request.state.tenant_slug = tenant_slug
    return await call_next(request)


# ── Exception Handlers ──────────────────────────────────────

@app.exception_handler(404)
async def not_found(request, exc):
    return JSONResponse(status_code=404, content={"detail": "Resource not found"})


@app.exception_handler(500)
async def server_error(request, exc):
    logger.error(f"Server error: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# ── Routes ──────────────────────────────────────────────────

PREFIX = "/api/v1"

app.include_router(auth.router,           prefix=f"{PREFIX}/auth",           tags=["Authentication"])
app.include_router(companies.router,      prefix=f"{PREFIX}/companies",      tags=["Companies"])
app.include_router(dashboard.router,      prefix=f"{PREFIX}/dashboard",      tags=["Dashboard"])
app.include_router(uploads.router,        prefix=f"{PREFIX}/uploads",        tags=["File Uploads"])
app.include_router(reconciliation.router, prefix=f"{PREFIX}/reconciliation", tags=["Reconciliation"])
app.include_router(gstr1.router,          prefix=f"{PREFIX}/gstr1",          tags=["GSTR-1"])
app.include_router(gstr2b.router,         prefix=f"{PREFIX}/gstr2b",         tags=["GSTR-2B"])
app.include_router(gstr3b.router,         prefix=f"{PREFIX}/gstr3b",         tags=["GSTR-3B"])
app.include_router(vendors.router,        prefix=f"{PREFIX}/vendors",        tags=["Vendors"])
app.include_router(reports.router,        prefix=f"{PREFIX}/reports",        tags=["Reports"])
app.include_router(ai_insights.router,    prefix=f"{PREFIX}/ai",             tags=["AI Insights"])
app.include_router(admin.router,          prefix=f"{PREFIX}/admin",          tags=["Admin"])


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "GST Audit Pro API",
        "version": "2.4.0",
        "status": "operational",
        "docs": "/docs"
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "timestamp": time.time()}
