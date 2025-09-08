# Trusted Trading Crew

Awesome—let’s lock this down with a single, copy-pasteable README that your friend can follow to run:
	•	backend only
	•	frontend only
	•	full stack (both)

This works on macOS/Linux shells (zsh/bash). It uses the exact ports and commands you’ve been using.

⸻

Trusted Trading Crew — Mono-Repo (Backend + Frontend)

A small trading system with:
	•	Orchestrator (API gateway, port 7000)
	•	Market Simulator (7001)
	•	Risk Agent (7002)
	•	Broker Agent (7003)
	•	Strategy Trio: Analyst (7010), Researcher (7011), Manager (7012)
	•	Frontend (Vite React app in frontend/)

⚠️ This repo contains working environment files/keys so teammates can run it quickly. If you fork or open-source, rotate/remove secrets.

⸻

Prerequisites
	•	Python 3.11+ (3.13 works great)

python3 --version


	•	pip and venv available
	•	Node.js 18 or 20+ and npm

node -v
npm -v


	•	curl and jq (for quick API checks)

jq --version



If you use pyenv and see a warning about 3.10 from .python-version, either install 3.10 with pyenv or ignore it and always run from .venv as shown below.

⸻

Ports used
	•	Backend API gateway (orchestrator): 7000
	•	Market simulator: 7001
	•	Risk agent: 7002
	•	Broker agent: 7003
	•	Strategy services: 7010, 7011, 7012
	•	Frontend (Vite dev): 5173 (may auto-pick 5174/5175 if busy)
	•	Frontend preview (built): 4173

⸻

Repo layout

trusted-trading-crew/
├── services/                # all backend services
│   ├── orchestrator/        # API gateway (reads .env here)
│   ├── sim/                 # market simulator
│   ├── risk/                # risk microservice
│   ├── broker/              # broker microservice
│   ├── analyst/             # strategy microservices
│   ├── researcher/
│   └── manager/
├── frontend/                # Vite + React app
├── secrets/                 # signing keys (kept for teammates)
├── .logs/                   # runtime logs (created at run-time)
├── requirements.txt         # backend deps
├── pyproject.toml           # (optional) python project metadata
├── start_all.sh / stop_all.sh (optional helper scripts)
└── README.md


⸻

0) One-time backend setup (first clone)

cd ~/trusted-trading-crew

# Create & activate venv
python3 -m venv .venv
source .venv/bin/activate

# Install backend deps
pip install -r requirements.txt

# (Optional) make logs dir
mkdir -p .logs

Orchestrator env

services/orchestrator/.env is already present. It should include:
	•	Client IDs/Secrets for token mint
	•	Token URL (Descope)
	•	URLs to risk/broker/strategy services (we’ll start these below)

You can confirm it’s wired later with:
curl -s http://127.0.0.1:7000/debug/env

⸻

1) Run backend only (from a fresh terminal)

You can run each service in its own terminal, or copy-paste this whole block in one terminal (background mode). It matches what we validated.

cd ~/trusted-trading-crew
source .venv/bin/activate
export PYTHONPATH="$PWD"

# Clean any leftovers (safe if none)
pkill -f "uvicorn.*7000" 2>/dev/null || true
pkill -f "uvicorn.*7001" 2>/dev/null || true
pkill -f "uvicorn.*7002" 2>/dev/null || true
pkill -f "uvicorn.*7003" 2>/dev/null || true
pkill -f "uvicorn.*7010" 2>/dev/null || true
pkill -f "uvicorn.*7011" 2>/dev/null || true
pkill -f "uvicorn.*7012" 2>/dev/null || true

# Start Market Simulator (7001)
.venv/bin/uvicorn services.sim.main:app --port 7001 > .logs/sim.log 2>&1 &

