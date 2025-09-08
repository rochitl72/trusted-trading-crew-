const BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:7000";

export async function grantConsent(user_id: string, scope = "place:live") {
  const r = await fetch(`${BASE}/consent/grant`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id, scope }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json(); // { consent_id }
}

export async function debugMint(scope: string) {
  const r = await fetch(`${BASE}/debug/mint?scope=${encodeURIComponent(scope)}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json(); // {scope, token_prefix, len}
}
