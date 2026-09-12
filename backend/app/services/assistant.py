"""Grounded assistant (Phase 9, increment 1: deterministic, no LLM).

Contract: every answer is COMPUTED from governed endpoints
(services/stats.py, services/orders.py, services/forecast.py) at request time.
The response always carries its sources. Unknown questions get the capability
list — never a fabricated answer. An LLM layer may later replace intent
matching; the `{answer, intent, sources}` contract stays stable.
"""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.entities import OrderItem
from backend.app.services import forecast as fc
from backend.app.services import stats
from backend.app.services.orders import NotFound, get_order


def _inr(n: float, digits: int = 2) -> str:
    return f"₹{n:,.{digits}f}"


def _pct(ratio: float, digits: int = 1) -> str:
    return f"{ratio * 100:.{digits}f}%"


def _src(endpoint: str, params: dict | None = None) -> dict:
    return {"endpoint": endpoint, "params": params or {}}


def ask(session: Session, question: str) -> dict:
    """Answer a business question with cited, freshly-computed numbers."""
    q = question.strip().lower()
    if not q:
        return _help()

    m = re.search(r"order\s*#?(\d+)", q)
    if m and any(w in q for w in ("status", "where", "order", "track")):
        return _order_status(session, int(m.group(1)))
    m = re.search(r"\btop\s*(\d+)", q)
    if m and "seller" in q:
        return _top_sellers(session, min(int(m.group(1)), 50))
    if "seller" in q and ("attention" in q or "worst" in q or "flag" in q):
        return _sellers_attention(session)
    if "forecast" in q or "predict" in q or "projection" in q:
        return _forecast(session)
    if (("stock" in q or "reorder" in q or "restock" in q or "inventory" in q)
            and ("critical" in q or "reorder" in q or "restock" in q or "low" in q
                 or "alert" in q or "need" in q or "products" in q or "inventory" in q)):
        return _stock(session)
    if "discount" in q:
        return _discounts(session)
    if "aov" in q or "average order" in q or "basket" in q:
        return _aov(session)
    if "return" in q and ("rate" in q or "how many" in q or "%" in q or "percent" in q):
        return _return_rate(session)
    if "delay" in q:
        return _delayed(session, q)
    if "category" in q or "categories" in q or "mix" in q:
        return _categories(session)
    if "citi" in q or "cities" in q or "region" in q:
        return _cities(session, q)
    if "revenue" in q or "sales" in q or "turnover" in q:
        return _revenue(session)
    if "quality" in q or "dq" in q or "pipeline" in q or "health" in q or "gate" in q:
        return _dq(session)
    if "pareto" in q or "concentration" in q or "top 20" in q:
        return _pareto(session)
    if "help" in q or "what can you" in q or "capabilit" in q:
        return _help()
    return _fallback()


def _answer(text: str, intent: str, sources: list[dict]) -> dict:
    return {"answer": text, "intent": intent, "sources": sources}


def _help() -> dict:
    return _answer(
        "I answer from live platform data. Try: total revenue · AOV · return rate · "
        "delayed rate · top 5 sellers · sellers needing attention · stock critical · "
        "discount effectiveness · revenue by category/region · 30-day forecast · "
        "order 123 status · data quality.",
        "help", [])


def _fallback() -> dict:
    return _answer(
        "I can't answer that from governed data — I won't guess. " + _help()["answer"],
        "unknown", [])


def _revenue(session: Session) -> dict:
    o = stats.overview(session)
    return _answer(
        f"Total revenue is {_inr(o['revenue'])} across {o['total_orders']:,} orders "
        f"(AOV {_inr(o['aov'])}).",
        "revenue", [_src("GET /stats/overview")])


def _aov(session: Session) -> dict:
    o = stats.overview(session)
    return _answer(
        f"Average order value is {_inr(o['aov'])} "
        f"({_inr(o['revenue'])} / {o['total_orders']:,} orders, "
        f"average discount {o['avg_discount_pct']:.1f}%).",
        "aov", [_src("GET /stats/overview")])


