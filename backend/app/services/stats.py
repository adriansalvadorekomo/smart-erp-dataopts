"""Read-only aggregate stats — business questions, not just data readouts.

Every function exists to answer a named business question (see comments).
All queries hit indexed OLTP columns (orders.order_date/status, FK joins).
No business rules live here — pure aggregation over committed state.

Business questions answered:
  overview()           → "What is the state of the business right now?"
  revenue_trend()      → "Is revenue growing or slowing?"
  revenue_by_category()→ "Which categories drive revenue vs volume?"
  sales_by_city()      → "Which cities are over/underperforming?"
  category_trend()     → "Which categories are growing or declining?"
  channel_mix()        → "Which payment/device channels drive orders?"
  discount_bands()     → "Do heavy discounts correlate with more revenue?"
  top_sellers()        → "Who are the top revenue generators?"
  seller_performance() → "Which sellers have quality problems (high returns)?"
  operations_breakdown() → "Where are delays and returns concentrated?"
  shipping_return_correlation() → "Does faster shipping reduce returns?"
  pareto_share()       → "How concentrated is our customer revenue?"
  dq_checks()          → "Is the data platform healthy?"
"""
from __future__ import annotations

import datetime

from sqlalchemy import case, func, select, text
from sqlalchemy.orm import Session

from backend.app.models.entities import Inventory, Order, OrderItem, Product


def overview(session: Session) -> dict:
    total_orders = session.execute(select(func.count()).select_from(Order)).scalar() or 0
    revenue = session.execute(
        select(func.coalesce(func.sum(OrderItem.final_price), 0))
    ).scalar() or 0
    avg_discount = session.execute(
        select(func.coalesce(func.avg(OrderItem.discount_pct), 0))
    ).scalar() or 0

    by_status = dict(
        session.execute(
            select(Order.delivery_status, func.count()).group_by(Order.delivery_status)
        ).all()
    )
    delivered = by_status.get("DELIVERED", 0)
    delayed = by_status.get("DELAYED", 0)
    returned = by_status.get("RETURNED", 0)
    in_transit = by_status.get("IN TRANSIT", 0)
    completed = delivered + delayed

    latest_sub = (
        select(
            Inventory.product_id,
            func.max(Inventory.snapshot_date).label("max_date"),
        )
        .group_by(Inventory.product_id)
        .subquery()
    )
    stock_critical = session.execute(
        select(func.count())
        .select_from(Inventory)
        .join(
            latest_sub,
            (Inventory.product_id == latest_sub.c.product_id)
            & (Inventory.snapshot_date == latest_sub.c.max_date),
        )
        .where(Inventory.stock < 20)
    ).scalar() or 0

    return {
        "total_orders": total_orders,
        "revenue": float(revenue),
        "aov": float(revenue) / total_orders if total_orders else 0.0,
        "avg_discount_pct": float(avg_discount),
        "return_rate": returned / total_orders if total_orders else 0.0,
        "delayed_rate": delayed / completed if completed else 0.0,
        "in_transit": in_transit,
        "stock_critical": stock_critical,
        "by_status": by_status,
    }


def revenue_trend(session: Session, days: int = 30) -> list[dict]:
    """Revenue + order counts for the last N days WITH DATA (dense seed
    windows read as trailing days; a sparse live tail doesn't blank the chart)."""
    recent = (
        select(Order.order_date)
        .distinct()
        .order_by(Order.order_date.desc())
        .limit(days)
        .subquery()
    )
    rows = session.execute(
        select(
            Order.order_date.label("date"),
            func.count(Order.order_id).label("orders"),
            func.coalesce(func.sum(OrderItem.final_price), 0).label("revenue"),
        )
        .join(OrderItem, OrderItem.order_id == Order.order_id)
        .where(Order.order_date.in_(select(recent.c.order_date)))
        .group_by(Order.order_date)
        .order_by(Order.order_date)
    ).all()
    return [
        {"date": r.date.isoformat(), "orders": r.orders, "revenue": float(r.revenue)}
        for r in rows
    ]


