"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
export default function LoginPage() {
  const [email,setEmail]=useState("");
  const [password,setPassword]=useState("");
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState("");
  const router=useRouter();
  const API=process.env.NEXT_PUBLIC_API_URL||"http://localhost:8000";
  async function handleLogin(e: React.FormEvent){
    e.preventDefault();setLoading(true);setError("");
    try{
      const res=await fetch(`${API}/api/v1/auth/login`,{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({email,password}),
      });
      const data=await res.json();
      if(!res.ok)throw new Error(data.detail||"Login failed");
      localStorage.setItem("access_token",data.access_token);
      localStorage.setItem("user",JSON.stringify(data.user));
      router.push("/dashboard");
    }catch(err: unknown){
      setError(err instanceof Error?err.message:"Login failed");
    }finally{setLoading(false);}
  }
  return(
    <div style={{minHeight:"100vh",display:"flex",alignItems:"center",justifyContent:"center",background:"#f8f9fc",padding:"20px"}}>
      <div style={{background:"#fff",border:"0.5px solid #e2e8f0",borderRadius:"16px",padding:"36px 40px",width:"100%",maxWidth:"400px"}}>
        <div style={{textAlign:"center",marginBottom:"28px"}}>
          <div style={{fontSize:"24px",fontWeight:600,color:"#4f46e5",marginBottom:"6px"}}>GST Audit Pro</div>
          <div style={{fontSize:"13px",color:"#64748b"}}>Sign in to your account</div>
        </div>
        {error&&<div style={{background:"#fef2f2",border:"1px solid #fecaca",color:"#991b1b",padding:"10px 14px",borderRadius:"8px",fontSize:"13px",marginBottom:"16px"}}>{error}</div>}
        <form onSubmit={handleLogin}>
          <div style={{marginBottom:"16px"}}>
            <label style={{display:"block",fontSize:"13px",fontWeight:500,marginBottom:"6px"}}>Email</label>
            <input type="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="ca@yourfirm.com" required style={{width:"100%",padding:"10px 12px",border:"1px solid #d1d5db",borderRadius:"8px",fontSize:"14px",outline:"none"}} />
          </div>
          <div style={{marginBottom:"24px"}}>
            <label style={{display:"block",fontSize:"13px",fontWeight:500,marginBottom:"6px"}}>Password</label>
            <input type="password" value={password} onChange={e=>setPassword(e.target.value)} placeholder="••••••••" required style={{width:"100%",padding:"10px 12px",border:"1px solid #d1d5db",borderRadius:"8px",fontSize:"14px",outline:"none"}} />
          </div>
          <button type="submit" disabled={loading} style={{width:"100%",padding:"11px",background:loading?"#9ca3af":"#4f46e5",color:"#fff",border:"none",borderRadius:"8px",fontSize:"14px",fontWeight:600,cursor:loading?"not-allowed":"pointer"}}>{loading?"Signing in...":"Sign in"}</button>
        </form>
        <div style={{marginTop:"20px",padding:"14px",background:"#f8f9fc",borderRadius:"8px",fontSize:"12px",color:"#64748b"}}>
          <div style={{fontWeight:500,marginBottom:"4px"}}>Demo credentials:</div>
          <div>admin@gstauditpro.in / Admin@123</div>
          <div>ca@demo.in / Demo@123</div>
          <div>user@demo.in / Demo@123</div>
        </div>
      </div>
    </div>
  );
}
