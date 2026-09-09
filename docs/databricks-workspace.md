# Workspace commands — CLI or SDK instead of curl

> Auth once via env (`DATABRICKS_HOST` + `DATABRICKS_TOKEN`), then one-liners.
> Install the CLI: `mise use -g databricks-cli` (v1.15.0 verified). Python
> alternative: `uv sync --group ops` (`databricks-sdk`). Never commit the token.

```bash
export DATABRICKS_HOST="https://dbc-cba3c27a-ade0.cloud.databricks.com"
export DATABRICKS_TOKEN="YOUR_TOKEN"
```

| Task | Python SDK (`uv run --group ops python -c "…"`) | Databricks CLI |
|---|---|---|
| Who am I | `WorkspaceClient().current_user.me().user_name` | `databricks auth whoami` / `databricks current-user me` |
| List catalogs | `w.catalogs.list()` | `databricks catalogs list` |
| List schemas | `w.schemas.list("workspace")` | `databricks schemas list workspace` |
| List volume files | `w.files.list_directory_contents("/Volumes/workspace/bronze/landing")` | `databricks fs ls dbfs:/Volumes/workspace/bronze/landing/` (note the `dbfs:` prefix) |
| Upload CSV | `open(...,'rb')` + `w.files.upload("/Volumes/.../sample_10k.csv", f, overwrite=True)` | `databricks fs cp sample_10k.csv dbfs:/Volumes/workspace/bronze/landing/ --overwrite` |
| Run job | `w.jobs.run_now(228018114268524).run_id` | `databricks jobs run-now 228018114268524` |
| Check run | `w.jobs.get_run(run_id).state` | `databricks runs get <run_id>` |
| SQL query | `w.statement_execution.execute_statement("<sql>", "<warehouse_id>", wait_timeout="50s").result.data_array` | `databricks sql execute --warehouse-id <id> --statement "<sql>"` |
| Import repo | `w.repos.create(url, provider, path)` + `w.repos.update(id, branch=...)` | `databricks repos create --url … --path …` |

Concrete IDs for this workspace (also in `docs/databricks-free-edition.md`):

- Job `smart-erp-medallion`: `228018114268524`
- Serverless Starter Warehouse: `7a0f4f9c083ec2c4`
- Landing: `/Volumes/workspace/bronze/landing/`
- Repo: `/Repos/larrymclarens@gmail.com/smart-erp`

Notes:

- SQL `wait_timeout` must be `0s` or 5–50s — the API rejects anything else.
- The Repos list endpoint does not enumerate on this workspace; fetch a known
  repo id directly (`w.repos.get(id)`) or delete + re-create to refresh.
- `terraform apply` remains the path for catalog/schemas/volume/job (declarative,
  reviewed); SDK/CLI are for data movement, runs, and checks.
