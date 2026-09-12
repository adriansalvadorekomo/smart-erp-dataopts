#!/usr/bin/env python3
"""Phase 8 — Churn feasibility probe (negative result, kept for the record).

Question: can K11 churn (no order in trailing 90 days) be predicted from
customer history? Answer: NO — PR-AUC = base rate, ROC-AUC = 0.50.

Why (mechanism): purchase arrivals look memoryless (constant-rate,
history-independent), so P(no purchase in next 90d) is flat across customers.
Recency/frequency cannot help by construction. See docs/decisions.md ADR-9.

Usage:
    PGHOST=... PGUSER=... PGDATABASE=smart uv run python ml/churn_feasibility.py
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

SQL = """
WITH hist AS (
  SELECT customer_id,
         COUNT(*) AS n_orders,
         MIN(order_date) AS first_d,
         MAX(order_date) AS last_d,
         SUM(oi.final_price) AS revenue,
         AVG(CASE WHEN o.delivery_status = 'RETURNED' THEN 1.0 ELSE 0 END) AS ret_rate,
         AVG(oi.discount_pct) AS avg_disc
  FROM public.orders o JOIN public.order_items oi USING (order_id)
  WHERE o.order_date <= DATE '2025-12-31'
  GROUP BY customer_id
),
gaps AS (
  SELECT customer_id, AVG(gap_d) AS avg_gap
  FROM (SELECT customer_id,
               order_date - LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date) AS gap_d
        FROM (SELECT DISTINCT customer_id, order_date FROM public.orders
              WHERE order_date <= DATE '2025-12-31') t) g
  WHERE gap_d IS NOT NULL GROUP BY customer_id
),
lbl AS (
  SELECT DISTINCT customer_id, 1 AS churned FROM public.orders
  WHERE order_date > DATE '2025-12-31'
)
SELECT h.customer_id, h.n_orders, (DATE '2025-12-31' - h.first_d) AS tenure,
       (DATE '2025-12-31' - h.last_d) AS recency, COALESCE(g.avg_gap, -1) AS avg_gap,
       h.revenue, h.ret_rate, h.avg_disc,
       CASE WHEN l.customer_id IS NULL THEN 1 ELSE 0 END AS churned
FROM hist h LEFT JOIN gaps g USING (customer_id) LEFT JOIN lbl l USING (customer_id)
"""


def main() -> int:
    import numpy as np
    import pandas as pd
    from backend.app.core.config import get_settings
    from sqlalchemy import create_engine, text
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import average_precision_score, roc_auc_score
    from sklearn.model_selection import train_test_split

    t0 = time.time()
    df = pd.read_sql(text(SQL), create_engine(get_settings().dsn))
    print(f"extract: {len(df):,} customers in {time.time()-t0:.1f}s, "
          f"churn rate {df['churned'].mean():.3f}")
    X = df[["n_orders", "tenure", "recency", "avg_gap", "revenue", "ret_rate", "avg_disc"]].fillna(-1).astype(float)
    y = df["churned"].astype(int)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=42)
    for name, model in {
        "logreg": LogisticRegression(max_iter=1000, class_weight="balanced"),
        "forest": RandomForestClassifier(n_estimators=200, min_samples_leaf=50,
                                         class_weight="balanced_subsample", n_jobs=-1,
                                         random_state=42),
    }.items():
        model.fit(Xtr, ytr)
        proba = model.predict_proba(Xte)[:, 1]
        print(f"{name}: PR-AUC={average_precision_score(yte, proba):.4f} "
              f"ROC-AUC={roc_auc_score(yte, proba):.4f} (base rate {yte.mean():.4f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