def revenue_by_category(session: Session) -> list[dict]:
    """Revenue + line counts per product category (all time)."""
    rows = session.execute(
        select(
            Product.category.label("category"),
            func.coalesce(func.sum(OrderItem.final_price), 0).label("revenue"),
            func.count(OrderItem.order_item_id).label("lines"),
        )
        .join(OrderItem, OrderItem.product_id == Product.product_id)
        .group_by(Product.category)
        .order_by(func.sum(OrderItem.final_price).desc())
    ).all()
    return [
        {"category": r.category, "revenue": float(r.revenue), "lines": r.lines}
        for r in rows
    ]


def discount_bands(session: Session) -> list[dict]:
    """K6 — revenue and lines per discount band."""
    band = case(
        (OrderItem.discount_pct < 10, "0–10"),
        (OrderItem.discount_pct < 30, "10–30"),
        (OrderItem.discount_pct < 50, "30–50"),
        else_="50–70",
    )
    rows = session.execute(
        select(
            band.label("band"),
            func.count(OrderItem.order_item_id).label("lines"),
            func.coalesce(func.sum(OrderItem.final_price), 0).label("revenue"),
        )
        .group_by(band)
        .order_by(band)
    ).all()
    return [
        {"band": r.band, "lines": r.lines, "revenue": float(r.revenue)} for r in rows
    ]


def top_sellers(session: Session, limit: int = 10) -> list[dict]:
    """K7 — sellers by revenue with average rating at sale."""
    rows = session.execute(
        select(
            OrderItem.seller_id.label("seller_id"),
            func.coalesce(func.sum(OrderItem.final_price), 0).label("revenue"),
            func.count(OrderItem.order_item_id).label("lines"),
            func.coalesce(func.avg(OrderItem.seller_rating_at_sale), 0).label("avg_rating"),
        )
        .group_by(OrderItem.seller_id)
        .order_by(func.sum(OrderItem.final_price).desc())
        .limit(limit)
    ).all()
    return [
        {
            "seller_id": r.seller_id,
            "revenue": float(r.revenue),
            "lines": r.lines,
            "avg_rating": float(r.avg_rating),
        }
        for r in rows
    ]


def pareto_share(session: Session) -> dict:
    """K9 — revenue share of the top 20% of customers by lifetime revenue."""
    row = session.execute(
        text(
            """
            WITH per_cust AS (
              SELECT o.customer_id AS customer_id, SUM(oi.final_price) AS rev
              FROM public.orders o
              JOIN public.order_items oi ON oi.order_id = o.order_id
              GROUP BY o.customer_id
            ),
            ranked AS (
              SELECT rev, NTILE(5) OVER (ORDER BY rev DESC) AS quintile FROM per_cust
            )
            SELECT SUM(CASE WHEN quintile = 1 THEN rev ELSE 0 END) / SUM(rev) AS top20
            FROM ranked
            """
        )
    ).first()
    return {"top20_share": float(row[0]) if row and row[0] is not None else 0.0}


def dq_checks(session: Session) -> list[dict]:
    """OLTP-side mirror of the lakehouse DQ gate R1–R7 (same predicates).

    Lets the Pipeline page show gate status over live OLTP state; the
    authoritative gate still runs in the lakehouse before Gold builds.
    """
    checks = [
        ("R1 customers null keys",
         "SELECT COUNT(*) FROM public.customers WHERE customer_id IS NULL"),
        ("R1 orders null keys",
         "SELECT COUNT(*) FROM public.orders WHERE order_id IS NULL OR customer_id IS NULL"),
        ("R1 order_items null keys",
         "SELECT COUNT(*) FROM public.order_items WHERE order_id IS NULL OR product_id IS NULL OR seller_id IS NULL"),
        ("R2 customers unique",
         "SELECT COUNT(*) FROM (SELECT customer_id FROM public.customers GROUP BY customer_id HAVING COUNT(*) > 1) t"),
        ("R2 products unique",
         "SELECT COUNT(*) FROM (SELECT product_id FROM public.products GROUP BY product_id HAVING COUNT(*) > 1) t"),
        ("R3 order_items → orders",
         "SELECT COUNT(*) FROM public.order_items oi WHERE NOT EXISTS (SELECT 1 FROM public.orders o WHERE o.order_id = oi.order_id)"),
        ("R3 order_items → products",
         "SELECT COUNT(*) FROM public.order_items oi WHERE NOT EXISTS (SELECT 1 FROM public.products p WHERE p.product_id = oi.product_id)"),
        ("R4 final_price invariant",
         "SELECT COUNT(*) FROM public.order_items WHERE ABS(final_price - ROUND(unit_price * quantity * (1 - discount_pct / 100), 2)) > 5.00"),
        ("R5 delivery_status enum",
         "SELECT COUNT(*) FROM public.orders WHERE delivery_status NOT IN ('IN TRANSIT','DELIVERED','DELAYED','RETURNED')"),
        ("R6 quantity/discount/price ranges",
         "SELECT COUNT(*) FROM public.order_items WHERE quantity < 1 OR discount_pct < 0 OR discount_pct > 70 OR unit_price <= 0 OR final_price < 0"),
        ("R7 order_date window",
         "SELECT COUNT(*) FROM public.orders WHERE order_date < DATE '2024-03-31' OR order_date > DATE '2026-03-31'"),
    ]
    return [
        {"rule": name, "violations": session.execute(text(sql)).scalar() or 0}
        for name, sql in checks
    ]


