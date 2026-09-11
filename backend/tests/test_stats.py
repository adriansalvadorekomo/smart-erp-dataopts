"""Stats endpoint contract tests."""
from __future__ import annotations

from backend.tests.conftest import today


def _order(client, order_date: str | None = None):
    return client.post(
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


def test_overview_shape_and_values(client):
    _order(client)
    r = client.get("/stats/overview")
    assert r.status_code == 200
    body = r.json()
    for key in (
        "total_orders", "revenue", "aov", "avg_discount_pct",
        "return_rate", "delayed_rate", "in_transit", "stock_critical", "by_status",
    ):
        assert key in body, key
    assert body["total_orders"] >= 1
    assert body["revenue"] >= 900.00
    assert body["aov"] == body["revenue"] / body["total_orders"]
    assert body["by_status"].get("IN TRANSIT", 0) >= 1
    assert 0.0 <= body["return_rate"] <= 1.0


def test_revenue_trend_shape(client):
    _order(client)
    r = client.get("/stats/revenue-trend", params={"days": 30})
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list) and rows
    assert {"date", "orders", "revenue"} <= set(rows[0])
    assert rows[-1]["revenue"] >= 900.00


def test_revenue_by_category(client):
    _order(client)
    r = client.get("/stats/revenue-by-category")
    assert r.status_code == 200
    rows = {row["category"]: row for row in r.json()}
    assert rows["Electronics"]["revenue"] >= 900.00
    assert rows["Electronics"]["lines"] >= 1


def test_trend_days_bounds(client):
    assert client.get("/stats/revenue-trend", params={"days": 3}).status_code == 422
    assert client.get("/stats/revenue-trend", params={"days": 400}).status_code == 422


def test_gold_kpi_endpoints(client):
    # In-window date so the R7 gate stays green over test data.
    _order(client, order_date="2024-04-01")

    bands = client.get("/stats/discount-bands").json()
    assert {b["band"] for b in bands} <= {"0–10", "10–30", "30–50", "50–70"}
    assert sum(b["lines"] for b in bands) >= 1

    sellers = client.get("/stats/top-sellers").json()
    assert sellers and sellers[0]["seller_id"] == "S_TEST"
    assert sellers[0]["revenue"] >= 900.00

    pareto = client.get("/stats/pareto").json()
    assert 0.0 < pareto["top20_share"] <= 1.0

    checks = {c["rule"]: c["violations"] for c in client.get("/stats/dq-checks").json()}
    assert len(checks) == 11
    assert all(v == 0 for v in checks.values()), checks


def test_business_endpoints(client):
    _order(client, order_date="2024-04-01")

    sellers = client.get("/stats/seller-performance").json()
    assert sellers and sellers[0]["seller_id"] == "S_TEST"
    for key in ("revenue", "lines", "avg_rating", "delayed_rate", "return_rate"):
        assert key in sellers[0], key
    assert sellers[0]["delayed_rate"] == 0.0  # single IN TRANSIT line

    trend = client.get("/stats/category-trend", params={"months": 12}).json()
    assert trend and {"month", "category", "revenue"} <= set(trend[0])
    assert any(r["category"] == "Electronics" for r in trend)

    critical = client.get("/stats/stock-critical").json()
    assert isinstance(critical, list)  # fixture stock is 100 → empty here

    cities = {c["city"]: c for c in client.get("/stats/city-performance").json()}
    assert cities["Delhi"]["orders"] >= 1
    assert cities["Delhi"]["revenue"] >= 900.00
