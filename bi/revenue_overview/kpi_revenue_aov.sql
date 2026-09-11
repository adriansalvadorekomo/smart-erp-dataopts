-- BI · Revenue overview → headline KPIs (K1 revenue, K2 AOV).
-- Tile: number counters. Catalog bound by the dashboard (parameter `catalog`).
-- Read-only over Gold; refresh = re-run (Gold rebuilds come from the job).

SELECT
  SUM(final_price) AS revenue,
  COUNT(*) AS orders,
  SUM(final_price) / COUNT(*) AS aov
FROM ${catalog}.gold.fact_sales;
