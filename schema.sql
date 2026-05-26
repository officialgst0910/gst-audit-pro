-- ============================================================
-- GST AUDIT PRO — Complete PostgreSQL Database Schema
-- Version: 2.4 | FY 2024-25
-- ============================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- TENANTS & COMPANIES
-- ============================================================

CREATE TABLE tenants (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(200) NOT NULL,
    slug            VARCHAR(100) UNIQUE NOT NULL,
    plan            VARCHAR(50) NOT NULL DEFAULT 'trial' CHECK (plan IN ('trial','starter','professional','enterprise')),
    plan_expires_at TIMESTAMP,
    max_gstins      INTEGER NOT NULL DEFAULT 1,
    max_users       INTEGER NOT NULL DEFAULT 5,
    max_invoices    INTEGER NOT NULL DEFAULT 500,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE companies (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name            VARCHAR(200) NOT NULL,
    gstin           VARCHAR(15) NOT NULL,
    pan             VARCHAR(10) NOT NULL,
    trade_name      VARCHAR(200),
    address         TEXT,
    state_code      VARCHAR(2) NOT NULL,
    email           VARCHAR(200),
    phone           VARCHAR(15),
    registration_type VARCHAR(50) DEFAULT 'regular' CHECK (registration_type IN ('regular','composition','sez','uin')),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, gstin)
);

CREATE INDEX idx_companies_gstin ON companies(gstin);
CREATE INDEX idx_companies_tenant ON companies(tenant_id);

-- ============================================================
-- USERS & AUTH
-- ============================================================

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email           VARCHAR(200) NOT NULL,
    phone           VARCHAR(15),
    full_name       VARCHAR(200) NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    role            VARCHAR(50) NOT NULL DEFAULT 'user' CHECK (role IN ('super_admin','admin','ca','user','viewer')),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified     BOOLEAN NOT NULL DEFAULT FALSE,
    last_login_at   TIMESTAMP,
    otp_secret      VARCHAR(100),
    otp_expires_at  TIMESTAMP,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, email)
);

CREATE TABLE user_company_access (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    company_id  UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    permissions JSONB NOT NULL DEFAULT '{"read":true,"write":false,"export":false,"admin":false}',
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, company_id)
);

