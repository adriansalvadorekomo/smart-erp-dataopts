# Production image for the FastAPI OLTP backend.
# Context is the REPO ROOT (Alembic replays database/migrations/*.sql at boot).
# Build:  docker build -f backend/Dockerfile -t smart-erp-backend .
# Run (compose wires env + deps): see infra/docker-compose.yml.
# Entrypoint migrates (Alembic) BEFORE serving, so deploys never run
# against a stale schema. Rollback = redeploy the previous tag.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/usr/local

WORKDIR /app

RUN pip install --no-cache-dir uv==0.11.16

COPY pyproject.toml uv.lock README.md ./
# UV_PROJECT_ENVIRONMENT puts the project env on the system prefix, so console
# scripts land in /usr/local/bin. (Plain `uv sync` hides everything in
# /app/.venv, off PATH — the container then dies with "alembic: not found".)
RUN uv sync --frozen --no-dev --no-editable && rm -rf /root/.cache/uv

# Fail the BUILD (not the deploy) if the runtime CLIs are missing.
RUN alembic --version && uvicorn --version

COPY backend/ ./backend/
COPY database/ ./database/

EXPOSE 8000

ENTRYPOINT ["./backend/docker-entrypoint.sh"]
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
