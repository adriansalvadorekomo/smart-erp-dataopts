-- Gold: customer_360 — one row per customer (K9/K11/K12 feature base).
-- home_city / first_purchase_date come from silver.customers (mode-city rule
-- owned by Silver — never recomputed here). Churn/return-propensity features
-- (recency, frequency, monetary, return count) feed the Phase-8 ML models.

CREATE OR REPLACE TABLE ${catalog}.gold.customer_360 AS
SELECT
  c.customer_id,
  c.home_city,
  c.first_purchase_date,
  COUNT(DISTINCT o.order_id) AS lifetime_orders,
  SUM(f.final_price) AS lifetime_revenue,
  MAX(o.order_date) AS last_order_date,
  SUM(CASE WHEN o.delivery_status = 'RETURNED' THEN 1 ELSE 0 END) AS lifetime_returns
FROM ${catalog}.silver.customers c
LEFT JOIN ${catalog}.silver.orders o
  ON o.customer_id = c.customer_id
LEFT JOIN ${catalog}.silver.order_items f
  ON f.order_id = o.order_id
GROUP BY c.customer_id, c.home_city, c.first_purchase_date;
