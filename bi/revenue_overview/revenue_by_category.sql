-- BI · Revenue overview → revenue by category (K5).
-- Tile: bar or donut. Parameter `catalog` bound by the dashboard.

SELECT
  category,
  SUM(final_price) AS revenue,
  COUNT(*) AS lines
FROM ${catalog}.gold.fact_sales
GROUP BY category
ORDER BY revenue DESC;