def _return_rate(session: Session) -> dict:
    o = stats.overview(session)
    n = o["by_status"].get("RETURNED", 0)
    return _answer(
        f"Return rate is {_pct(o['return_rate'])} ({n:,} of {o['total_orders']:,} orders). "
        "Returns refund final_price in full.",
        "return_rate", [_src("GET /stats/overview")])


def _delayed(session: Session, q: str) -> dict:
    cities = stats.city_performance(session)
    city = next((c for c in cities if c["city"].lower() in q), None)
    if city:
        return _answer(
            f"{city['city']}: delayed rate {_pct(city['delayed_rate'], 0)} "
            f"({city['orders']:,} orders, {_inr(city['revenue'], 0)} revenue).",
            "delayed_by_city", [_src("GET /stats/city-performance")])
    o = stats.overview(session)
    worst = max(cities, key=lambda c: c["delayed_rate"]) if cities else None
    extra = (f" Worst region: {worst['city']} at {_pct(worst['delayed_rate'], 0)}."
             if worst else "")
    return _answer(
        f"Delayed rate is {_pct(o['delayed_rate'])} of completed orders "
        f"(DELIVERED + DELAYED).{extra}",
        "delayed_rate", [_src("GET /stats/overview"), _src("GET /stats/city-performance")])


def _top_sellers(session: Session, n: int) -> dict:
    rows = stats.top_sellers(session, limit=n)
    if not rows:
        return _answer("No seller revenue recorded yet.", "top_sellers",
                       [_src("GET /stats/top-sellers", {"limit": n})])
    lines = "; ".join(f"{r['seller_id']} ({_inr(r['revenue'], 0)}, ★{r['avg_rating']:.1f})"
                      for r in rows)
    return _answer(f"Top {len(rows)} sellers by revenue: {lines}.",
                   "top_sellers", [_src("GET /stats/top-sellers", {"limit": n})])


def _sellers_attention(session: Session) -> dict:
    rows = stats.seller_performance(session, limit=200)
    bad = [r for r in rows
           if r["avg_rating"] < 3.5 or r["delayed_rate"] > 0.6 or r["return_rate"] > 0.2]
    if not bad:
        return _answer("No seller currently trips the attention rules "
                       "(rating < 3.5, delayed > 60%, returns > 20%).",
                       "sellers_attention", [_src("GET /stats/seller-performance")])
    top = sorted(bad, key=lambda r: r["revenue"], reverse=True)[:5]
    lines = "; ".join(
        f"{r['seller_id']} (★{r['avg_rating']:.1f}, {_pct(r['delayed_rate'], 0)} delayed, "
        f"{_pct(r['return_rate'], 0)} returned)" for r in top)
    return _answer(f"{len(bad)} sellers flagged — largest first: {lines}.",
                   "sellers_attention", [_src("GET /stats/seller-performance")])


def _stock(session: Session) -> dict:
    o = stats.overview(session)
    rows = stats.stock_critical_list(session, limit=5)
    detail = (" Lowest: " + "; ".join(f"{r['product_id']} ({r['latest_stock']} left)" for r in rows)
              if rows else "")
    return _answer(
        f"{o['stock_critical']:,} products are stock-critical (latest stock < 20)."
        f"{detail}",
        "stock_critical",
        [_src("GET /stats/overview"), _src("GET /stats/stock-critical", {"limit": 5})])


def _discounts(session: Session) -> dict:
    bands = stats.discount_bands(session)
    best = max(bands, key=lambda b: b["revenue"]) if bands else None
    if not best:
        return _answer("No discount data recorded yet.", "discounts",
                       [_src("GET /stats/discount-bands")])
    return _answer(
        f"The {best['band']}% band brings the most revenue "
        f"({_inr(best['revenue'], 0)} on {best['lines']:,} lines).",
        "discounts", [_src("GET /stats/discount-bands")])


