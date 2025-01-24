#!/bin/bash
set -e

PORT="${PORT:-8080}"
export PORT

echo "Starting server on port ${PORT}"
exec uvicorn main:app --host 0.0.0.0 --port "${PORT}" --log-level debug

