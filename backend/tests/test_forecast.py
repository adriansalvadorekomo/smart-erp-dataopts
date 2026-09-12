"""Forecast pipeline contract tests (fast synthetic series + roundtrip)."""
from __future__ import annotations

import datetime

import pandas as pd
from sqlalchemy import text


def _synthetic(n_days: int = 120) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=n_days, freq="D")
    trend = 1000 + 5 * (dates - dates[0]).days
    weekly = 100 * (dates.dayofweek >= 5).astype(float)
    return pd.DataFrame({"date": dates, "revenue": trend + weekly})


def test_train_and_forecast_shapes():
    from backend.app.services import forecast as fc

    df = _synthetic()
    rows = fc.forecast_next(df, horizon=7)
    assert len(rows) == 7
    assert [r["horizon_d"] for r in rows] == list(range(1, 8))
    assert rows[0]["target_date"] == (df["date"].max() + pd.Timedelta(days=1)).date()
    for r in rows:
        assert r["rf"] >= 0 and r["prophet"] >= 0
    # trend learned: far-horizon above early history on a rising series
    assert rows[-1]["rf"] > df["revenue"].iloc[0]


def test_refresh_roundtrip_and_endpoint(client, session):
    from backend.app.services import forecast as fc

    day = datetime.date(2024, 1, 1)
    session.execute(
        text(
            "INSERT INTO public.customers (customer_id, home_city, first_purchase_date)"
            " VALUES ('U_FC', 'Delhi', '2024-01-01') ON CONFLICT DO NOTHING"
        )
    )
    session.execute(
        text(
            "INSERT INTO public.sellers (seller_id, current_rating)"
            " VALUES ('S_FC', 4.0) ON CONFLICT DO NOTHING"
        )
    )
    session.execute(
        text(
            "INSERT INTO public.products (product_id, category, subcategory, brand,"
            " current_price, product_rating, review_count)"
            " VALUES ('P_FC', 'Home', 'Decor', 'FC', 100.00, 4.0, 1)"
            " ON CONFLICT DO NOTHING"
        )
    )
    session.execute(
        text("DELETE FROM public.order_items WHERE order_id >= 900000")
    )
    session.execute(text("DELETE FROM public.orders WHERE order_id >= 900000"))
    for i in range(70):
        d = (day + datetime.timedelta(days=i)).isoformat()
        session.execute(
            text(
                "INSERT INTO public.orders (order_id, customer_id, order_date, ship_to_city,"
                " payment_method, device, delivery_status, shipping_time_days)"
                f" VALUES ({900000 + i}, 'U_FC', '{d}', 'Delhi', 'UPI', 'Web', 'DELIVERED', 2)"
            )
        )
        session.execute(
            text(
                "INSERT INTO public.order_items (order_id, product_id, seller_id, quantity,"
                " unit_price, discount_pct, final_price, seller_rating_at_sale)"
                f" VALUES ({900000 + i}, 'P_FC', 'S_FC', 1, 100.00, 0, 100.00, 4.0)"
            )
        )
    session.commit()

    try:
        result = fc.refresh(session, horizon=7)
        assert result["rows"] == 14
        n = session.execute(text("SELECT count(*) FROM public.revenue_forecasts")).scalar()
        assert n == 14
        # idempotent rerun
        fc.refresh(session, horizon=7)
        n2 = session.execute(text("SELECT count(*) FROM public.revenue_forecasts")).scalar()
        assert n2 == 14

        r = client.get("/stats/forecast", params={"trailing": 30})
        assert r.status_code == 200
        body = r.json()
        assert len(body["actuals"]) == 30
        assert len(body["forecasts"]["rf"]) == 7
        assert len(body["forecasts"]["prophet"]) == 7
        assert body["asof"] == "2024-03-10"
    finally:
        session.execute(text("DELETE FROM public.revenue_forecasts"))
        session.execute(text("DELETE FROM public.order_items WHERE order_id >= 900000"))
        session.execute(text("DELETE FROM public.orders WHERE order_id >= 900000"))
        for t in ("public.customers", "public.sellers", "public.products"):
            pk = {"public.customers": "customer_id", "public.sellers": "seller_id",
                  "public.products": "product_id"}[t]
            val = {"public.customers": "U_FC", "public.sellers": "S_FC",
                   "public.products": "P_FC"}[t]
            session.execute(text(f"DELETE FROM {t} WHERE {pk} = '{val}'"))
        session.commit()
