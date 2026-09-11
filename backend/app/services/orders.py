"""Orders service — the Phase 4 contract (business-model §3–§4).

Rules enforced here (in ONE transaction per operation):
- Money: final_price is SERVER-computed, never client-supplied.
- Lifecycle: IN TRANSIT → {DELIVERED, DELAYED, RETURNED}; terminal states immutable.
- Stock: each line decrements the product's latest inventory snapshot atomically
  (row lock + same transaction); insufficient stock aborts the whole order.
- Audit: every mutation writes audit_log rows in the same transaction.
"""
from __future__ import annotations

import datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models.entities import (
    TERMINAL_STATUSES,
    AuditLog,
    Customer,
    Inventory,
    Order,
    OrderItem,
    Product,
    Seller,
)


class OrderError(Exception):
    """Domain error — mapped to an HTTP status by the API layer."""


class NotFound(OrderError):
    pass


class Conflict(OrderError):
    """Terminal-state mutation, insufficient stock, or missing reference."""


def line_final_price(unit_price: Decimal, quantity: int, discount_pct: Decimal) -> Decimal:
    """final_price = unit_price × qty × (1 − discount/100), HALF_UP to match PG round()."""
    return (unit_price * quantity * (Decimal(1) - discount_pct / Decimal(100))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def _audit(
    session: Session,
    *,
    table: str,
    row_pk: str,
    action: str,
    details: dict | None = None,
    actor: str = "api",
) -> None:
    session.add(
        AuditLog(table_name=table, row_pk=row_pk, action=action, details=details, actor=actor)
    )


def create_order(session: Session, payload, actor: str = "api") -> Order:
    """Create an order with its lines; decrement inventory; audit. All atomic."""
    customer = session.get(Customer, payload.customer_id)
    if customer is None:
        raise NotFound(f"customer {payload.customer_id!r} does not exist")

    today = payload.order_date
    order = Order(
        customer_id=payload.customer_id,
        order_date=today,
        ship_to_city=payload.ship_to_city,
        payment_method=payload.payment_method,
        device=payload.device,
        delivery_status="IN TRANSIT",
        shipping_time_days=payload.shipping_time_days,
    )
    session.add(order)
    session.flush()  # order_id for FK pairing + audit

    for line in payload.items:
        product = session.get(Product, line.product_id)
        if product is None:
            raise NotFound(f"product {line.product_id!r} does not exist")
        seller = session.get(Seller, line.seller_id)
        if seller is None:
            raise NotFound(f"seller {line.seller_id!r} does not exist")

        unit = Decimal(str(line.unit_price))
        disc = Decimal(str(line.discount_pct))
        final = line_final_price(unit, line.quantity, disc)

        session.add(
            OrderItem(
                order_id=order.order_id,
                product_id=line.product_id,
                seller_id=line.seller_id,
                quantity=line.quantity,
                unit_price=unit,
                discount_pct=disc,
                final_price=final,
                seller_rating_at_sale=seller.current_rating,
            )
        )
        _decrement_stock(session, product_id=line.product_id, qty=line.quantity, on=today)

    session.flush()
    _audit(
        session,
        table="orders",
        row_pk=str(order.order_id),
        action="insert",
        details={"customer_id": order.customer_id, "lines": len(payload.items)},
        actor=actor,
    )
    session.commit()
    session.refresh(order)
    return order


def _decrement_stock(session: Session, *, product_id: str, qty: int, on: datetime.date) -> None:
    """Decrement the latest snapshot for (product); today's row absorbs the change.

    Row-level lock (FOR UPDATE) serializes concurrent decrements — no lost updates.
    """
    latest = session.execute(
        select(Inventory)
        .where(Inventory.product_id == product_id)
        .order_by(Inventory.snapshot_date.desc())
        .limit(1)
        .with_for_update()
    ).scalar_one_or_none()

    if latest is None:
        raise Conflict(f"no inventory snapshot for product {product_id!r}")

    if latest.snapshot_date == on:
        target = latest
        new_stock = latest.stock - qty
    else:
        if latest.stock < qty:
            raise Conflict(f"insufficient stock for product {product_id!r}")
        target = Inventory(product_id=product_id, snapshot_date=on, stock=latest.stock)
        session.add(target)
        new_stock = latest.stock - qty

    if new_stock < 0:
        raise Conflict(f"insufficient stock for product {product_id!r}")
    target.stock = new_stock
    _audit(
        session,
        table="inventory",
        row_pk=f"{product_id}/{target.snapshot_date.isoformat()}",
        action="update",
        details={"product_id": product_id, "stock": new_stock, "decrement": qty},
    )


def transition_status(
    session: Session, order_id: int, to_status: str, actor: str = "api"
) -> Order:
    """Move IN TRANSIT → terminal. Terminal states are immutable (409 on violation)."""
    order = session.get(Order, order_id)
    if order is None:
        raise NotFound(f"order {order_id} does not exist")
    if order.delivery_status in TERMINAL_STATUSES:
        raise Conflict(
            f"order {order_id} is terminal ({order.delivery_status}) — immutable"
        )
    if to_status == "IN TRANSIT" or to_status not in TERMINAL_STATUSES:
        raise Conflict(
            f"illegal transition {order.delivery_status} → {to_status}; "
            "only IN TRANSIT → {DELIVERED, DELAYED, RETURNED}"
        )
    from_status = order.delivery_status
    order.delivery_status = to_status
    order.updated_at = func.now()
    _audit(
        session,
        table="orders",
        row_pk=str(order_id),
        action="update",
        details={"from": from_status, "to": to_status},
        actor=actor,
    )
    session.commit()
    session.refresh(order)
    return order


def get_order(session: Session, order_id: int) -> Order:
    order = session.get(Order, order_id)
    if order is None:
        raise NotFound(f"order {order_id} does not exist")
    return order
