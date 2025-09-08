#!/usr/bin/env bash
set -euo pipefail

echo "Node: $(node -v)"
echo "Checking VITE_API_BASE…"
grep -R "VITE_API_BASE" src/ .env* || true

echo "Testing API POST (simulate)…"
curl -s -i -H "Origin: http://localhost:5173" \
     -H "Content-Type: application/json" \
     -X POST http://127.0.0.1:7000/trade/simulate \
     -d '{"symbol":"AAPL","side":"BUY","qty":1,"type":"market"}' | sed -n '1,20p'

echo "Rebuilding…"
rm -rf dist
npm run build

echo "Previewing on http://localhost:4173 (Ctrl+C to stop)"
npm run preview
