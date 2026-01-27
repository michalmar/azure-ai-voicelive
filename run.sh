#!/bin/bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")" && pwd)
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

cleanup() {
	echo "\nStopping backend and frontend..."
	if [[ -n "${backend_pid:-}" ]]; then
		kill "${backend_pid}" 2>/dev/null || true
	fi
	if [[ -n "${frontend_pid:-}" ]]; then
		kill "${frontend_pid}" 2>/dev/null || true
	fi
}

trap cleanup EXIT INT TERM

start_backend() {
	cd "$BACKEND_DIR"
	if [[ -f ".venv/bin/activate" ]]; then
		# Activate the virtualenv created during setup.
		# shellcheck disable=SC1091
		source .venv/bin/activate
	fi
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
}

start_frontend() {
	cd "$FRONTEND_DIR"
	npm run dev
}

echo "Starting backend (uvicorn on :8000)..."
start_backend &
backend_pid=$!

echo "Starting frontend (npm run dev on :3000)..."
start_frontend &
frontend_pid=$!

wait "$backend_pid" "$frontend_pid"
