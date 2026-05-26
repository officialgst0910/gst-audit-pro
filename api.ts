// ============================================================
// src/lib/api.ts — Axios API Client
// ============================================================

import axios, { AxiosError, AxiosRequestConfig } from "axios";
import toast from "react-hot-toast";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

// Request interceptor — attach JWT
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;

    const companyId = localStorage.getItem("active_company_id");
    if (companyId) config.headers["X-Company-ID"] = companyId;
  }
  return config;
});

// Response interceptor — handle errors globally
api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError<{ detail: string }>) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      window.location.href = "/login";
      return;
    }
    if (error.response?.status === 403) {
      toast.error("Access denied. Insufficient permissions.");
    } else if (error.response?.status === 422) {
      toast.error("Validation error. Check your input.");
    } else if (error.response?.status >= 500) {
      toast.error("Server error. Please try again.");
    }
    return Promise.reject(error);
  }
);

// ── Typed API Methods ────────────────────────────────────────

export const authApi = {
  login:       (email: string, password: string) =>
    api.post("/auth/login", { email, password }),
  signup:      (data: SignupPayload) =>
    api.post("/auth/signup", data),
  verifyOtp:   (email: string, otp: string) =>
    api.post("/auth/verify-otp", { email, otp }),
  logout:      () => api.post("/auth/logout"),
};

export const dashboardApi = {
  getSummary:    (companyId: string, year: number, month: number) =>
    api.get("/dashboard/summary", { params: { company_id: companyId, year, month } }),
  getMonthlyTrend: (companyId: string, year: number) =>
    api.get("/dashboard/monthly-trend", { params: { company_id: companyId, year } }),
};

export const uploadsApi = {
  upload: (formData: FormData) =>
    api.post("/uploads/", formData, { headers: { "Content-Type": "multipart/form-data" } }),
  listUploads: (companyId: string) =>
    api.get("/uploads/", { params: { company_id: companyId } }),
};

export const reconApi = {
  runRecon:   (payload: ReconPayload) =>
    api.post("/reconciliation/run", payload),
  listRuns:   (companyId: string) =>
    api.get("/reconciliation/runs", { params: { company_id: companyId } }),
  getItems:   (runId: string, params?: Record<string, string | number>) =>
    api.get(`/reconciliation/items/${runId}`, { params }),
  resolveItem:(itemId: string, note: string) =>
    api.patch(`/reconciliation/items/${itemId}/resolve`, { resolution_note: note }),
};

export const vendorsApi = {
  list:         (companyId: string) =>
    api.get("/vendors/", { params: { company_id: companyId } }),
  getById:      (id: string) => api.get(`/vendors/${id}`),
  sendFollowUp: (vendorIds: string[]) =>
    api.post("/vendors/follow-up", { vendor_ids: vendorIds }),
  updateRisk:   (id: string, riskLevel: string) =>
    api.patch(`/vendors/${id}/risk`, { risk_level: riskLevel }),
};

export const reportsApi = {
  generate:    (payload: ReportPayload) =>
    api.post("/reports/generate", payload),
  download:    (reportId: string) =>
    api.get(`/reports/${reportId}/download`, { responseType: "blob" }),
  list:        (companyId: string) =>
    api.get("/reports/", { params: { company_id: companyId } }),
};

export const aiApi = {
  analyze:          (payload: AIAnalysisPayload) =>
    api.post("/ai/analyze", payload),
  explainMismatch:  (mismatch: object) =>
    api.post("/ai/explain-mismatch", mismatch),
};

export const companiesApi = {
  list:    () => api.get("/companies/"),
  getById: (id: string) => api.get(`/companies/${id}`),
  create:  (data: object) => api.post("/companies/", data),
  update:  (id: string, data: object) => api.put(`/companies/${id}`, data),
};

// ── Types ─────────────────────────────────────────────────────

