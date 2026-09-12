#!/usr/bin/env python3
"""Phase 8 — Local proof for K12 return propensity (no cluster needed).

Runs the SAME modeling design as lakehouse/notebooks/05_train_return_propensity.py
(point-in-time features, train-only target encoding, time split, logreg vs
forest on PR-AUC) against the OLTP mirror (public.* has the same grains as
silver.*). Expected cluster behavior: same code path, same metric order.

Usage:
    PGHOST=... PGUSER=... PGDATABASE=smart uv run python ml/local_proof.py
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pandas as pd
from backend.app.core.config import get_settings
from sqlalchemy import create_engine, text

SPLIT = "2025-10-01"
ALPHA = 50.0

FEATURE_SQL = """
WITH resolved AS (
  SELECT o.order_id, o.customer_id, o.order_date, o.payment_method, o.device,
         oi.product_id, oi.quantity, oi.unit_price, oi.discount_pct,
         p.category, p.brand,
         CASE WHEN o.delivery_status = 'RETURNED' THEN 1 ELSE 0 END AS is_returned
  FROM public.orders o
  JOIN public.order_items oi ON oi.order_id = o.order_id
  JOIN public.products p ON p.product_id = oi.product_id
  WHERE o.delivery_status IN ('DELIVERED', 'DELAYED', 'RETURNED')
),
daily AS (
  SELECT customer_id, order_date AS d, COUNT(*) AS n_orders,
         SUM(CASE WHEN delivery_status = 'RETURNED' THEN 1 ELSE 0 END) AS n_returns
  FROM public.orders
  GROUP BY customer_id, order_date
),
hist AS (
  SELECT customer_id, d,
         COALESCE(SUM(n_orders) OVER w, 0) AS prior_orders,
         COALESCE(SUM(n_returns) OVER w, 0) AS prior_returns,
         MAX(d) OVER w AS last_order_date
  FROM daily
  WINDOW w AS (PARTITION BY customer_id ORDER BY d
               ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)
)
SELECT r.*,
       COALESCE(h.prior_orders, 0) AS prior_orders,
       COALESCE(h.prior_returns, 0) AS prior_returns,
       CASE WHEN COALESCE(h.prior_orders, 0) > 0
            THEN h.prior_returns::float / h.prior_orders ELSE 0.0 END AS prior_return_rate,
       (r.order_date - c.first_purchase_date) AS tenure_days,
       COALESCE((r.order_date - h.last_order_date), (r.order_date - c.first_purchase_date)) AS days_since_last
FROM resolved r
JOIN public.customers c ON c.customer_id = r.customer_id
LEFT JOIN hist h ON h.customer_id = r.customer_id AND h.d = r.order_date
"""


def main() -> int:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import average_precision_score, roc_auc_score

    settings = get_settings()
    engine = create_engine(settings.dsn)
    t0 = time.time()
    with engine.connect() as conn:
        df = pd.read_sql(text(FEATURE_SQL), conn)
    print(f"extract: {len(df):,} rows in {time.time()-t0:.1f}s  (pos rate {df['is_returned'].mean():.4f})")

    train = df[df["order_date"].astype(str) < SPLIT].copy()
    test = df[df["order_date"].astype(str) >= SPLIT].copy()
    print(f"train: {len(train):,}  test: {len(test):,}")

    gmean = train["is_returned"].mean()
    for col in ("category", "brand"):
        agg = train.groupby(col)["is_returned"].agg(["sum", "count"])
        smooth = (agg["sum"] + ALPHA * gmean) / (agg["count"] + ALPHA)
        train[f"{col}_rate"] = train[col].map(smooth)
        test[f"{col}_rate"] = test[col].map(smooth).fillna(gmean)

    for part in (train, test):
        part["log_price"] = np.log1p(part["unit_price"].astype(float))
        part["month"] = pd.to_datetime(part["order_date"]).dt.month

    num = ["prior_orders", "prior_returns", "prior_return_rate", "tenure_days",
           "days_since_last", "discount_pct", "log_price", "quantity",
           "category_rate", "brand_rate", "month"]
    train_enc = pd.get_dummies(train, columns=["payment_method", "device"])
    test_enc = pd.get_dummies(test, columns=["payment_method", "device"])
    for c in list(train_enc.columns):
        if c.startswith(("payment_method_", "device_")) and c not in test_enc:
            test_enc[c] = 0
    feats = num + [c for c in train_enc.columns if c.startswith(("payment_method_", "device_"))]
    X_train, y_train = train_enc[feats].astype(float), train_enc["is_returned"].astype(int)
    X_test, y_test = test_enc[feats].astype(float), test_enc["is_returned"].astype(int)

    for name, model in {
        "logreg": LogisticRegression(max_iter=1000, class_weight="balanced"),
        "forest": RandomForestClassifier(n_estimators=300, min_samples_leaf=50,
                                         class_weight="balanced_subsample", n_jobs=-1,
                                         random_state=42),
    }.items():
        t0 = time.time()
        model.fit(X_train, y_train)
        proba = model.predict_proba(X_test)[:, 1]
        print(f"{name}: PR-AUC={average_precision_score(y_test, proba):.4f} "
              f"ROC-AUC={roc_auc_score(y_test, proba):.4f} "
              f"(fit+score {time.time()-t0:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
