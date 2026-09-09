"""Data quality rules — explicit, observable, fail-fast.

Each rule is a pure function over plain Python rows/records so it runs
identically in local unit tests and (via the same SQL predicates in comments)
on Databricks. Rules encode ``docs/business-model.md`` §6 acceptance plus the
§2–§3 invariants:

  R1  PKs/FKs never NULL
  R2  Business keys unique (customers/sellers/products)
  R3  FK references valid (no orphans)
  R4  final_price invariant within ±₹5.00
  R5  delivery_status ∈ contract enum
  R6  Quantities positive (qty ≥ 1); discount ∈ [0, 70]; stock ∈ [0, 500]
  R7  Dates valid and within the 2024-03-31 → 2026-03-31 window
  R8  Revenue checksum vs ₹9,938,876,985 ± ₹1,000 (full-load gate only)
  R9  Schema conformance (expected columns present — Bronze/Silver contract)

A rule returns a list of violation messages (empty = pass). The runner in
``runner.py`` collects them and fails the pipeline fast — Gold never builds
on red data.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from lakehouse.src.silver.transform import (
    CATEGORIES,
    DELIVERY_STATUSES,
    DEVICES,
    PAYMENT_METHODS,
    final_price_ok,
)

Row = Mapping

EXPECTED_REVENUE = 9_938_876_985.0
REVENUE_TOLERANCE = 1_000.0
WINDOW_START = "2024-03-31"
WINDOW_END = "2026-03-31"


def check_no_null_keys(rows: Iterable[Row], key_columns: list[str], table: str) -> list[str]:
    """R1 — no NULL in any PK/FK column."""
    violations = []
    for i, row in enumerate(rows):
        for col in key_columns:
            if row.get(col) is None:
                violations.append(f"R1 {table} row {i}: NULL in key column {col!r}")
    return violations


def check_unique(rows: Iterable[Row], column: str, table: str) -> list[str]:
    """R2 — business key uniqueness."""
    seen: dict = {}
    violations = []
    for i, row in enumerate(rows):
        key = row.get(column)
        if key in seen:
            violations.append(f"R2 {table}: duplicate {column}={key!r} (rows {seen[key]}, {i})")
        else:
            seen[key] = i
    return violations


def check_fk(rows: Iterable[Row], column: str, valid_keys: set, table: str) -> list[str]:
    """R3 — every FK value exists in its parent key set."""
    return [f"R3 {table}: orphan {column}={row.get(column)!r} (row {i})" for i, row in enumerate(rows) if row.get(column) not in valid_keys]


def check_final_price(rows: Iterable[Row]) -> list[str]:
    """R4 — money invariant on every order line."""
    violations = []
    for i, row in enumerate(rows):
        try:
            ok = final_price_ok(
                float(row["unit_price"]),
                int(row["quantity"]),
                float(row["discount_pct"]),
                float(row["final_price"]),
            )
        except (KeyError, TypeError, ValueError):
            violations.append(f"R4 order_items row {i}: unparseable money fields")
            continue
        if not ok:
            violations.append(f"R4 order_items row {i}: final_price invariant violated (order {row.get('order_id')!r})")
    return violations


def check_enums(orders: Iterable[Row]) -> list[str]:
    """R5 (+payment/device/category) — enum conformance."""
    violations = []
    for i, row in enumerate(orders):
        if row.get("delivery_status") not in DELIVERY_STATUSES:
            violations.append(f"R5 orders row {i}: bad delivery_status={row.get('delivery_status')!r}")
        if "payment_method" in row and row.get("payment_method") not in PAYMENT_METHODS:
            violations.append(f"R5 orders row {i}: bad payment_method={row.get('payment_method')!r}")
        if "device" in row and row.get("device") not in DEVICES:
            violations.append(f"R5 orders row {i}: bad device={row.get('device')!r}")
        if "category" in row and row.get("category") not in CATEGORIES:
            violations.append(f"R5 products row {i}: bad category={row.get('category')!r}")
    return violations


def check_ranges(items: Iterable[Row], stocks: Iterable[Row] | None = None) -> list[str]:
    """R6 — qty ≥ 1, discount ∈ [0,70], stock ∈ [0,500], prices > 0."""
    violations = []
    for i, row in enumerate(items):
        try:
            if int(row["quantity"]) < 1:
                violations.append(f"R6 order_items row {i}: quantity < 1")
            if not (0 <= float(row["discount_pct"]) <= 70):
                violations.append(f"R6 order_items row {i}: discount_pct out of [0,70]")
            if float(row["unit_price"]) <= 0:
                violations.append(f"R6 order_items row {i}: unit_price <= 0")
            if float(row["final_price"]) < 0:
                violations.append(f"R6 order_items row {i}: final_price < 0")
        except (KeyError, TypeError, ValueError):
            violations.append(f"R6 order_items row {i}: unparseable range fields")
    for i, row in enumerate(stocks or []):
        try:
            if not (0 <= int(row["stock"]) <= 500):
                violations.append(f"R6 inventory row {i}: stock out of [0,500]")
        except (KeyError, TypeError, ValueError):
            violations.append(f"R6 inventory row {i}: unparseable stock")
    return violations


def check_date_window(order_dates: Iterable[str]) -> list[str]:
    """R7 — dates parseable and inside the dataset window."""
    violations = []
    for i, d in enumerate(order_dates):
        if not (isinstance(d, str) and len(d) == 10 and WINDOW_START <= d <= WINDOW_END):
            violations.append(f"R7 orders row {i}: order_date {d!r} outside [{WINDOW_START},{WINDOW_END}]")
    return violations


def check_revenue(revenue: float) -> list[str]:
    """R8 — full-load revenue checksum (gate for full refreshes only)."""
    if abs(revenue - EXPECTED_REVENUE) > REVENUE_TOLERANCE:
        return [f"R8 revenue checksum: ₹{revenue:,.2f} != ₹{EXPECTED_REVENUE:,.0f} ± ₹{REVENUE_TOLERANCE:,.0f}"]
    return []


def check_schema(columns: list[str], expected: list[str], table: str) -> list[str]:
    """R9 — unexpected schema changes are detectable (missing columns fail)."""
    missing = [c for c in expected if c not in columns]
    if missing:
        return [f"R9 {table}: missing columns {missing}"]
    return []
