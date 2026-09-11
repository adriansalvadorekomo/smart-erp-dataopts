"""Orders core contract tests (business-model §3–§4)."""
from __future__ import annotations

from sqlalchemy import text

from backend.tests.conftest import today


def _payload(**overrides):
    body = {
        "customer_id": "U_TEST",
        "order_date": today(),
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
    }
    body.update(overrides)
    return body


def test_create_computes_final_price_and_decrements_stock(client, session):
    r = client.post("/orders", json=_payload())
    assert r.status_code == 201, r.text
    order = r.json()
    assert order["delivery_status"] == "IN TRANSIT"
    assert order["items"][0]["final_price"] == 900.00  # 1000 × (1 − 10%)

    stock = session.execute(
        text(
            "SELECT stock FROM public.inventory WHERE product_id = 'P_TEST'"
            " ORDER BY snapshot_date DESC LIMIT 1"
        )
    ).scalar()
    assert stock == 99

    audits = session.execute(text("SELECT count(*) FROM public.audit_log")).scalar()
    assert audits >= 2  # order insert + inventory update


def test_lifecycle_forward_and_terminal_immutable(client):
    order_id = client.post("/orders", json=_payload()).json()["order_id"]

    r = client.patch(f"/orders/{order_id}/status", json={"delivery_status": "DELIVERED"})
    assert r.status_code == 200
    assert r.json()["delivery_status"] == "DELIVERED"

    r = client.patch(f"/orders/{order_id}/status", json={"delivery_status": "RETURNED"})
    assert r.status_code == 409  # terminal → immutable


def test_illegal_transition_rejected(client):
    order_id = client.post("/orders", json=_payload()).json()["order_id"]
    r = client.patch(f"/orders/{order_id}/status", json={"delivery_status": "IN TRANSIT"})
    assert r.status_code == 409


def test_unknown_references_404(client):
    r = client.post("/orders", json=_payload(customer_id="U_NOPE"))
    assert r.status_code == 404
    r = client.get("/orders/999999999")
    assert r.status_code == 404


def test_validation_rejects_bad_money(client):
    bad = _payload()
    bad["items"][0]["discount_pct"] = 80  # max 70
    assert client.post("/orders", json=bad).status_code == 422


def test_insufficient_stock_409(client, session):
    session.execute(
        text("UPDATE public.inventory SET stock = 0 WHERE product_id = 'P_TEST'")
    )
    session.commit()
    payload = _payload()
    payload["items"][0]["quantity"] = 2
    r = client.post("/orders", json=payload)
    assert r.status_code == 409


def test_multi_line_order(client):
    payload = _payload()
    payload["items"].append(
        {
            "product_id": "P_TEST",
            "seller_id": "S_TEST",
            "quantity": 2,
            "unit_price": 500.00,
            "discount_pct": 0,
        }
    )
    r = client.post("/orders", json=payload)
    assert r.status_code == 201
    totals = sorted(i["final_price"] for i in r.json()["items"])
    assert totals == [900.00, 1000.00]


def test_list_orders_with_status_filter(client):
    order_id = client.post("/orders", json=_payload()).json()["order_id"]

    r = client.get("/orders")
    assert r.status_code == 200
    assert any(o["order_id"] == order_id for o in r.json())

    r = client.get("/orders", params={"delivery_status": "DELIVERED"})
    assert r.status_code == 200
    assert all(o["delivery_status"] == "DELIVERED" for o in r.json())

    client.patch(f"/orders/{order_id}/status", json={"delivery_status": "DELIVERED"})
    r = client.get("/orders", params={"delivery_status": "DELIVERED"})
    assert any(o["order_id"] == order_id for o in r.json())
