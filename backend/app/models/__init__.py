"""ORM models (tables register on backend.app.core.db.Base)."""
from backend.app.models.entities import (  # noqa: F401
    AuditLog,
    Customer,
    Inventory,
    Order,
    OrderItem,
    Product,
    Seller,
)
