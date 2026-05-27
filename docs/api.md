# GST Audit Pro — API Documentation
**Version:** 2.4.0 | **Base URL:** `https://api.gstauditpro.in/api/v1`

---

## Authentication

All protected endpoints require JWT Bearer token:
```
Authorization: Bearer <access_token>
```

---

## Endpoints

### 🔐 Auth

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/signup` | Create account + tenant |
| POST | `/auth/login` | Login → JWT tokens |
| POST | `/auth/verify-otp` | Verify email OTP |
| POST | `/auth/refresh` | Refresh access token |
| POST | `/auth/logout` | Revoke refresh token |

#### POST `/auth/login`
```json
// Request
{ "email": "ca@firm.com", "password": "Secret@123" }

// Response 200
{
  "access_token":  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "dGhpcyBpcyBhIHJlZnJlc2ggdG9rZW4...",
  "token_type":    "bearer",
  "user": {
    "id":        "550e8400-e29b-41d4-a716-446655440000",
    "email":     "ca@firm.com",
    "full_name": "CA Rajesh Mehta",
    "role":      "ca"
  }
}
```

---

### 🏢 Companies

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/companies/` | List all companies for tenant |
| POST | `/companies/` | Create new company/GSTIN |
| GET  | `/companies/{id}` | Get company details |
| PUT  | `/companies/{id}` | Update company |
| DELETE | `/companies/{id}` | Deactivate company |

#### POST `/companies/`
```json
// Request
{
  "name":              "Tech Mahindra Ltd",
  "gstin":             "27AABCT0898L1ZB",
  "pan":               "AABCT0898L",
  "state_code":        "27",
  "registration_type": "regular",
  "address":           "Pune, Maharashtra",
  "email":             "gst@techmahindra.com"
}
```

---

### 📁 File Uploads

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/uploads/` | Upload GST file (multipart) |
| GET  | `/uploads/` | List uploaded files |
| GET  | `/uploads/{id}` | Get upload details |
| DELETE | `/uploads/{id}` | Delete upload |

#### POST `/uploads/` (multipart/form-data)
```
company_id:   <uuid>
file_type:    gstr1 | gstr2b | gstr3b | sales_register | purchase_register | journal
period_month: 1–12
period_year:  2024
file:         <binary>
```

Response:
```json
{
  "upload_id": "uuid",
  "file_type": "gstr1",
  "row_count": 284,
  "status":    "processed",
  "message":   "Successfully uploaded 284 records"
}
```

---

### 🔄 Reconciliation

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/reconciliation/run` | Start reconciliation job |
| GET  | `/reconciliation/runs` | List all runs |
| GET  | `/reconciliation/runs/{id}` | Get run status |
| GET  | `/reconciliation/items/{run_id}` | Get mismatch items |
| PATCH | `/reconciliation/items/{id}/resolve` | Mark item resolved |

#### POST `/reconciliation/run`
```json
{
  "company_id":   "uuid",
  "recon_type":   "gstr1_vs_books",
  "period_month": 10,
  "period_year":  2024
}
// recon_type options: gstr1_vs_books | gstr2b_vs_books | gstr3b_vs_books | full_audit
```

#### GET `/reconciliation/items/{run_id}`
Query params: `mismatch_type`, `risk_level`, `page`, `page_size`

```json
[
  {
    "id":              "uuid",
    "invoice_number":  "INV-2024-003",
    "supplier_gstin":  "33AAACV0209R1Z1",
    "party_name":      "Wipro Ltd",
    "mismatch_type":   "missing_in_gstr",
    "mismatch_reason": "Invoice in Sales Register not in GSTR-1",
    "books_taxable":   155000.00,
    "gstr_taxable":    null,
    "itc_impact":      27900.00,
    "risk_level":      "high",
    "is_resolved":     false
  }
]
```

---

### 📊 Dashboard

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/dashboard/summary` | KPI summary |
| GET | `/dashboard/monthly-trend` | 12-month chart data |
| GET | `/dashboard/compliance-score` | Company compliance score |

#### GET `/dashboard/summary?company_id=uuid&year=2024&month=10`
```json
{
  "period":             "10/2024",
  "total_sales":        48236000.00,
  "output_gst":         8682480.00,
  "invoice_count":      1284,
  "total_purchases":    31472000.00,
  "itc_available":      5664960.00,
  "itc_claimed":        5231200.00,
  "pending_mismatches": 47,
  "compliance_score":   82
}
```

---

### 👥 Vendors

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/vendors/` | List vendors with risk scores |
| GET  | `/vendors/{id}` | Vendor details + ITC history |
| POST | `/vendors/follow-up` | Send email reminders |
| PATCH | `/vendors/{id}/risk` | Update risk level |
| GET  | `/vendors/at-risk` | High-risk vendors only |

