"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

interface Summary {
  total_sales: number; output_gst: number;
  itc_available: number; pending_mismatches: number; compliance_score: number;
}
function fmt(n: number) {
  if (n >= 10000000) return "\u20b9" + (n/10000000).toFixed(2) + " Cr";
  if (n >= 100000) return "\u20b9" + (n/100000).toFixed(2) + " L";
  return "\u20b9" + n.toLocaleString("en-IN");
}
export default function DashboardPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) { router.push("/login"); return; }
    fetch(`${API}/api/v1/dashboard/summary?company_id=bbbbbbbb-0000-0000-0000-000000000001&year=2024&month=10`, {
      headers: { Authorization: `Bearer ${token}` }
    }).then(r => r.json()).then(d => setSummary(d)).catch(() => setSummary(null)).finally(() => setLoading(false));
  }, [API, router]);

  const kpis = [
    { label:"Total Sales",  key:"total_sales",          color:"#4f46e5" },
    { label:"Output GST",   key:"output_gst",           color:"#059669" },
    { label:"ITC Available",key:"itc_available",        color:"#d97706" },
    { label:"Mismatches",   key:"pending_mismatches",   color:"#dc2626", raw:true },
  ];

  return (
    <div style={{minHeight:"100vh",background:"#f8f9fc"}}>
      <nav style={{background:"#0f172a",padding:"14px 28px",display:"flex",alignItems:"center",justifyContent:"space-between",flexWrap:"wrap",gap:"10px"}}>
        <span style={{color:"#818cf8",fontWeight:600,fontSize:"16px"}}>GST Audit Pro</span>
        <div style={{display:"flex",gap:"8px",flexWrap:"wrap"}}>
          {([["Upload","/upload"],["Reconcile","/reconciliation"],["Reports","/reports"],["AI Insights","/ai-insights"],["Vendors","/vendors"]] as [string,string][]).map(([l,h]) => (
            <button key={l} onClick={() => router.push(h)} style={{padding:"6px 12px",background:"rgba(255,255,255,0.08)",color:"#cbd5e1",border:"1px solid rgba(255,255,255,0.1)",borderRadius:"7px",fontSize:"12px",cursor:"pointer"}}>{l}</button>
          ))}
          <button onClick={() => { localStorage.clear(); router.push("/login"); }} style={{padding:"6px 12px",background:"#dc2626",color:"#fff",border:"none",borderRadius:"7px",fontSize:"12px",cursor:"pointer"}}>Sign out</button>
        </div>
      </nav>
      <div style={{padding:"24px 28px"}}>
        <h1 style={{fontSize:"20px",fontWeight:600,marginBottom:"4px"}}>Dashboard</h1>
        <p style={{fontSize:"13px",color:"#64748b",marginBottom:"20px"}}>FY 2024-25 · October 2024</p>
        {loading ? (
          <div style={{textAlign:"center",padding:"60px",color:"#64748b",fontSize:"14px"}}>Loading dashboard data...</div>
        ) : (
          <>
            <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(180px,1fr))",gap:"14px",marginBottom:"20px"}}>
              {kpis.map(c => (
                <div key={c.key} style={{background:"#fff",border:"0.5px solid #e2e8f0",borderRadius:"12px",padding:"18px 20px",borderTop:`3px solid ${c.color}`}}>
                  <div style={{fontSize:"11px",fontWeight:500,color:"#94a3b8",textTransform:"uppercase",letterSpacing:"0.5px",marginBottom:"8px"}}>{c.label}</div>
                  <div style={{fontSize:"22px",fontWeight:600,color:"#0f172a"}}>
                    {summary ? (c.raw ? String(summary[c.key as keyof Summary]) : fmt(Number(summary[c.key as keyof Summary]))) : "—"}
                  </div>
                </div>
              ))}
            </div>
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"14px"}}>
              <div style={{background:"#fff",border:"0.5px solid #e2e8f0",borderRadius:"12px",padding:"20px"}}>
                <div style={{fontSize:"11px",fontWeight:500,color:"#94a3b8",textTransform:"uppercase",letterSpacing:"0.5px",marginBottom:"12px"}}>Compliance Score</div>
                <div style={{fontSize:"48px",fontWeight:600,color:(summary?.compliance_score??0)>=80?"#059669":"#d97706"}}>
                  {summary?.compliance_score??82}<span style={{fontSize:"18px",color:"#94a3b8"}}>/100</span>
                </div>
                <div style={{marginTop:"10px",background:"#f1f5f9",borderRadius:"6px",height:"8px",overflow:"hidden"}}>
                  <div style={{height:"100%",background:"#4f46e5",width:`${summary?.compliance_score??82}%`,borderRadius:"6px"}} />
                </div>
              </div>
              <div style={{background:"#fff",border:"0.5px solid #e2e8f0",borderRadius:"12px",padding:"20px"}}>
                <div style={{fontSize:"11px",fontWeight:500,color:"#94a3b8",textTransform:"uppercase",letterSpacing:"0.5px",marginBottom:"12px"}}>Quick Actions</div>
                {([["Run GSTR-1 Reconciliation","/reconciliation"],["Upload GST Files","/upload"],["AI Insights","/ai-insights"],["Generate Report","/reports"]] as [string,string][]).map(([l,h]) => (
                  <button key={l} onClick={() => router.push(h)} style={{display:"block",width:"100%",textAlign:"left",padding:"8px 12px",marginBottom:"6px",background:"#f8f9fc",border:"0.5px solid #e2e8f0",borderRadius:"8px",fontSize:"13px",cursor:"pointer",color:"#475569"}}>{l} →</button>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
