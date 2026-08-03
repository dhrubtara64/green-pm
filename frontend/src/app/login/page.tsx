"use client";

import { useEffect, useRef, useState } from "react";

const NODES = [
  { id:"S",  label:"START", name:"",            rx:0.05, ry:0.50, crit:true,  score:null, flag:null     },
  { id:"N1", label:"1.1",   name:"GT Fdn",      rx:0.21, ry:0.16, crit:true,  score:85,   flag:"ok"     },
  { id:"N2", label:"2.1",   name:"Civils",      rx:0.21, ry:0.50, crit:false, score:72,   flag:"review" },
  { id:"N3", label:"3.1",   name:"Procure",     rx:0.21, ry:0.84, crit:false, score:91,   flag:"ok"     },
  { id:"N4", label:"1.2",   name:"Steelwork",   rx:0.40, ry:0.10, crit:true,  score:63,   flag:"review" },
  { id:"N5", label:"2.2",   name:"MCC Room",    rx:0.40, ry:0.44, crit:false, score:48,   flag:"verify" },
  { id:"N6", label:"3.2",   name:"GT Delivery", rx:0.40, ry:0.78, crit:true,  score:95,   flag:"ok"     },
  { id:"N7", label:"1.3",   name:"GT Install",  rx:0.60, ry:0.26, crit:true,  score:41,   flag:"verify" },
  { id:"N8", label:"2.3",   name:"Cabling",     rx:0.60, ry:0.63, crit:false, score:29,   flag:"verify" },
  { id:"N9", label:"1.4",   name:"Commsn",      rx:0.79, ry:0.39, crit:true,  score:22,   flag:"verify" },
  { id:"F",  label:"END",   name:"",            rx:0.94, ry:0.50, crit:true,  score:null, flag:null     },
] as const;

const EDGES = [
  { f:"S",  t:"N1", crit:true  },
  { f:"S",  t:"N2", crit:false },
  { f:"S",  t:"N3", crit:false },
  { f:"N1", t:"N4", crit:true  },
  { f:"N2", t:"N5", crit:false },
  { f:"N3", t:"N6", crit:true  },
  { f:"N4", t:"N7", crit:true  },
  { f:"N5", t:"N8", crit:false },
  { f:"N6", t:"N7", crit:true  },
  { f:"N7", t:"N9", crit:true  },
  { f:"N7", t:"N8", crit:false },
  { f:"N8", t:"N9", crit:false },
  { f:"N9", t:"F",  crit:true  },
  { f:"N8", t:"F",  crit:false },
];

function flagColor(flag: string | null) {
  if (flag === "ok")     return "#4ade80";
  if (flag === "review") return "#fbbf24";
  if (flag === "verify") return "#f87171";
  return "rgba(255,255,255,0.2)";
}

