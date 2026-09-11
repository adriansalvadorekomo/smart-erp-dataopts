"""Read-only stats router — dashboard aggregates (business-model §5)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.core.db import get_db
from backend.app.services import stats

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview")
def get_overview(session: Session = Depends(get_db)):
    return stats.overview(session)


@router.get("/revenue-trend")
def get_revenue_trend(
    days: int = Query(default=30, ge=7, le=365),
    session: Session = Depends(get_db),
):
    return stats.revenue_trend(session, days=days)


@router.get("/revenue-by-category")
def get_revenue_by_category(session: Session = Depends(get_db)):
    return stats.revenue_by_category(session)


@router.get("/discount-bands")
def get_discount_bands(session: Session = Depends(get_db)):
    return stats.discount_bands(session)


@router.get("/top-sellers")
def get_top_sellers(
    limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_db),
):
    return stats.top_sellers(session, limit=limit)


@router.get("/pareto")
def get_pareto(session: Session = Depends(get_db)):
    return stats.pareto_share(session)


@router.get("/dq-checks")
def get_dq_checks(session: Session = Depends(get_db)):
    return stats.dq_checks(session)
