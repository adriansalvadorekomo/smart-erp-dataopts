-- Gold: fact_sales — one row per order line, the revenue grain.
-- Contract: docs/business-model.md K1/K2/K5/K6/K10. Source: silver only.
-- Margin column is ESTIMATED (est. unit_cost = 0.65 × unit_price, §4) — every
-- downstream consumer must keep the `estimated_` prefix / label.
-- Catalog/schema parameterized via ${catalog} (Databricks SQL parameter).

CREATE OR REPLACE TABLE ${catalog}.gold.fact_sales AS
SELECT
  oi.order_id,
  o.order_date,
  date_trunc('month', o.order_date) AS order_month,
  o.ship_to_city,
  o.payment_method,
  o.device,
  o.delivery_status,
  oi.product_id,
  p.category,
  p.subcategory,
  p.brand,
  oi.seller_id,
  oi.quantity,
  oi.unit_price,
  oi.discount_pct,
  oi.final_price,
  CASE
    WHEN oi.discount_pct < 10 THEN '0-10'
    WHEN oi.discount_pct < 30 THEN '10-30'
    WHEN oi.discount_pct < 50 THEN '30-50'
    ELSE '50-70'
  END AS discount_band,                       -- K6
  ROUND(oi.final_price - 0.65 * oi.unit_price * oi.quantity, 2)
    AS estimated_line_margin                  -- K10, ESTIMATED
FROM ${catalog}.silver.order_items oi
JOIN ${catalog}.silver.orders o
  ON o.order_id = oi.order_id
JOIN ${catalog}.silver.products p
  ON p.product_id = oi.product_id;
