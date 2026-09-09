# Architectural Decision Log — Lakehouse migration

Short, reasoned records. Format: decision · context · alternatives · reasoning · consequences.

---

## ADR-1 — Databricks instead of Airflow + dbt + Postgres analytics

- **Decision:** Databricks Lakehouse (Delta + Workflows + SQL) is the analytical platform; Airflow/dbt/OLTP-analytics leave the architecture.
- **Context:** Pipeline placeholders (`data/airbyte`, `data/airflow`) are empty; the dbt project has zero models; BI/ML/AI are unbuilt. There is no working code to displace — only direction to choose.
- **Alternatives:** (a) build out Airflow + dbt on Postgres; (b) keep both stacks (dbt for SQL, Spark for scale).
- **Reasoning:** One platform with one storage format (Delta), one orchestrator (Workflows), one SQL engine removes three integration seams and the need to scale analytics on the transactional database (invariant 2). Dual-stack (b) duplicates business logic across layers, violating invariant 8 for no demonstrated benefit at 1M rows.
- **Consequences:** Team learns one paradigm (medallion + Delta); Postgres is protected; migration risk is low because nothing production exists to migrate.

## ADR-2 — PostgreSQL remains OLTP

- **Decision:** PostgreSQL stays the system of record for transactions; Databricks is read-only downstream of it.
- **Context:** ERP needs atomic order/stock writes and the `delivery_status` lifecycle contract (business-model §3).
- **Alternatives:** Write through Databricks / Delta directly from the app.
- **Reasoning:** Delta Lake is an analytical store, not an OLTP engine (no row-level transactional API semantics the ERP contract needs). Keeping Postgres preserves the CHECKs, FKs and the Phase-4 API contract untouched (critical rule: preserve business functionality).
- **Consequences:** Explicit JDBC-snapshot seam (off-peak) between OLTP and Bronze; app code never touches the lakehouse for CRUD.

## ADR-3 — Medallion (Bronze / Silver / Gold)

- **Decision:** Three layers with the responsibilities in `docs/lakehouse.md` §5.
- **Context:** Raw CSV snapshots vary per event (price/stock/rating are time-varying); KPIs need stable governed marts.
- **Alternatives:** Two layers (raw → marts) or dbt staging/intermediate/marts naming.
- **Reasoning:** Bronze preserves replayable history (auditability, invariant 5); Silver isolates cleaning/validation so exactly one layer defines entities (invariant 8); Gold serves named KPIs only (no speculative marts). The existing `raw → staging → public` Postgres pipeline already thinks this way — medallion is its analytical twin, not a new idea.
- **Consequences:** Slightly more tables, but each has one reason to exist; DQ gate has a natural home (Silver→Gold).

## ADR-4 — PySpark / SQL instead of dbt

- **Decision:** New transforms are PySpark + Databricks SQL; the empty dbt scaffold is removed (owner-approved).
- **Context:** `data/dbt/` contains zero models, zero sources, zero tests — no reusable logic exists.
- **Alternatives:** Keep dbt for Silver/Gold SQL and add Spark only where needed.
- **Reasoning:** At this stage dbt would be a second engine, second test framework and second CI path serving no workload. PySpark covers the 1M-row batch comfortably and shares the cluster with ML; Databricks SQL covers the serving models. Fewer technologies + clear architecture (guiding principle). KPI logic is mirrored in tested Python helpers so it stays verifiable without a cluster.
- **Consequences:** `dbt-core`/`dbt-postgres` deps and `dbt-*` CI jobs removed; SQL review happens in `lakehouse/sql/gold/` instead of `data/dbt/models/`.

## ADR-5 — Databricks Workflows instead of Airflow

- **Decision:** `lakehouse/workflows/smart_erp_job.json` (bronze → silver → dq_gate → gold → sql_refresh) orchestrates the platform.
- **Context:** No DAGs exist; Free Edition supports Workflows with serverless compute.
- **Alternatives:** Self-hosted Airflow (Compose) orchestrating Databricks jobs.
- **Reasoning:** Airflow would be a whole second control plane (scheduler, metadata DB, executor ops) orchestrating a platform that already has a native scheduler. Workflows gives retries, task deps and observability with zero extra infrastructure — minimal operational complexity wins.
- **Consequences:** `data/airflow/` removed; local parity via `lakehouse/local_run.py` (same task order, sample data).

## ADR-6 — Databricks SQL instead of Metabase as the core BI layer

- **Decision:** Gold is served through Databricks SQL queries/dashboards; Metabase is deferred, not built.
- **Context:** `bi/` is empty; no dashboards exist to migrate.
- **Alternatives:** Stand up Metabase (Compose) against Postgres or Gold.
- **Reasoning:** Querying Gold where it lives avoids another database load path and another service to operate; Free Edition includes SQL warehouses and dashboards. `bi/` remains as an export folder if a second BI tool later proves its value (interoperability over replacement).
- **Consequences:** BI depends on the workspace; local BI is out of scope until Phase 7.

## ADR-7 — MLflow (Databricks-native)

- **Decision:** Experiment tracking and model registry via the workspace-native MLflow.
- **Context:** No models exist; Phase 8 targets return propensity (K12) and churn (K11).
- **Alternatives:** Self-hosted MLflow server.
- **Reasoning:** Native integration means zero tracking-server ops, autologging on the training cluster, and Gold-to-model lineage in one UI. A self-hosted server would duplicate what the platform already provides.
- **Consequences:** Local training logs to file-store; runs are reproducible via pinned features from `customer_360` + `fact_sales`.

## ADR-8 — Local-first dev with documented production equivalents (Free Edition)

- **Decision:** Every cloud capability used here has a stdlib/local equivalent in-repo
  (unittest instead of cluster tests, `local_run.py` instead of a job run,
  `lakehouse/delta/` instead of UC storage); production alternatives are
  documented, never faked.
- **Context:** Free Edition limits (single catalog, serverless-only, low concurrency — see `databricks-free-edition.md`).
- **Alternatives:** Require a live workspace for any validation.
- **Reasoning:** Contributors can verify the full data path with zero cloud access
  (correctness → maintainability), while the workspace remains the only place
  real data lands. This keeps `main` green without credentials in CI.
- **Consequences:** Two clearly-labelled modes ("portfolio/free-edition" vs "production enterprise"); no enterprise-only features in the critical path.
