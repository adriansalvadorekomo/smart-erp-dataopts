-- BI · Revenue overview → monthly trend (K5 slices).
-- Tile: line/bar over order_month. Parameter `catalog` bound by the dashboard.

SELECT
  order_month,
  SUM(final_price) AS revenue,
  COUNT(*) AS orders,
  SUM(final_price) / COUNT(*) AS aov
FROM ${catalog}.gold.fact_sales
GROUP BY order_month
ORDER BY order_month;
