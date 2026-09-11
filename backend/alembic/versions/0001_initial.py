"""Initial schema — replays database/migrations/001–005 verbatim.

Single source of truth is the SQL files: this revision executes them in order,
so `alembic upgrade head` and `database/apply.sh` always produce the same
schema. The dollar-quote-aware splitter below exists because 002 defines a
plpgsql function body containing semicolons.
"""
from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "database" / "migrations"
FILES = [
    "001_schemas.sql",
    "002_core_tables.sql",
    "003_raw_staging.sql",
    "004_final_price_tolerance.sql",
    "005_audit_log.sql",
]


def _split_statements(sql: str) -> list[str]:
    """Split on semicolons outside $$ dollar-quoted blocks and -- comments."""
    statements, buf, in_dollar = [], [], False
    for raw_line in sql.splitlines():
        line = raw_line if in_dollar else raw_line.split("--", 1)[0]
        if line.count("$$") % 2 == 1:
            in_dollar = not in_dollar
        buf.append(raw_line)
        if not in_dollar and line.rstrip().endswith(";"):
            stmt = "\n".join(buf).strip()
            if stmt.strip(";").strip():
                statements.append(stmt)
            buf = []
    tail = "\n".join(buf).strip()
    if tail.strip(";").strip():
        statements.append(tail)
    return statements


def upgrade() -> None:
    conn = op.get_bind()
    for name in FILES:
        sql = (MIGRATIONS_DIR / name).read_text(encoding="utf-8")
        for stmt in _split_statements(sql):
            # exec_driver_sql uses printf-style placeholders — our DDL has no
            # bound parameters, so literal % (e.g. in COMMENTs) must be doubled.
            conn.exec_driver_sql(stmt.replace("%", "%%"))


def downgrade() -> None:
    # Early scaffold uses full-refresh semantics — downgrade drops everything
    # this revision created (children before parents, FK-safe).
    conn = op.get_bind()
    conn.exec_driver_sql("DROP TABLE IF EXISTS public.audit_log CASCADE;")
    conn.exec_driver_sql("DROP TABLE IF EXISTS public.order_items CASCADE;")
    conn.exec_driver_sql("DROP TABLE IF EXISTS public.orders CASCADE;")
    conn.exec_driver_sql("DROP TABLE IF EXISTS public.inventory CASCADE;")
    conn.exec_driver_sql("DROP TABLE IF EXISTS public.products CASCADE;")
    conn.exec_driver_sql("DROP TABLE IF EXISTS public.sellers CASCADE;")
    conn.exec_driver_sql("DROP TABLE IF EXISTS public.customers CASCADE;")
    conn.exec_driver_sql("DROP TABLE IF EXISTS staging.purchases CASCADE;")
    conn.exec_driver_sql("DROP TABLE IF EXISTS raw.purchases CASCADE;")
