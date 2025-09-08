export type Idea = { symbol: string; score: number; rationale: string; }
export type Research = { symbol: string; sentiment: string; notes: string; asof: string; }
export type Intent = { symbol: string; side: "BUY"|"SELL"; qty: number; type: "market"; confidence: number; source: string; }

export async function postJSON<T>(path: string, body?: any): Promise<T> {
  const r = await fetch(`/api${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
export async function getJSON<T>(path: string): Promise<T> {
  const r = await fetch(`/api${path}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export type ChatResponse = {
  conversation: {
    user_message: string;
    focus_symbol: string;
    research: Research;
    ideas: Idea[];
    decision: Intent;
  },
  execution: any
}

export function connectAuditSSE(onRow: (row:any)=>void): EventSource {
  const es = new EventSource(`/api/logs/stream`);
  es.addEventListener("audit", (ev) => {
    try { onRow(JSON.parse((ev as MessageEvent).data)); } catch {}
  });
  return es;
}
