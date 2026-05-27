"use client";
import { useRouter } from "next/navigation";
export default function Page() {
  const router = useRouter();
  return (
    <div style={{minHeight:"100vh",background:"#f8f9fc"}}>
      <nav style={{background:"#0f172a",padding:"14px 28px",display:"flex",alignItems:"center",justifyContent:"space-between"}}>
        <span style={{color:"#818cf8",fontWeight:600,fontSize:"16px"}}>GST Audit Pro</span>
        <button onClick={() => router.push("/dashboard")} style={{padding:"6px 14px",background:"rgba(255,255,255,0.08)",color:"#cbd5e1",border:"1px solid rgba(255,255,255,0.1)",borderRadius:"7px",fontSize:"12px",cursor:"pointer"}}>Back to Dashboard</button>
      </nav>
      <div style={{padding:"28px"}}>
        <h1 style={{fontSize:"20px",fontWeight:600,marginBottom:"24px"}}>Upload Center</h1>
        <div style={{background:"#fff",border:"0.5px solid #e2e8f0",borderRadius:"12px",padding:"40px",textAlign:"center"}}>
          <div style={{fontSize:"48px",marginBottom:"12px"}}>🚀</div>
          <div style={{fontSize:"14px",fontWeight:500,marginBottom:"8px",color:"#0f172a"}}>Module Ready</div>
          <div style={{fontSize:"13px",color:"#64748b"}}>Connect your backend API to activate this module.</div>
        </div>
      </div>
    </div>
  );
}
