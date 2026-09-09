# Lakehouse Architecture — Databricks-centered analytical platform

> **Status:** ✅ Skeleton (contracts + pure logic + job definition). Backfill, ML and AI arrive incrementally.
> **Workspace (Free Edition):** `https://dbc-cba3c27a-ade0.cloud.databricks.com/?o=7477247481199325`
> **Companion docs:** [business-model](business-model.md) (domain truth) · [decisions](decisions.md) (ADRs) · [free-edition](databricks-free-edition.md) (limits).

---

## 1. Logical architecture

```
┌──────────────┐  OLTP writes (FastAPI, Phase 4)  ┌──────────────┐
│  App layer   │ ────────────────────────────────► │  PostgreSQL  │
│ FastAPI+React│ ◄── reads (orders, stock, CRUD) ─ │ public.*     │
└──────────────┘                                   └──────┬───────┘
                                                          │ JDBC snapshot, off-peak only
                                                          ▼
                                                   ┌──────────────┐
                                                   │    BRONZE    │  Delta · append-only · raw + _ingest_ts/_source
                                                   │ raw_purchases│  raw preserved 1:1, watermarked on purchase_date
                                                   └──────┬───────┘
                                                          │ validate / cleanse / standardize + DQ gate (fail fast)
                                                          ▼
                                                   ┌──────────────┐
                                                   │    SILVER    │  Delta · 6 entities, same grains as business-model §2
                                                   │ 6 OLTP twins │  enums normalized, ONE home for grouping logic
                                                   └──────┬───────┘
                                                          │ business transforms (KPI logic, one definition each)
                                                          ▼
                                                   ┌──────────────┐
                                                   │     GOLD     │  Delta · star schema + serving marts
                                                   │ fact/dim/*   │  BI, ML features, Genie — governed data only
                                                   └─┬─┬────┬─────┘
                                                     │ │    │
                        Databricks SQL dashboards ◄──┘ │    └──► Genie / AI (grounded Q&A over Gold)
                        MLflow training (ml/) ◄───────┘
```

PostgreSQL stays the transactional system (invariants 1–2). Databricks never
serves OLTP traffic; the app never queries the lakehouse for CRUD.

## 2. Data flow

| Step | From → To | Mechanism | Idempotency |
|---|---|---|---|
| OLTP bootstrap | CSV → `raw`/`staging` → `public.*` | `scripts/seed/ingest.py` (kept) | Full refresh, deterministic surrogates |
| Ingestion | `staging.purchases` → `bronze.raw_purchases` | JDBC snapshot → Delta `append`, watermark `max(purchase_date)` | Re-run ingests 0 rows; first load = full snapshot |
| Cleansing | Bronze → Silver (6 tables) | PySpark transforms (`silver/transform.py`) + `MERGE` | Deterministic keys; re-runnable per watermark |
| Quality gate | Silver → (gate) → Gold | `quality/runner.py`, rules R1–R9 | Gate blocks Gold on red data — no silent corruption |
| Serving | Silver → Gold (7 tables) | PySpark + `sql/gold/*.sql` | Full rebuild from Silver (acceptable at 1M rows) |

## 3. Component responsibilities

| Component | Owns | Does NOT own |
|---|---|---|
| PostgreSQL | Transactions, CHECKs, API lifecycle (`IN TRANSIT → …`) | Analytics aggregations (no BI on OLTP) |
| Bronze | Raw preservation, audit columns, watermark | Any cleaning or business rules |
| Silver | Normalization (Title→UPPER enums, trims, types), grouping (mode city, latest snapshots) | KPI aggregation |
| Gold | KPI-ready models only (K1–K12 matrix in §7) | Raw access, new business rules |
| `quality/` | Explicit rules R1–R9, observable fail-fast | Silent coercion / defaulting |
| Workflows | Orchestration (`smart_erp_job.json`: bronze→silver→dq→gold→sql) | Business logic (delegates to code) |
| Databricks SQL | Dashboards over Gold | OLTP queries |
| `ml/` | Feature reads from Gold, MLflow tracking | Training on Silver/Bronze directly |
| AI/Genie | Grounded answers over governed Gold | Source-of-truth claims (platform is truth) |

