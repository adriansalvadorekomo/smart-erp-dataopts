#!/usr/bin/env python3
"""Phase 3 — Acceptance checks (docs/business-model.md §6).

Validates the ingested dataset against the contract. Exits non-zero on any failure.

Checks:
  * raw row count                    = 1,000,000
  * orders row count                 = 1,000,000
  * customers / sellers / products   = 603,815 / 9,000 / 89,999
  * no orphan order_items            = 0
  * no NULL PK/FK                    = 0
  * final_price invariant violations = 0 (± ₹5.00; source rounded from higher precision)
  * Σ final_price                    = ₹9,938,876,985 ± ₹1,000

Usage:
    ./scripts/seed/acceptance.py [--conn "...dsn..."]
"""
from __future__ import annotations

import argparse
import os
import sys

import psycopg2

# (name, expected) — None means "only assert zero / non-neg."
EXPECTED_ROWS = {
    "raw.purchases": 1_000_000,
    "public.orders": 1_000_000,
    "public.customers": 603_815,
    "public.sellers": 9_000,
    "public.products": 89_999,
}


def default_dsn() -> str:
    return (
        f"host={os.environ.get('PGHOST', 'uptown')} "
        f"port={os.environ.get('PGPORT', '5432')} "
        f"user={os.environ.get('PGUSER', 'magrey')} "
        f"dbname={os.environ.get('PGDATABASE', 'smart')} "
        f"password={os.environ.get('PGPASSWORD', '')}"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=default_dsn())
    args = ap.parse_args()

    conn = psycopg2.connect(args.dsn)
    errors: list[str] = []
    try:
        with conn, conn.cursor() as cur:
            for table, expected in EXPECTED_ROWS.items():
                cur.execute(f"SELECT count(*) FROM {table};")
                got = cur.fetchone()[0]
                if got != expected:
                    errors.append(f"{table}: row count {got} != expected {expected}")

            cur.execute(
                """SELECT
                  (SELECT count(*) FROM order_items oi WHERE NOT EXISTS
                     (SELECT 1 FROM orders o WHERE o.order_id = oi.order_id))
                  AS orphan_order,
                  (SELECT count(*) FROM order_items oi WHERE NOT EXISTS
                     (SELECT 1 FROM products p WHERE p.product_id = oi.product_id))
                  AS orphan_product,
                  (SELECT count(*) FROM order_items oi WHERE NOT EXISTS
                     (SELECT 1 FROM sellers s WHERE s.seller_id = oi.seller_id))
                  AS orphan_seller;"""
            )
            orphan_order, orphan_product, orphan_seller = cur.fetchone()
            if orphan_order:
                errors.append(f"orphan order_items (no order): {orphan_order}")
            if orphan_product:
                errors.append(f"orphan order_items (no product): {orphan_product}")
            if orphan_seller:
                errors.append(f"orphan order_items (no seller): {orphan_seller}")

            # NULLs in any PK / FK
            cur.execute(
                """
                SELECT
                  (SELECT count(*) FROM customers WHERE customer_id IS NULL) +
                  (SELECT count(*) FROM sellers    WHERE seller_id    IS NULL) +
                  (SELECT count(*) FROM products   WHERE product_id   IS NULL) +
                  (SELECT count(*) FROM orders     WHERE order_id     IS NULL OR customer_id IS NULL) +
                  (SELECT count(*) FROM order_items WHERE order_id IS NULL OR product_id IS NULL OR seller_id IS NULL);
                """
            )
            nulls = cur.fetchone()[0]
            if nulls:
                errors.append(f"NULLs in PK/FK columns: {nulls}")

            # final_price invariant (± ₹5.00; max observed source deviation ₹3.99)
            cur.execute(
                """
                SELECT count(*) FROM order_items
                WHERE abs(final_price - round(unit_price * quantity * (1 - discount_pct / 100), 2)) > 5.00;
                """
            )
            bad_price = cur.fetchone()[0]
            if bad_price:
                errors.append(f"final_price invariant violations: {bad_price}")

            # revenue checksum
            cur.execute("SELECT sum(final_price) FROM order_items;")
            revenue = cur.fetchone()[0]
            if abs(revenue - 9_938_876_985) > 1_000:
                errors.append(f"Σ final_price {revenue} != ₹9,938,876,985 ± ₹1,000")

        if errors:
            print("❌ ACCEPTANCE FAILED", file=sys.stderr)
            for msg in errors:
                print(f"  - {msg}", file=sys.stderr)
            return 1

        print("✅ ACCEPTANCE PASSED")
        print(f"  orders={EXPECTED_ROWS['public.orders']:,} customers={EXPECTED_ROWS['public.customers']:,} "
              f"sellers={EXPECTED_ROWS['public.sellers']:,} products={EXPECTED_ROWS['public.products']:,}")
        print(f"  revenue=₹{revenue:,.2f}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())