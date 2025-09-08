from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict
import hashlib, datetime as dt

app = FastAPI(title="Researcher", version="0.1")

class SupportRequest(BaseModel):
    symbol: str

@app.get("/health")
def health(): return {"status":"ok"}

@app.post("/support")
def support(req: SupportRequest) -> Dict:
    # Minimal “evidence” payload the manager can use
    seed = int(hashlib.md5(req.symbol.encode()).hexdigest(), 16)
    sentiment = "bullish" if seed % 3 == 0 else ("neutral" if seed % 3 == 1 else "bearish")
    notes = f"Auto-research summary for {req.symbol}: {sentiment} (seed={seed % 1000})."
    return {
        "symbol": req.symbol,
        "sentiment": sentiment,
        "notes": notes,
        "asof": dt.datetime.utcnow().isoformat()+"Z"
    }