## 4. Data lifecycle

Bronze rows are immutable history; Silver is rebuilt deterministically from
Bronze + watermark; Gold is rebuilt from Silver after a green DQ gate.
Re-running any step with the same watermark produces identical output
(reproducible, idempotent where possible — invariant 10).

## 5. Bronze / Silver / Gold responsibilities

- **Bronze** (`lakehouse/src/bronze/`): 1 table (`raw_purchases`), 1:1 with the
  OLTP snapshot + `_ingest_ts`/`_source`. No transforms. (`bronze_schema_ok`, watermark filter tested.)
- **Silver** (`lakehouse/src/silver/`): 6 entity twins, contract enums
  (`DELIVERY_STATUSES`, `PAYMENT_METHODS`, `DEVICES`, `CATEGORIES`), money
  invariant ±₹5.00, est. cost factor 0.65. Grouping logic lives here and
  nowhere else (invariant 8).
- **Gold** (`lakehouse/src/gold/` + `sql/gold/`): `fact_sales`, `dim_customer`,
  `dim_product`, `dim_date` (backbone 2024-03-31 → 2026-03-31),
  `sales_daily`, `customer_360`, `inventory_kpis`. Each serves named KPIs (§7);
  margin columns keep the `estimated_` prefix.

## 6. ML lifecycle (skeleton — models land in Phase 8)

```
Gold (customer_360, fact_sales) → features → training (scikit-learn/XGBoost)
  → MLflow experiment (Databricks-native, autolog) → metrics + artifacts
  → model version → batch predictions back to gold.*_predictions
```

Targets, in value order: **return propensity** (K12, 11.6% base rate) and
**churn risk** (K11). Max two models first — no model zoo.

## 7. KPI → Gold matrix (addendum to business-model §5 — no rule changes)

| KPI | Gold table | Notes |
|---|---|---|
| K1 Revenue, K2 AOV | `fact_sales`, `sales_daily` | Baseline AOV ₹9,938.88 |
| K3 Return rate | `sales_daily` (status split) | Baseline 11.60% |
| K4 Delayed rate | `sales_daily` | ≈50% of completed |
| K5 Slices / trend | `fact_sales`, `sales_daily`, dims | `dim_date` backbone |
| K6 Discount bands | `fact_sales.discount_band` | Bands owned by Gold |
| K7 Top sellers | `fact_sales` ⋈ `dim_product` | Rating snapshot preserved |
| K8 Stock-critical | `inventory_kpis` | Baseline 3,561; threshold 20 |
| K9 Pareto | `customer_360` | Baseline top-20% → 62.9% |
| K10 Est. margin | `fact_sales.estimated_line_margin` | Always labelled estimated |
| K11 Churn / K12 Return propensity | `customer_360` features | Phase-8 targets |

## 8. Infrastructure lifecycle

Terraform (`infra/terraform/`) owns workspace assets: catalog + 3 schemas,
job deployment, warehouse permissions. Local dev needs no cloud: Postgres via
`infra/docker-compose.yml`, lakehouse logic via `local_run.py` + unittest.
Secrets (Databricks token, PG password) via env / secret scopes only.

## 9. CI/CD flow

PR → `lockfile` → `lint` (compileall) → `lakehouse-test` (unittest, no
cluster) → `sql-parse` (Gold SQL sanity) → `terraform-validate` →
`database-sanity` (migrations, unchanged) → review → squash-merge → `main`.
Workspace deploy stays manual (`workflow_dispatch`) on Free Edition — CI never
pushes to Databricks. Tag `v*` → release notes (unchanged).