export interface SignupPayload {
  full_name:    string;
  email:        string;
  phone:        string;
  password:     string;
  company_name: string;
  gstin:        string;
  role?:        string;
}

export interface ReconPayload {
  company_id:   string;
  recon_type:   "gstr1_vs_books" | "gstr2b_vs_books" | "gstr3b_vs_books" | "full_audit";
  period_month: number;
  period_year:  number;
}

export interface ReportPayload {
  company_id:  string;
  report_type: string;
  period_from: string;
  period_to:   string;
  file_format: "pdf" | "xlsx" | "csv";
}

export interface AIAnalysisPayload {
  company_id:  string;
  period:      string;
  mismatches:  object[];
  vendor_data: object[];
  gstr3b?:     object;
}

// ============================================================
// src/lib/store.ts — Zustand Global State
// ============================================================

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

interface User {
  id:        string;
  email:     string;
  full_name: string;
  role:      string;
}

interface Company {
  id:    string;
  name:  string;
  gstin: string;
}

interface AppState {
  // Auth
  user:          User | null;
  accessToken:   string | null;
  refreshToken:  string | null;
  isAuthenticated: boolean;
  setAuth:       (user: User, accessToken: string, refreshToken: string) => void;
  clearAuth:     () => void;

  // Active Company
  activeCompany:    Company | null;
  companies:        Company[];
  setActiveCompany: (company: Company) => void;
  setCompanies:     (companies: Company[]) => void;

  // UI State
  sidebarCollapsed: boolean;
  toggleSidebar:    () => void;
  isDark:           boolean;
  toggleTheme:      () => void;

  // Period selector
  activePeriod: { month: number; year: number };
  setPeriod:    (month: number, year: number) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      // Auth
      user:            null,
      accessToken:     null,
      refreshToken:    null,
      isAuthenticated: false,
      setAuth: (user, accessToken, refreshToken) => {
        localStorage.setItem("access_token", accessToken);
        set({ user, accessToken, refreshToken, isAuthenticated: true });
      },
      clearAuth: () => {
        localStorage.removeItem("access_token");
        set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false });
      },

      // Company
      activeCompany: null,
      companies:     [],
      setActiveCompany: (company) => {
        localStorage.setItem("active_company_id", company.id);
        set({ activeCompany: company });
      },
      setCompanies: (companies) => set({ companies }),

      // UI
      sidebarCollapsed: false,
      toggleSidebar:    () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      isDark:           false,
      toggleTheme:      () => set((s) => ({ isDark: !s.isDark })),

      // Period (default: current month)
      activePeriod: {
        month: new Date().getMonth() + 1,
        year:  new Date().getFullYear(),
      },
      setPeriod: (month, year) => set({ activePeriod: { month, year } }),
    }),
    {
      name:    "gst-audit-pro",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        activeCompany:   state.activeCompany,
        activePeriod:    state.activePeriod,
        isDark:          state.isDark,
        sidebarCollapsed:state.sidebarCollapsed,
      }),
    }
  )
);

// ============================================================
// src/lib/utils.ts — Shared Utilities
// ============================================================

import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatINR(amount: number, decimals = 2): string {
  if (isNaN(amount)) return "₹0";
  const absAmt = Math.abs(amount);
  let formatted: string;
  if (absAmt >= 10_000_000) {
    formatted = `${(absAmt / 10_000_000).toFixed(2)} Cr`;
  } else if (absAmt >= 100_000) {
    formatted = `${(absAmt / 100_000).toFixed(2)} L`;
  } else {
    formatted = absAmt.toLocaleString("en-IN", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  }
  return `${amount < 0 ? "−" : ""}₹${formatted}`;
}

export function formatGSTIN(gstin: string): string {
  if (!gstin || gstin.length !== 15) return gstin;
  return `${gstin.slice(0, 2)} ${gstin.slice(2, 7)} ${gstin.slice(7, 11)} ${gstin.slice(11, 12)} ${gstin.slice(12)}`;
}

export function validateGSTIN(gstin: string): boolean {
  const re = /^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}Z[A-Z\d]{1}$/;
  return re.test(gstin.toUpperCase());
}

