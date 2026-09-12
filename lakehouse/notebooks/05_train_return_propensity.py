# Databricks notebook source
# Task: train_return_propensity — K12 P(return) per order (Phase 8, first model).
#
# Design (see docs/business-model.md K12; no-leakage rules below):
# - Grain: one row per ORDER. Label = 1 iff delivery_status = 'RETURNED'.
# - Censored labels: IN TRANSIT orders have unknown outcome — train ONLY on
#   resolved orders (DELIVERED/DELAYED/RETURNED); IN TRANSIT is the inference
#   population, never training data.
# - Point-in-time features: customer history counts outcomes on STRICTLY
#   earlier days (daily grain + 1-PRECEDING window), so same-day outcomes can
#   never leak. Category/brand rates are target-encoded on TRAIN only.
# - Time split (not random): train order_date < 2025-10-01, test after.
#   Metric: PR-AUC (average_precision) — 11.6% base rate makes accuracy lie.
# - Models: logistic regression vs random forest; best on test PR-AUC wins,
#   logged + registered in native MLflow; batch scores → gold table.
# Widgets: catalog, experiment.

# COMMAND ----------

dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("experiment", "smart-erp-return-propensity")

catalog = dbutils.widgets.get("catalog")
experiment = dbutils.widgets.get("experiment")

# COMMAND ----------

# MLflow native tracking (ADR-7). sklearn may be absent on some serverless
# images — install on the driver if needed (no-op when present).
import importlib, subprocess, sys  # noqa: E402

for pkg in ("scikit-learn", "pandas"):
    try:
        importlib.import_module("sklearn" if pkg == "scikit-learn" else "pandas")
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "-q", "install", pkg])

import mlflow  # noqa: E402
import mlflow.sklearn  # noqa: E402

mlflow.set_experiment(experiment)
mlflow.sklearn.autolog(log_models=True)
print(f"experiment: {experiment}")

# COMMAND ----------

# Resolved orders only — IN TRANSIT is censored, excluded from training.
spark.sql(f"""
CREATE OR REPLACE TEMP VIEW orders_resolved AS
SELECT o.order_id, o.customer_id, o.order_date, o.payment_method, o.device,
       oi.product_id, oi.quantity, oi.unit_price, oi.discount_pct,
       p.category, p.brand,
       CASE WHEN o.delivery_status = 'RETURNED' THEN 1 ELSE 0 END AS is_returned
FROM {catalog}.silver.orders o
JOIN {catalog}.silver.order_items oi ON oi.order_id = o.order_id
JOIN {catalog}.silver.products p ON p.product_id = oi.product_id
WHERE o.delivery_status IN ('DELIVERED', 'DELAYED', 'RETURNED')
""")

# Daily-grain customer history, then a strictly-earlier window: the 1-PRECEDING
# frame over daily rows excludes the order's own day entirely (no same-day
# outcome leakage, even for multi-order days).
spark.sql("""
CREATE OR REPLACE TEMP VIEW cust_hist AS
WITH daily AS (
  SELECT customer_id, order_date AS d,
         COUNT(*) AS n_orders,
         SUM(CASE WHEN delivery_status = 'RETURNED' THEN 1 ELSE 0 END) AS n_returns
  FROM {catalog}.silver.orders
  GROUP BY customer_id, order_date
)
SELECT customer_id, d,
       COALESCE(SUM(n_orders) OVER w, 0) AS prior_orders,
       COALESCE(SUM(n_returns) OVER w, 0) AS prior_returns,
       MAX(d) OVER w AS last_order_date
FROM daily
WINDOW w AS (PARTITION BY customer_id ORDER BY d
             ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)
""".format(catalog=catalog))

spark.sql(f"""
CREATE OR REPLACE TEMP VIEW order_features AS
SELECT r.*,
       COALESCE(h.prior_orders, 0) AS prior_orders,
       COALESCE(h.prior_returns, 0) AS prior_returns,
       CASE WHEN COALESCE(h.prior_orders, 0) > 0
            THEN h.prior_returns * 1.0 / h.prior_orders ELSE 0.0 END AS prior_return_rate,
       DATEDIFF(r.order_date, c.first_purchase_date) AS tenure_days,
       COALESCE(DATEDIFF(r.order_date, h.last_order_date),
                DATEDIFF(r.order_date, c.first_purchase_date)) AS days_since_last
FROM orders_resolved r
JOIN {catalog}.silver.customers c ON c.customer_id = r.customer_id
LEFT JOIN cust_hist h ON h.customer_id = r.customer_id AND h.d = r.order_date
""")

n = spark.sql("SELECT COUNT(*) AS n, SUM(is_returned) AS pos FROM order_features").collect()[0]
print(f"resolved orders: {n['n']:,}  positives: {n['pos']:,} ({n['pos']/n['n']*100:.2f}%)")

