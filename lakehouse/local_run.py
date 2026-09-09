"""Local dev runner — mirrors the Databricks Workflows task order without a cluster.

Runs the cluster-independent parts (Bronze helpers → Silver transforms →
DQ gate → Gold KPI math) over a tiny inline sample so any engineer can verify
the full data path end-to-end before deploying to the Free Edition workspace:

    python lakehouse/local_run.py

Exit code 0 = the whole path passed. This is the "portfolio/free edition"
equivalent of the Workflows run; on Databricks the same logic executes as
Spark tasks defined in workflows/smart_erp_job.json.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ensure `lakehouse.*` imports resolve when run as `python lakehouse/local_run.py`
# (script dir would otherwise shadow the repo root on sys.path).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

from lakehouse.src.bronze.ingest import with_audit_columns  # noqa: E402
from lakehouse.src.gold.models import aov, rate, total_revenue  # noqa: E402
from lakehouse.src.quality import rules, runner  # noqa: E402
from lakehouse.src.silver.transform import final_price_ok, normalize_delivery_status  # noqa: E402

SAMPLE_BRONZE_ROWS = [
    {
        "user_id": "U1", "product_id": "P1", "category": "Electronics", "subcategory": "Mobile",
        "brand": "Samsung", "price": 10000.00, "discount": 10.0, "final_price": 9000.00,
        "rating": 4.5, "review_count": 10, "stock": 50, "seller_id": "S1",
        "seller_rating": 4.8, "purchase_date": "2025-06-15", "shipping_time_days": 2,
        "location": "Delhi", "device": "Mobile App", "payment_method": "UPI",
        "delivery_status": "Delivered",
    },
]


def main() -> int:
    # 1. Bronze — stamp audit columns.
    bronze = [with_audit_columns(r, source="local-sample") for r in SAMPLE_BRONZE_ROWS]
    print(f"bronze: {len(bronze)} rows stamped (_ingest_ts, _source)")

    # 2. Silver — normalize + invariant check.
    orders = [
        {
            "order_id": 1, "customer_id": r["user_id"], "order_date": r["purchase_date"],
            "delivery_status": normalize_delivery_status(r["delivery_status"]),
            "payment_method": r["payment_method"], "device": r["device"],
        }
        for r in bronze
    ]
    items = [
        {
            "order_id": 1, "product_id": r["product_id"], "seller_id": r["seller_id"],
            "quantity": 1, "unit_price": r["price"], "discount_pct": r["discount"],
            "final_price": r["final_price"],
        }
        for r in bronze
    ]
    assert all(final_price_ok(i["unit_price"], 1, i["discount_pct"], i["final_price"]) for i in items)
    print(f"silver: {len(orders)} orders, {len(items)} items normalized")

    # 3. DQ gate — fail fast before Gold.
    results = [
        runner.run_rule("R1 pk-not-null", rules.check_no_null_keys, orders, ["order_id"], "orders"),
        runner.run_rule("R5 enums", rules.check_enums, orders),
        runner.run_rule("R4 final-price", rules.check_final_price, items),
        runner.run_rule("R6 ranges", rules.check_ranges, items),
        runner.run_rule("R7 dates", rules.check_date_window, [o["order_date"] for o in orders]),
    ]
    try:
        runner.fail_fast(results)
    except runner.DataQualityError as e:
        print(f"DQ GATE FAILED: {e}")
        return 1

    # 4. Gold — KPI math on the sample.
    revenue = total_revenue([i["final_price"] for i in items])
    print(f"gold: revenue=₹{revenue:,.2f} aov=₹{aov(revenue, len(orders)):,.2f} "
          f"return_rate={rate(0, len(orders)):.2%}")
    print("LOCAL RUN PASSED — bronze → silver → DQ → gold path verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
