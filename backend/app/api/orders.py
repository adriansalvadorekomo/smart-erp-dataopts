"""Orders router — thin HTTP over services/orders.py (all rules live there)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.db import get_db
from backend.app.models.entities import Order, OrderItem
from backend.app.schemas.orders import OrderCreate, OrderRead, StatusUpdate
from backend.app.services.orders import (
    Conflict,
    NotFound,
    create_order,
    get_order,
    transition_status,
)

router = APIRouter(prefix="/orders", tags=["orders"])


def _to_read(order: Order, session: Session) -> OrderRead:
    from backend.app.schemas.orders import OrderItemRead

    items = session.execute(
        select(OrderItem).where(OrderItem.order_id == order.order_id)
    ).scalars().all()
    data = OrderRead.model_validate(order)
    data.items = [OrderItemRead.model_validate(i) for i in items]
    return data


@router.post("", response_model=OrderRead, status_code=201)
def post_order(payload: OrderCreate, session: Session = Depends(get_db)):
    try:
        order = create_order(session, payload)
    except NotFound as e:
        session.rollback()
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Conflict as e:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from e
    return _to_read(order, session)


@router.get("/{order_id}", response_model=OrderRead)
def read_order(order_id: int, session: Session = Depends(get_db)):
    try:
        order = get_order(session, order_id)
    except NotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return _to_read(order, session)


@router.patch("/{order_id}/status", response_model=OrderRead)
def patch_status(order_id: int, payload: StatusUpdate, session: Session = Depends(get_db)):
    try:
        order = transition_status(session, order_id, payload.delivery_status)
    except NotFound as e:
        session.rollback()
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Conflict as e:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from e
    return _to_read(order, session)
