import os, json, base64, sqlite3
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.security import HTTPBearer
import jwt, httpx
from datetime import datetime
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

app = FastAPI(title="Risk Agent", version="0.3")

DESCOPE_ISSUER   = os.getenv("DESCOPE_ISSUER")
DESCOPE_JWKS_URL = os.getenv("DESCOPE_JWKS_URL")
REQUIRED_SCOPE   = os.getenv("REQUIRED_SCOPE", "risk.evaluate")
RISK_SIGNING_PRIV= os.getenv("RISK_SIGNING_PRIV", "./secrets/risk_priv.pem")
DB_PATH          = os.getenv("DATABASE_URL", "sqlite:///./data/trusted_trading.sqlite3").replace("sqlite:///", "")

security = HTTPBearer()

# Load Ed25519 signing key from PEM
with open(RISK_SIGNING_PRIV, "rb") as f:
    private_key = serialization.load_pem_private_key(f.read(), password=None)
assert isinstance(private_key, Ed25519PrivateKey)

@app.get("/health")
def health():
    return {"status": "ok", "required_scope": REQUIRED_SCOPE}

def _fetch_jwks():
    try:
        r = httpx.get(DESCOPE_JWKS_URL, timeout=10)
        r.raise_for_status()
        j = r.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"JWKS fetch failed: {e}")
    if "keys" not in j or not j["keys"]:
        raise HTTPException(status_code=502, detail="JWKS has no keys")
    return j["keys"]

def verify_jwt(token: str):
    jwks = _fetch_jwks()
    try:
        header = jwt.get_unverified_header(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Bad JWT header: {e}")

    kid = header.get("kid")
    key = next((k for k in jwks if k.get("kid") == kid), None)
    if not key:
        raise HTTPException(status_code=401, detail="kid not found in JWKS")

    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
    try:
        # IMPORTANT: disable audience verification explicitly
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=DESCOPE_ISSUER,
            options={"verify_aud": False},
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"JWT decode failed: {e}")

    scopes = payload.get("permissions") or payload.get("scope", "").split()
    if REQUIRED_SCOPE not in scopes:
        raise HTTPException(status_code=403, detail=f"Missing scope {REQUIRED_SCOPE}")
    return payload

def sign_verdict(v: dict) -> str:
    msg = json.dumps(v, sort_keys=True).encode()
    return base64.b64encode(private_key.sign(msg)).decode()

def log_audit(agent: str, action: str, scope: str, signed_result: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS audit_logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent TEXT, action TEXT, scope TEXT, signed_result TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    cur.execute("INSERT INTO audit_logs(agent,action,scope,signed_result,created_at) VALUES(?,?,?,?,?)",
                (agent, action, scope, signed_result, datetime.utcnow().isoformat()))
    conn.commit(); conn.close()

@app.post("/risk/evaluate")
async def evaluate(request: Request, credentials=Depends(security)):
    token = credentials.credentials
    _ = verify_jwt(token)

    body = await request.json()
    symbol = body.get("symbol"); side = body.get("side"); qty = body.get("qty")

    ok, reason = True, "approved"
    if qty and qty > 1000:
        ok, reason = False, "position size too large"

    verdict = {
        "ok": ok, "reason": reason, "symbol": symbol, "side": side, "qty": qty,
        "evaluated_at": datetime.utcnow().isoformat()
    }
    verdict["signature"] = sign_verdict(verdict)
    log_audit("risk-agent", "evaluate", REQUIRED_SCOPE, json.dumps(verdict))
    return verdict