# ─── NEW BUSINESS-ORIENTED ENDPOINTS ────────────────────────────────────────

def sales_by_city(session: Session) -> list[dict]:
    """Question: Which cities are over- or underperforming?
    Returns revenue, order count, AOV, and return rate per city.
    Cities with high orders but low AOV or high return rates are worth investigating.
    """
    rows = session.execute(
        text("""
            SELECT
                o.ship_to_city                                     AS city,
                COUNT(DISTINCT o.order_id)                         AS orders,
                COALESCE(SUM(oi.final_price), 0)                   AS revenue,
                COALESCE(SUM(oi.final_price), 0)
                    / NULLIF(COUNT(DISTINCT o.order_id), 0)        AS aov,
                COUNT(DISTINCT CASE WHEN o.delivery_status = 'RETURNED'
                    THEN o.order_id END)::float
                    / NULLIF(COUNT(DISTINCT o.order_id), 0)        AS return_rate,
                COUNT(DISTINCT CASE WHEN o.delivery_status = 'DELAYED'
                    THEN o.order_id END)::float
                    / NULLIF(COUNT(DISTINCT CASE WHEN o.delivery_status IN ('DELIVERED','DELAYED')
                    THEN o.order_id END), 0)                       AS delayed_rate
            FROM public.orders o
            JOIN public.order_items oi ON oi.order_id = o.order_id
            GROUP BY o.ship_to_city
            ORDER BY revenue DESC
        """)
    ).all()
    return [
        {
            "city": r.city,
            "orders": r.orders,
            "revenue": float(r.revenue),
            "aov": float(r.aov) if r.aov else 0.0,
            "return_rate": float(r.return_rate) if r.return_rate else 0.0,
            "delayed_rate": float(r.delayed_rate) if r.delayed_rate else 0.0,
        }
        for r in rows
    ]


def category_trend(session: Session) -> list[dict]:
    """Question: Which categories are growing or declining?
    Returns monthly revenue per category — the browser computes growth direction.
    Electronics dominates at 66% revenue; this shows if that concentration is changing.
    """
    rows = session.execute(
        text("""
            SELECT
                TO_CHAR(DATE_TRUNC('month', o.order_date), 'YYYY-MM') AS month,
                p.category,
                COALESCE(SUM(oi.final_price), 0)                       AS revenue,
                COUNT(DISTINCT o.order_id)                             AS orders
            FROM public.orders o
            JOIN public.order_items oi ON oi.order_id = o.order_id
            JOIN public.products p ON p.product_id = oi.product_id
            GROUP BY DATE_TRUNC('month', o.order_date), p.category
            ORDER BY month, revenue DESC
        """)
    ).all()
    return [
        {"month": r.month, "category": r.category, "revenue": float(r.revenue), "orders": r.orders}
        for r in rows
    ]