export function getMismatchColor(type: string): string {
  const map: Record<string, string> = {
    matched:         "text-emerald-700 bg-emerald-50 border-emerald-200",
    mismatch:        "text-amber-700 bg-amber-50 border-amber-200",
    missing_in_gstr: "text-red-700 bg-red-50 border-red-200",
    missing_in_books:"text-red-700 bg-red-50 border-red-200",
    duplicate:       "text-purple-700 bg-purple-50 border-purple-200",
    rate_error:      "text-orange-700 bg-orange-50 border-orange-200",
    value_diff:      "text-amber-700 bg-amber-50 border-amber-200",
  };
  return map[type] || "text-slate-700 bg-slate-50 border-slate-200";
}

export function getRiskColor(level: string): string {
  const map: Record<string, string> = {
    low:      "text-emerald-700 bg-emerald-50",
    medium:   "text-amber-700 bg-amber-50",
    high:     "text-red-700 bg-red-50",
    critical: "text-red-800 bg-red-100 font-bold",
  };
  return map[level] || "text-slate-700 bg-slate-50";
}

export function getMonthName(month: number): string {
  return ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][month - 1] || "";
}

export function getPeriodLabel(month: number, year: number): string {
  return `${getMonthName(month)}-${year}`;
}

export function downloadBlob(data: Blob, filename: string) {
  const url = URL.createObjectURL(data);
  const a   = document.createElement("a");
  a.href    = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function parseApiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return error.response?.data?.detail || error.message || "Unknown error";
  }
  return String(error);
}

// ============================================================
// src/hooks/useRecon.ts — Reconciliation hook
// ============================================================
import { useState, useCallback } from "react";
import { reconApi, ReconPayload } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import toast from "react-hot-toast";

export function useRecon() {
  const [isRunning, setIsRunning] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const activeCompany = useAppStore((s) => s.activeCompany);
  const activePeriod  = useAppStore((s) => s.activePeriod);

  const startRecon = useCallback(
    async (reconType: ReconPayload["recon_type"]) => {
      if (!activeCompany) {
        toast.error("Please select a company first");
        return;
      }
      setIsRunning(true);
      try {
        const res = await reconApi.runRecon({
          company_id:   activeCompany.id,
          recon_type:   reconType,
          period_month: activePeriod.month,
          period_year:  activePeriod.year,
        });
        setRunId(res.data.run_id);
        toast.success("Reconciliation started!");
        return res.data.run_id as string;
      } catch (err) {
        toast.error("Failed to start reconciliation");
        throw err;
      } finally {
        setIsRunning(false);
      }
    },
    [activeCompany, activePeriod]
  );

  return { isRunning, runId, startRecon };
}

// ============================================================
// src/hooks/useDashboard.ts
// ============================================================
import useSWR from "swr";
import { dashboardApi } from "@/lib/api";

export function useDashboard(companyId: string, year: number, month: number) {
  const { data, error, isLoading, mutate } = useSWR(
    companyId ? [`/dashboard/summary`, companyId, year, month] : null,
    () => dashboardApi.getSummary(companyId, year, month).then((r) => r.data),
    { revalidateOnFocus: false, dedupingInterval: 30000 }
  );

  return {
    summary:   data,
    isLoading,
    error,
    refresh:   mutate,
  };
}

export function useMonthlyTrend(companyId: string, year: number) {
  const { data, isLoading } = useSWR(
    companyId ? [`/dashboard/trend`, companyId, year] : null,
    () => dashboardApi.getMonthlyTrend(companyId, year).then((r) => r.data),
    { revalidateOnFocus: false }
  );
  return { trend: data, isLoading };
}

// ============================================================
// src/types/index.ts — Shared TypeScript Interfaces
// ============================================================

