import os, json, sqlite3, uuid, base64, time, asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException, Body
from starlette.responses import StreamingResponse
import httpx

# --- Load .env automatically ---
try:
    from dotenv import load_dotenv
    load_dotenv("services/orchestrator/.env")
except Exception:
    pass

app = FastAPI(title="Orchestrator", version="0.4")

# env
DESCOPE_TOKEN_URL       = os.getenv("DESCOPE_TOKEN_URL")
ORCH_CLIENT_ID          = os.getenv("ORCH_CLIENT_ID")
ORCH_CLIENT_SECRET      = os.getenv("ORCH_CLIENT_SECRET")
ORCH_LIVE_CLIENT_ID     = os.getenv("ORCH_LIVE_CLIENT_ID")
ORCH_LIVE_CLIENT_SECRET = os.getenv("ORCH_LIVE_CLIENT_SECRET")

RISK_URL   = os.getenv("RISK_URL",   "http://localhost:7002")
BROKER_URL = os.getenv("BROKER_URL", "http://localhost:7003")
DB_PATH    = os.getenv("DATABASE_URL", "sqlite:///./data/trusted_trading.sqlite3").replace("sqlite:///", "")

def db():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = db(); cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS consents(
        id TEXT PRIMARY KEY,
        user_id TEXT,
        scope TEXT,
        granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS audit_logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent TEXT, action TEXT, scope TEXT, signed_result TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit(); conn.close()
init_db()

# ---------- TOKEN MINTING WITH CACHE + RETRY ----------

_TOKEN_CACHE: dict[str, tuple[float, str]] = {}

async def _mint(scope: str) -> str:
    """
    Mint an OAuth access token from Descope.
    Adds:
      - per-scope in-memory cache (30s)
      - 3 retries with exponential backoff
      - longer timeout for slowness
    """
    if not DESCOPE_TOKEN_URL:
        raise RuntimeError("DESCOPE_TOKEN_URL is not set")

    # serve cached token if still fresh
    now = time.time()
    cached = _TOKEN_CACHE.get(scope)
    if cached and now - cached[0] < 30:
        return cached[1]

    if scope == "place:live":
        cid  = ORCH_LIVE_CLIENT_ID or os.getenv("ORCH_LIVE_CLIENT_ID")
        csec = ORCH_LIVE_CLIENT_SECRET or os.getenv("ORCH_LIVE_CLIENT_SECRET")
    else:
        cid, csec = ORCH_CLIENT_ID, ORCH_CLIENT_SECRET

    if not cid or not csec:
        raise RuntimeError(f"Missing client credentials for scope '{scope}'")

    basic = base64.b64encode(f"{cid}:{csec}".encode()).decode()
    headers = {"Authorization": f"Basic {basic}"}

    last_err = None
    for attempt in range(3):  # retries
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.post(
                    DESCOPE_TOKEN_URL,
                    headers=headers,
                    data={"grant_type": "client_credentials", "scope": scope},
                )
            if r.status_code == 200:
                token = r.json()["access_token"]
                _TOKEN_CACHE[scope] = (time.time(), token)
                return token
            last_err = r.text
        except httpx.ConnectTimeout as e:
            last_err = f"ConnectTimeout: {e}"
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
        time.sleep(0.5 * (2 ** attempt))  # exponential backoff

    raise HTTPException(502, detail=f"Token mint failed after retries: {last_err}")

# ---------- LOGGING ----------

def _log(agent: str, action: str, scope: str, payload: dict):
    conn = db(); cur = conn.cursor()
    cur.execute("INSERT INTO audit_logs(agent,action,scope,signed_result,created_at) VALUES(?,?,?,?,?)",
                (agent, action, scope, json.dumps(payload), datetime.utcnow().isoformat()))
    conn.commit(); conn.close()

# ---------- HEALTH / DEBUG ----------

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/debug/env")
def debug_env():
    return {
        "has_ORCH_CLIENT_ID": bool(ORCH_CLIENT_ID),
        "has_ORCH_CLIENT_SECRET": bool(ORCH_CLIENT_SECRET),
        "has_ORCH_LIVE_CLIENT_ID": bool(ORCH_LIVE_CLIENT_ID),
        "has_ORCH_LIVE_CLIENT_SECRET": bool(ORCH_LIVE_CLIENT_SECRET),
        "token_url_set": bool(DESCOPE_TOKEN_URL),
        "risk_url": RISK_URL,
        "broker_url": BROKER_URL,
    }

@app.get("/debug/mint")
async def debug_mint(scope: str = "place:live"):
    token = await _mint(scope)
    return {"scope": scope, "token_prefix": token[:20] + "...", "len": len(token)}

# ---------- CONSENT FLOW ----------

@app.post("/consent/grant")
def consent_grant(user_id: str = Body(...), scope: str = Body("place:live")):
    if scope != "place:live":
        raise HTTPException(400, detail="only place:live consent is supported in this demo")
    cid = str(uuid.uuid4())
    conn = db(); cur = conn.cursor()
    cur.execute("INSERT INTO consents(id,user_id,scope,granted_at) VALUES(?,?,?,?)",
                (cid, user_id, scope, datetime.utcnow().isoformat()))
    conn.commit(); conn.close()
    return {"consent_id": cid, "user_id": user_id, "scope": scope}

@app.get("/consent/{consent_id}")
def consent_get(consent_id: str):
    conn = db(); cur = conn.cursor()
    cur.execute("SELECT id,user_id,scope,granted_at FROM consents WHERE id = ?", (consent_id,))
    row = cur.fetchone(); conn.close()
    if not row:
        raise HTTPException(404, detail="consent not found")
    return {"consent_id": row[0], "user_id": row[1], "scope": row[2], "granted_at": row[3]}

@app.get("/consent")
def consent_list():
    conn = db(); cur = conn.cursor()
    cur.execute("SELECT id,user_id,scope,granted_at FROM consents ORDER BY granted_at DESC LIMIT 50")
    rows = cur.fetchall(); conn.close()
    return [{"consent_id": r[0], "user_id": r[1], "scope": r[2], "granted_at": r[3]} for r in rows]

# ---------- SIMULATED TRADE ----------

@app.post("/trade/simulate")
async def trade_sim(order: dict):
    risk_token = await _mint("risk.evaluate")
    async with httpx.AsyncClient(timeout=10) as client:
        rr = await client.post(f"{RISK_URL}/risk/evaluate",
                               headers={"Authorization": f"Bearer {risk_token}"},
                               json=order)
    if rr.status_code != 200:
        raise HTTPException(rr.status_code, detail=rr.text)
    verdict = rr.json()
    _log("risk-agent","evaluate","risk.evaluate",verdict)
    if not verdict.get("ok"):
        return {"step":"risk","approved":False,"verdict":verdict}

    broker_token = await _mint("place:simulate")
    async with httpx.AsyncClient(timeout=10) as client:
        br = await client.post(f"{BROKER_URL}/orders",
                               headers={"Authorization": f"Bearer {broker_token}"},
                               json=order)
    if br.status_code != 200:
        raise HTTPException(br.status_code, detail=br.text)
    receipt = br.json()
    _log("broker-agent","order","place:simulate",receipt)
    return {"step":"broker","approved":True,"verdict":verdict,"receipt":receipt}

# ---------- LIVE TRADE (REQUIRES CONSENT) ----------

def _require_consent(consent_id: str, user_id: str, scope: str = "place:live"):
    conn = db(); cur = conn.cursor()
    cur.execute("SELECT id,user_id,scope FROM consents WHERE id = ?", (consent_id,))
    row = cur.fetchone(); conn.close()
    if not row:
        raise HTTPException(400, detail="invalid consent_id")
    if row[1] != user_id:
        raise HTTPException(403, detail="consent_id does not belong to this user")
    if row[2] != scope:
        raise HTTPException(403, detail="consent scope mismatch")
    return True

@app.post("/trade/live")
async def trade_live(order: dict):
    user_id, consent_id = order.get("user_id"), order.get("consent_id")
    if not user_id or not consent_id:
        raise HTTPException(400, detail="user_id and consent_id are required")
    _require_consent(consent_id, user_id, "place:live")

    risk_token = await _mint("risk.evaluate")
    async with httpx.AsyncClient(timeout=10) as client:
        rr = await client.post(f"{RISK_URL}/risk/evaluate",
                               headers={"Authorization": f"Bearer {risk_token}"},
                               json=order)
    if rr.status_code != 200:
        raise HTTPException(rr.status_code, detail=rr.text)
    verdict = rr.json()
    _log("risk-agent","evaluate","risk.evaluate",verdict)
    if not verdict.get("ok"):
        return {"step":"risk","approved":False,"verdict":verdict}

    broker_token = await _mint("place:live")
    async with httpx.AsyncClient(timeout=10) as client:
        br = await client.post(f"{BROKER_URL}/orders",
                               headers={"Authorization": f"Bearer {broker_token}"},
                               json=order)
    if br.status_code != 200:
        raise HTTPException(br.status_code, detail=br.text)
    receipt = br.json()
    _log("broker-agent","order","place:live",receipt)
    return {"step":"broker","approved":True,"verdict":verdict,"receipt":receipt}

# ---------- AUDIT LOGS ----------
@app.get("/logs/recent")
def logs_recent(limit: int = 10):
    if limit <= 0 or limit > 200:
        raise HTTPException(400, detail="limit must be between 1 and 200")
    conn = db(); cur = conn.cursor()
    cur.execute(
        "SELECT id,agent,action,scope,signed_result,created_at "
        "FROM audit_logs ORDER BY created_at DESC LIMIT ?",
        (limit,),
    )
    rows = cur.fetchall(); conn.close()
    return [
        {
            "id": r[0], "agent": r[1], "action": r[2], "scope": r[3],
            "signed_result": json.loads(r[4]), "created_at": r[5],
        }
        for r in rows
    ]

@app.get("/logs/stream")
async def logs_stream(poll_interval: float = 1.0):
    async def event_generator():
        conn = db(); cur = conn.cursor()
        cur.execute("SELECT IFNULL(MAX(id), 0) FROM audit_logs")
        last_id = cur.fetchone()[0] or 0
        conn.close()
        while True:
            await asyncio.sleep(poll_interval)
            conn = db(); cur = conn.cursor()
            cur.execute(
                "SELECT id,agent,action,scope,signed_result,created_at "
                "FROM audit_logs WHERE id > ? ORDER BY id ASC",
                (last_id,),
            )
            rows = cur.fetchall(); conn.close()
            for r in rows:
                last_id = r[0]
                payload = {
                    "id": r[0], "agent": r[1], "action": r[2], "scope": r[3],
                    "signed_result": json.loads(r[4]), "created_at": r[5],
                }
                yield f"event: audit\ndata: {json.dumps(payload)}\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")

# ---------- STRATEGY STUBS ----------

@app.post("/strategy/ideas")
def strategy_ideas(body: dict | None = None):
    from .strategy import gather_ideas
    symbols = (body or {}).get("symbols")
    return {"ideas": gather_ideas(symbols)}

@app.post("/strategy/decide")
def strategy_decide(body: dict):
    from .strategy import decide_order
    symbol = body.get("symbol", "AAPL")
    side   = body.get("side")
    return {"intent": decide_order(symbol, side)}

@app.post("/strategy/execute")
async def strategy_execute(body: dict):
    from .strategy import decide_order
    symbol = body.get("symbol", "AAPL")
    side   = body.get("side")
    intent = decide_order(symbol, side)
    if "qty" in body: intent["qty"] = int(body["qty"])
    if body.get("live"):
        intent["user_id"]   = body.get("user_id")
        intent["consent_id"]= body.get("consent_id")
        return await trade_live(intent)
    else:
        return await trade_sim(intent)