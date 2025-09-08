import os
from fastapi import FastAPI, Body
from pydantic import BaseModel
from typing import List, Optional
from services.common.openai_client import get_client, get_model, extract_json

PORT = int(os.getenv("PORT", "7010"))
app = FastAPI(title="Analyst", version="1.0")

class IdeasIn(BaseModel):
    symbols: Optional[List[str]] = None

@app.get("/health")
def health():
    return {"status":"ok"}

@app.post("/ideas")
def ideas(body: IdeasIn):
    symbols = body.symbols or ["AAPL","MSFT","TSLA","NVDA"]
    client = get_client()
    model = get_model()
    prompt = f"""
You are an equity analyst. Score each ticker between -1 and 1, and give a one-line rationale.
Return STRICT JSON: {{"ideas":[{{"symbol":"SYM","score":0.12,"rationale":"..."}}...]}}.
Symbols: {symbols}
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
        # ultra-safe fallback if parsing fails
        return {"ideas":[{"symbol":s,"score":0.0,"rationale":"model-parse-failed"} for s in symbols]}
