"""Application settings — env-driven, same convention as database/apply.sh.

No secrets in code: connection values come from the standard libpq
environment (PGHOST/PGPORT/PGUSER/PGPASSWORD/PGDATABASE).
"""
from __future__ import annotations

import os
from functools import lru_cache


class Settings:
    pg_host: str = os.environ.get("PGHOST", "uptown")
    pg_port: int = int(os.environ.get("PGPORT", "5432"))
    pg_user: str = os.environ.get("PGUSER", "magrey")
    pg_password: str = os.environ.get("PGPASSWORD", "")
    pg_database: str = os.environ.get("PGDATABASE", "smart")

    @property
    def dsn(self) -> str:
        return build_dsn(
            self.pg_host, self.pg_port, self.pg_user, self.pg_password, self.pg_database
        )


def build_dsn(host: str, port: int, user: str, password: str, database: str) -> str:
    """SQLAlchemy DSN for psycopg — socket dirs go in ?host= (a '/' in the
    authority section would misparse)."""
    if host.startswith("/"):
        return (
            f"postgresql+psycopg://{user}:{password}@/{database}"
            f"?host={host}&port={port}"
        )
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{database}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