export default function LoginPage() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("error") === "AccessDenied") {
      setErrorMsg("Access restricted. Contact your administrator.");
    }
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const parent = canvas.parentElement;
    if (!parent) return;

    const ctx = canvas.getContext("2d")!;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let frameId = 0;

    function resize() {
      canvas!.width  = parent!.offsetWidth  * dpr;
      canvas!.height = parent!.offsetHeight * dpr;
      canvas!.style.width  = parent!.offsetWidth  + "px";
      canvas!.style.height = parent!.offsetHeight + "px";
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(parent);

    const W = () => canvas!.offsetWidth;
    const H = () => canvas!.offsetHeight;
    const R = 19;

    const critEdges = EDGES.filter(e => e.crit);
    const edgeOffsets = new Map(critEdges.map((e, i) => [`${e.f}-${e.t}`, i / critEdges.length]));

    const t0 = performance.now();

    function draw() {
      const w = W(), h = H();
      ctx.clearRect(0, 0, w, h);
      const t = (performance.now() - t0) / 1000;

      // grid
      ctx.save();
      ctx.strokeStyle = "rgba(74,222,128,0.05)";
      ctx.lineWidth = 0.5;
      const gs = Math.max(w, h) / 18;
      for (let x = 0; x <= w + gs; x += gs) { ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,h); ctx.stroke(); }
      for (let y = 0; y <= h + gs; y += gs) { ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(w,y); ctx.stroke(); }
      ctx.restore();

      // resolve positions
      const nm: Record<string, { px:number; py:number; vis:boolean; crit:boolean; score:number|null; flag:string|null; label:string; name:string; id:string; rx:number }> = {};
      NODES.forEach(n => { nm[n.id] = { ...n, px: n.rx*w, py: n.ry*h, vis: t > n.rx*3 }; });

      // scan line
      const scanX = ((t * 0.11) % 1.2 - 0.1) * w;
      const sg = ctx.createLinearGradient(scanX-20, 0, scanX+20, 0);
      sg.addColorStop(0,   "rgba(74,222,128,0)");
      sg.addColorStop(0.5, "rgba(74,222,128,0.055)");
      sg.addColorStop(1,   "rgba(74,222,128,0)");
      ctx.fillStyle = sg;
      ctx.fillRect(scanX-20, 0, 40, h);

      // edges
      EDGES.forEach(e => {
        const fn = nm[e.f], tn = nm[e.t];
        if (!fn?.vis || !tn?.vis) return;
        const dx = tn.px-fn.px, dy = tn.py-fn.py;
        const dist = Math.sqrt(dx*dx+dy*dy);
        const nx = dx/dist, ny = dy/dist;
        const x1 = fn.px+nx*(R+2), y1 = fn.py+ny*(R+2);
        const x2 = tn.px-nx*(R+5), y2 = tn.py-ny*(R+5);

        ctx.save();
        if (e.crit) {
          const p = 0.55 + 0.45*Math.sin(t*1.6);
          ctx.shadowColor = "#4ade80"; ctx.shadowBlur = 7*p;
          ctx.strokeStyle = `rgba(74,222,128,${0.72*p})`; ctx.lineWidth = 1.8;
        } else {
          ctx.strokeStyle = "rgba(255,255,255,0.11)"; ctx.lineWidth = 1;
        }
        ctx.beginPath(); ctx.moveTo(x1,y1); ctx.lineTo(x2,y2); ctx.stroke();
        ctx.restore();

        // arrowhead
        const ang = Math.atan2(y2-y1, x2-x1);
        ctx.save();
        ctx.beginPath();
        ctx.moveTo(x2,y2);
        ctx.lineTo(x2-6*Math.cos(ang-0.42), y2-6*Math.sin(ang-0.42));
        ctx.lineTo(x2-6*Math.cos(ang+0.42), y2-6*Math.sin(ang+0.42));
        ctx.closePath();
        ctx.fillStyle = e.crit ? "rgba(74,222,128,0.65)" : "rgba(255,255,255,0.11)";
        ctx.fill();
        ctx.restore();

        // flow dot on critical path
        if (e.crit) {
          const off = edgeOffsets.get(`${e.f}-${e.t}`) ?? 0;
          const ft = ((t*0.38 + off) % 1);
          ctx.save();
          ctx.beginPath(); ctx.arc(x1+(x2-x1)*ft, y1+(y2-y1)*ft, 2.5, 0, Math.PI*2);
          ctx.fillStyle = "#4ade80"; ctx.shadowColor = "#4ade80"; ctx.shadowBlur = 6;
          ctx.fill();
          ctx.restore();
        }
      });

      // nodes
      NODES.forEach(nd => {
        const n = nm[nd.id];
        if (!n.vis) return;
        const { px, py, crit, score, flag } = n;
        const isTerm = n.id === "S" || n.id === "F";

        // score track + arc
        if (score !== null) {
          ctx.save();
          ctx.beginPath(); ctx.arc(px, py, R+5, 0, Math.PI*2);
          ctx.strokeStyle = "rgba(255,255,255,0.06)"; ctx.lineWidth = 2.5;
          ctx.stroke();
          ctx.beginPath();
          ctx.arc(px, py, R+5, -Math.PI/2, -Math.PI/2+(score/100)*Math.PI*2);
          ctx.strokeStyle = flagColor(flag); ctx.lineWidth = 2.5; ctx.lineCap = "round";
          ctx.shadowColor = flagColor(flag); ctx.shadowBlur = 5;
          ctx.stroke();
          ctx.restore();
        }

        // outer pulse
        if (crit) {
          const p2 = 0.4+0.6*Math.sin(t*1.4+n.rx*6);
          ctx.save();
          ctx.beginPath(); ctx.arc(px, py, R+10, 0, Math.PI*2);
          ctx.strokeStyle = `rgba(74,222,128,${0.14*p2})`; ctx.lineWidth = 2;
          ctx.stroke();
          ctx.restore();
        }

        // fill
        ctx.save();
        ctx.beginPath(); ctx.arc(px, py, R, 0, Math.PI*2);
        ctx.fillStyle = isTerm ? "#16a34a" : "#1a5e36";
        ctx.fill();
        ctx.strokeStyle = crit ? "rgba(74,222,128,0.65)" : "rgba(255,255,255,0.18)"; ctx.lineWidth = 1.5;
        ctx.stroke();
        const sd = Math.abs(px-scanX);
        if (sd < 55) { ctx.beginPath(); ctx.arc(px,py,R,0,Math.PI*2); ctx.fillStyle=`rgba(74,222,128,${(1-sd/55)*0.18})`; ctx.fill(); }
        ctx.restore();

        // labels
        ctx.save();
        ctx.textAlign = "center"; ctx.textBaseline = "middle";
        ctx.fillStyle = "rgba(255,255,255,0.92)";
        ctx.font = "bold 9px system-ui";
        ctx.fillText(n.label, px, py);
        if (n.name) {
          ctx.fillStyle = "rgba(255,255,255,0.33)"; ctx.font = "7px system-ui";
          ctx.fillText(n.name, px, py+R+9);
        }
        ctx.restore();
      });

      frameId = requestAnimationFrame(draw);
    }

    frameId = requestAnimationFrame(draw);
    return () => { cancelAnimationFrame(frameId); ro.disconnect(); };
  }, []);

  return (
    <div className="gpm-layout">

      {/* LEFT: Hero */}
      <div className="gpm-hero">

        {/* Animation area */}
        <div style={{ flex:"1 1 0%", position:"relative", minHeight:0 }}>
          <canvas ref={canvasRef} style={{ position:"absolute", inset:0, display:"block" }} />
          <div style={{ position:"absolute", bottom:0, left:0, right:0, height:64, background:"linear-gradient(to top, #0f5132 0%, transparent 100%)", pointerEvents:"none" }} />
        </div>

        {/* Brand */}
        <div style={{ flexShrink:0, display:"flex", flexDirection:"column", alignItems:"center", gap:"0.3rem", padding:"1.75rem 2rem 2.5rem", textAlign:"center" }}>
          <div style={{ width:62, height:62, background:"#16a34a", borderRadius:"50%", display:"flex", alignItems:"center", justifyContent:"center", marginBottom:"0.625rem", boxShadow:"0 0 0 2.5px rgba(74,222,128,0.38), 0 8px 32px rgba(0,0,0,0.5)" }}>
            <svg viewBox="0 0 24 24" width="30" height="30" fill="none">
              <rect x="3" y="5" width="11" height="2.5" rx="1" fill="white"/>
              <rect x="3" y="10.75" width="16" height="2.5" rx="1" fill="white"/>
              <rect x="3" y="16.5" width="8" height="2.5" rx="1" fill="white"/>
            </svg>
          </div>
          <p style={{ fontSize:"0.9375rem", fontWeight:700, letterSpacing:"0.04em", color:"rgba(255,255,255,0.55)", margin:0 }}>BELLARY CCGT · 900 MW</p>
          <h1 style={{ fontSize:"3rem", fontWeight:800, letterSpacing:"-0.035em", color:"#fff", lineHeight:1, margin:0 }}>Green PM</h1>
          <p style={{ fontSize:"0.9rem", color:"rgba(255,255,255,0.42)", lineHeight:1.65, margin:0 }}>
            Built on Evidence.<br />Powered by Intelligence.
          </p>
        </div>
      </div>

      {/* RIGHT: Form */}
      <div className="gpm-form">
        <div style={{ width:"100%", maxWidth:340 }}>

          {/* App icon */}
          <div style={{ width:56, height:56, background:"#16a34a", borderRadius:14, display:"flex", alignItems:"center", justifyContent:"center", marginBottom:"1.375rem", boxShadow:"0 4px 14px rgba(22,163,74,0.3)" }}>
            <svg viewBox="0 0 24 24" width="26" height="26">
              <rect x="3"  y="5.5"  width="11" height="2.5" rx="1" fill="white"/>
              <rect x="3"  y="10.75" width="16" height="2.5" rx="1" fill="white"/>
              <rect x="3"  y="16"   width="8"  height="2.5" rx="1" fill="white"/>
            </svg>
          </div>

          <h2 style={{ fontSize:"1.5rem", fontWeight:700, letterSpacing:"-0.025em", color:"#111827", marginBottom:"0.25rem" }}>
            Sign in to Green PM
          </h2>
          <p style={{ fontSize:"0.875rem", color:"#6b7280", marginBottom:"1.875rem" }}>Sign in to continue</p>

          {errorMsg && (
            <div style={{ padding:"0.625rem 0.875rem", background:"#fef2f2", border:"1px solid #fecaca", borderRadius:8, color:"#dc2626", fontSize:"0.8125rem", marginBottom:"1rem" }}>
              {errorMsg}
            </div>
          )}

          <button
            onClick={() => {
              document.cookie = "greenpm_session=1; path=/; max-age=86400; SameSite=Lax";
              window.location.href = "/";
            }}
            style={{ display:"flex", alignItems:"center", justifyContent:"center", gap:"0.75rem", width:"100%", padding:"0.6875rem 1rem", background:"#fff", color:"#3c4043", border:"1px solid #dadce0", borderRadius:8, fontSize:"0.9375rem", fontWeight:500, cursor:"pointer", fontFamily:"inherit", letterSpacing:"0.01em", boxShadow:"0 1px 3px rgba(0,0,0,0.08)" }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
            </svg>
            Sign in with Google
          </button>

          <p style={{ marginTop:"2rem", textAlign:"center", fontSize:"0.75rem", color:"#9ca3af" }}>
            Controlled UAT build · Not for production use
          </p>
        </div>
      </div>
    </div>
  );
}