export interface Company {
  id:                string;
  tenant_id:         string;
  name:              string;
  gstin:             string;
  pan:               string;
  trade_name?:       string;
  address?:          string;
  state_code:        string;
  email?:            string;
  phone?:            string;
  registration_type: string;
  is_active:         boolean;
}

export interface DashboardSummary {
  period:             string;
  total_sales:        number;
  output_gst:         number;
  invoice_count:      number;
  total_purchases:    number;
  itc_available:      number;
  itc_claimed:        number;
  pending_mismatches: number;
  compliance_score:   number;
}

export interface ReconciliationRun {
  id:             string;
  recon_type:     string;
  period:         string;
  status:         "running" | "completed" | "failed";
  total_invoices: number;
  matched:        number;
  mismatches:     number;
  missing:        number;
  itc_impact:     number;
  started_at:     string;
  completed_at?:  string;
}

export interface ReconciliationItem {
  id:             string;
  invoice_number: string;
  supplier_gstin: string;
  party_name:     string;
  mismatch_type:  MismatchType;
  mismatch_reason:string;
  books_taxable:  number;
  gstr_taxable:   number;
  itc_impact:     number;
  risk_level:     RiskLevel;
  is_resolved:    boolean;
}

export type MismatchType =
  | "matched"
  | "value_diff"
  | "missing_in_gstr"
  | "missing_in_books"
  | "duplicate"
  | "rate_error"
  | "gstin_mismatch"
  | "date_diff";

export type RiskLevel = "low" | "medium" | "high" | "critical";

export interface Vendor {
  id:                    string;
  name:                  string;
  gstin:                 string;
  pan?:                  string;
  email?:                string;
  phone?:                string;
  registration_status:   string;
  gstr1_filing_status:   string;
  last_filing_date?:     string;
  risk_score:            number;
  risk_level:            RiskLevel;
  total_purchases:       number;
  total_itc:             number;
  itc_at_risk:           number;
  follow_up_sent:        boolean;
}

export interface AIInsight {
  type:             string;
  title:            string;
  description:      string;
  risk_level:       RiskLevel;
  financial_impact: number;
  suggested_action: string;
  priority:         number;
}

export interface FileUpload {
  id:           string;
  file_name:    string;
  file_type:    string;
  file_size:    number;
  row_count:    number;
  period:       string;
  status:       string;
  created_at:   string;
}

export interface AuditReport {
  id:          string;
  report_type: string;
  period_from: string;
  period_to:   string;
  report_name: string;
  file_format: string;
  status:      string;
  created_at:  string;
}

export const MONTHS = [
  "April","May","June","July","August","September",
  "October","November","December","January","February","March"
];

export const FILE_TYPES = [
  { value: "gstr1",             label: "GSTR-1",          icon: "ti-file-invoice" },
  { value: "gstr2b",            label: "GSTR-2B",         icon: "ti-receipt-2" },
  { value: "gstr3b",            label: "GSTR-3B",         icon: "ti-calculator" },
  { value: "sales_register",    label: "Sales Register",   icon: "ti-report-money" },
  { value: "purchase_register", label: "Purchase Register",icon: "ti-shopping-cart" },
  { value: "journal",           label: "Journal Entries",  icon: "ti-book" },
] as const;

export const REPORT_TYPES = [
  { value: "gst_audit",              label: "GST Audit Report",       icon: "ti-clipboard-list" },
  { value: "reconciliation_summary", label: "Reconciliation Summary",  icon: "ti-git-compare" },
  { value: "exception_report",       label: "Exception Report",        icon: "ti-alert-triangle" },
  { value: "vendor_followup",        label: "Vendor Follow-up",        icon: "ti-users" },
  { value: "itc_utilization",        label: "ITC Utilization",         icon: "ti-chart-line" },
  { value: "compliance_certificate", label: "Compliance Certificate",  icon: "ti-certificate" },
] as const;
