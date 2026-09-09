# Databricks notebook source
# Task: dq_gate — fail-fast data quality gate R1–R9 over Silver.
#
# Contract: lakehouse/src/quality/rules.py. Any violation raises, which fails
# the task and blocks gold_build — corrupted data never reaches Gold.
# Widget: catalog.

# COMMAND ----------

dbutils.widgets.text("catalog", "workspace")
catalog = dbutils.widgets.get("catalog")
violations = []

def check(name, sql, expect_zero=True):
    n = spark.sql(sql).collect()[0]["n"]
    status = "PASS" if (n == 0 if expect_zero else True) else "FAIL"
    print(f"DQ {status} {name}: {n:,}")
    if n != 0 and expect_zero:
        violations.append(f"{name}: {n:,} violation(s)")
    return n

# COMMAND ----------

# R1 — no NULL PK/FK
check("R1 customers null keys",
      f"SELECT COUNT(*) n FROM {catalog}.silver.customers WHERE customer_id IS NULL")
check("R1 orders null keys",
      f"SELECT COUNT(*) n FROM {catalog}.silver.orders WHERE order_id IS NULL OR customer_id IS NULL")
check("R1 order_items null keys",
      f"SELECT COUNT(*) n FROM {catalog}.silver.order_items WHERE order_id IS NULL OR product_id IS NULL OR seller_id IS NULL")
# R2 — business key uniqueness
check("R2 customers unique",
      f"SELECT COUNT(*) n FROM (SELECT customer_id FROM {catalog}.silver.customers GROUP BY customer_id HAVING COUNT(*) > 1)")
check("R2 products unique",
      f"SELECT COUNT(*) n FROM (SELECT product_id FROM {catalog}.silver.products GROUP BY product_id HAVING COUNT(*) > 1)")
# R3 — FK validity (no orphans)
check("R3 order_items → orders",
      f"""SELECT COUNT(*) n FROM {catalog}.silver.order_items oi
          LEFT ANTI JOIN {catalog}.silver.orders o ON o.order_id = oi.order_id""")
check("R3 order_items → products",
      f"""SELECT COUNT(*) n FROM {catalog}.silver.order_items oi
          LEFT ANTI JOIN {catalog}.silver.products p ON p.product_id = oi.product_id""")
# R4 — money invariant ±₹5.00
check("R4 final_price invariant",
      f"""SELECT COUNT(*) n FROM {catalog}.silver.order_items
          WHERE ABS(final_price - ROUND(unit_price * quantity * (1 - discount_pct / 100), 2)) > 5.00""")
# R5 — enum conformance
check("R5 delivery_status enum",
      f"""SELECT COUNT(*) n FROM {catalog}.silver.orders
          WHERE delivery_status NOT IN ('IN TRANSIT','DELIVERED','DELAYED','RETURNED')""")
# R6 — ranges
check("R6 quantity/discount/price ranges",
      f"""SELECT COUNT(*) n FROM {catalog}.silver.order_items
          WHERE quantity < 1 OR discount_pct < 0 OR discount_pct > 70
             OR unit_price <= 0 OR final_price < 0""")
# R7 — date window
check("R7 order_date window",
      f"""SELECT COUNT(*) n FROM {catalog}.silver.orders
          WHERE order_date < DATE'2024-03-31' OR order_date > DATE'2026-03-31'""")

# COMMAND ----------

if violations:
    raise Exception("DQ GATE FAILED — Gold blocked: " + "; ".join(violations))
print(f"DQ GATE PASSED — {catalog}.silver is green, Gold may build")
