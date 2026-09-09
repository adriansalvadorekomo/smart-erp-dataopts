# Databricks notebook source
# Task: silver_build — bronze.raw_purchases → 6 cleaned Silver entities.
#
# Contract: lakehouse/src/silver/transform.py. All enum normalization and
# business grouping (mode city, latest snapshots) happens HERE and nowhere
# else. Sample scale: full rebuild (CREATE OR REPLACE) — acceptable and
# documented; production uses watermarked MERGE (docs/lakehouse.md §4).
# Widget: catalog.

# COMMAND ----------

dbutils.widgets.text("catalog", "workspace")
catalog = dbutils.widgets.get("catalog")
B = f"{catalog}.bronze.raw_purchases"

# COMMAND ----------

# Typed, trimmed, enum-normalized staging view (mirrors scripts/seed/ staging).
spark.sql(f"""
CREATE OR REPLACE TEMP VIEW stg AS
SELECT
  TRIM(user_id) AS user_id, TRIM(product_id) AS product_id,
  TRIM(category) AS category, TRIM(subcategory) AS subcategory, TRIM(brand) AS brand,
  ROUND(price_dec, 2) AS price, ROUND(discount_dec, 2) AS discount,
  ROUND(final_price_dec, 2) AS final_price,
  ROUND(rating_dec, 1) AS rating, review_count_int AS review_count, stock_int AS stock,
  TRIM(seller_id) AS seller_id, ROUND(seller_rating_dec, 1) AS seller_rating,
  purchase_date_dt AS purchase_date, shipping_time_int AS shipping_time_days,
  TRIM(location) AS location, TRIM(device) AS device, TRIM(payment_method) AS payment_method,
  UPPER(TRIM(delivery_status)) AS delivery_status
FROM (
  SELECT *,
    TRY_CAST(price AS DECIMAL(10,2)) AS price_dec,
    TRY_CAST(discount AS DECIMAL(4,2)) AS discount_dec,
    TRY_CAST(final_price AS DECIMAL(10,2)) AS final_price_dec,
    TRY_CAST(rating AS DECIMAL(2,1)) AS rating_dec,
    TRY_CAST(review_count AS INT) AS review_count_int,
    TRY_CAST(stock AS INT) AS stock_int,
    TRY_CAST(seller_rating AS DECIMAL(2,1)) AS seller_rating_dec,
    TRY_CAST(purchase_date AS DATE) AS purchase_date_dt,
    TRY_CAST(shipping_time_days AS SMALLINT) AS shipping_time_int
  FROM {B}
)
""")

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE TABLE {catalog}.silver.customers AS
WITH ranked AS (
  SELECT user_id, location, MAX(purchase_date) AS last_seen, COUNT(*) AS cnt,
         ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY COUNT(*) DESC, MAX(purchase_date) DESC) AS rn
  FROM stg GROUP BY user_id, location
)
SELECT s.user_id AS customer_id, r.location AS home_city, MIN(s.purchase_date) AS first_purchase_date
FROM (SELECT user_id, MIN(purchase_date) AS first_seen FROM stg GROUP BY user_id) f
JOIN stg s ON s.user_id = f.user_id
JOIN ranked r ON r.user_id = f.user_id AND r.rn = 1
GROUP BY s.user_id, r.location
""")

spark.sql(f"""
CREATE OR REPLACE TABLE {catalog}.silver.sellers AS
SELECT seller_id, seller_rating AS current_rating FROM (
  SELECT seller_id, seller_rating,
         ROW_NUMBER() OVER (PARTITION BY seller_id ORDER BY purchase_date DESC) AS rn
  FROM stg
) WHERE rn = 1
""")

spark.sql(f"""
CREATE OR REPLACE TABLE {catalog}.silver.products AS
SELECT product_id, category, subcategory, brand, price AS current_price,
       rating AS product_rating, review_count FROM (
  SELECT product_id, category, subcategory, brand, price, rating, review_count,
         ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY purchase_date DESC) AS rn
  FROM stg
) WHERE rn = 1
""")

spark.sql(f"""
CREATE OR REPLACE TABLE {catalog}.silver.inventory AS
SELECT product_id, purchase_date AS snapshot_date, stock FROM (
  SELECT product_id, purchase_date, stock,
         ROW_NUMBER() OVER (PARTITION BY product_id, purchase_date ORDER BY purchase_date) AS rn
  FROM (SELECT DISTINCT product_id, purchase_date, stock FROM stg)
) WHERE rn = 1
""")

# COMMAND ----------

# Deterministic surrogate shared by orders ↔ order_items (mirrors ingest.py row_idx).
spark.sql(f"""
CREATE OR REPLACE TABLE {catalog}.silver.orders AS
SELECT
  ROW_NUMBER() OVER (ORDER BY purchase_date, user_id, product_id) AS order_id,
  user_id AS customer_id, purchase_date AS order_date, location AS ship_to_city,
  payment_method, device, delivery_status, shipping_time_days
FROM stg
""")

spark.sql(f"""
CREATE OR REPLACE TABLE {catalog}.silver.order_items AS
SELECT
  o.order_id, s.product_id, s.seller_id, 1 AS quantity,
  s.price AS unit_price, s.discount AS discount_pct, s.final_price,
  s.seller_rating AS seller_rating_at_sale
FROM (
  SELECT *, ROW_NUMBER() OVER (ORDER BY purchase_date, user_id, product_id) AS rn
  FROM stg
) s
JOIN {catalog}.silver.orders o
  ON o.order_id = s.rn
""")

# COMMAND ----------

for t in ["customers", "sellers", "products", "inventory", "orders", "order_items"]:
    n = spark.sql(f"SELECT COUNT(*) AS n FROM {catalog}.silver.{t}").collect()[0]["n"]
    print(f"silver.{t}: {n:,} rows")
