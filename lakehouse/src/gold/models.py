"""Gold layer — business-ready analytical models.

Contract (see docs/lakehouse.md + KPI→Gold matrix in docs/business-model.md):
- Gold tables answer the §5 KPIs and nothing else. No speculative marts.
- All margin figures are **estimated** (est. unit_cost = 0.65 × unit_price).
- Pure helpers below implement the KPI arithmetic on plain Python iterables
  (same formulas the SQL models use) so business logic is tested without a
  cluster and cannot drift between Python/ML and SQL/BI.

Table → KPI mapping:
  fact_sales     K1 revenue, K2 AOV, K5 slices, K6 discount bands, K10 est. margin
  dim_customer   K9 Pareto support
  dim_product    K5 category/brand slices, K7 seller joins
  dim_date       K5 monthly trend backbone (2024-03-31 → 2026-03-31)
  sales_daily    K5 daily/monthly revenue, K4 delayed rate, K3 return rate
  customer_360   K9 concentration, K11 churn features, K12 return-propensity features
  inventory_kpis K8 stock-critical list
"""

from __future__ import annotations

from collections.abc import Iterable

from lakehouse.src.silver.transform import EST_UNIT_COST_FACTOR


def total_revenue(final_prices: Iterable[float]) -> float:
    """K1 — Σ final_price, rounded to paise."""
    return round(sum(final_prices), 2)


def aov(total: float, order_count: int) -> float:
    """K2 — average order value. Baseline ₹9,938.88."""
    if order_count == 0:
        raise ValueError("order_count must be > 0")
    return round(total / order_count, 2)


def rate(part: int, whole: int) -> float:
    """Generic rate helper (K3 return rate, K4 delayed rate). Baseline K3 = 11.60%."""
    if whole == 0:
        raise ValueError("denominator must be > 0")
    return round(part / whole, 4)


def pareto_share(sorted_desc_revenues: list[float], top_fraction: float = 0.20) -> float:
    """K9 — revenue share of the top fraction of customers (baseline 62.9%)."""
    if not sorted_desc_revenues:
        raise ValueError("empty revenue list")
    n = max(1, int(len(sorted_desc_revenues) * top_fraction))
    return round(sum(sorted_desc_revenues[:n]) / sum(sorted_desc_revenues), 4)


def discount_band(discount_pct: float) -> str:
    """K6 — discount band bucket (0–10/10–30/30–50/50–70%)."""
    if discount_pct < 0 or discount_pct > 70:
        raise ValueError(f"discount_pct out of contract range: {discount_pct!r}")
    if discount_pct < 10:
        return "0-10"
    if discount_pct < 30:
        return "10-30"
    if discount_pct < 50:
        return "30-50"
    return "50-70"


def is_stock_critical(latest_stock: int, threshold: int = 20) -> bool:
    """K8 — stock-critical flag (baseline 3,561 products)."""
    return latest_stock < threshold


def estimated_line_margin(unit_price: float, quantity: int, final_price: float) -> float:
    """K10 — estimated margin per line. Consumers must label 'estimated'."""
    return round(final_price - EST_UNIT_COST_FACTOR * unit_price * quantity, 2)
