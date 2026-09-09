# Databricks Community Edition — setup guide

> Community Edition (CE) is the **free, limited Databricks** at
> `https://community.cloud.databricks.com` — no credit card, but also no Unity
> Catalog, no serverless, small single-node clusters only. This guide gets the
> Smart-ERP lakehouse running on it. The `dbc-….cloud.databricks.com` URL with
> `?o=…` from earlier is a **new Free Edition workspace**, a different offering —
> if you can't open it (expired trial, no login), use CE below instead.

## Free Edition vs Community Edition (what changes for this repo)

| Capability | New Free Edition | Community Edition (this guide) |
|---|---|---|
| Login | `dbc-…cloud.databricks.com/?o=<workspace-id>` | `community.cloud.databricks.com` |
| Namespace | Unity Catalog: `catalog.schema.table` | Hive Metastore: `schema.table` (no catalog) |
| Compute | Serverless | Single-node cluster you start/stop yourself |
| Delta Lake / notebooks / jobs | Yes | Yes (core feature — works fine) |
| MLflow | Native | Yes (workspace-local) |
| Terraform provider | Works (host + token) | Mostly **not usable** (no UC resources); manage schemas via SQL |
| Genie / Vector Search | Sometimes | No — use SQL-first Q&A over Gold |

Repo support: `LakehouseConfig(use_uc=False)` (`LAKEHOUSE_USE_UC=false`) makes
`table()` return two-level names, and every Gold SQL model takes `${catalog}`
as a parameter — on CE, bind it to the schema directly or `USE <schema>` and
drop the prefix (each file header says so; the only change is the qualifier).

## Step-by-step

1. **Sign up / log in** at `https://community.cloud.databricks.com` (email, no card).
2. **Create a cluster:** Compute → Create → single-node, latest LTS runtime
   (e.g. 15.4 LTS), smallest node type. Start it; **terminate when done** (CE
   suspends idle clusters, but manual shutdown is cleaner).
3. **Get the code in:** Repos → Add Repo → connect your GitHub
   (`smart-erp-dataopts`, branch `feat/4-lakehouse-skeleton` until merged).
   CE Repos works with public repos out of the box.
4. **Create the layer schemas** (one cell, Hive Metastore = plain databases):
   ```sql
   CREATE DATABASE IF NOT EXISTS bronze;
   CREATE DATABASE IF NOT EXISTS silver;
   CREATE DATABASE IF NOT EXISTS gold;
   ```
5. **First data:** CE clusters have no JDBC route to your laptop Postgres, so
   start from the CSV: upload a **small sample** (e.g. first 10k rows) via
   Data → Add Data → Upload file to a `bronze.raw_purchases` seed table, or
   `COPY INTO` from DBFS. Full 1M-row backfill is a later increment — prove the
   path on the sample first.
6. **Run the logic:** open the `lakehouse/src/*` notebooks (or `%run` the job
   order bronze → silver → DQ gate → gold) with `LAKEHOUSE_USE_UC=false`.
   DQ failures stop the run before Gold — that is the gate working, not an error.
7. **Query Gold:** Data → SQL Editor (CE includes a SQL endpoint):
   open `lakehouse/sql/gold/*.sql`, qualify tables as `gold.sales_daily`
   (two-level names), run K1–K10 checks against `docs/business-model.md` §5.
8. **MLflow:** experiments run workspace-locally; open the Experiments tab to
   see runs (Phase 8).

## Limits to respect on CE

- One small cluster, cluster sleeps — batch runs only, no concurrency
  (`max_concurrent_runs: 1` in the job JSON already assumes this).
- No secret scopes wiring like paid tiers — tokens/env via notebook widgets or
  cluster env vars, never committed.
- Storage is ephemeral-ish: keep the OLTP Postgres + CSV as the durable source
  of truth; CE tables are a re-derivable cache (re-run the job to rebuild).

## When you outgrow CE

Move to the new Free Edition workspace (UC three-level names, serverless,
Terraform-managed catalog — already scaffolded in `infra/terraform/`), then
paid tiers for Lakeflow Declarative Pipelines / Vector Search. The medallion
code doesn't change — only the qualifier (`LAKEHOUSE_USE_UC=true`) and compute.
