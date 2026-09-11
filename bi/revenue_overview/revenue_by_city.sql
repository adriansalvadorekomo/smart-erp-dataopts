-- BI · Revenue overview → revenue by ship-to city (K5).
-- Tile: bar, one series. Parameter `catalog` bound by the dashboard.

SELECT
  ship_to_city,
  SUM(final_price) AS revenue,
  COUNT(*) AS orders
FROM ${catalog}.gold.fact_sales
GROUP BY ship_to_city
ORDER BY revenue DESC;
