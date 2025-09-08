#!/usr/bin/env bash
set -euo pipefail
PIDDIR="$HOME/trusted-trading-crew/.pids"

if ls "$PIDDIR"/*.pid >/dev/null 2>&1; then
  for f in "$PIDDIR"/*.pid; do
    pid=$(cat "$f" 2>/dev/null || true)
    name=$(basename "$f" .pid)
    if [[ -n "${pid:-}" ]]; then
      echo "⛔ stopping $name (pid $pid)"
      kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$f"
  done
fi

for p in 7000 7001 7002 7003 7010 7011 7012; do
  lsof -ti tcp:$p | xargs -I{} kill -9 {} 2>/dev/null || true
done

echo "✅ all stopped"
