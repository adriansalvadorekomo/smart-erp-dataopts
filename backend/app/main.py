"""Smart-ERP backend — FastAPI over the PostgreSQL OLTP core.

Phase 4 increment: orders core (create/read/lifecycle) + health.
Contract: docs/business-model.md §3–§4.
"""
from __future__ import annotations

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from backend.app.api.orders import router as orders_router
from backend.app.core.db import get_session_factory

app = FastAPI(title="Smart-ERP", version="0.1.0")

# Separate-deploys path (Vite dev uses the /api proxy instead, same-origin).
_frontend_origins = [
    o.strip()
    for o in os.environ.get("FRONTEND_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_frontend_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(orders_router)


@app.get("/health")
def health():
    """Liveness + DB reachability (no auth — safe for orchestrators)."""
    try:
        with get_session_factory()() as session:
            session.execute(text("SELECT 1"))
        db = "up"
    except Exception:
        db = "down"
    return {"status": "ok" if db == "up" else "degraded", "db": db}
