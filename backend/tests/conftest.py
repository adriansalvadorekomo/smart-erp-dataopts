"""pytest fixtures — throwaway Postgres (PGDATABASE_TEST, default smart_test).

Each run: create DB if missing → alembic upgrade head → seed minimal
catalog fixtures. Tests truncate only the tables they mutate.
"""
from __future__ import annotations

import datetime
import os
import subprocess

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

TEST_DB = os.environ.get("PGDATABASE_TEST", "smart_test")


def _pg_env(dbname: str) -> dict:
    env = dict(os.environ)
    env["PGDATABASE"] = dbname
    return env


def _dsn(dbname: str) -> str:
    from backend.app.core.config import build_dsn

    return build_dsn(
        os.environ.get("PGHOST", "uptown"),
        int(os.environ.get("PGPORT", "5432")),
        os.environ.get("PGUSER", "magrey"),
        os.environ.get("PGPASSWORD", ""),
        dbname,
    )


@pytest.fixture(scope="session")
def engine():
    base = _dsn("postgres")
    admin = create_engine(base, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :db"), {"db": TEST_DB}
        ).first()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{TEST_DB}"'))
    admin.dispose()

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    subprocess.run(
        ["alembic", "-c", "alembic.ini", "upgrade", "head"],
        cwd=os.path.join(repo_root, "backend"),
        env=_pg_env(TEST_DB),
        check=True,
        capture_output=True,
        text=True,
    )
    eng = create_engine(_dsn(TEST_DB))
    yield eng
    eng.dispose()


@pytest.fixture()
def session(engine):
    Session = sessionmaker(bind=engine)
    s = Session()
    # Minimal catalog fixtures (upsert — idempotent across tests).
    s.execute(
        text(
            "INSERT INTO public.customers (customer_id, home_city, first_purchase_date)"
            " VALUES ('U_TEST', 'Delhi', '2024-03-31') ON CONFLICT DO NOTHING"
        )
    )
    s.execute(
        text(
            "INSERT INTO public.sellers (seller_id, current_rating)"
            " VALUES ('S_TEST', 4.5) ON CONFLICT DO NOTHING"
        )
    )
    s.execute(
        text(
            "INSERT INTO public.products"
            " (product_id, category, subcategory, brand, current_price, product_rating, review_count)"
            " VALUES ('P_TEST', 'Electronics', 'Mobile', 'TestBrand', 1000.00, 4.0, 10)"
            " ON CONFLICT DO NOTHING"
        )
    )
    s.execute(
        text(
            "INSERT INTO public.inventory (product_id, snapshot_date, stock)"
            " VALUES ('P_TEST', '2024-03-31', 100)"
            " ON CONFLICT (product_id, snapshot_date) DO UPDATE SET stock = 100"
        )
    )
    s.commit()
    yield s
    # Reset mutated tables (keep catalog fixtures).
    for table in ("public.order_items", "public.orders", "public.audit_log"):
        s.execute(text(f"DELETE FROM {table};"))
    s.execute(
        text(
            "UPDATE public.inventory SET stock = 100"
            " WHERE product_id = 'P_TEST' AND snapshot_date = '2024-03-31'"
        )
    )
    s.execute(
        text(
            "DELETE FROM public.inventory WHERE product_id = 'P_TEST'"
            " AND snapshot_date <> '2024-03-31'"
        )
    )
    s.commit()
    s.close()


@pytest.fixture()
def client(session):
    from fastapi.testclient import TestClient

    from backend.app.core.db import get_db
    from backend.app.main import app

    def override():
        yield session

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def today() -> str:
    return datetime.date.today().isoformat()