---

### 📄 GSTR-1

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/gstr1/summary` | B2B/B2CS/Export totals |
| GET | `/gstr1/invoices` | Paginated invoice list |
| GET | `/gstr1/unreported` | Invoices missing from GSTR-1 |
| GET | `/gstr1/comparison` | Month-wise Books vs GSTR-1 |

---

### 📋 GSTR-2B

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/gstr2b/summary` | ITC summary |
| GET | `/gstr2b/invoices` | Paginated ITC records |
| GET | `/gstr2b/unclaimed` | Unclaimed ITC invoices |
| GET | `/gstr2b/ineligible` | Section 17(5) blocked |

---

### ✅ GSTR-3B

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/gstr3b/comparison` | 3B vs Books head-wise |
| GET | `/gstr3b/rcm-audit` | RCM liability summary |
| GET | `/gstr3b/rate-validation` | HSN rate errors |

---

### 📑 Reports

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/reports/generate` | Queue report generation |
| GET  | `/reports/` | List generated reports |
| GET  | `/reports/{id}/download` | Download report file |
| DELETE | `/reports/{id}` | Delete report |

#### POST `/reports/generate`
```json
{
  "company_id":  "uuid",
  "report_type": "gst_audit",
  "period_from": "2024-04-01",
  "period_to":   "2025-03-31",
  "file_format": "xlsx"
}
// report_type: gst_audit | reconciliation_summary | exception_report | vendor_followup | itc_utilization
// file_format: pdf | xlsx | csv
```

---

### 🤖 AI Insights

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/ai/analyze` | Full AI analysis of reconciliation |
| POST | `/ai/explain-mismatch` | Explain one mismatch |
| GET  | `/ai/insights` | List stored insights |
| PATCH | `/ai/insights/{id}/address` | Mark insight addressed |

#### POST `/ai/analyze`
```json
{
  "company_id":  "uuid",
  "period":      "10-2024",
  "mismatches":  [...],
  "vendor_data": [...]
}

// Response
{
  "analysis": {
    "insights": [
      {
        "type":             "fraud_detection",
        "title":            "Potential Invoice Inflation",
        "description":      "Vendor 29AADCS2649N1Z1 shows pattern consistent with circular trading...",
        "risk_level":       "high",
        "financial_impact": 162000,
        "suggested_action": "Verify physical delivery with GRN. Cross-check with Form 26AS.",
        "priority":         1
      }
    ],
    "overall_risk":    "medium",
    "compliance_score": 82,
    "itc_at_risk":      718700,
    "summary":          "47 mismatches detected with ₹7.19L ITC at risk..."
  },
  "tokens_used": 1842,
  "model":       "claude-sonnet-4-20250514"
}
```

---

### ⚙️ Admin

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/admin/tenants` | List all tenants |
| GET  | `/admin/stats` | Platform-wide stats |
| GET  | `/admin/audit-logs` | User activity logs |
| POST | `/admin/tenants/{id}/plan` | Change subscription plan |
| GET  | `/admin/subscriptions` | All active subscriptions |

---

## Error Codes

| Code | Meaning |
|------|---------|
| 400 | Bad request / validation error |
| 401 | Unauthenticated — invalid/expired token |
| 403 | Forbidden — insufficient role |
| 404 | Resource not found |
| 413 | File too large (>50MB) |
| 422 | Unprocessable entity |
| 429 | Rate limit exceeded |
| 500 | Server error |

---

## Rate Limits

| Plan | Requests/min | File Uploads/day | Recon Runs/day |
|------|-------------|-----------------|----------------|
| Trial | 60 | 10 | 5 |
| Starter | 120 | 50 | 20 |
| Professional | 300 | Unlimited | Unlimited |
| Enterprise | Custom | Custom | Custom |

---

## Webhooks

Configure webhooks at `/admin/webhooks` for:
- `reconciliation.completed` — when a recon run finishes
- `report.ready` — when a report is generated
- `vendor.risk_changed` — when vendor risk level changes
- `upload.processed` — when file processing completes

Payload:
```json
{
  "event":    "reconciliation.completed",
  "run_id":   "uuid",
  "company_id":"uuid",
  "timestamp":"2024-11-01T10:30:00Z",
  "data":     { "matched": 1206, "mismatches": 47 }
}
```
