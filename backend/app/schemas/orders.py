"""Request/response contracts for the orders API (Phase 4 core)."""
from __future__ import annotations

import datetime
from typing import Literal

from pydantic import BaseModel, Field

PaymentMethod = Literal["UPI", "Credit Card", "Debit Card", "Cash on Delivery"]
Device = Literal["Mobile App", "Web", "Tablet"]
DeliveryStatus = Literal["IN TRANSIT", "DELIVERED", "DELAYED", "RETURNED"]


class OrderItemCreate(BaseModel):
    product_id: str
    seller_id: str
    quantity: int = Field(default=1, ge=1)
    unit_price: float = Field(gt=0)
    discount_pct: float = Field(default=0, ge=0, le=70)


class OrderCreate(BaseModel):
    customer_id: str
    order_date: datetime.date = Field(default_factory=datetime.date.today)
    ship_to_city: str
    payment_method: PaymentMethod
    device: Device
    shipping_time_days: int = Field(ge=1, le=6)
    items: list[OrderItemCreate] = Field(min_length=1)


class StatusUpdate(BaseModel):
    delivery_status: DeliveryStatus


class OrderItemRead(BaseModel):
    order_item_id: int
    order_id: int
    product_id: str
    seller_id: str
    quantity: int
    unit_price: float
    discount_pct: float
    final_price: float
    seller_rating_at_sale: float

    model_config = {"from_attributes": True}


class OrderRead(BaseModel):
    order_id: int
    customer_id: str
    order_date: datetime.date
    ship_to_city: str
    payment_method: str
    device: str
    delivery_status: str
    shipping_time_days: int
    items: list[OrderItemRead] = []

    model_config = {"from_attributes": True}
