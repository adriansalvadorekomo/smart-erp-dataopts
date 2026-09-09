# Lakehouse (Databricks) — analytical data platform

PostgreSQL remains the ERP **transactional system** (`database/`, `scripts/seed/`).
This package is the **analytical platform**: OLTP snapshots flow into a Delta
Lake medallion architecture on Databricks (Free Edition), where they become
governed Bronze → Silver → Gold data for BI, ML and AI.

Full contract: [`docs/lakehouse.md`](../docs/lakehouse.md). Free Edition limits:
[`docs/databricks-free-edition.md`](../docs/databricks-free-edition.md).
On **Community Edition** (`community.cloud.databricks.com`, no Unity Catalog):
[`docs/databricks-community-edition.md`](../docs/databricks-community-edition.md)
— set `LAKEHOUSE_USE_UC=false` for two-level `schema.table` names.

## Layout

```
lakehouse/
├── src/
│   ├── common/config.py     # UC catalog/schema names, Delta root, PG DSN (all env-driven)
│   ├── bronze/ingest.py     # Raw landing: staging.purchases snapshot → bronze.raw_purchases (+_ingest_ts/_source)
│   ├── silver/transform.py  # Cleaned entities: 6 tables, enums normalized, ONE home for business grouping
│   ├── gold/models.py       # KPI arithmetic (K1–K10) as tested pure functions; SQL mirrors them
│   └── quality/             # rules.py (R1–R9) + runner.py (fail-fast gate before Gold)
├── workflows/smart_erp_job.json  # Databricks Workflows: bronze → silver → dq_gate → gold → sql_refresh
├── sql/gold/                # Databricks SQL models: fact_sales, sales_daily, customer_360, inventory_kpis
├── tests/                   # stdlib unittest (no cluster, no extra deps): python -m unittest discover -s lakehouse/tests
├── local_run.py             # Local end-to-end mirror of the job over a tiny sample: python lakehouse/local_run.py
└── delta/                   # Local Delta root (git-ignored). Prod equivalent: UC managed storage.
```

## Data flow

```
PostgreSQL staging.purchases ──JDBC snapshot──► bronze.raw_purchases (append, watermarked)
   ──validate/cleanse/standardize──► silver.{customers,sellers,products,inventory,orders,order_items}
   ──DQ gate R1–R9 (fail fast)──► gold.{fact_sales,dim_*,sales_daily,customer_360,inventory_kpis}
   ──► Databricks SQL dashboards │ MLflow (ml/) │ Genie/AI (governed Gold only)
```

## Verify

```bash
python -m unittest discover -s lakehouse/tests -v   # pure-logic tests, no DB, no cluster
python lakehouse/local_run.py                        # bronze → silver → DQ → gold on a sample
python -c "import json; json.load(open('lakehouse/workflows/smart_erp_job.json'))"  # job JSON valid
```

## Conventions

- Business logic lives in **exactly one layer** (Silver owns grouping/normalization,
  Gold owns KPI aggregation). SQL and Python implementations mirror each other and
  share the baselines in `docs/business-model.md` §5.
- Money: `final_price ≈ unit_price × qty × (1 − discount/100)`, tolerance ±₹5.00.
  Margin is always **estimated** (`unit_cost = 0.65 × unit_price`).
- Secrets (Databricks token, PG password) via env / secret scopes only — never in code.
