#!/bin/sh
# Deploy gate: migrate first, serve second. If migrations fail the container
# exits non-zero and the orchestrator keeps the previous healthy revision.
set -e

echo "→ alembic upgrade head"
alembic -c backend/alembic.ini upgrade head

echo "→ exec: $*"
exec "$@"
