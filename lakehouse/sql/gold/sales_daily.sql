-- Gold: sales_daily — daily revenue backbone for BI (K3/K4/K5).
-- One row per (order_date, delivery_status). Consumed by Databricks SQL
-- dashboards; monthly trend = GROUP BY date_trunc('month', order_date).
--
-- NOTE: this file is EXECUTED by the smart-erp-medallion job (sql_refresh
-- file task), and SQL file tasks do not interpolate ${catalog} parameters —
-- that syntax only works in dashboard queries with bound parameters (which is
-- why the other files under sql/gold/ keep it). The catalog is therefore
-- concrete here. Free Edition has a single catalog (workspace, managed by
-- Terraform var catalog_name), so this is exact, not a shortcut. Production
-- enterprise with a dedicated catalog: point the sql_refresh file at the
-- catalog-qualified copy of this model.

CREATE OR REPLACE TABLE workspace.gold.sales_daily AS
SELECT
  order_date,
  delivery_status,
  COUNT(*) AS orders,
  SUM(final_price) AS revenue,
  SUM(final_price) / COUNT(*) AS aov
FROM workspace.gold.fact_sales
GROUP BY order_date, delivery_status;
