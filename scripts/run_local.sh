#!/usr/bin/env bash
# Start the local FastAPI + Streamlit stack (SQLite-backed).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

export MOCK_MODE="${MOCK_MODE:-true}"
export WAREHOUSE_API_BASE="${WAREHOUSE_API_BASE:-http://127.0.0.1:8765}"

echo "Starting FastAPI on :8765 (local SQLite)..."
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765 &
API_PID=$!
sleep 2
echo "Starting Streamlit on :8510..."
streamlit run dashboard/app.py --server.port 8510 --server.address 127.0.0.1 --server.headless true &
UI_PID=$!

cleanup() {
  kill "$API_PID" "$UI_PID" 2>/dev/null || true
}
trap cleanup EXIT

echo
echo "Local stack ready:"
echo "  API:       http://127.0.0.1:8765/health"
echo "  Dashboard: http://127.0.0.1:8510  (open Local Voice page)"
echo "  ADK voice: cd app && adk web --port 8035"
echo
wait
