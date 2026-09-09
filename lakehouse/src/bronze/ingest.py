"""Bronze layer — raw, byte-faithful landing zone.

Contract (see docs/lakehouse.md):
- One Delta table per source: ``bronze.raw_purchases`` mirrors the OLTP
  ``staging.purchases`` snapshot 1:1 (same grains, no business transforms).
- Every record carries ``_ingest_ts`` (UTC ingestion timestamp) and
  ``_source`` (``postgres|csv``) for replayability and audit.
- Bronze is append-only with a watermark (``purchase_date`` max); history is
  never mutated. Corrections arrive as new snapshots downstream.

Execution note: the PySpark bodies run on Databricks (JDBC read from
PostgreSQL → Delta write). The pure helpers in this module are
cluster-independent and unit-tested locally.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

BRONZE_TABLE = "raw_purchases"

#: Source columns carried into Bronze verbatim (staging.purchases grain).
BRONZE_COLUMNS: tuple[str, ...] = (
    "user_id",
    "product_id",
    "category",
    "subcategory",
    "brand",
    "price",
    "discount",
    "final_price",
    "rating",
    "review_count",
    "stock",
    "seller_id",
    "seller_rating",
    "purchase_date",
    "shipping_time_days",
    "location",
    "device",
    "payment_method",
    "delivery_status",
)

AUDIT_COLUMNS: tuple[str, ...] = ("_ingest_ts", "_source")


def with_audit_columns(record: dict[str, Any], source: str, ingest_ts: str | None = None) -> dict[str, Any]:
    """Return a copy of *record* stamped with Bronze audit columns.

    Pure function — the same stamping logic the Spark job applies per row,
    testable without a cluster.
    """
    stamped = dict(record)
    stamped["_ingest_ts"] = ingest_ts or datetime.now(timezone.utc).isoformat(timespec="seconds")
    stamped["_source"] = source
    return stamped


def bronze_schema_ok(columns: list[str]) -> tuple[bool, list[str]]:
    """Check a candidate Bronze frame carries exactly the contracted columns.

    Returns ``(ok, missing)``; extra audit columns are allowed.
    """
    missing = [c for c in BRONZE_COLUMNS if c not in columns]
    return (not missing, missing)


def watermark_filter(current_watermark: str | None, purchase_date: str) -> bool:
    """True when a row is newer than the Bronze watermark and must be ingested.

    Dates are ISO ``YYYY-MM-DD`` so lexicographic comparison is chronological.
    ``None`` watermark (empty Bronze) ingests everything — first load.
    """
    if current_watermark is None:
        return True
    return purchase_date > current_watermark


# --- Databricks task body (executed on the cluster, not locally) --------------
# Kept as an explicit SQL/pseudo-spec so the Workflows task has one readable
# implementation instead of logic scattered across notebooks:
#
#   1. jdbc_df = spark.read.jdbc(url, "staging.purchases", properties)  -- off-peak snapshot
#   2. watermark = spark.sql("SELECT max(purchase_date) FROM bronze.raw_purchases")
#   3. new_rows = jdbc_df.filter(col("purchase_date") > watermark)  -- full snapshot if Bronze empty
#   4. stamped = new_rows.withColumn("_ingest_ts", current_timestamp()).withColumn("_source", lit("postgres"))
#   5. stamped.write.format("delta").mode("append").saveAsTable("smart_erp.bronze.raw_purchases")
#
# Idempotency: re-running with the same watermark ingests zero rows (filter is
# deterministic on purchase_date); first load is a full snapshot by construction.
