-- Gold: inventory_kpis — stock-critical list (K8, baseline 3,561 products).
-- One row per product with its latest snapshot; `is_stock_critical` mirrors
-- gold.models.is_stock_critical (threshold 20) so SQL and Python agree.

CREATE OR REPLACE TABLE ${catalog}.gold.inventory_kpis AS
WITH latest AS (
  SELECT product_id, snapshot_date, stock,
         ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY snapshot_date DESC) AS rn
  FROM ${catalog}.silver.inventory
)
SELECT
  p.product_id,
  p.category,
  p.brand,
  l.stock AS latest_stock,
  l.snapshot_date AS latest_snapshot_date,
  (l.stock < 20) AS is_stock_critical
FROM ${catalog}.silver.products p
JOIN latest l
  ON l.product_id = p.product_id AND l.rn = 1;
