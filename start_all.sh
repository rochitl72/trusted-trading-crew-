#!/usr/bin/env bash
set -euo pipefail

REPO="$HOME/trusted-trading-crew"
VENV="$REPO/.venv"
LOGDIR="$REPO/.logs"
PIDDIR="$REPO/.pids"

mkdir -p "$LOGDIR" "$PIDDIR"

# ----- ENV (your real OpenAI key + model) -----
export OPENAI_API_KEY="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"
export OPENAI_MODEL="gpt-4o-mini"

# strategy URLs for orchestrator
grep -q '^STRAT_ANALYST_URL='    "$REPO/services/orchestrator/.env" || echo 'STRAT_ANALYST_URL=http://127.0.0.1:7010' >> "$REPO/services/orchestrator/.env"
grep -q '^STRAT_RESEARCHER_URL=' "$REPO/services/orchestrator/.env" || echo 'STRAT_RESEARCHER_URL=http://127.0.0.1:7011' >> "$REPO/services/orchestrator/.env"
grep -q '^STRAT_MANAGER_URL='    "$REPO/services/orchestrator/.env" || echo 'STRAT_MANAGER_URL=http://127.0.0.1:7012' >> "$REPO/services/orchestrator/.env"

kill_port () { lsof -ti tcp:"$1" | xargs -I{} kill -9 {} 2>/dev/null || true; }
start () {
  local name="$1" module="$2" port="$3"
  kill_port "$port"
  echo "▶️  $name @ $port"
  nohup "$VENV/bin/uvicorn" "$module" --port "$port" --log-level info > "$LOGDIR/$name.log" 2>&1 &
  echo $! > "$PIDDIR/$name.pid"
}
wait_health () {
  local url="$1" label="$2"
  for i in {1..40}; do
    if curl -fsS "$url" >/dev/null; then
      echo "✅ $label"
      return 0
    fi
    sleep 0.3
  done
  echo "❌ $label did not come up: $url"
  exit 1
}

# activate venv
source "$VENV/bin/activate"

# core
start "sim"           "services.sim.main:app"            7001
start "risk"          "services.risk.main:app"           7002
start "broker"        "services.broker.main:app"         7003

# agents (OpenAI-powered)
start "analyst"       "services.analyst.main:app"        7010
start "researcher"    "services.researcher.main:app"     7011
start "manager"       "services.manager.main:app"        7012

# orchestrator
start "orchestrator"  "services.orchestrator.main:app"   7000

# health checks
wait_health "http://127.0.0.1:7001/health"   "market-sim"
wait_health "http://127.0.0.1:7002/health"   "risk"
wait_health "http://127.0.0.1:7003/health"   "broker"
wait_health "http://127.0.0.1:7010/health"   "analyst"
wait_health "http://127.0.0.1:7011/health"   "researcher"
wait_health "http://127.0.0.1:7012/health"   "manager"
wait_health "http://127.0.0.1:7000/health"   "orchestrator"

echo "🚀 All services up. Logs in $LOGDIR"
