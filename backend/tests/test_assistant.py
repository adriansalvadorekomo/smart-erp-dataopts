"""Assistant contract tests — answers are computed, cited, never invented."""
from __future__ import annotations

from backend.tests.conftest import today


def _seed_order(client, order_date: str | None = None):
    r = client.post(
        "/orders",
        json={
            "customer_id": "U_TEST",
            "order_date": order_date or today(),
            "ship_to_city": "Delhi",
            "payment_method": "UPI",
            "device": "Web",
            "shipping_time_days": 2,
            "items": [
                {
                    "product_id": "P_TEST",
                    "seller_id": "S_TEST",
                    "quantity": 1,
                    "unit_price": 1000.00,
                    "discount_pct": 10.0,
                }
            ],
        },
    )
    assert r.status_code == 201
    return r.json()["order_id"]


def _ask(client, question: str) -> dict:
    r = client.post("/ai/ask", json={"question": question})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"answer", "intent", "sources"}
    return body


def test_revenue_aov_return_rates(client):
    _seed_order(client)
    body = _ask(client, "What is total revenue?")
    assert body["intent"] == "revenue"
    assert "₹900.00" in body["answer"]
    assert body["sources"]

    body = _ask(client, "average order value?")
    assert body["intent"] == "aov" and "₹900.00" in body["answer"]

    body = _ask(client, "return rate?")
    assert body["intent"] == "return_rate" and "0.0%" in body["answer"]


def test_top_sellers_and_stock(client):
    _seed_order(client)
    body = _ask(client, "top 3 sellers?")
    assert body["intent"] == "top_sellers" and "S_TEST" in body["answer"]

    body = _ask(client, "which products need reordering?")
    assert body["intent"] == "stock_critical" and "0 products" in body["answer"]


def test_order_status_and_unknown(client):
    order_id = _seed_order(client)
    body = _ask(client, f"status of order {order_id}?")
    assert body["intent"] == "order_status" and "IN TRANSIT" in body["answer"]

    body = _ask(client, f"status of order 999999999?")
    assert "does not exist" in body["answer"]

    body = _ask(client, "tell me a joke about the moon")
    assert body["intent"] == "unknown"
    assert "won't guess" in body["answer"]


def test_forecast_and_dq(client):
    _seed_order(client, order_date="2024-04-01")  # in-window: keeps the R7 gate green
    body = _ask(client, "forecast revenue next month")
    assert body["intent"] in ("forecast",)
    assert "forecast" in body["answer"].lower()

    body = _ask(client, "is data quality green?")
    assert body["intent"] == "dq" and "green" in body["answer"].lower()


def test_validation(client):
    assert client.post("/ai/ask", json={"question": ""}).status_code == 422
    assert client.post("/ai/ask", json={}).status_code == 422