def _categories(session: Session) -> dict:
    rows = stats.revenue_by_category(session)
    total = sum(r["revenue"] for r in rows) or 1
    top = rows[0] if rows else None
    if not rows:
        return _answer("No sales yet.", "categories",
                       [_src("GET /stats/revenue-by-category")])
    lines = "; ".join(f"{r['category']} {_inr(r['revenue'], 0)} ({_pct(r['revenue'] / total, 0)})"
                      for r in rows)
    return _answer(f"Revenue by category: {lines}.",
                   "categories", [_src("GET /stats/revenue-by-category")])


def _cities(session: Session, q: str) -> dict:
    cities = stats.city_performance(session)
    city = next((c for c in cities if c["city"].lower() in q), None)
    if city:
        return _answer(
            f"{city['city']}: {_inr(city['revenue'], 0)} revenue, "
            f"{city['orders']:,} orders, {_pct(city['delayed_rate'], 0)} delayed, "
            f"{_pct(city['return_rate'], 0)} returned.",
            "city_detail", [_src("GET /stats/city-performance")])
    top = cities[0] if cities else None
    if not cities:
        return _answer("No sales yet.", "cities", [_src("GET /stats/city-performance")])
    if "by cit" in q or "cities" in q or "region" in q or "mix" in q:
        total = sum(c["revenue"] for c in cities) or 1
        lines = "; ".join(f"{c['city']} {_inr(c['revenue'], 0)} ({_pct(c['revenue'] / total, 0)})"
                          for c in cities)
        return _answer(f"Revenue by region: {lines}.",
                       "cities", [_src("GET /stats/city-performance")])
    return _answer(
        f"{top['city']} leads at {_inr(top['revenue'], 0)}.",
        "cities", [_src("GET /stats/city-performance")])


def _forecast(session: Session) -> dict:
    data = fc.read_forecast(session, trailing=30)
    rf = data["forecasts"]["rf"]
    ph = data["forecasts"]["prophet"]
    if not rf:
        return _answer("No forecasts stored — run the forecast refresh job first.",
                       "forecast", [_src("GET /stats/forecast")])
    rf_total = sum(r["yhat"] for r in rf)
    ph_total = sum(r["yhat"] for r in ph)
    return _answer(
        f"Next {len(rf)} days project {_inr(rf_total, 0)} (RF; as of {data['asof']}), "
        f"Prophet second opinion {_inr(ph_total, 0)}.",
        "forecast", [_src("GET /stats/forecast")])


def _order_status(session: Session, order_id: int) -> dict:
    try:
        order = get_order(session, order_id)
    except NotFound:
        return _answer(f"Order {order_id} does not exist.", "order_status", [])
    items = session.execute(
        select(OrderItem).where(OrderItem.order_id == order_id)).scalars().all()
    total = sum(float(i.final_price) for i in items)
    return _answer(
        f"Order {order_id} is {order.delivery_status} "
        f"({order.customer_id}, {order.order_date}, {_inr(total)}).",
        "order_status", [{"endpoint": f"GET /orders/{order_id}", "params": {}}])


def _dq(session: Session) -> dict:
    checks = stats.dq_checks(session)
    bad = [c for c in checks if c["violations"]]
    if not bad:
        return _answer(f"DQ gate green — all {len(checks)} R1–R7 checks pass over live data.",
                       "dq", [_src("GET /stats/dq-checks")])
    return _answer(
        "DQ gate failing: " + "; ".join(f"{c['rule']}: {c['violations']:,}" for c in bad),
        "dq", [_src("GET /stats/dq-checks")])


def _pareto(session: Session) -> dict:
    share = stats.pareto_share(session)["top20_share"]
    return _answer(
        f"The top 20% of customers drive {_pct(share)} of revenue.",
        "pareto", [_src("GET /stats/pareto")])
