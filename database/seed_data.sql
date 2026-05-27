-- GST Audit Pro — Seed Data
-- Run this in Supabase SQL Editor after running schema.sql

INSERT INTO tenants (id,name,slug,plan,max_gstins,max_users,max_invoices)
VALUES ('aaaaaaaa-0000-0000-0000-000000000001','Demo CA Firm','demo-ca-firm','professional',5,15,99999)
ON CONFLICT (id) DO NOTHING;

INSERT INTO companies (id,tenant_id,name,gstin,pan,state_code,registration_type)
VALUES ('bbbbbbbb-0000-0000-0000-000000000001','aaaaaaaa-0000-0000-0000-000000000001','Tech Mahindra Ltd','27AABCT0898L1ZB','AABCT0898L','27','regular')
ON CONFLICT (tenant_id,gstin) DO NOTHING;

-- Admin@123
INSERT INTO users (id,tenant_id,email,full_name,password_hash,role,is_verified,is_active)
VALUES ('cccccccc-0000-0000-0000-000000000001','aaaaaaaa-0000-0000-0000-000000000001','admin@gstauditpro.in','Super Admin','$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewYpfQcIjOH8mTHm','super_admin',true,true)
ON CONFLICT (tenant_id,email) DO NOTHING;

-- Demo@123
INSERT INTO users (id,tenant_id,email,full_name,password_hash,role,is_verified,is_active)
VALUES ('cccccccc-0000-0000-0000-000000000002','aaaaaaaa-0000-0000-0000-000000000001','ca@demo.in','CA Rajesh Mehta','$2b$12$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uYagRBHgK','ca',true,true)
ON CONFLICT (tenant_id,email) DO NOTHING;

INSERT INTO users (id,tenant_id,email,full_name,password_hash,role,is_verified,is_active)
VALUES ('cccccccc-0000-0000-0000-000000000003','aaaaaaaa-0000-0000-0000-000000000001','user@demo.in','Priya Sharma','$2b$12$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uYagRBHgK','user',true,true)
ON CONFLICT (tenant_id,email) DO NOTHING;

INSERT INTO vendors (company_id,gstin,name,state_code,gstr1_filing_status,risk_level,total_purchases,total_itc,itc_at_risk)
VALUES
('bbbbbbbb-0000-0000-0000-000000000001','27AAPFU0939F1ZV','Infosys Ltd','27','filed','low',4800000,864000,0),
('bbbbbbbb-0000-0000-0000-000000000001','29AADCI0859A1ZP','TCS Pvt Ltd','29','filed','low',2200000,396000,0),
('bbbbbbbb-0000-0000-0000-000000000001','33AAACV0209R1Z1','Wipro Ltd','33','pending','high',1550000,279000,279000),
('bbbbbbbb-0000-0000-0000-000000000001','07AABCS1429B1Z1','HCL Technologies','07','filed','low',3100000,558000,0),
('bbbbbbbb-0000-0000-0000-000000000001','27AAFCS8865R1Z7','Cognizant India','27','partial','medium',6700000,1206000,120600),
('bbbbbbbb-0000-0000-0000-000000000001','29AADCS2649N1Z1','Mphasis Ltd','29','pending','high',900000,162000,162000)
ON CONFLICT (company_id,gstin) DO NOTHING;

INSERT INTO sales_register (company_id,period_month,period_year,invoice_number,invoice_date,customer_gstin,customer_name,taxable_value,igst,cgst,sgst,total_value,gst_rate,invoice_type)
VALUES
('bbbbbbbb-0000-0000-0000-000000000001',10,2024,'TM/2024-25/10/0001','2024-10-05','27AAPFU0939F1ZV','Infosys Ltd',4800000,864000,0,0,5664000,18,'B2B'),
('bbbbbbbb-0000-0000-0000-000000000001',10,2024,'TM/2024-25/10/0002','2024-10-08','29AADCI0859A1ZP','TCS Pvt Ltd',2200000,396000,0,0,2596000,18,'B2B'),
('bbbbbbbb-0000-0000-0000-000000000001',10,2024,'TM/2024-25/10/0003','2024-10-15','33AAACV0209R1Z1','Wipro Ltd',1550000,279000,0,0,1829000,18,'B2B'),
('bbbbbbbb-0000-0000-0000-000000000001',10,2024,'TM/2024-25/10/0004','2024-10-18','07AABCS1429B1Z1','HCL Technologies',3100000,558000,0,0,3658000,18,'B2B'),
('bbbbbbbb-0000-0000-0000-000000000001',10,2024,'TM/2024-25/10/0005','2024-10-22','','Walk-in Customer',450000,0,40500,40500,531000,18,'B2C');

INSERT INTO purchase_register (company_id,period_month,period_year,invoice_number,invoice_date,supplier_gstin,supplier_name,taxable_value,igst,cgst,sgst,total_value,gst_rate,itc_eligible,itc_claimed)
VALUES
('bbbbbbbb-0000-0000-0000-000000000001',10,2024,'INF/2024/10/001','2024-10-03','27AAPFU0939F1ZV','Infosys Ltd',4800000,864000,0,0,5664000,18,true,864000),
('bbbbbbbb-0000-0000-0000-000000000001',10,2024,'TCS/2024/10/001','2024-10-06','29AADCI0859A1ZP','TCS Pvt Ltd',2200000,396000,0,0,2596000,18,true,396000),
('bbbbbbbb-0000-0000-0000-000000000001',10,2024,'WIP/2024/10/001','2024-10-12','33AAACV0209R1Z1','Wipro Ltd',1550000,279000,0,0,1829000,18,true,0),
('bbbbbbbb-0000-0000-0000-000000000001',10,2024,'HCL/2024/10/001','2024-10-15','07AABCS1429B1Z1','HCL Technologies',3100000,558000,0,0,3658000,18,true,558000);

-- Verify everything:
SELECT 'tenants' as tbl,COUNT(*) as rows FROM tenants
UNION ALL SELECT 'companies',COUNT(*) FROM companies
UNION ALL SELECT 'users',COUNT(*) FROM users
UNION ALL SELECT 'vendors',COUNT(*) FROM vendors
UNION ALL SELECT 'sales_register',COUNT(*) FROM sales_register
UNION ALL SELECT 'purchase_register',COUNT(*) FROM purchase_register;
