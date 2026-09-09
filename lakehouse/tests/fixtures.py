"""Shared fixtures for lakehouse unit tests (stdlib unittest, no cluster needed)."""

GOOD_ITEM = {
    "order_id": 1,
    "product_id": "P1",
    "seller_id": "S1",
    "quantity": 1,
    "unit_price": 1000.00,
    "discount_pct": 10.0,
    "final_price": 900.00,
}

GOOD_ORDER = {
    "order_id": 1,
    "customer_id": "U1",
    "order_date": "2025-06-15",
    "delivery_status": "DELIVERED",
    "payment_method": "UPI",
    "device": "Mobile App",
}

BRONZE_COLUMNS = [
    "user_id", "product_id", "category", "subcategory", "brand",
    "price", "discount", "final_price", "rating", "review_count",
    "stock", "seller_id", "seller_rating", "purchase_date",
    "shipping_time_days", "location", "device", "payment_method",
    "delivery_status",
]
