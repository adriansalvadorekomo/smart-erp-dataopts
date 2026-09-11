-- BI · Fulfillment funnel → counts + revenue per delivery status.
-- Tile: funnel/bar. Feeds the K3/K4 rate tiles below; baselines in
-- docs/business-model.md §5 (return 11.60%, delayed ≈50% of completed).

SELECT
  delivery_status,
  COUNT(*) AS orders,
  SUM(final_price) AS revenue
FROM ${catalog}.gold.fact_sales
GROUP BY delivery_status
ORDER BY orders DESC;