# Start Risk (7002) with OIDC/JWKS
DESCOPE_ISSUER="https://api.descope.com/v1/apps/P32Nz2TQgggJsGxTGth151tHEvkB" \
DESCOPE_JWKS_URL="https://api.descope.com/P32Nz2TQgggJsGxTGth151tHEvkB/.well-known/jwks.json" \
REQUIRED_SCOPE="risk.evaluate" \
RISK_SIGNING_PRIV="./secrets/risk_priv.pem" \
RISK_SIGNING_PUB="./secrets/risk_pub.pem" \
.venv/bin/uvicorn services.risk.main:app --port 7002 > .logs/risk.log 2>&1 &

# Start Broker (7003) with OIDC/JWKS
DESCOPE_ISSUER="https://api.descope.com/v1/apps/P32Nz2TQgggJsGxTGth151tHEvkB" \
DESCOPE_JWKS_URL="https://api.descope.com/P32Nz2TQgggJsGxTGth151tHEvkB/.well-known/jwks.json" \
ALLOWED_SCOPES="place:simulate place:live" \
REQUIRE_CONSENT_FOR="place:live" \
SIM_BASE_URL="http://127.0.0.1:7001" \
BROKER_SIGNING_PRIV="./secrets/broker_priv.pem" \
BROKER_SIGNING_PUB="./secrets/broker_pub.pem" \
.venv/bin/uvicorn services.broker.main:app --port 7003 > .logs/broker.log 2>&1 &

# Start Strategy trio (7010/7011/7012)
.venv/bin/uvicorn services.analyst.main:app    --port 7010 > .logs/analyst.log 2>&1 &
.venv/bin/uvicorn services.researcher.main:app --port 7011 > .logs/researcher.log 2>&1 &
.venv/bin/uvicorn services.manager.main:app    --port 7012 > .logs/manager.log 2>&1 &

# Start Orchestrator last (7000) – reads services/orchestrator/.env
.venv/bin/uvicorn services.orchestrator.main:app --port 7000 > .logs/orchestrator.log 2>&1 &

# Health checks
sleep 1
for p in 7000 7001 7002 7003 7010 7011 7012; do
  echo -n "Health $p: "
  curl -s "http://127.0.0.1:$p/health" || true
  echo
done

Quick API sanity checks

# Mint tokens (should show token_prefix + length)
curl -s "http://127.0.0.1:7000/debug/mint?scope=risk.evaluate"  -H 'Accept: application/json' | jq .
curl -s "http://127.0.0.1:7000/debug/mint?scope=place:simulate" -H 'Accept: application/json' | jq .
curl -s "http://127.0.0.1:7000/debug/mint?scope=place:live"     -H 'Accept: application/json' | jq .

# Sim trade
curl -s -H "Content-Type: application/json" \
  -X POST http://127.0.0.1:7000/trade/simulate \
  -d '{"symbol":"AAPL","side":"BUY","qty":1,"type":"market"}' | jq .

# Live trade (requires consent)
CID=$(curl -s -H "Content-Type: application/json" \
  -X POST http://127.0.0.1:7000/consent/grant \
  -d '{"user_id":"demo-user","scope":"place:live"}' | jq -r .consent_id)

curl -s -H "Content-Type: application/json" \
  -X POST http://127.0.0.1:7000/trade/live \
  -d "{\"symbol\":\"AAPL\",\"side\":\"BUY\",\"qty\":1,\"type\":\"market\",\"user_id\":\"demo-user\",\"consent_id\":\"$CID\"}" \
  | jq .

# Strategy chat (needs 7010/7011/7012 running)
curl -s -H "Content-Type: application/json" \
  -X POST http://127.0.0.1:7000/strategy/chat \
  -d '{"message":"Compare AAPL vs NVDA and act on AAPL","symbol":"AAPL"}' | jq .

# Inspect recent logs
curl -s "http://127.0.0.1:7000/logs/recent?limit=10" | jq .

✅ If you ever see JWKS fetch failed: ... NoneType, it means Risk/Broker were started without DESCOPE_ISSUER and DESCOPE_JWKS_URL. Restart them with the envs above.

⸻

2) Run frontend only

cd ~/trusted-trading-crew/frontend

# Backend API base (adjust if needed)
echo 'VITE_API_BASE=http://127.0.0.1:7000' > .env.local