def channel_mix(session: Session) -> dict:
    """Question: Which payment/device channels drive orders and does channel
    correlate with return behavior?
    COD often drives higher returns in Indian e-commerce — this surfaces that.
    """
    payment_rows = session.execute(
        text("""
            SELECT
                o.payment_method,
                COUNT(DISTINCT o.order_id)                             AS orders,
                COALESCE(SUM(oi.final_price), 0)                       AS revenue,
                COUNT(DISTINCT CASE WHEN o.delivery_status = 'RETURNED'
                    THEN o.order_id END)::float
                    / NULLIF(COUNT(DISTINCT o.order_id), 0)            AS return_rate
            FROM public.orders o
            JOIN public.order_items oi ON oi.order_id = o.order_id
            GROUP BY o.payment_method
            ORDER BY revenue DESC
        """)
    ).all()
    device_rows = session.execute(
        text("""
            SELECT
                o.device,
                COUNT(DISTINCT o.order_id)    AS orders,
                COALESCE(SUM(oi.final_price), 0) AS revenue,
                COUNT(DISTINCT CASE WHEN o.delivery_status = 'RETURNED'
                    THEN o.order_id END)::float
                    / NULLIF(COUNT(DISTINCT o.order_id), 0) AS return_rate
            FROM public.orders o
            JOIN public.order_items oi ON oi.order_id = o.order_id
            GROUP BY o.device
            ORDER BY revenue DESC
        """)
    ).all()
    return {
        "payment": [
            {
                "method": r.payment_method,
                "orders": r.orders,
                "revenue": float(r.revenue),
                "return_rate": float(r.return_rate) if r.return_rate else 0.0,
            }
            for r in payment_rows
        ],
        "device": [
            {
                "device": r.device,
                "orders": r.orders,
                "revenue": float(r.revenue),
                "return_rate": float(r.return_rate) if r.return_rate else 0.0,
            }
            for r in device_rows
        ],
    }


def seller_performance(session: Session, limit: int = 20) -> list[dict]:
    """Question: Which sellers have quality problems?
    Ranks sellers by revenue and overlays return rate + avg rating.
    High revenue + high return rate = quality risk.
    High revenue + low rating = reputation risk.
    The anomaly signal: sellers where return_rate > 2× the platform average (11.6%).
    """
    rows = session.execute(
        text("""
            SELECT
                oi.seller_id,
                COUNT(DISTINCT o.order_id)                             AS orders,
                COALESCE(SUM(oi.final_price), 0)                       AS revenue,
                AVG(oi.seller_rating_at_sale)                          AS avg_rating,
                COUNT(DISTINCT CASE WHEN o.delivery_status = 'RETURNED'
                    THEN o.order_id END)::float
                    / NULLIF(COUNT(DISTINCT o.order_id), 0)            AS return_rate,
                COUNT(DISTINCT CASE WHEN o.delivery_status = 'DELAYED'
                    THEN o.order_id END)::float
                    / NULLIF(COUNT(DISTINCT CASE WHEN o.delivery_status
                    IN ('DELIVERED','DELAYED') THEN o.order_id END), 0) AS delayed_rate
            FROM public.order_items oi
            JOIN public.orders o ON o.order_id = oi.order_id
            GROUP BY oi.seller_id
            HAVING COUNT(DISTINCT o.order_id) >= 10
            ORDER BY revenue DESC
            LIMIT :limit
        """),
        {"limit": limit},
    ).all()
    return [
        {
            "seller_id": r.seller_id,
            "orders": r.orders,
            "revenue": float(r.revenue),
            "avg_rating": float(r.avg_rating) if r.avg_rating else 0.0,
            "return_rate": float(r.return_rate) if r.return_rate else 0.0,
            "delayed_rate": float(r.delayed_rate) if r.delayed_rate else 0.0,
        }
        for r in rows
    ]


