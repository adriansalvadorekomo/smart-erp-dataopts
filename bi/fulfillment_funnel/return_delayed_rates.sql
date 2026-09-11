-- BI · Fulfillment funnel → headline rates (K3 return rate, K4 delayed rate).
-- Tile: number counters. K3 = RETURNED / all; K4 = DELAYED / completed
-- (DELIVERED + DELAYED).

SELECT
  SUM(CASE WHEN delivery_status = 'RETURNED' THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS return_rate,
  SUM(CASE WHEN delivery_status = 'DELAYED' THEN 1 ELSE 0 END) * 1.0
    / NULLIF(SUM(CASE WHEN delivery_status IN ('DELIVERED', 'DELAYED') THEN 1 ELSE 0 END), 0) AS delayed_rate,
  SUM(CASE WHEN delivery_status = 'IN TRANSIT' THEN 1 ELSE 0 END) AS in_transit
FROM ${catalog}.gold.fact_sales;
