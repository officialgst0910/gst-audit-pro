# GST Audit Pro — Quick Deployment Guide
## Everything is browser-based. No installation needed.

---

## STEP 1 — GitHub (5 min)
1. Go to github.com/signup → create free account
2. Click + → New repository → name: gst-audit-pro → Public → Create
3. Upload this entire zip contents to the repository
   - Click "Add file" → "Upload files"
   - Drag and drop ALL files and folders from this zip
   - Click "Commit changes"

---

## STEP 2 — Supabase Database (5 min)
1. Go to supabase.com → sign up with GitHub
2. New Project → name: gstauditpro → Singapore region → set password → Create
3. SQL Editor → New query → open database/schema.sql → copy all → paste → Run
4. SQL Editor → New query → open database/seed_data.sql → copy all → paste → Run
5. Settings → Database → copy Connection string (URI format)
   - Change start from: postgresql://
   - Change to: postgresql+asyncpg://

---

## STEP 3 — Render Backend (5 min)
1. Go to render.com → sign up with GitHub
2. New → Web Service → connect gst-audit-pro repo
3. Settings:
   - Root Directory: backend
   - Build Command: pip install -r requirements.txt
   - Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
   - Instance Type: Free
4. Environment Variables (add each):
   - DATABASE_URL = your supabase URI (postgresql+asyncpg://...)
   - SECRET_KEY = any 40 random characters
   - DEBUG = false
5. Click Create Web Service → wait 3-5 min
6. Test: open https://YOUR-SERVICE.onrender.com/health → should show {"status":"ok"}

---

## STEP 4 — Vercel Frontend (3 min)
1. Go to vercel.com → sign up with GitHub
2. New Project → import gst-audit-pro
3. Root Directory → Edit → type: frontend → Continue
4. Environment Variables:
   - NEXT_PUBLIC_API_URL = https://YOUR-SERVICE.onrender.com
   - NEXT_PUBLIC_APP_NAME = GST Audit Pro
5. Click Deploy → wait 2 min
6. Your app is live at https://your-app.vercel.app

---

## Login Credentials (after seed data is loaded)
- Admin: admin@gstauditpro.in / Admin@123
- CA: ca@demo.in / Demo@123
- User: user@demo.in / Demo@123

---

## File Structure
```
gst-audit-pro/
├── backend/               ← Python FastAPI (deploy on Render)
│   ├── app/
│   │   ├── main.py        ← API entry point
│   │   ├── core/config.py ← settings & JWT
│   │   ├── models/        ← database models
│   │   ├── api/routes/    ← all API endpoints
│   │   └── services/      ← reconciliation engine, AI, reports
│   ├── requirements.txt   ← Python packages
│   └── Dockerfile         ← for Render
├── frontend/              ← Next.js app (deploy on Vercel)
│   ├── src/app/           ← all pages
│   │   ├── page.tsx       ← landing page
│   │   ├── login/         ← login page
│   │   ├── dashboard/     ← main dashboard
│   │   └── ...            ← other pages
│   ├── package.json       ← npm packages list
│   ├── next.config.ts     ← Next.js settings
│   └── tailwind.config.ts ← styling config
└── database/
    ├── schema.sql         ← run FIRST in Supabase
    └── seed_data.sql      ← run SECOND (demo data)
```