def operations_breakdown(session: Session) -> dict:
    """Question: Where are delays and returns concentrated?
    Breaks down return_rate and delayed_rate by: category, city, payment method,
    and shipping_time_days.
    A 50% delayed rate is the platform's biggest operational problem — this shows
    whether it's uniform or concentrated in specific segments.
    """
    category_rows = session.execute(
        text("""
            SELECT
                p.category,
                COUNT(DISTINCT o.order_id)                         AS orders,
                COUNT(DISTINCT CASE WHEN o.delivery_status = 'RETURNED'
                    THEN o.order_id END)::float
                    / NULLIF(COUNT(DISTINCT o.order_id), 0)        AS return_rate,
                COUNT(DISTINCT CASE WHEN o.delivery_status = 'DELAYED'
                    THEN o.order_id END)::float
                    / NULLIF(COUNT(DISTINCT CASE WHEN o.delivery_status
                    IN ('DELIVERED','DELAYED') THEN o.order_id END), 0) AS delayed_rate
            FROM public.orders o
            JOIN public.order_items oi ON oi.order_id = o.order_id
            JOIN public.products p ON p.product_id = oi.product_id
            GROUP BY p.category
            ORDER BY delayed_rate DESC NULLS LAST
        """)
    ).all()

    city_rows = session.execute(
        text("""
            SELECT
                o.ship_to_city                                     AS city,
                COUNT(DISTINCT o.order_id)                         AS orders,
                COUNT(DISTINCT CASE WHEN o.delivery_status = 'RETURNED'
                    THEN o.order_id END)::float
                    / NULLIF(COUNT(DISTINCT o.order_id), 0)        AS return_rate,
                COUNT(DISTINCT CASE WHEN o.delivery_status = 'DELAYED'
                    THEN o.order_id END)::float
                    / NULLIF(COUNT(DISTINCT CASE WHEN o.delivery_status
                    IN ('DELIVERED','DELAYED') THEN o.order_id END), 0) AS delayed_rate
            FROM public.orders o
            GROUP BY o.ship_to_city
            ORDER BY delayed_rate DESC NULLS LAST
        """)
    ).all()

    shipping_rows = session.execute(
        text("""
            SELECT
                o.shipping_time_days,
                COUNT(DISTINCT o.order_id)                         AS orders,
                COUNT(DISTINCT CASE WHEN o.delivery_status = 'RETURNED'
                    THEN o.order_id END)::float
                    / NULLIF(COUNT(DISTINCT o.order_id), 0)        AS return_rate,
                COUNT(DISTINCT CASE WHEN o.delivery_status = 'DELAYED'
                    THEN o.order_id END)::float
                    / NULLIF(COUNT(DISTINCT CASE WHEN o.delivery_status
                    IN ('DELIVERED','DELAYED') THEN o.order_id END), 0) AS delayed_rate
            FROM public.orders o
            GROUP BY o.shipping_time_days
            ORDER BY o.shipping_time_days
        """)
    ).all()

    payment_rows = session.execute(
        text("""
            SELECT
                o.payment_method,
                COUNT(DISTINCT o.order_id)                         AS orders,
                COUNT(DISTINCT CASE WHEN o.delivery_status = 'RETURNED'
                    THEN o.order_id END)::float
                    / NULLIF(COUNT(DISTINCT o.order_id), 0)        AS return_rate,
                COUNT(DISTINCT CASE WHEN o.delivery_status = 'DELAYED'
                    THEN o.order_id END)::float
                    / NULLIF(COUNT(DISTINCT CASE WHEN o.delivery_status
                    IN ('DELIVERED','DELAYED') THEN o.order_id END), 0) AS delayed_rate
            FROM public.orders o
            GROUP BY o.payment_method
            ORDER BY return_rate DESC NULLS LAST
        """)
    ).all()

    def _row(r, key: str):
        return {
            key: getattr(r, key),
            "orders": r.orders,
            "return_rate": float(r.return_rate) if r.return_rate else 0.0,
            "delayed_rate": float(r.delayed_rate) if r.delayed_rate else 0.0,
        }

    return {
        "by_category": [_row(r, "category") for r in category_rows],
        "by_city": [_row(r, "city") for r in city_rows],
        "by_shipping_days": [
            {
                "shipping_time_days": r.shipping_time_days,
                "orders": r.orders,
                "return_rate": float(r.return_rate) if r.return_rate else 0.0,
                "delayed_rate": float(r.delayed_rate) if r.delayed_rate else 0.0,
            }
            for r in shipping_rows
        ],
        "by_payment": [_row(r, "payment_method") for r in payment_rows],
    }
