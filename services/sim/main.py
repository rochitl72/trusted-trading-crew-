import os, time
from datetime import datetime
from fastapi import FastAPI, Request

app = FastAPI(title="Trading Simulator", version="0.1")

SLIPPAGE_BPS = int(os.getenv("SLIPPAGE_BPS","2"))
FEES_BPS     = int(os.getenv("FEES_BPS","1"))
PRICE        = {"AAPL": 200.00, "MSFT": 440.00, "TSLA": 240.00, "NVDA": 120.00}

@app.get("/health")
def health():
    return {"status":"ok", "symbols": list(PRICE.keys())}

@app.get("/market/quote")
def quote(symbol: str):
    px = PRICE.get(symbol.upper(), 100.0)
    return {"symbol": symbol.upper(), "price": px, "ts": datetime.utcnow().isoformat()}

@app.post("/orders")
async def create_order(req: Request):
    body = await req.json()
    sym = str(body.get("symbol","")).upper()
    side = body.get("side","BUY").upper()
    qty  = int(body.get("qty",0))
    typ  = body.get("type","market").lower()

    px = PRICE.get(sym, 100.0)
    slip = (SLIPPAGE_BPS/10000.0) * px
    fill_px = px + slip if side=="BUY" else px - slip
    fees = (FEES_BPS/10000.0) * (fill_px * max(qty,0))
    PRICE[sym] = round(px * (1 + (0.0005 if side=="BUY" else -0.0005)), 4)

    return {
        "symbol": sym,
        "side": side,
        "qty": qty,
        "avg_price": round(fill_px, 4),
        "fees": round(fees, 4),
        "filled_at": datetime.utcnow().isoformat()
    }
