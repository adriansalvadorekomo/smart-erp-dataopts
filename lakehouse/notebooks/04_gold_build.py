# Databricks notebook source
# Task: gold_build — Silver → business-ready Gold marts.
#
# Contract: lakehouse/src/gold/models.py + lakehouse/sql/gold/*.sql (same KPI
# formulas; margin columns keep the `estimated_` prefix — §4, no COGS in source).
# Sample scale: full rebuild (CREATE OR REPLACE). Widget: catalog.

# COMMAND ----------

dbutils.widgets.text("catalog", "workspace")
catalog = dbutils.widgets.get("catalog")

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE TABLE {catalog}.gold.fact_sales AS
SELECT
  oi.order_id, o.order_date, date_trunc('month', o.order_date) AS order_month,
  o.ship_to_city, o.payment_method, o.device, o.delivery_status,
  oi.product_id, p.category, p.subcategory, p.brand, oi.seller_id,
  oi.quantity, oi.unit_price, oi.discount_pct, oi.final_price,
  CASE WHEN oi.discount_pct < 10 THEN '0-10'
       WHEN oi.discount_pct < 30 THEN '10-30'
       WHEN oi.discount_pct < 50 THEN '30-50' ELSE '50-70' END AS discount_band,
  ROUND(oi.final_price - 0.65 * oi.unit_price * oi.quantity, 2) AS estimated_line_margin
FROM {catalog}.silver.order_items oi
JOIN {catalog}.silver.orders o ON o.order_id = oi.order_id
JOIN {catalog}.silver.products p ON p.product_id = oi.product_id
""")

spark.sql(f"""
CREATE OR REPLACE TABLE {catalog}.gold.sales_daily AS
SELECT order_date, delivery_status, COUNT(*) AS orders,
       SUM(final_price) AS revenue, SUM(final_price) / COUNT(*) AS aov
FROM {catalog}.gold.fact_sales GROUP BY order_date, delivery_status
""")

spark.sql(f"""
CREATE OR REPLACE TABLE {catalog}.gold.customer_360 AS
SELECT c.customer_id, c.home_city, c.first_purchase_date,
       COUNT(DISTINCT o.order_id) AS lifetime_orders,
       SUM(f.final_price) AS lifetime_revenue,
       MAX(o.order_date) AS last_order_date,
       SUM(CASE WHEN o.delivery_status = 'RETURNED' THEN 1 ELSE 0 END) AS lifetime_returns
FROM {catalog}.silver.customers c
LEFT JOIN {catalog}.silver.orders o ON o.customer_id = c.customer_id
LEFT JOIN {catalog}.silver.order_items f ON f.order_id = o.order_id
GROUP BY c.customer_id, c.home_city, c.first_purchase_date
""")

spark.sql(f"""
CREATE OR REPLACE TABLE {catalog}.gold.inventory_kpis AS
WITH latest AS (
  SELECT product_id, snapshot_date, stock,
         ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY snapshot_date DESC) AS rn
  FROM {catalog}.silver.inventory
)
SELECT p.product_id, p.category, p.brand, l.stock AS latest_stock,
       l.snapshot_date AS latest_snapshot_date, (l.stock < 20) AS is_stock_critical
FROM {catalog}.silver.products p
JOIN latest l ON l.product_id = p.product_id AND l.rn = 1
""")

# COMMAND ----------

for t in ["fact_sales", "sales_daily", "customer_360", "inventory_kpis"]:
    n = spark.sql(f"SELECT COUNT(*) AS n FROM {catalog}.gold.{t}").collect()[0]["n"]
    print(f"gold.{t}: {n:,} rows")
rev = spark.sql(f"SELECT ROUND(SUM(final_price), 2) AS r FROM {catalog}.gold.fact_sales").collect()[0]["r"]
print(f"gold sample revenue: ₹{rev:,.2f} (sample of 10k rows — full 1M baseline is ₹9,938,876,985)")