CREATE TABLE refresh_tokens (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token       VARCHAR(500) NOT NULL UNIQUE,
    expires_at  TIMESTAMP NOT NULL,
    revoked_at  TIMESTAMP,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ============================================================
-- FILE UPLOADS
-- ============================================================

CREATE TABLE file_uploads (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    uploaded_by     UUID NOT NULL REFERENCES users(id),
    file_name       VARCHAR(300) NOT NULL,
    original_name   VARCHAR(300) NOT NULL,
    file_type       VARCHAR(50) NOT NULL CHECK (file_type IN (
                        'gstr1','gstr2b','gstr3b','sales_register',
                        'purchase_register','journal','cdnr','b2b','b2cs'
                    )),
    file_format     VARCHAR(10) NOT NULL CHECK (file_format IN ('xlsx','csv','json')),
    file_size       BIGINT NOT NULL,
    s3_key          VARCHAR(500) NOT NULL,
    period_month    INTEGER CHECK (period_month BETWEEN 1 AND 12),
    period_year     INTEGER CHECK (period_year BETWEEN 2017 AND 2099),
    row_count       INTEGER,
    status          VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','processing','processed','failed','validated')),
    error_message   TEXT,
    processed_at    TIMESTAMP,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_uploads_company ON file_uploads(company_id);
CREATE INDEX idx_uploads_period ON file_uploads(period_year, period_month);
CREATE INDEX idx_uploads_type ON file_uploads(file_type);

-- ============================================================
-- INVOICES (GSTR-1 — Sales)
-- ============================================================

CREATE TABLE gstr1_invoices (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    upload_id       UUID REFERENCES file_uploads(id),
    period_month    INTEGER NOT NULL,
    period_year     INTEGER NOT NULL,
    invoice_type    VARCHAR(20) NOT NULL CHECK (invoice_type IN ('B2B','B2CS','B2CL','EXPORT','CDNR','CDNUR')),
    invoice_number  VARCHAR(50) NOT NULL,
    invoice_date    DATE NOT NULL,
    supplier_gstin  VARCHAR(15) NOT NULL,
    receiver_gstin  VARCHAR(15),
    receiver_name   VARCHAR(200),
    place_of_supply VARCHAR(2),
    hsn_code        VARCHAR(10),
    taxable_value   NUMERIC(15,2) NOT NULL DEFAULT 0,
    igst            NUMERIC(15,2) NOT NULL DEFAULT 0,
    cgst            NUMERIC(15,2) NOT NULL DEFAULT 0,
    sgst            NUMERIC(15,2) NOT NULL DEFAULT 0,
    cess            NUMERIC(15,2) NOT NULL DEFAULT 0,
    total_value     NUMERIC(15,2) NOT NULL DEFAULT 0,
    gst_rate        NUMERIC(5,2),
    is_amended      BOOLEAN DEFAULT FALSE,
    original_invoice VARCHAR(50),
    source          VARCHAR(20) NOT NULL DEFAULT 'gstr1' CHECK (source IN ('gstr1','books','portal')),
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_gstr1_company_period ON gstr1_invoices(company_id, period_year, period_month);
CREATE INDEX idx_gstr1_invoice_no ON gstr1_invoices(invoice_number, supplier_gstin);
CREATE INDEX idx_gstr1_receiver ON gstr1_invoices(receiver_gstin);

-- ============================================================
-- GSTR-2B (Purchase — ITC)
-- ============================================================

CREATE TABLE gstr2b_invoices (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    upload_id       UUID REFERENCES file_uploads(id),
    period_month    INTEGER NOT NULL,
    period_year     INTEGER NOT NULL,
    record_type     VARCHAR(20) NOT NULL CHECK (record_type IN ('B2B','CDNR','ISD','IMPG','IMPGSEZ')),
    supplier_gstin  VARCHAR(15) NOT NULL,
    supplier_name   VARCHAR(200),
    invoice_number  VARCHAR(50) NOT NULL,
    invoice_date    DATE NOT NULL,
    invoice_type    VARCHAR(20),
    taxable_value   NUMERIC(15,2) NOT NULL DEFAULT 0,
    igst            NUMERIC(15,2) NOT NULL DEFAULT 0,
    cgst            NUMERIC(15,2) NOT NULL DEFAULT 0,
    sgst            NUMERIC(15,2) NOT NULL DEFAULT 0,
    cess            NUMERIC(15,2) NOT NULL DEFAULT 0,
    total_itc       NUMERIC(15,2) GENERATED ALWAYS AS (igst + cgst + sgst + cess) STORED,
    itc_availability VARCHAR(30) DEFAULT 'available' CHECK (itc_availability IN ('available','not_available','ineligible','deferred')),
    reason_ineligible VARCHAR(100),
    is_reverse_charge BOOLEAN DEFAULT FALSE,
    gstr1_filing_date DATE,
    source_period   VARCHAR(7),  -- MM-YYYY of supplier's GSTR-1
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_gstr2b_company_period ON gstr2b_invoices(company_id, period_year, period_month);
CREATE INDEX idx_gstr2b_supplier ON gstr2b_invoices(supplier_gstin);

-- ============================================================
-- PURCHASE REGISTER (Books)
-- ============================================================

CREATE TABLE purchase_register (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    upload_id       UUID REFERENCES file_uploads(id),
    period_month    INTEGER NOT NULL,
    period_year     INTEGER NOT NULL,
    invoice_number  VARCHAR(50) NOT NULL,
    invoice_date    DATE NOT NULL,
    supplier_gstin  VARCHAR(15),
    supplier_name   VARCHAR(200) NOT NULL,
    hsn_code        VARCHAR(10),
    description     TEXT,
    taxable_value   NUMERIC(15,2) NOT NULL DEFAULT 0,
    igst            NUMERIC(15,2) NOT NULL DEFAULT 0,
    cgst            NUMERIC(15,2) NOT NULL DEFAULT 0,
    sgst            NUMERIC(15,2) NOT NULL DEFAULT 0,
    cess            NUMERIC(15,2) NOT NULL DEFAULT 0,
    total_value     NUMERIC(15,2) NOT NULL DEFAULT 0,
    gst_rate        NUMERIC(5,2),
    itc_eligible    BOOLEAN DEFAULT TRUE,
    itc_claimed     NUMERIC(15,2) DEFAULT 0,
    expense_head    VARCHAR(100),
    voucher_number  VARCHAR(50),
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_purchase_company_period ON purchase_register(company_id, period_year, period_month);
CREATE INDEX idx_purchase_supplier ON purchase_register(supplier_gstin);

-- ============================================================
-- SALES REGISTER (Books)
-- ============================================================

CREATE TABLE sales_register (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    upload_id       UUID REFERENCES file_uploads(id),
    period_month    INTEGER NOT NULL,
    period_year     INTEGER NOT NULL,
    invoice_number  VARCHAR(50) NOT NULL,
    invoice_date    DATE NOT NULL,
    customer_gstin  VARCHAR(15),
    customer_name   VARCHAR(200) NOT NULL,
    place_of_supply VARCHAR(2),
    hsn_code        VARCHAR(10),
    description     TEXT,
    taxable_value   NUMERIC(15,2) NOT NULL DEFAULT 0,
    igst            NUMERIC(15,2) NOT NULL DEFAULT 0,
    cgst            NUMERIC(15,2) NOT NULL DEFAULT 0,
    sgst            NUMERIC(15,2) NOT NULL DEFAULT 0,
    cess            NUMERIC(15,2) NOT NULL DEFAULT 0,
    total_value     NUMERIC(15,2) NOT NULL DEFAULT 0,
    gst_rate        NUMERIC(5,2),
    invoice_type    VARCHAR(20) DEFAULT 'B2B',
    is_export       BOOLEAN DEFAULT FALSE,
    voucher_number  VARCHAR(50),
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sales_company_period ON sales_register(company_id, period_year, period_month);

-- ============================================================
-- GSTR-3B DATA
-- ============================================================

CREATE TABLE gstr3b_data (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    upload_id       UUID REFERENCES file_uploads(id),
    period_month    INTEGER NOT NULL,
    period_year     INTEGER NOT NULL,
    -- 3.1 Details of Outward and Inward Supplies
    taxable_outward_igst        NUMERIC(15,2) DEFAULT 0,
    taxable_outward_cgst        NUMERIC(15,2) DEFAULT 0,
    taxable_outward_sgst        NUMERIC(15,2) DEFAULT 0,
    zero_rated_supply           NUMERIC(15,2) DEFAULT 0,
    nil_exempt_nongst           NUMERIC(15,2) DEFAULT 0,
    inward_rcm_igst             NUMERIC(15,2) DEFAULT 0,
    inward_rcm_cgst             NUMERIC(15,2) DEFAULT 0,
    inward_rcm_sgst             NUMERIC(15,2) DEFAULT 0,
    -- 4. Eligible ITC
    itc_available_igst          NUMERIC(15,2) DEFAULT 0,
    itc_available_cgst          NUMERIC(15,2) DEFAULT 0,
    itc_available_sgst          NUMERIC(15,2) DEFAULT 0,
    itc_reversed_igst           NUMERIC(15,2) DEFAULT 0,
    itc_reversed_cgst           NUMERIC(15,2) DEFAULT 0,
    itc_reversed_sgst           NUMERIC(15,2) DEFAULT 0,
    net_itc_igst                NUMERIC(15,2) DEFAULT 0,
    net_itc_cgst                NUMERIC(15,2) DEFAULT 0,
    net_itc_sgst                NUMERIC(15,2) DEFAULT 0,
    -- 5.1 Interest & Late Fee
    interest_igst               NUMERIC(15,2) DEFAULT 0,
    interest_cgst               NUMERIC(15,2) DEFAULT 0,
    interest_sgst               NUMERIC(15,2) DEFAULT 0,
    late_fee_cgst               NUMERIC(15,2) DEFAULT 0,
    late_fee_sgst               NUMERIC(15,2) DEFAULT 0,
    -- Tax Paid
    tax_paid_igst               NUMERIC(15,2) DEFAULT 0,
    tax_paid_cgst               NUMERIC(15,2) DEFAULT 0,
    tax_paid_sgst               NUMERIC(15,2) DEFAULT 0,
    filing_date                 DATE,
    filing_status               VARCHAR(20) DEFAULT 'filed' CHECK (filing_status IN ('filed','pending','nil')),
    created_at                  TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(company_id, period_year, period_month)
);

-- ============================================================
-- RECONCILIATION RESULTS
-- ============================================================

CREATE TABLE reconciliation_runs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    run_by          UUID NOT NULL REFERENCES users(id),
    recon_type      VARCHAR(30) NOT NULL CHECK (recon_type IN ('gstr1_vs_books','gstr2b_vs_books','gstr3b_vs_books','itc_recon','full_audit')),
    period_month    INTEGER NOT NULL,
    period_year     INTEGER NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'running' CHECK (status IN ('running','completed','failed')),
    total_invoices  INTEGER DEFAULT 0,
    matched_count   INTEGER DEFAULT 0,
    mismatch_count  INTEGER DEFAULT 0,
    missing_count   INTEGER DEFAULT 0,
    duplicate_count INTEGER DEFAULT 0,
    itc_impact      NUMERIC(15,2) DEFAULT 0,
    summary_json    JSONB,
    error_log       TEXT,
    started_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMP
);

CREATE TABLE reconciliation_items (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id          UUID NOT NULL REFERENCES reconciliation_runs(id) ON DELETE CASCADE,
    company_id      UUID NOT NULL REFERENCES companies(id),
    invoice_number  VARCHAR(50),
    invoice_date    DATE,
    supplier_gstin  VARCHAR(15),
    party_name      VARCHAR(200),
    invoice_type    VARCHAR(20),
    -- Book Values
    books_taxable   NUMERIC(15,2),
    books_igst      NUMERIC(15,2),
    books_cgst      NUMERIC(15,2),
    books_sgst      NUMERIC(15,2),
    -- GST Return Values
    gstr_taxable    NUMERIC(15,2),
    gstr_igst       NUMERIC(15,2),
    gstr_cgst       NUMERIC(15,2),
    gstr_sgst       NUMERIC(15,2),
    -- Differences
    diff_taxable    NUMERIC(15,2) GENERATED ALWAYS AS (COALESCE(gstr_taxable,0) - COALESCE(books_taxable,0)) STORED,
    diff_igst       NUMERIC(15,2) GENERATED ALWAYS AS (COALESCE(gstr_igst,0) - COALESCE(books_igst,0)) STORED,
    diff_total_gst  NUMERIC(15,2) GENERATED ALWAYS AS (
                        COALESCE(gstr_igst,0)+COALESCE(gstr_cgst,0)+COALESCE(gstr_sgst,0)
                        - COALESCE(books_igst,0)-COALESCE(books_cgst,0)-COALESCE(books_sgst,0)
                    ) STORED,
    mismatch_type   VARCHAR(30) CHECK (mismatch_type IN ('matched','value_diff','missing_in_gstr','missing_in_books','duplicate','rate_error','gstin_mismatch','date_diff')),
    mismatch_reason TEXT,
    itc_impact      NUMERIC(15,2) DEFAULT 0,
    risk_level      VARCHAR(10) DEFAULT 'low' CHECK (risk_level IN ('low','medium','high','critical')),
    is_resolved     BOOLEAN DEFAULT FALSE,
    resolution_note TEXT,
    resolved_by     UUID REFERENCES users(id),
    resolved_at     TIMESTAMP,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_recon_items_run ON reconciliation_items(run_id);
CREATE INDEX idx_recon_items_company ON reconciliation_items(company_id);
CREATE INDEX idx_recon_items_mismatch ON reconciliation_items(mismatch_type) WHERE mismatch_type != 'matched';

-- ============================================================
-- VENDORS
-- ============================================================

CREATE TABLE vendors (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    gstin           VARCHAR(15) NOT NULL,
    name            VARCHAR(200) NOT NULL,
    pan             VARCHAR(10),
    email           VARCHAR(200),
    phone           VARCHAR(15),
    state_code      VARCHAR(2),
    registration_status VARCHAR(30) DEFAULT 'active' CHECK (registration_status IN ('active','cancelled','suspended','provisional')),
    gstr1_filing_status VARCHAR(20) DEFAULT 'unknown',
    last_filing_date DATE,
    risk_score      INTEGER DEFAULT 0 CHECK (risk_score BETWEEN 0 AND 100),
    risk_level      VARCHAR(10) DEFAULT 'low' CHECK (risk_level IN ('low','medium','high','critical')),
    total_purchases NUMERIC(15,2) DEFAULT 0,
    total_itc       NUMERIC(15,2) DEFAULT 0,
    itc_at_risk     NUMERIC(15,2) DEFAULT 0,
    follow_up_sent  BOOLEAN DEFAULT FALSE,
    last_follow_up  TIMESTAMP,
    notes           TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(company_id, gstin)
);

CREATE INDEX idx_vendors_gstin ON vendors(gstin);
CREATE INDEX idx_vendors_risk ON vendors(risk_level);

-- ============================================================
-- AUDIT REPORTS
-- ============================================================

CREATE TABLE audit_reports (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    generated_by    UUID NOT NULL REFERENCES users(id),
    report_type     VARCHAR(50) NOT NULL CHECK (report_type IN (
                        'gst_audit','reconciliation_summary','exception_report',
                        'vendor_followup','itc_utilization','compliance_certificate'
                    )),
    period_from     DATE NOT NULL,
    period_to       DATE NOT NULL,
    report_name     VARCHAR(200) NOT NULL,
    file_format     VARCHAR(10) NOT NULL CHECK (file_format IN ('pdf','xlsx','csv')),
    s3_key          VARCHAR(500),
    file_size       BIGINT,
    summary_json    JSONB,
    status          VARCHAR(20) DEFAULT 'generating' CHECK (status IN ('generating','ready','failed')),
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMP DEFAULT (NOW() + INTERVAL '30 days')
);

-- ============================================================
-- AI INSIGHTS
-- ============================================================

CREATE TABLE ai_insights (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    run_id          UUID REFERENCES reconciliation_runs(id),
    period_month    INTEGER,
    period_year     INTEGER,
    insight_type    VARCHAR(50) NOT NULL CHECK (insight_type IN (
                        'mismatch_explanation','fraud_detection','risk_scoring',
                        'itc_suggestion','compliance_tip','vendor_alert'
                    )),
    title           VARCHAR(300) NOT NULL,
    description     TEXT NOT NULL,
    risk_level      VARCHAR(10) CHECK (risk_level IN ('low','medium','high','critical')),
    financial_impact NUMERIC(15,2) DEFAULT 0,
    suggested_action TEXT,
    is_addressed    BOOLEAN DEFAULT FALSE,
    model_used      VARCHAR(50) DEFAULT 'claude-3-5-sonnet',
    tokens_used     INTEGER,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ============================================================
-- HSN MASTER (Rate Validation)
-- ============================================================

CREATE TABLE hsn_master (
    id              SERIAL PRIMARY KEY,
    hsn_code        VARCHAR(10) NOT NULL UNIQUE,
    description     TEXT NOT NULL,
    gst_rate        NUMERIC(5,2) NOT NULL,
    igst_rate       NUMERIC(5,2),
    cgst_rate       NUMERIC(5,2),
    sgst_rate       NUMERIC(5,2),
    cess_rate       NUMERIC(5,2) DEFAULT 0,
    effective_from  DATE NOT NULL,
    effective_to    DATE,
    is_active       BOOLEAN DEFAULT TRUE
);

-- ============================================================
-- AUDIT LOGS
-- ============================================================

CREATE TABLE audit_logs (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   UUID NOT NULL,
    user_id     UUID REFERENCES users(id),
    company_id  UUID REFERENCES companies(id),
    action      VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id   UUID,
    old_value   JSONB,
    new_value   JSONB,
    ip_address  INET,
    user_agent  TEXT,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_tenant ON audit_logs(tenant_id, created_at DESC);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id, created_at DESC);

-- ============================================================
-- SUBSCRIPTIONS
-- ============================================================

CREATE TABLE subscriptions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    plan            VARCHAR(50) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active','cancelled','past_due','trial')),
    billing_cycle   VARCHAR(10) NOT NULL DEFAULT 'monthly' CHECK (billing_cycle IN ('monthly','annual')),
    amount          NUMERIC(10,2) NOT NULL,
    currency        VARCHAR(3) DEFAULT 'INR',
    start_date      DATE NOT NULL,
    end_date        DATE,
    razorpay_sub_id VARCHAR(100),
    last_payment_at TIMESTAMP,
    next_billing_at TIMESTAMP,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ============================================================
-- FUNCTIONS & TRIGGERS
-- ============================================================

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_companies_updated
    BEFORE UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_vendors_updated
    BEFORE UPDATE ON vendors
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Compliance score view
CREATE OR REPLACE VIEW company_compliance_scores AS
SELECT
    c.id AS company_id,
    c.name,
    c.gstin,
    COALESCE(
        (
            -- GSTR-1 filing score (25 pts)
            CASE WHEN g3.filing_status = 'filed' THEN 25 ELSE 0 END +
            -- ITC reconciliation score (30 pts)
            CASE WHEN rr.mismatch_count IS NULL OR rr.mismatch_count = 0 THEN 30
                 WHEN rr.mismatch_count < 10 THEN 20
                 ELSE 10 END +
            -- Vendor compliance (25 pts)
            GREATEST(0, 25 - (
                SELECT COUNT(*) * 5
                FROM vendors v
                WHERE v.company_id = c.id
                  AND v.risk_level IN ('high','critical')
            )) +
            -- On-time filing (20 pts)
            20
        ), 0
    ) AS compliance_score
FROM companies c
LEFT JOIN gstr3b_data g3 ON g3.company_id = c.id
    AND g3.period_year = EXTRACT(YEAR FROM NOW())
    AND g3.period_month = EXTRACT(MONTH FROM NOW()) - 1
LEFT JOIN reconciliation_runs rr ON rr.company_id = c.id
    AND rr.status = 'completed'
    AND rr.period_year = EXTRACT(YEAR FROM NOW())
    AND rr.period_month = EXTRACT(MONTH FROM NOW()) - 1
    AND rr.recon_type = 'full_audit';

-- Monthly GST summary view
CREATE OR REPLACE VIEW monthly_gst_summary AS
SELECT
    s.company_id,
    s.period_year,
    s.period_month,
    SUM(s.taxable_value)   AS total_sales,
    SUM(s.igst + s.cgst + s.sgst + s.cess) AS total_output_gst,
    COALESCE(p.total_purchases, 0) AS total_purchases,
    COALESCE(p.total_itc, 0)       AS total_itc_available
FROM sales_register s
LEFT JOIN (
    SELECT company_id, period_year, period_month,
           SUM(taxable_value) AS total_purchases,
           SUM(igst + cgst + sgst + cess) AS total_itc
    FROM purchase_register
    GROUP BY company_id, period_year, period_month
) p ON p.company_id = s.company_id
    AND p.period_year = s.period_year
    AND p.period_month = s.period_month
GROUP BY s.company_id, s.period_year, s.period_month, p.total_purchases, p.total_itc;

-- ============================================================
-- SAMPLE SEED DATA (HSN Master — subset)
-- ============================================================

INSERT INTO hsn_master (hsn_code, description, gst_rate, igst_rate, cgst_rate, sgst_rate, effective_from) VALUES
('0101', 'Live horses, asses, mules and hinnies', 0, 0, 0, 0, '2017-07-01'),
('1001', 'Wheat and meslin', 0, 0, 0, 0, '2017-07-01'),
('2201', 'Waters, including natural or artificial mineral waters', 18, 18, 9, 9, '2017-07-01'),
('3004', 'Medicaments for retail sale', 12, 12, 6, 6, '2017-07-01'),
('4016', 'Other articles of vulcanised rubber', 28, 28, 14, 14, '2017-07-01'),
('6101', 'Men''s or boys'' overcoats (>1000)', 12, 12, 6, 6, '2017-07-01'),
('7108', 'Gold (including gold plated with platinum)', 3, 3, 1.5, 1.5, '2017-07-01'),
('8471', 'Automatic data processing machines (computers)', 18, 18, 9, 9, '2017-07-01'),
('8517', 'Telephone sets including smartphones', 18, 18, 9, 9, '2017-07-01'),
('8703', 'Motor cars and other motor vehicles', 28, 28, 14, 14, '2017-07-01'),
('9403', 'Other furniture', 18, 18, 9, 9, '2017-07-01'),
('9954', 'Construction services', 18, 18, 9, 9, '2017-07-01'),
('9961', 'Services in wholesale trade', 18, 18, 9, 9, '2017-07-01'),
('9983', 'Other professional, technical & business services', 18, 18, 9, 9, '2017-07-01'),
('9984', 'Telecommunications, broadcasting, information supply', 18, 18, 9, 9, '2017-07-01'),
('9985', 'Support services', 18, 18, 9, 9, '2017-07-01'),
('9997', 'Other services', 18, 18, 9, 9, '2017-07-01');
