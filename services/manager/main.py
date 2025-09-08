import os, random
from fastapi import FastAPI, Body
from pydantic import BaseModel
from typing import Optional
from services.common.openai_client import get_client, get_model, extract_json

PORT = int(os.getenv("PORT", "7012"))
app = FastAPI(title="Manager", version="1.0")

class DecideIn(BaseModel):
    symbol: str
    sentiment: Optional[str] = None
    confidence_hint: Optional[float] = None
    note: Optional[str] = None

@app.get("/health")
def health():
    return {"status":"ok"}

@app.post("/decide")
def decide(body: DecideIn):
    client = get_client()
    model = get_model()
    prompt = f"""
You are a portfolio manager. Decide a single market order on {body.symbol}.
Use any hints:
- sentiment: {body.sentiment}
- note: {body.note}
Output STRICT JSON:
{{
  "intent": {{
    "symbol":"{body.symbol}",
    "side":"BUY"|"SELL",
    "qty": <int between 1 and 10>,
    "type":"market",
    "confidence": <float between 0 and 1>,
    "source":"manager"
  }}
}}
If uncertain, lower confidence and qty.
"""
    resp = client.chat.completions.create(
        model=model,
        temperature=0.3,
        messages=[{"role":"user","content":prompt}]
    )
    raw = resp.choices[0].message.content
    try:
        data = extract_json(raw)
        return data
    except Exception:
        # ultra-conservative fallback
        return {"intent":{"symbol":body.symbol,"side":"BUY","qty":1,"type":"market","confidence":0.3,"source":"manager-fallback"}}
