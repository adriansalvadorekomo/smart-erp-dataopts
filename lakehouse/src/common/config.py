"""Shared configuration for the Smart-ERP lakehouse.

All environment-specific values (workspace URL, catalog names, credentials)
come from environment variables — never hardcoded. See docs/lakehouse.md.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class LakehouseConfig:
    """Resolved lakehouse configuration.

    Unity Catalog three-level namespace: catalog.schema.table.
    Free Edition cannot create catalogs via API, so the default catalog is the
    workspace's built-in ``workspace`` catalog (schemas managed by Terraform);
    a dedicated catalog (e.g. ``smart_erp``) is the production pattern, selected
    via LAKEHOUSE_CATALOG. Community Edition sets LAKEHOUSE_USE_UC=false.
    """

    catalog: str = field(default_factory=lambda: os.environ.get("LAKEHOUSE_CATALOG", "workspace"))
    bronze_schema: str = "bronze"
    silver_schema: str = "silver"
    gold_schema: str = "gold"
    # Local dev equivalent of the Unity Catalog volume (Delta files live here).
    # Production equivalent: a UC external volume / managed storage.
    # Community Edition: DBFS / workspace files instead (see community guide).
    delta_root: str = field(default_factory=lambda: os.environ.get("LAKEHOUSE_DELTA_ROOT", "lakehouse/delta"))
    # OLTP connection ( Bronze source). Same DSN conventions as scripts/seed/.
    pg_dsn: str = field(
        default_factory=lambda: (
            f"host={os.environ.get('PGHOST', 'uptown')} "
            f"port={os.environ.get('PGPORT', '5432')} "
            f"user={os.environ.get('PGUSER', 'magrey')} "
            f"dbname={os.environ.get('PGDATABASE', 'smart')} "
            f"password={os.environ.get('PGPASSWORD', '')}"
        )
    )
    databricks_host: str = field(default_factory=lambda: os.environ.get("DATABRICKS_HOST", ""))
    # NOTE: token is read at runtime only; never logged, never committed.
    # Unity Catalog is NOT available on Databricks Community Edition (Hive
    # Metastore only). Set LAKEHOUSE_USE_UC=false there and table() degrades
    # to the two-level hive name (schema.table). See
    # docs/databricks-community-edition.md.
    use_uc: bool = field(
        default_factory=lambda: os.environ.get("LAKEHOUSE_USE_UC", "true").lower() not in ("0", "false", "no")
    )

    def table(self, layer: str, name: str) -> str:
        """Fully-qualified table name.

        Unity Catalog mode: ``workspace.silver.orders`` (Free Edition default).
        Community Edition (Hive Metastore): ``silver.orders``.
        """
        schemas = {"bronze": self.bronze_schema, "silver": self.silver_schema, "gold": self.gold_schema}
        if layer not in schemas:
            raise ValueError(f"unknown layer {layer!r}; expected one of {sorted(schemas)}")
        if self.use_uc:
            return f"{self.catalog}.{schemas[layer]}.{name}"
        return f"{schemas[layer]}.{name}"


# Layer → table inventory. Single place where the medallion surface is declared.
BRONZE_TABLES: tuple[str, ...] = ("raw_purchases",)

SILVER_TABLES: tuple[str, ...] = (
    "customers",
    "sellers",
    "products",
    "inventory",
    "orders",
    "order_items",
)

GOLD_TABLES: tuple[str, ...] = (
    "fact_sales",
    "dim_customer",
    "dim_product",
    "dim_date",
    "sales_daily",
    "customer_360",
    "inventory_kpis",
)