# Install deps
npm install

# Dev server (http://localhost:5173)
npm run dev

# OR build & preview (http://localhost:4173)
npm run build
npm run preview

Note: an OPTIONS preflight to /trade/simulate with curl will show 405 (not implemented). That’s fine; the actual POST works and the app functions normally in the browser.

⸻

3) Run both (full stack)
	•	Start backend first (Section 1)
	•	Then start frontend (Section 2)

That’s it. Open the app at http://localhost:5173 (or whatever Vite prints).

⸻

Fresh restart checklist (quick)

cd ~/trusted-trading-crew
source .venv/bin/activate

# Kill old uvicorns
for p in 7000 7001 7002 7003 7010 7011 7012; do
  pkill -f "uvicorn.*:$p" 2>/dev/null || true
done

# Start all (same as Section 1)
# ... (paste the start commands from Section 1) ...

# Verify
for p in 7000 7001 7002 7003 7010 7011 7012; do
  echo -n "Health $p: "; curl -s "http://127.0.0.1:$p/health"; echo
done


⸻

Common errors & quick fixes
	•	JWKS fetch failed: Invalid type for url ... NoneType
Start Risk (7002) and Broker (7003) with DESCOPE_ISSUER and DESCOPE_JWKS_URL envs (exact commands in Section 1).
	•	Token mint failed ... invalid secret (for place:live)
Update ORCH_LIVE_CLIENT_ID/SECRET in services/orchestrator/.env to the correct live app credentials.
	•	address already in use on 7010/7011/7012
Kill ports and start again:

for p in 7010 7011 7012; do lsof -ti tcp:$p | xargs -r kill -9; done


	•	pyenv complains about 3.10
This repo includes .python-version. Either install 3.10 via pyenv, or ignore pyenv and always run from .venv.
	•	CORS preflight shows 405
That’s just curl hitting OPTIONS. The browser + POST works fine.
	•	Strategy chat 500
Ensure 7010/7011/7012 are up and that the orchestrator has the STRAT_ANALYST_URL/STRAT_RESEARCHER_URL/STRAT_MANAGER_URL pointing to them (already set).

⸻

Verifying signatures (optional)

# Save a live receipt and verify
curl -s -H "Content-Type: application/json" \
  -X POST http://127.0.0.1:7000/consent/grant \
  -d '{"user_id":"demo-user","scope":"place:live"}' | jq -r .consent_id > /tmp/cid.txt

CID=$(cat /tmp/cid.txt)

curl -s -H "Content-Type: application/json" \
  -X POST http://127.0.0.1:7000/trade/live \
  -d "{\"symbol\":\"AAPL\",\"side\":\"BUY\",\"qty\":1,\"type\":\"market\",\"user_id\":\"demo-user\",\"consent_id\":\"$CID\"}" \
  | jq .receipt > live_receipt.json

python3 verify_sig.py live_receipt.json secrets/broker_pub.pem
# expect: ✅ signature valid


⸻

Troubleshooting logs

tail -n 80 .logs/orchestrator.log
tail -n 80 .logs/risk.log
tail -n 80 .logs/broker.log
tail -n 80 .logs/analyst.log
tail -n 80 .logs/researcher.log
tail -n 80 .logs/manager.log
tail -n 80 .logs/sim.log


⸻

Frontend notes
	•	Update API base via frontend/.env.local

VITE_API_BASE=http://127.0.0.1:7000


	•	Dev build: npm run dev
	•	Production build: npm run build && npm run preview

⸻

Stop all services

pkill -f "uvicorn.*7000" 2>/dev/null || true
pkill -f "uvicorn.*7001" 2>/dev/null || true
pkill -f "uvicorn.*7002" 2>/dev/null || true
pkill -f "uvicorn.*7003" 2>/dev/null || true
pkill -f "uvicorn.*7010" 2>/dev/null || true
pkill -f "uvicorn.*7011" 2>/dev/null || true
pkill -f "uvicorn.*7012" 2>/dev/null || true


⸻
