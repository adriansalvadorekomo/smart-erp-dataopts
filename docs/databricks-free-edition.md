# Databricks Free Edition — limits and dev/prod mapping

> Workspace: `https://dbc-cba3c27a-ade0.cloud.databricks.com/?o=7477247481199325`
> Workspace ID: `7474647481199325` · Environment ID: `aws:us-east-2:82159aa2-8057-4ea2-a93d-2f3a1b373d37`
> (also externalized as `workspace_id` / `environment_id` in `infra/terraform/variables.tf`)
>
> **Which free tier?** This page covers the **new Free Edition** workspace above.
> On **Community Edition** (`community.cloud.databricks.com`) — no Unity Catalog,
> Hive Metastore only — follow [`databricks-community-edition.md`](databricks-community-edition.md)
> instead and set `LAKEHOUSE_USE_UC=false`.
> Workspace ID: `7474647481199325` · Environment ID: `aws:us-east-2:82159aa2-8057-4ea2-a93d-2f3a1b373d37`
> (also externalized as `workspace_id` / `environment_id` in `infra/terraform/variables.tf`)
> Rule: document the production alternative wherever Free Edition constrains us; never fake unavailable functionality.

## What Free Edition gives us (used)

| Capability | Use in Smart-ERP |
|---|---|
| Unity Catalog (single user catalog) | `smart_erp` catalog with `bronze` / `silver` / `gold` schemas |
| Delta Lake + serverless compute (small) | Medallion batch at 1M rows — comfortably in range |
| Workflows (limited concurrency) | `smart_erp_job.json`, `max_concurrent_runs: 1` |
| Databricks SQL (warehouse + dashboards) | `lakehouse/sql/gold/` + Phase-7 dashboards |
| MLflow (native) | Phase-8 experiments |
| Genie (AI/BI, availability varies) | Phase-9 grounded Q&A over Gold (adopt when available, else SQL-first assistant) |
| Repos ↔ GitHub | Deploy `feat/*` branches for review; `main` = deployable |

## Known limitations (do not design around these as if enterprise)

1. **Single small serverless cluster shape** — no autoscaling fleets, no job-concurrency headroom. Mitigation: one serial job, off-peak Bronze snapshots, full-rebuild Gold (fine at 1M rows).
2. **Storage/compute budgets** — keep one full Bronze history + current Silver/Gold; no long retention experiments. Local `lakehouse/delta/` is scratch only.
3. **No enterprise DLT expectations** — the skeleton uses standard Workflows + Delta (`MERGE`/CTAS). **Production alternative:** Lakeflow Declarative Pipelines with expectations and SCD2 — documented here, not implemented, not faked.
4. **Genie / Vector Search availability varies** — Phase 9 ships SQL-grounded answers first; semantic search only if the workspace offers it. **Production alternative:** Databricks Vector Search over Gold-derived embeddings.
5. **Secrets/backends** — dev uses env vars; **production** uses secret scopes + service principals (Terraform wires scope names, never values).

## Dev ↔ prod equivalence table

| Portfolio / Free Edition (in repo) | Production enterprise (documented) |
|---|---|
| `python -m unittest discover -s lakehouse/tests` | Cluster integration tests on a staging catalog |
| `python lakehouse/local_run.py` (sample) | Workflows run on serverless (same task order) |
| `lakehouse/delta/` (local files) | UC managed storage / external volumes |
| JDBC snapshot from Postgres | Lakeflow Connect / CDC (Debezium) for change-feed |
| Manual `workflow_dispatch` deploy | `databricks bundle deploy` from tags in CD |
| Env-var secrets locally | Secret scopes + service principals |

## Connecting a dev machine (no secrets in repo)

```bash
export DATABRICKS_HOST="https://dbc-cba3c27a-ade0.cloud.databricks.com"
export DATABRICKS_TOKEN="<personal-access-token>"   # never commit; rotate regularly
export LAKEHOUSE_CATALOG="smart_erp"
# databricks CLI / Terraform read these automatically
```