# COMMAND ----------

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

df = spark.sql("SELECT * FROM order_features").toPandas()
print(f"collected: {df.shape}")

SPLIT = "2025-10-01"
train = df[df["order_date"] < SPLIT].copy()
test = df[df["order_date"] >= SPLIT].copy()
print(f"train: {len(train):,} (pos rate {train['is_returned'].mean():.4f})")
print(f"test:  {len(test):,} (pos rate {test['is_returned'].mean():.4f})")
assert len(train) > 0 and len(test) > 0, "empty split — check date window"
assert test["is_returned"].nunique() == 2, "test split needs both classes"

# Target-encode category/brand on TRAIN ONLY (smoothed toward the train mean).
ALPHA = 50.0
gmean = train["is_returned"].mean()
for col in ("category", "brand"):
    agg = train.groupby(col)["is_returned"].agg(["sum", "count"])
    smooth = (agg["sum"] + ALPHA * gmean) / (agg["count"] + ALPHA)
    train[f"{col}_rate"] = train[col].map(smooth)
    test[f"{col}_rate"] = test[col].map(smooth).fillna(gmean)

for part in (train, test):
    part["log_price"] = np.log1p(part["unit_price"].astype(float))
    part["month"] = pd.to_datetime(part["order_date"]).dt.month

NUM = ["prior_orders", "prior_returns", "prior_return_rate", "tenure_days",
       "days_since_last", "discount_pct", "log_price", "quantity",
       "category_rate", "brand_rate", "month"]
train_enc = pd.get_dummies(train, columns=["payment_method", "device"])
test_enc = pd.get_dummies(test, columns=["payment_method", "device"])
for c in list(train_enc.columns):
    if c.startswith(("payment_method_", "device_")) and c not in test_enc:
        test_enc[c] = 0
DUMMIES = [c for c in train_enc.columns if c.startswith(("payment_method_", "device_"))]
FEATS = NUM + DUMMIES

X_train, y_train = train_enc[FEATS].astype(float), train_enc["is_returned"].astype(int)
X_test, y_test = test_enc[FEATS].astype(float), test_enc["is_returned"].astype(int)

# COMMAND ----------

from sklearn.ensemble import RandomForestClassifier  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import average_precision_score, roc_auc_score  # noqa: E402

CANDIDATES = {
    "logreg": LogisticRegression(max_iter=1000, class_weight="balanced"),
    "forest": RandomForestClassifier(n_estimators=300, min_samples_leaf=50,
                                     class_weight="balanced_subsample", n_jobs=-1,
                                     random_state=42),
}

results = {}
best_name, best_prauc, best_run = None, -1.0, None
for name, model in CANDIDATES.items():
    with mlflow.start_run(run_name=f"return_propensity_{name}") as run:
        mlflow.log_param("split_date", SPLIT)
        mlflow.log_param("n_features", len(FEATS))
        mlflow.log_param("train_rows", len(X_train))
        model.fit(X_train, y_train)
        proba = model.predict_proba(X_test)[:, 1]
        prauc = average_precision_score(y_test, proba)
        roc = roc_auc_score(y_test, proba)
        mlflow.log_metric("test_pr_auc", prauc)
        mlflow.log_metric("test_roc_auc", roc)
        print(f"{name}: PR-AUC={prauc:.4f} ROC-AUC={roc:.4f}")
        results[name] = (prauc, roc, run.info.run_id)
        if prauc > best_prauc:
            best_name, best_prauc, best_run = name, prauc, run.info.run_id

print(f"BEST: {best_name} PR-AUC={best_prauc:.4f}")

# Register the winner (may lack privileges on some editions — non-fatal).
try:
    mv = mlflow.register_model(f"runs:/{best_run}/model", f"{catalog}.gold.return_propensity")
    print(f"registered model version: {mv.version}")
except Exception as e:
    print(f"register skipped ({type(e).__name__}): {str(e)[:160]}")

# COMMAND ----------

# Batch scores for the test window → governed Gold table (downstream: BI flag,
# Phase-9 grounding, ops review — never auto-cancel orders).
best = CANDIDATES[best_name]
best.fit(X_train, y_train)  # refit exact winner (autologged run already ended)
scored = test[["order_id"]].copy()
scored["p_return"] = best.predict_proba(X_test)[:, 1]
scored["model"] = best_name
scored["scored_at"] = pd.Timestamp.utcnow()

spark.createDataFrame(scored).write.mode("overwrite").saveAsTable(f"{catalog}.gold.order_return_predictions")
cnt = spark.sql(f"SELECT COUNT(*) AS n FROM {catalog}.gold.order_return_predictions").collect()[0]["n"]
print(f"{catalog}.gold.order_return_predictions rows: {cnt:,}")
dbutils.notebook.exit(f"{best_name} PR-AUC={best_prauc:.4f} rows={cnt}")
