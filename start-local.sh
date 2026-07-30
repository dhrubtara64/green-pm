#!/bin/bash
# Local dev startup without Docker. Requires:
#   - Python 3.11+
#   - PostgreSQL running locally
#   - Node 18+
#
# Usage: ./start-local.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DB_URL="${DATABASE_URL:-postgresql://localhost/greenpm}"

echo "=== Green PM — Local Dev Startup ==="
echo ""

# Backend setup
echo "[1/4] Setting up Python environment..."
cd "$SCRIPT_DIR/backend"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt
echo "      Dependencies installed."

# Create database
echo "[2/4] Creating database..."
createdb greenpm 2>/dev/null || echo "      (database already exists)"

# Seed data
echo "[3/4] Seeding demo project..."
DATABASE_URL="$DB_URL" ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}" python3 seed/generate_seed_data.py

# Start backend in background
echo "[4/4] Starting backend on http://localhost:8000 ..."
DATABASE_URL="$DB_URL" ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}" \
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Frontend setup
echo ""
echo "[5/5] Starting frontend on http://localhost:3000 ..."
cd "$SCRIPT_DIR/frontend"
if [ ! -d "node_modules" ]; then
  npm install --silent
fi
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev &
FRONTEND_PID=$!

echo ""
echo "=== Green PM is running ==="
echo "  Dashboard:   http://localhost:3000"
echo "  API docs:    http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
