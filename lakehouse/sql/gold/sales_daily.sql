-- Gold: sales_daily — daily revenue backbone for BI (K3/K4/K5).
-- One row per (order_date, delivery_status). Consumed by Databricks SQL
-- dashboards; monthly trend = GROUP BY date_trunc('month', order_date).

CREATE OR REPLACE TABLE ${catalog}.gold.sales_daily AS
SELECT
  order_date,
  delivery_status,
  COUNT(*) AS orders,
  SUM(final_price) AS revenue,
  SUM(final_price) / COUNT(*) AS aov
FROM ${catalog}.gold.fact_sales
GROUP BY order_date, delivery_status;
