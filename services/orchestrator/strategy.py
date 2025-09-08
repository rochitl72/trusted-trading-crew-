import os, json, random
import httpx

ANALYST_URL    = os.getenv("ANALYST_URL", "http://localhost:7010")
RESEARCHER_URL = os.getenv("RESEARCHER_URL", "http://localhost:7011")
MANAGER_URL    = os.getenv("MANAGER_URL", "http://localhost:7012")

DEFAULT_SYMBOLS = ["AAPL","MSFT","TSLA","NVDA"]

def _post(url: str, payload: dict, timeout=10):
    with httpx.Client(timeout=timeout) as client:
        r = client.post(url, json=payload)
        r.raise_for_status()
        return r.json()

def gather_ideas(symbols: list[str] | None = None) -> list[dict]:
    """Ask the Analyst agent for scored ideas. Fallback if agent fails."""
    symbols = symbols or DEFAULT_SYMBOLS
    try:
        resp = _post(f"{ANALYST_URL}/ideas", {"symbols": symbols})
        ideas = resp.get("ideas", [])
        # Ensure at least symbol/score/rationale fields exist
        norm = []
        for s in symbols:
            found = next((i for i in ideas if i.get("symbol")==s), None)
            if found:
                score = float(found.get("score", 0))
                rat   = found.get("rationale","n/a")
            else:
                score = round(random.uniform(-1,1), 2)
                rat   = "fallback"
            norm.append({"symbol": s, "score": score, "rationale": rat})
        return norm
    except Exception:
        # Fallback: static/random
        return [
            {"symbol": s, "score": round(random.uniform(-1,1),2), "rationale":"fallback"}
            for s in symbols
        ]

def _insights(symbol: str) -> str:
    try:
        resp = _post(f"{RESEARCHER_URL}/insights", {"symbol": symbol})
        return resp.get("insights","")
    except Exception:
        return "(no insights available)"

def decide_order(symbol: str, preferred_side: str | None = None) -> dict:
    """
    Compose: ideas -> insights -> manager decision
    Returns an executable intent: {symbol, side, qty, type, confidence, source}
    """
    ideas = gather_ideas([symbol])
    insights = _insights(symbol)

    # Manager returns decision as JSON string or dict
    payload = {"symbol": symbol, "ideas": ideas, "insights": insights}
    try:
        resp = _post(f"{MANAGER_URL}/decide", payload)
        decision = resp.get("decision")
        if isinstance(decision, str):
            try:
                decision = json.loads(decision)
            except Exception:
                decision = {}
        if not isinstance(decision, dict):
            decision = {}
        side = (preferred_side or decision.get("side") or
                ("BUY" if (ideas[0]["score"] >= 0) else "SELL"))
        qty  = int(decision.get("qty") or max(1, int(abs(ideas[0]["score"])*10)))
        conf = float(decision.get("confidence") or min(1.0, abs(ideas[0]["score"])))
        return {
            "symbol": symbol,
            "side": side.upper(),
            "qty": qty,
            "type": "market",
            "confidence": round(conf, 2),
            "source": "manager-agent" if decision else "fallback-manager",
        }
    except Exception:
        # Fallback manager
        side = (preferred_side or ("BUY" if (ideas[0]["score"] >= 0) else "SELL"))
        return {
            "symbol": symbol,
            "side": side.upper(),
            "qty": max(1, int(abs(ideas[0]["score"])*10)),
            "type": "market",
            "confidence": round(min(1.0, abs(ideas[0]["score"])), 2),
            "source": "fallback-manager",
        }
