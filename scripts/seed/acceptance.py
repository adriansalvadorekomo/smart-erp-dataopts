#!/usr/bin/env python3
"""Phase 3 — Acceptance checks (docs/business-model.md §6, stdlib only).

Validates the ingested dataset against the contract. Exits non-zero on
any failure. Read-only: runs SELECTs through the ``psql`` CLI, so no
database driver is needed (same connection env vars as ingest.py).

Checks:
  * raw row count                    = 1,000,000
  * orders row count                 = 1,000,000
  * customers / sellers / products   = 603,815 / 9,000 / 89,999
  * no orphan order_items            = 0
  * no NULL PK/FK                    = 0
  * final_price invariant violations = 0 (± ₹5.00; source rounded from higher precision)
  * Σ final_price                    = ₹9,938,876,985 ± ₹1,000

Usage:
    python3 scripts/seed/acceptance.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys

# (name, expected) — row-count contract, business-model §6.
EXPECTED_ROWS = {
    "raw.purchases": 1_000_000,
    "public.orders": 1_000_000,
    "public.customers": 603_815,
    "public.sellers": 9_000,
    "public.products": 89_999,
}

EXPECTED_REVENUE = 9_938_876_985
REVENUE_TOLERANCE = 1_000
FINAL_PRICE_TOLERANCE = 5.00


def query(sql: str) -> str:
    """Run a single-value SELECT via psql. Raises on error."""
    proc = subprocess.run(
        ["psql", "-X", "-q", "-v", "ON_ERROR_STOP=1", "-At", "-c", sql],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print(proc.stderr.strip(), file=sys.stderr)
        raise SystemExit(f"psql failed (exit {proc.returncode})")
    return proc.stdout.strip()


def main() -> int:
    if shutil.which("psql") is None:
        print("ERROR: `psql` not found on PATH (PostgreSQL client required).", file=sys.stderr)
        return 1

    errors: list[str] = []

    for table, expected in EXPECTED_ROWS.items():
        got = int(query(f"SELECT count(*) FROM {table};"))
        print(f"  {table}: {got:,} (expected {expected:,})")
        if got != expected:
            errors.append(f"{table}: row count {got} != expected {expected}")

    orphans = query(
        """SELECT
             (SELECT count(*) FROM public.order_items oi WHERE NOT EXISTS
                (SELECT 1 FROM public.orders o WHERE o.order_id = oi.order_id))
             || ' ' ||
             (SELECT count(*) FROM public.order_items oi WHERE NOT EXISTS
                (SELECT 1 FROM public.products p WHERE p.product_id = oi.product_id))
             || ' ' ||
             (SELECT count(*) FROM public.order_items oi WHERE NOT EXISTS
                (SELECT 1 FROM public.sellers s WHERE s.seller_id = oi.seller_id));"""
    )
    orphan_order, orphan_product, orphan_seller = (int(v) for v in orphans.split())
    print(f"  orphans (order/product/seller): {orphan_order}/{orphan_product}/{orphan_seller}")
    if orphan_order:
        errors.append(f"orphan order_items (no order): {orphan_order}")
    if orphan_product:
        errors.append(f"orphan order_items (no product): {orphan_product}")
    if orphan_seller:
        errors.append(f"orphan order_items (no seller): {orphan_seller}")

    nulls = int(
        query(
            """
            SELECT
              (SELECT count(*) FROM public.customers WHERE customer_id IS NULL) +
              (SELECT count(*) FROM public.sellers    WHERE seller_id    IS NULL) +
              (SELECT count(*) FROM public.products   WHERE product_id   IS NULL) +
              (SELECT count(*) FROM public.orders     WHERE order_id     IS NULL OR customer_id IS NULL) +
              (SELECT count(*) FROM public.order_items WHERE order_id IS NULL OR product_id IS NULL OR seller_id IS NULL);
            """
        )
    )
    print(f"  NULLs in PK/FK columns: {nulls}")
    if nulls:
        errors.append(f"NULLs in PK/FK columns: {nulls}")

    # final_price invariant (± ₹5.00; max observed source deviation ≈ ₹3.99)
    bad_price = int(
        query(
            f"""
            SELECT count(*) FROM public.order_items
            WHERE abs(final_price - round(unit_price * quantity * (1 - discount_pct / 100), 2))
                  > {FINAL_PRICE_TOLERANCE};
            """
        )
    )
    print(f"  final_price invariant violations (±₹{FINAL_PRICE_TOLERANCE:.2f}): {bad_price}")
    if bad_price:
        errors.append(f"final_price invariant violations: {bad_price}")

    revenue = float(query("SELECT sum(final_price) FROM public.order_items;"))
    print(f"  revenue: ₹{revenue:,.2f} (expected ₹{EXPECTED_REVENUE:,} ± ₹{REVENUE_TOLERANCE:,})")
    if abs(revenue - EXPECTED_REVENUE) > REVENUE_TOLERANCE:
        errors.append(f"Σ final_price {revenue} != ₹{EXPECTED_REVENUE:,} ± ₹{REVENUE_TOLERANCE:,}")

    if errors:
        print("ACCEPTANCE FAILED", file=sys.stderr)
        for msg in errors:
            print(f"  - {msg}", file=sys.stderr)
        return 1

    print("ACCEPTANCE PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
