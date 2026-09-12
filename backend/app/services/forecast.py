"""Batch revenue forecasting (Phase 8 production leg).

Design (notebooks/04_forecasting.ipynb scoreboard, rolling 90d MAPE):
RF 3.38% ships; Prophet 3.96% rides as second opinion. Both train on the full
daily series and predict the next HORIZON days; results land in
public.revenue_forecasts (full refresh per model — UNIQUE(model, target_date)
makes reruns idempotent). Served read-only via GET /stats/forecast.
"""
from __future__ import annotations

import datetime
import logging

import numpy as np
import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models.entities import AuditLog, Order, OrderItem, RevenueForecast

HORIZON = 30
LAGS = [1, 2, 3, 7, 14, 21, 28]

log = logging.getLogger("smart_erp.forecast")


def daily_series(session: Session) -> pd.DataFrame:
    rows = session.execute(
        select(Order.order_date, func.sum(OrderItem.final_price))
        .join(OrderItem, OrderItem.order_id == Order.order_id)
        .group_by(Order.order_date)
        .order_by(Order.order_date)
    ).all()
    return pd.DataFrame(rows, columns=["date", "revenue"]).astype(
        {"date": "datetime64[ns]", "revenue": "float64"}
    )


def _features(s: pd.Series) -> tuple[np.ndarray, list[str]]:
    idx = pd.DatetimeIndex(s.index)
    X = pd.DataFrame(
        {f"lag{L}": s.shift(L).values for L in LAGS}
        | {
            "roll7": s.rolling(7).mean().values,
            "roll28": s.rolling(28).mean().values,
            "std7": s.rolling(7).std(ddof=0).fillna(0).values,
            "t": np.arange(len(s), dtype=float),
            "dow": idx.dayofweek.values.astype(float),
            "month": idx.month.values.astype(float),
            "doy": idx.dayofyear.values.astype(float),
        }
    ).iloc[28:]
    return X.to_numpy(), list(X.columns)


def train_rf(X: np.ndarray, y: np.ndarray):
    from sklearn.ensemble import RandomForestRegressor

    model = RandomForestRegressor(
        n_estimators=200, min_samples_leaf=10, n_jobs=-1, random_state=42
    )
    model.fit(X, y)
    return model


def train_prophet(dates: pd.DatetimeIndex, y: np.ndarray):
    import logging as _logging

    _logging.getLogger("cmdstanpy").disabled = True
    _logging.getLogger("prophet").disabled = True
    from prophet import Prophet

    model = Prophet(daily_seasonality=False, weekly_seasonality=True,
                    yearly_seasonality=True)
    model.fit(pd.DataFrame({"ds": dates, "y": y}))
    return model


def forecast_next(df: pd.DataFrame, horizon: int = HORIZON) -> list[dict]:
    """Iterative multi-step forecast from both models (RF feeds its own outputs)."""
    s = df.set_index("date")["revenue"].asfreq("D").ffill()
    X, _ = _features(s)
    y = s.iloc[28:].to_numpy()
    rf = train_rf(X, y)
    ph = train_prophet(s.index, s.to_numpy())

    ext_idx = list(s.index)
    ext_val = list(s.values)
    rows: list[dict] = []
    fut = pd.DataFrame({"ds": pd.date_range(s.index[-1] + pd.Timedelta(days=1),
                                            periods=horizon, freq="D")})
    ph_pred = iter(ph.predict(fut)["yhat"].tolist())
    for h in range(1, horizon + 1):
        step = pd.Series(ext_val, index=pd.DatetimeIndex(ext_idx))
        Xs, _ = _features(step)
        rf_hat = max(float(rf.predict(Xs[-1:])[0]), 0.0)
        rows.append({
            "target_date": (s.index[-1] + pd.Timedelta(days=h)).date(),
            "rf": rf_hat,
            "prophet": max(float(next(ph_pred)), 0.0),
            "horizon_d": h,
        })
        ext_idx.append(s.index[-1] + pd.Timedelta(days=h))
        ext_val.append(rf_hat)  # RF rolls on its own outputs; prophet is direct
    return rows


def refresh(session: Session, horizon: int = HORIZON, actor: str = "forecast-job") -> dict:
    """Retrain both models on all history; replace stored forecasts. Atomic."""
    df = daily_series(session)
    if len(df) < 60:
        raise ValueError(f"need ≥60 days of history, have {len(df)}")
    asof = df["date"].max().date()
    rows = forecast_next(df, horizon)
    session.query(RevenueForecast).delete()
    for r in rows:
        for model in ("rf", "prophet"):
            session.add(RevenueForecast(
                asof_date=asof, target_date=r["target_date"], model=model,
                horizon_d=r["horizon_d"], yhat=round(r[model], 2)))
    session.add(AuditLog(table_name="revenue_forecasts", row_pk=f"asof={asof}",
                         action="insert",
                         details={"models": ["rf", "prophet"], "horizon": horizon},
                         actor=actor))
    session.commit()
    log.info("forecast refresh asof=%s horizon=%d", asof, horizon)
    return {"asof": asof.isoformat(), "horizon": horizon, "rows": len(rows) * 2}


def read_forecast(session: Session, trailing: int = 90) -> dict:
    actual = daily_series(session).tail(trailing)
    stored = session.execute(
        select(RevenueForecast).order_by(RevenueForecast.target_date)
    ).scalars().all()
    by_model: dict[str, list] = {"rf": [], "prophet": []}
    asof = None
    for r in stored:
        asof = r.asof_date.isoformat()
        by_model[r.model].append({"date": r.target_date.isoformat(),
                                  "yhat": float(r.yhat)})
    return {
        "asof": asof,
        "actuals": [{"date": d.date().isoformat(), "revenue": float(v)}
                    for d, v in zip(actual["date"], actual["revenue"])],
        "forecasts": by_model,
    }
