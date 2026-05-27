import Link from "next/link";

export default function HomePage() {
  return (
    <main style={{
      minHeight:"100vh",
      background:"linear-gradient(135deg,#0f172a 0%,#1e1b4b 50%,#0f172a 100%)",
      display:"flex",flexDirection:"column",alignItems:"center",
      justifyContent:"center",padding:"40px 20px",textAlign:"center"
    }}>
      <div style={{
        background:"rgba(99,102,241,0.15)",border:"1px solid rgba(99,102,241,0.3)",
        color:"#a5b4fc",padding:"6px 16px",borderRadius:"20px",
        fontSize:"12px",fontWeight:500,marginBottom:"24px",display:"inline-block"
      }}>
        Trusted by 2,000+ CAs &amp; Tax Consultants
      </div>
      <h1 style={{fontSize:"42px",fontWeight:600,color:"#fff",lineHeight:1.2,letterSpacing:"-1px",marginBottom:"16px"}}>
        India&apos;s Smartest{" "}
        <span style={{color:"#818cf8"}}>GST Audit</span>
        <br />&amp; Reconciliation Platform
      </h1>
      <p style={{fontSize:"16px",color:"#94a3b8",maxWidth:"520px",margin:"0 auto 32px",lineHeight:1.6}}>
        Auto-reconcile GSTR-1, GSTR-2B, GSTR-3B with your books.
        Detect mismatches, claim correct ITC, stay GST compliant — in minutes.
      </p>
      <div style={{display:"flex",gap:"12px",justifyContent:"center",flexWrap:"wrap"}}>
        <Link href="/login" style={{
          padding:"12px 28px",borderRadius:"10px",fontSize:"14px",fontWeight:600,
          background:"#4f46e5",color:"#fff",textDecoration:"none",display:"inline-block"
        }}>Start Free Trial →</Link>
        <Link href="/dashboard" style={{
          padding:"12px 28px",borderRadius:"10px",fontSize:"14px",fontWeight:600,
          background:"rgba(255,255,255,0.08)",color:"#e2e8f0",
          border:"1px solid rgba(255,255,255,0.15)",textDecoration:"none",display:"inline-block"
        }}>View Live Demo</Link>
      </div>
      <div style={{
        display:"grid",gridTemplateColumns:"repeat(4,1fr)",
        background:"#4f46e5",padding:"28px 40px",marginTop:"60px",
        borderRadius:"12px",width:"100%",maxWidth:"700px"
      }}>
        {[["₹2,400 Cr+","GST Reconciled"],["1.2M+","Invoices"],["2,000+","Businesses"],["99.8%","Accuracy"]].map(([n,l])=>(
          <div key={l} style={{textAlign:"center",padding:"0 12px",borderRight:"1px solid rgba(255,255,255,0.2)"}}>
            <div style={{fontSize:"22px",fontWeight:600,color:"#fff"}}>{n}</div>
            <div style={{fontSize:"11px",color:"#c7d2fe",marginTop:"3px"}}>{l}</div>
          </div>
        ))}
      </div>
    </main>
  );
}
