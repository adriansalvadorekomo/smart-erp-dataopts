# Skeleton: catalog + medallion schemas + medallion job.
# Targets the NEW Free Edition workspace (Unity Catalog available).
# Community Edition (community.cloud.databricks.com) has NO Unity Catalog:
# databricks_catalog / databricks_schema resources do NOT apply there —
# create `bronze`/`silver`/`gold` via SQL (see
# docs/databricks-community-edition.md step 4) and only use the
# databricks_job resource (or run notebooks manually).
# The job JSON in lakehouse/workflows/smart_erp_job.json is the human-readable
# task contract; this resource is its deployed equivalent. Deploy is manual
# (workflow_dispatch) on Free Edition — CI only runs `terraform validate`.

resource "databricks_schema" "bronze" {
  catalog_name = var.catalog_name
  name         = "bronze"
  comment      = "Raw landing: byte-faithful snapshots + audit columns."
}

resource "databricks_schema" "silver" {
  catalog_name = var.catalog_name
  name         = "silver"
  comment      = "Cleaned, validated, standardized entities."
}

resource "databricks_schema" "gold" {
  catalog_name = var.catalog_name
  name         = "gold"
  comment      = "Business-ready analytical models (KPI matrix: docs/lakehouse.md §7)."
}

# Raw CSV landing (sample-first: the workspace cannot reach laptop Postgres,
# so backfill reads CSV from here; production enterprise uses a JDBC snapshot).
resource "databricks_volume" "landing" {
  catalog_name = var.catalog_name
  schema_name  = databricks_schema.bronze.name
  name         = "landing"
  volume_type  = "MANAGED"
  comment      = "Raw CSV landing (sample-first; production: Postgres snapshot)."
}

resource "databricks_job" "medallion" {
  name                    = "smart-erp-medallion"
  description             = "PostgreSQL → Bronze → Silver → DQ gate → Gold → SQL refresh."
  max_concurrent_runs     = 1
  timeout_seconds         = 3600

  # Free Edition supports serverless compute only — no node types (ADR-8).
  environment {
    environment_key   = "serverless"
    spec {
      environment_version = "2"
    }
  }

  task {
    task_key        = "bronze_ingest"
    environment_key = "serverless"
    notebook_task {
      notebook_path   = "${var.job_path_prefix}/lakehouse/notebooks/01_bronze_backfill"
      base_parameters = { catalog = var.catalog_name, source = "postgres" }
    }
  }

  task {
    task_key        = "silver_build"
    environment_key = "serverless"
    depends_on { task_key = "bronze_ingest" }
    notebook_task {
      notebook_path   = "${var.job_path_prefix}/lakehouse/notebooks/02_silver_build"
      base_parameters = { catalog = var.catalog_name }
    }
  }

  task {
    task_key        = "dq_gate"
    environment_key = "serverless"
    depends_on { task_key = "silver_build" }
    notebook_task {
      notebook_path   = "${var.job_path_prefix}/lakehouse/notebooks/03_dq_gate"
      base_parameters = { catalog = var.catalog_name }
    }
  }

  task {
    task_key        = "gold_build"
    environment_key = "serverless"
    depends_on { task_key = "dq_gate" }
    notebook_task {
      notebook_path   = "${var.job_path_prefix}/lakehouse/notebooks/04_gold_build"
      base_parameters = { catalog = var.catalog_name }
    }
  }
}
