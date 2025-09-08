import { useEffect, useMemo, useState } from "react";
import { connectAuditSSE, postJSON, type ChatResponse, type Idea } from "./api";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, CartesianGrid, BarChart, Bar } from "recharts";
import { Rocket, Workflow, Send, ShieldCheck, Activity, Brain, PlayCircle, Bot, CircleDollarSign } from "lucide-react";
import clsx from "clsx";
import "./index.css";

const UNIVERSE = ["AAPL","MSFT","TSLA","NVDA"];

const synth = (seed=200, n=90) => {
  let x = seed; const out:any[] = [];
  for (let i=0;i<n;i++){ x += (Math.random()-0.5)*0.8 + Math.sin(i/13)*0.3; out.push({t:i, p:+x.toFixed(2)}); }
  return out;
};

export default function App(){
  const [message,setMessage]=useState("I think semis are strong, what about AAPL vs NVDA?");
  const [symbol,setSymbol]=useState("AAPL");
  const [qty,setQty]=useState(2);
  const [live,setLive]=useState(false);
  const [consent,setConsent]=useState<{user_id:string,consent_id:string}|null>(null);
  const [ideas,setIdeas]=useState<Idea[]>([]);
  const [chat,setChat]=useState<ChatResponse|null>(null);
  const [busy,setBusy]=useState(false);
  const [err,setErr]=useState<string|null>(null);
  const [audit,setAudit]=useState<any[]>([]);
  useEffect(()=>{ const es=connectAuditSSE(r=>setAudit(a=>[r,...a].slice(0,150))); return ()=>es.close(); },[]);
  useEffect(()=>{ (async()=>{ try{ const r=await postJSON<{ideas:Idea[]}>("/strategy/ideas",{}); setIdeas(r.ideas);}catch{}})(); },[]);
  const series=useMemo(()=>synth(200,100),[]);

  async function orchestrate(){
    setBusy(true); setErr(null);
    try{
      const body:any={ message, symbol, qty };
      if(live){
        if(!consent){
          const c = await postJSON<{consent_id:string}>("/consent/grant",{user_id:"demo-user",scope:"place:live"});
          setConsent({user_id:"demo-user",consent_id:c.consent_id});
        }
        body.live=true; body.user_id="demo-user"; body.consent_id=(consent?.consent_id)!;
      }
      const r=await postJSON<ChatResponse>("/strategy/chat", body);
      setChat(r);
    }catch(e:any){ setErr(e?.message||"Failed"); }
    finally{ setBusy(false); }
  }
  async function sim(side:"BUY"|"SELL"){
    setBusy(true); setErr(null);
    try{
      const r=await postJSON("/trade/simulate",{symbol,side,qty,type:"market"});
      setChat(prev=>prev?{...prev,execution:r}:prev);
    }catch(e:any){ setErr(e?.message||"Failed"); }
    finally{ setBusy(false); }
  }

  const displayIdeas = chat?.conversation?.ideas ?? ideas;
  const research = chat?.conversation?.research;
  const decision = chat?.conversation?.decision;

  return (
    <div className="min-h-screen">
      {/* TOP NAV */}
      <div className="border-b border-line/80 bg-gradient-to-b from-bg1 to-bg0/0">
        <div className="container-xxl px-5 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-bg2 shadow-glow">
              <Workflow className="text-accent-1" size={18}/>
            </div>
            <div>
              <div className="text-xl font-semibold">Trusted Trading Crew</div>
              <div className="text-xs opacity-60">Multi-Agent Orchestration • Risk-Gated • Signed Receipts</div>
            </div>
          </div>
          <div className="badge">Local: 127.0.0.1</div>
        </div>
      </div>

      {/* GRID */}
      <div className="container-xxl px-5 py-6 grid grid-cols-12 gap-6">
        {/* LEFT */}
        <div className="col-span-12 lg:col-span-8 space-y-6">
          {/* Conversation */}
          <div className="card p-5">
            <div className="flex items-center gap-2 mb-4">
              <Bot size={18} className="text-accent-1"/><h3 className="font-semibold">Conversation → Orchestration → Execution</h3>
            </div>
            <div className="flex flex-col md:flex-row gap-3">
              <input className="flex-1 btn" value={message} onChange={e=>setMessage(e.target.value)} />
              <select className="btn" value={symbol} onChange={e=>setSymbol(e.target.value)}>
                {UNIVERSE.map(s=><option key={s}>{s}</option>)}
              </select>
              <input className="btn w-24" type="number" min={1} value={qty} onChange={e=>setQty(parseInt(e.target.value||"1"))}/>
              <label className={clsx("btn cursor-pointer", live && "ring-1 ring-accent-3/50")}>
                <input type="checkbox" className="mr-2" checked={live} onChange={e=>setLive(e.target.checked)}/> Live
              </label>
              <button className={clsx("btn btn-primary", busy && "opacity-60 cursor-wait")} onClick={orchestrate}>
                <div className="flex items-center gap-2"><Send size={16}/> Orchestrate</div>
              </button>
            </div>
            {err && <div className="mt-3 text-sm text-red-400">{err}</div>}

            <div className="grid grid-cols-12 gap-4 mt-5">
              {/* Research */}
              <div className="col-span-12 lg:col-span-6 card p-4">
                <div className="flex items-center gap-2 mb-2"><Brain size={16} className="text-accent-2"/><div className="font-semibold">Research</div></div>
                {!research ? <div className="opacity-60 text-sm">Run “Orchestrate” to fetch research.</div> :
                  <div className="text-sm">
                    <div className="opacity-80 mb-1">Sentiment: <span className={clsx(research.sentiment==="bullish"?"text-accent-3":"text-accent-4","font-semibold")}>{research.sentiment}</span></div>
                    <div className="opacity-90">{research.notes}</div>
                    <div className="opacity-60 text-xs mt-2">as of {new Date(research.asof).toLocaleString()}</div>
                  </div>}
              </div>

              {/* Ideas */}
              <div className="col-span-12 lg:col-span-6 card p-4">
                <div className="flex items-center gap-2 mb-2"><Activity size={16} className="text-accent-1"/><div className="font-semibold">Ideas (Analyst)</div></div>
                <div className="h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={displayIdeas} margin={{top:5,right:6,left:0,bottom:5}}>
                      <CartesianGrid stroke="#1a2744" strokeDasharray="3 3"/>
                      <XAxis dataKey="symbol" tick={{fill:"#a7c0ff"}}/>
                      <YAxis domain={[-1,1]} tick={{fill:"#a7c0ff"}}/>
                      <Tooltip contentStyle={{background:"#0E1626", border:"1px solid #1b2b4a", borderRadius:12}}/>
                      <Legend />
                      <Bar dataKey="score" name="score" fill="#19A7FF" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Decision */}
              <div className="col-span-12 card p-4">
                <div className="flex items-center gap-2 mb-2"><ShieldCheck size={16} className="text-accent-3"/><div className="font-semibold">Manager Decision</div></div>
                {!decision ? <div className="opacity-60 text-sm">Run “Orchestrate” to get a decision.</div> :
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                    <Stat label="Symbol" value={decision.symbol}/>
                    <Stat label="Side" value={decision.side} color={decision.side==="BUY"?"text-accent-3":"text-accent-4"}/>
                    <Stat label="Qty" value={String(decision.qty)}/>
                    <Stat label="Confidence" value={`${(decision.confidence*100).toFixed(0)}%`}/>
                  </div>}
                <div className="flex items-center gap-3 mt-3">
                  <button onClick={()=>sim("BUY")} className="btn bg-accent-3/10 hover:bg-accent-3/20 border-accent-3/30 flex items-center gap-2"><PlayCircle size={16}/> Sim BUY</button>
                  <button onClick={()=>sim("SELL")} className="btn bg-accent-4/10 hover:bg-accent-4/20 border-accent-4/30 flex items-center gap-2"><PlayCircle size={16}/> Sim SELL</button>
                </div>
              </div>

              {/* Price */}
              <div className="col-span-12 card p-4">
                <div className="flex items-center gap-2 mb-2"><CircleDollarSign size={16} className="text-accent-5"/><div className="font-semibold">Price (synthetic)</div></div>
                <div className="h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={series} margin={{top:5,right:8,left:0,bottom:5}}>
                      <CartesianGrid stroke="#1a2744" strokeDasharray="4 4"/>
                      <XAxis dataKey="t" tick={{fill:"#a7c0ff"}}/>
                      <YAxis tick={{fill:"#a7c0ff"}}/>
                      <Tooltip contentStyle={{background:"#0E1626", border:"1px solid #1b2b4a", borderRadius:12}}/>
                      <Legend />
                      <Line type="monotone" dataKey="p" name="price" stroke="#19A7FF" dot={false}/>
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </div>

          {/* Audit */}
          <div className="card p-5">
            <div className="flex items-center gap-2 mb-3"><Rocket size={16} className="text-accent-1"/><div className="font-semibold">Audit Stream (signed receipts + risk verdicts)</div></div>
            <div className="overflow-auto max-h-80">
              {audit.length===0 && <div className="opacity-60 text-sm">No audit rows yet. Execute a trade to see signed receipts.</div>}
              {audit.map((row,i)=>(
                <div key={i} className="py-2 border-b border-line/60 text-xs font-mono">
                  <div className="opacity-70">{(row.created_at||"").replace("T"," ").slice(0,19)} • {row.agent} • {row.scope}</div>
                  <div className="truncate">{JSON.stringify(row.signed_result)}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* RIGHT */}
        <div className="col-span-12 lg:col-span-4 space-y-6">
          <div className="card p-5">
            <div className="flex items-center gap-2 mb-3"><Workflow size={16} className="text-accent-2"/><div className="font-semibold">Crew Status</div></div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <Pill ok label="Orchestrator"/><Pill ok label="Risk"/>
              <Pill ok label="Broker"/><Pill ok label="Analyst"/>
              <Pill ok label="Researcher"/><Pill ok label="Manager"/>
            </div>
          </div>
          <div className="card p-5">
            <div className="font-semibold mb-3">Quick Actions</div>
            <div className="flex flex-wrap gap-3">
              <button className="btn" onClick={()=>setMessage("Rotate into strongest idea and go live 1 share")}>Rotate strongest</button>
              <button className="btn" onClick={()=>{ setLive(false); setMessage("Simulate buy 2 if research is bullish"); setQty(2); }}>Sim Bullish</button>
              <button className="btn" onClick={()=>{ setLive(true); setMessage("If risk ok, live sell 1"); setQty(1); }}>Live Risk-Gate</button>
            </div>
          </div>
        </div>
      </div>

      {/* FOOTER */}
      <div className="container-xxl px-5 py-6 text-xs opacity-60">
        © Trusted Trading Crew — Transparent multi-agent decisions • Signatures • Consent • Descope OAuth
      </div>
    </div>
  );
}

function Stat({label,value,color}:{label:string;value:string;color?:string}){
  return (
    <div className="p-3 rounded-xl bg-bg2 border border-line">
      <div className="opacity-60">{label}</div>
      <div className={clsx("font-semibold", color)}>{value}</div>
    </div>
  );
}
function Pill({label,ok}:{label:string;ok:boolean}){
  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-bg2 border border-line">
      <div className={clsx("w-2 h-2 rounded-full", ok?"bg-accent-3":"bg-accent-4")} />
      <span>{label}</span>
    </div>
  );
}
