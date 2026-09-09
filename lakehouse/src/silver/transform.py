"""Silver layer — cleaned, validated, standardized entities.

Contract (see docs/lakehouse.md):
- One table per OLTP entity: customers / sellers / products / inventory /
  orders / order_items. Same grains and business keys as
  ``docs/business-model.md`` §2 — Silver never redefines the domain.
- All Bronze Title-Case enums are normalized here (``In Transit`` →
  ``IN TRANSIT``); trimming; typing. Business *grouping* logic (mode city,
  latest-price snapshots) lives in exactly one place — this layer — so Gold
  and the API can never diverge.
- Rows failing validation never reach Silver (fail-fast via quality/runner.py).

Like Bronze, cluster bodies are specified as SQL in comments; the pure
helpers below encode the same rules and are unit-tested locally.
"""

from __future__ import annotations

#: Contract enums (business-model §2–§3). Single source for Python + SQL + docs.
DELIVERY_STATUSES: tuple[str, ...] = ("IN TRANSIT", "DELIVERED", "DELAYED", "RETURNED")
PAYMENT_METHODS: tuple[str, ...] = ("UPI", "Credit Card", "Debit Card", "Cash on Delivery")
DEVICES: tuple[str, ...] = ("Mobile App", "Web", "Tablet")
CATEGORIES: tuple[str, ...] = ("Electronics", "Home", "Sports", "Beauty", "Clothing")

#: Money invariant tolerance — business-model §6 (±₹5.00; source round-trip max ≈₹3.99).
FINAL_PRICE_TOLERANCE = 5.00

#: Estimated unit cost factor — business-model §4. No COGS in source;
#: every margin figure derived from this MUST be labelled "estimated".
EST_UNIT_COST_FACTOR = 0.65


def normalize_delivery_status(value: str) -> str:
    """Normalize a source delivery status to its contract value.

    Raises ValueError on unknown input — fail fast, never coerce silently.
    """
    normalized = value.strip().upper()
    if normalized not in DELIVERY_STATUSES:
        raise ValueError(f"unknown delivery_status {value!r}; expected one of {list(DELIVERY_STATUSES)}")
    return normalized


def final_price_ok(unit_price: float, quantity: int, discount_pct: float, final_price: float) -> bool:
    """Money invariant: final_price ≈ unit_price × qty × (1 − discount/100)."""
    expected = round(unit_price * quantity * (1 - discount_pct / 100), 2)
    return abs(final_price - expected) <= FINAL_PRICE_TOLERANCE


def estimated_margin(unit_price: float, quantity: int, final_price: float) -> float:
    """Estimated gross margin per line. Label every consumer 'estimated' (§4)."""
    return round(final_price - EST_UNIT_COST_FACTOR * unit_price * quantity, 2)


def trim_record(record: dict) -> dict:
    """Strip surrounding whitespace from all TEXT fields (staging parity)."""
    return {k: (v.strip() if isinstance(v, str) else v) for k, v in record.items()}


# --- Silver build spec (one Spark task per entity, Databricks) -----------------
# s_customers : mode(location) per user_id, ties → max(purchase_date); first_purchase_date = min(date)
# s_sellers   : latest seller_rating per seller_id at max(purchase_date)
# s_products  : latest price/rating/review_count per product_id at max(purchase_date)
# s_inventory : distinct (product_id, purchase_date, stock), last-wins on same-day dupes
# s_orders    : 1:1 with Bronze rows; delivery_status normalized; deterministic row surrogate
# s_order_items: 1:1 with s_orders via shared surrogate; seller_rating_at_sale preserved
# Each task: read bronze.raw_purchases → transform → quality gate → merge into silver.<entity>.
