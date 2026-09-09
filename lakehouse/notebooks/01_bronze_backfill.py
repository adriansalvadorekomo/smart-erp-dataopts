# Databricks notebook source
# Task: bronze_ingest — CSV (landing Volume) → bronze.raw_purchases (Delta, append).
#
# Contract: lakehouse/src/bronze/ingest.py. COPY INTO tracks ingested files, so
# re-runs ingest 0 new rows (idempotent). First load = full snapshot by construction.
# Widgets (also the Workflows task parameters): catalog, source_file.

# COMMAND ----------

dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("source_file", "/Volumes/workspace/bronze/landing/sample_10k.csv")

catalog = dbutils.widgets.get("catalog")
source_file = dbutils.widgets.get("source_file")

# COMMAND ----------

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {catalog}.bronze.raw_purchases (
  user_id STRING, product_id STRING, category STRING, subcategory STRING, brand STRING,
  price STRING, discount STRING, final_price STRING, rating STRING, review_count STRING,
  stock STRING, seller_id STRING, seller_rating STRING, purchase_date STRING,
  shipping_time_days STRING, location STRING, device STRING, payment_method STRING,
  is_returned STRING, delivery_status STRING,
  _ingest_ts TIMESTAMP, _source STRING
) USING DELTA
""")

# COMMAND ----------

# Staged COPY: file-level idempotency is handled by COPY INTO itself.
spark.sql(f"""
COPY INTO {catalog}.bronze.raw_purchases
FROM (
  SELECT
    *, current_timestamp() AS _ingest_ts, 'volume-csv' AS _source
  FROM '{source_file}'
)
FILEFORMAT = CSV FORMAT_OPTIONS ('header' = 'true')
COPY_OPTIONS ('mergeSchema' = 'false')
""")

# COMMAND ----------

count = spark.sql(f"SELECT COUNT(*) AS n FROM {catalog}.bronze.raw_purchases").collect()[0]["n"]
print(f"bronze.raw_purchases rows: {count:,}")
dbutils.notebook.exit(str(count))
