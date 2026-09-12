"""Batch revenue forecasts table (replays 006_revenue_forecasts.sql).

Separate revision (not folded into 0001): databases already at 0001 must
migrate forward — history is append-only. Single source of truth stays the
SQL file (see 0001_initial for the splitter rationale).
"""
from __future__ import annotations

import importlib
from pathlib import Path

from alembic import op

revision = "0002_revenue_forecasts"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "database" / "migrations"


def upgrade() -> None:
    v1 = importlib.import_module("backend.alembic.versions.0001_initial")
    conn = op.get_bind()
    sql = (MIGRATIONS_DIR / "006_revenue_forecasts.sql").read_text(encoding="utf-8")
    for stmt in v1._split_statements(sql):
        conn.exec_driver_sql(stmt.replace("%", "%%"))


def downgrade() -> None:
    op.get_bind().exec_driver_sql("DROP TABLE IF EXISTS public.revenue_forecasts CASCADE;")
