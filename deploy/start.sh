#!/usr/bin/env sh
set -eu

until alembic upgrade head; do
  echo "Waiting for database to become ready..."
  sleep 3
done

exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
