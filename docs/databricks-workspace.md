# Workspace commands — Databricks CLI, step by step

> Every command below was executed against the project workspace and its real
> output is shown. No `export` prefixes needed: the CLI is on PATH
> (`mise use -g databricks-cli`) and auth comes from your saved profile
> (`databricks auth login` → `~/.databrickscfg`). Never commit the token.

## 0. One-time setup

```bash
mise use -g databricks-cli                       # install CLI v1.15.0 (verified)
databricks auth login --host https://dbc-cba3c27a-ade0.cloud.databricks.com
# → paste your personal access token when prompted (needs scopes:
#   workspace, unity-catalog, clusters, sql, files)
```

Verify the profile:

```bash
databricks current-user me
# → larrymclarens@gmail.com
```

## 1. Explore — catalogs and schemas

```bash
databricks catalogs list --output json | python3 -c "import json,sys; print(sorted(c['name'] for c in json.load(sys.stdin)))"
# → ['samples', 'system', 'workspace']

databricks schemas list workspace --output json | python3 -c "import json,sys; print(sorted(s['name'] for s in json.load(sys.stdin)))"
# → ['bronze', 'default', 'gold', 'information_schema', 'silver']
```

Free Edition cannot create catalogs via API, so the medallion schemas live in
the built-in `workspace` catalog (Terraform-managed). `smart_erp` stays the
production-catalog name, selected via `LAKEHOUSE_CATALOG`.

## 2. Data files in the landing volume

```bash
databricks fs ls dbfs:/Volumes/workspace/bronze/landing/
# → sample_10k.csv
```

Volume paths need the `dbfs:` prefix. Upload a new file:

```bash
databricks fs cp ./sample_10k.csv dbfs:/Volumes/workspace/bronze/landing/ --overwrite
```

## 3. Repo checkout (what code the job runs)

```bash
databricks repos get 751655018240305 --output json | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['branch'], d['head_commit_id'][:7])"
# → feat/4-lakehouse-skeleton d86b246
```

Notes: the Repos *list* endpoint does not enumerate on this workspace — fetch
a known id directly. The path is `/Repos/larrymclarens@gmail.com/smart-erp`
(user-scoped; bare `/Repos/smart-erp` is rejected). Refresh after each push by
re-creating the repo on the same path (delete + create, then set the branch).

## 4. Job — inspect, run, follow

```bash
databricks jobs get 228018114268524 --output json | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['settings']['name'], [t['task_key'] for t in d['settings']['tasks']])"
# → smart-erp-medallion ['bronze_ingest', 'silver_build', 'dq_gate', 'gold_build']

databricks jobs run-now 228018114268524
# → {"run_id": 103219105703513, ...}

databricks jobs get-run 103219105703513 --output json | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['state']['life_cycle_state'], d['state']['result_state'])"
# → TERMINATED SUCCESS
```

There is no `databricks runs` command in v1.15 — run inspection is
`databricks jobs get-run <run_id>`. The job itself is Terraform-managed
(`infra/terraform/main.tf`); the CLI only triggers and follows runs.

## 5. Validate Gold over SQL

There is no `databricks sql` command group in v1.15 — use the generic API
passthrough (warehouse id from `databricks warehouses list`):

```bash
databricks api post /api/2.0/sql/statements --json '{"warehouse_id":"7a0f4f9c083ec2c4","statement":"SELECT COUNT(*) AS fact, ROUND(SUM(final_price),2) AS revenue FROM workspace.gold.fact_sales","wait_timeout":"50s"}' | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['status']['state'], d['result']['data_array'])"
# → SUCCEEDED [['10000', '99415946.09']]
```

`wait_timeout` must be `0s` or 5–50s — anything else is rejected. For longer
queries, take the returned `statement_id` and poll:

```bash
databricks api get /api/2.0/sql/statements/<statement_id>
```

## 6. Which tool for what

| Task | Tool |
|---|---|
| Catalog / schemas / volume / job definition | Terraform (`infra/terraform/`) — declarative, reviewed |
| Move data, trigger runs, inspect, query | CLI commands above |
| Scripted checks (CI-style) | Python SDK (`uv sync --group ops`, same auth via env) |

Concrete IDs for this workspace (also in `docs/databricks-free-edition.md`):

- Job `smart-erp-medallion`: `228018114268524`
- Serverless Starter Warehouse: `7a0f4f9c083ec2c4`
- Landing: `/Volumes/workspace/bronze/landing/`
- Repo: `/Repos/larrymclarens@gmail.com/smart-erp`
