import os, json, base64, sqlite3
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.security import HTTPBearer
import httpx, jwt
from datetime import datetime
from typing import List
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

app = FastAPI(title="Broker Agent", version="0.1")

DESCOPE_ISSUER     = os.getenv("DESCOPE_ISSUER")
DESCOPE_JWKS_URL   = os.getenv("DESCOPE_JWKS_URL")
ALLOWED_SCOPES     = (os.getenv("ALLOWED_SCOPES","place:simulate place:live").split())
REQUIRE_CONSENT_FOR= os.getenv("REQUIRE_CONSENT_FOR","place:live")
SIM_BASE_URL       = os.getenv("SIM_BASE_URL","http://localhost:7001")
DB_PATH            = os.getenv("DATABASE_URL", "sqlite:///./data/trusted_trading.sqlite3").replace("sqlite:///", "")
BROKER_PRIV        = os.getenv("BROKER_SIGNING_PRIV","./secrets/broker_priv.pem")

security = HTTPBearer()

# load signing key
with open(BROKER_PRIV, "rb") as f:
    private_key = serialization.load_pem_private_key(f.read(), password=None)
assert isinstance(private_key, Ed25519PrivateKey)

@app.get("/health")
def health():
    return {
        "status":"ok",
        "allowed_scopes": ALLOWED_SCOPES,
        "require_consent_for": REQUIRE_CONSENT_FOR
    }

def _jwks_keys():
    try:
        r = httpx.get(DESCOPE_JWKS_URL, timeout=10)
        r.raise_for_status()
        data = r.json()
        if "keys" not in data or not data["keys"]:
            raise RuntimeError("empty JWKS")
        return data["keys"]
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"JWKS fetch failed: {e}")

def verify_jwt(token: str) -> dict:
    keys = _jwks_keys()
    try:
        header = jwt.get_unverified_header(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"bad JWT header: {e}")
    kid = header.get("kid")
    k = next((kk for kk in keys if kk.get("kid")==kid), None)
    if not k: raise HTTPException(status_code=401, detail="kid not in JWKS")

    pub = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(k))
    try:
        payload = jwt.decode(token, pub, algorithms=["RS256"], issuer=DESCOPE_ISSUER, options={"verify_aud": False})
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"JWT decode failed: {e}")

    scopes: List[str] = payload.get("permissions") or payload.get("scope","").split()
    if not any(s in scopes for s in ALLOWED_SCOPES):
        raise HTTPException(status_code=403, detail=f"Missing one of allowed scopes {ALLOWED_SCOPES}")

    payload["_scopes"] = scopes
    return payload

def sign_receipt(d: dict) -> str:
    msg = json.dumps(d, sort_keys=True).encode()
    return base64.b64encode(private_key.sign(msg)).decode()

def log_audit(agent: str, action: str, scope: str, payload: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS audit_logs(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      agent TEXT, action TEXT, scope TEXT, signed_result TEXT,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    cur.execute("INSERT INTO audit_logs(agent,action,scope,signed_result,created_at) VALUES(?,?,?,?,?)",
                (agent, action, scope, payload, datetime.utcnow().isoformat()))
    conn.commit(); conn.close()

@app.post("/orders")
async def place_order(req: Request, cred=Depends(security)):
    token = cred.credentials
    payload = verify_jwt(token)
    body = await req.json()  # expects {symbol, side, qty, type}

    # pick the scope actually used
    used_scope = "place:simulate" if "place:simulate" in payload["_scopes"] else \
                 ("place:live" if "place:live" in payload["_scopes"] else None)
    if not used_scope:
        raise HTTPException(status_code=403, detail="No usable scope in token")

    # if live, require consent_id in body
    consent_required = (REQUIRE_CONSENT_FOR and used_scope == REQUIRE_CONSENT_FOR)
    consent_id = body.get("consent_id")
    if consent_required and not consent_id:
        raise HTTPException(status_code=400, detail="consent_id required for live orders")

    # forward to simulator (always for this demo; in real prod, live would hit broker)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            sim_resp = await client.post(f"{SIM_BASE_URL}/orders", json={
                "symbol": body.get("symbol"),
                "side": body.get("side"),
                "qty": body.get("qty"),
                "type": body.get("type","market")
            })
            sim_resp.raise_for_status()
            fill = sim_resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"sim error: {e}")

    receipt = {
        "mode": "live" if used_scope=="place:live" else "simulate",
        "symbol": fill.get("symbol"),
        "side": fill.get("side"),
        "qty": fill.get("qty"),
        "avg_price": fill.get("avg_price"),
        "fees": fill.get("fees"),
        "filled_at": fill.get("filled_at"),
        "consent_id": consent_id
    }
    signature = sign_receipt(receipt)
    receipt["signature"] = signature

    log_audit("broker-agent", "order", used_scope, json.dumps(receipt))
    return receipt
