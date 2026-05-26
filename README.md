# GST Audit Pro — Full Stack SaaS Platform

> India's Professional GST Reconciliation & Audit Platform for CAs, Tax Consultants & CFOs

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS, ShadCN UI |
| Charts | Recharts, Chart.js |
| Backend | Python 3.12, FastAPI 0.111 |
| Reconciliation | Pandas 2.2, NumPy |
| Database | PostgreSQL 16, SQLAlchemy 2.0, Alembic |
| Auth | JWT + Refresh Tokens, bcrypt |
| Cache | Redis 7 |
| Storage | AWS S3 / MinIO |
| Queue | Celery + Redis |
| AI | Anthropic Claude API |
| Deployment | Docker, Docker Compose, Nginx |

---

## Project Structure

```
gst-audit-pro/
├── frontend/                    # Next.js 15 App
│   ├── src/
│   │   ├── app/                 # App Router pages
│   │   │   ├── (auth)/          # Login, Signup
│   │   │   ├── (dashboard)/     # Protected routes
│   │   │   │   ├── dashboard/
│   │   │   │   ├── upload/
│   │   │   │   ├── reconciliation/
│   │   │   │   ├── reports/
│   │   │   │   ├── gstr1/
│   │   │   │   ├── gstr2b/
│   │   │   │   ├── gstr3b/
│   │   │   │   ├── ai-insights/
│   │   │   │   ├── vendors/
│   │   │   │   └── admin/
│   │   │   └── (landing)/       # Public pages
│   │   ├── components/
│   │   │   ├── ui/              # ShadCN components
│   │   │   ├── layout/          # Sidebar, Topbar
│   │   │   ├── charts/          # Recharts wrappers
│   │   │   ├── tables/          # Data tables
│   │   │   └── forms/           # Upload forms
│   │   ├── lib/                 # API client, utils
│   │   ├── hooks/               # Custom React hooks
│   │   └── types/               # TypeScript interfaces
│   └── public/
│
├── backend/                     # FastAPI Application
│   ├── app/
│   │   ├── main.py              # FastAPI app entry
│   │   ├── api/routes/          # All API endpoints
│   │   ├── core/                # Config, security, deps
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── services/            # Business logic
│   │   └── utils/               # Helpers
│   ├── alembic/                 # DB migrations
│   └── tests/
│
├── database/
│   └── schema.sql               # Full DB schema
│
├── docs/
│   └── api.md                   # API documentation
│
├── docker-compose.yml
└── README.md
```

---

## Quick Start

### Prerequisites
- Node.js 20+
- Python 3.12+
- PostgreSQL 16
- Redis 7

### 1. Clone & Setup

```bash
git clone https://github.com/yourorg/gst-audit-pro
cd gst-audit-pro
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your DB credentials

# Run migrations
alembic upgrade head

# Seed sample data
python scripts/seed_data.py

# Start server
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup

```bash
cd frontend
npm install
cp .env.local.example .env.local
# Edit .env.local with API URL
npm run dev
```

### 4. Docker (Recommended)

```bash
docker-compose up -d
# App: http://localhost:3000
# API: http://localhost:8000/docs
```

---

## Default Credentials

| Role | Email | Password |
|------|-------|----------|
| Super Admin | admin@gstauditpro.in | Admin@123 |
| CA User | ca@demo.in | Demo@123 |
| Company User | user@demo.in | Demo@123 |

---

## API Documentation

Interactive docs: `http://localhost:8000/docs` (Swagger UI)
ReDoc: `http://localhost:8000/redoc`
