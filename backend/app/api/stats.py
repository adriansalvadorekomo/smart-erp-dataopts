"""Business analytics router.

Each endpoint answers a named business question — see services/stats.py.
All endpoints are read-only aggregations; no mutations live here.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.core.db import get_db
from backend.app.services import stats

router = APIRouter(prefix="/stats", tags=["stats"])


# ─── PLATFORM HEALTH ─────────────────────────────────────────────────────────

@router.get("/overview")
def get_overview(session: Session = Depends(get_db)):
    """What is the state of the business right now?"""
    return stats.overview(session)


@router.get("/dq-checks")
def get_dq_checks(session: Session = Depends(get_db)):
    """Is the data platform healthy? (OLTP mirror of the lakehouse DQ gate)"""
    return stats.dq_checks(session)


# ─── SALES & REVENUE ─────────────────────────────────────────────────────────

@router.get("/revenue-trend")
def get_revenue_trend(
    days: int = Query(default=30, ge=7, le=365),
    session: Session = Depends(get_db),
):
    """Is revenue growing or slowing?"""
    return stats.revenue_trend(session, days=days)


@router.get("/revenue-by-category")
def get_revenue_by_category(session: Session = Depends(get_db)):
    """Which categories drive revenue vs. volume?"""
    return stats.revenue_by_category(session)


@router.get("/sales-by-city")
def get_sales_by_city(session: Session = Depends(get_db)):
    """Which cities are over- or underperforming?"""
    return stats.sales_by_city(session)


@router.get("/category-trend")
def get_category_trend(session: Session = Depends(get_db)):
    """Which categories are growing or declining over time?"""
    return stats.category_trend(session)


@router.get("/channel-mix")
def get_channel_mix(session: Session = Depends(get_db)):
    """Which payment/device channels drive orders and returns?"""
    return stats.channel_mix(session)


@router.get("/discount-bands")
def get_discount_bands(session: Session = Depends(get_db)):
    """Do heavy discounts correlate with more or less revenue?"""
    return stats.discount_bands(session)


@router.get("/pareto")
def get_pareto(session: Session = Depends(get_db)):
    """How concentrated is revenue in the top customer tier?"""
    return stats.pareto_share(session)


# ─── SELLERS ─────────────────────────────────────────────────────────────────

@router.get("/top-sellers")
def get_top_sellers(
    limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_db),
):
    """Who are the top revenue generators? (legacy — see seller-performance)"""
    return stats.top_sellers(session, limit=limit)


@router.get("/seller-performance")
def get_seller_performance(
    limit: int = Query(default=50, ge=10, le=200),
    session: Session = Depends(get_db),
):
    """Which sellers have quality problems (high return rate or low rating)?"""
    return stats.seller_performance(session, limit=limit)


# ─── OPERATIONS ──────────────────────────────────────────────────────────────

@router.get("/operations-breakdown")
def get_operations_breakdown(session: Session = Depends(get_db)):
    """Where are delays and returns concentrated (category, city, payment, shipping days)?"""
    return stats.operations_breakdown(session)
