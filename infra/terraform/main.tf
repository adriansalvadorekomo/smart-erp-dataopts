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

resource "databricks_catalog" "smart_erp" {
  name    = var.catalog_name
  comment = "Smart-ERP lakehouse (Free Edition). Managed by Terraform."
}

resource "databricks_schema" "bronze" {
  catalog_name = databricks_catalog.smart_erp.id
  name         = "bronze"
  comment      = "Raw landing: byte-faithful snapshots + audit columns."
}

resource "databricks_schema" "silver" {
  catalog_name = databricks_catalog.smart_erp.id
  name         = "silver"
  comment      = "Cleaned, validated, standardized entities."
}

resource "databricks_schema" "gold" {
  catalog_name = databricks_catalog.smart_erp.id
  name         = "gold"
  comment      = "Business-ready analytical models (KPI matrix: docs/lakehouse.md §7)."
}

resource "databricks_job" "medallion" {
  name                    = "smart-erp-medallion"
  description             = "PostgreSQL → Bronze → Silver → DQ gate → Gold → SQL refresh."
  max_concurrent_runs     = 1
  timeout_seconds         = 3600

  job_cluster {
    job_cluster_key = "serverless"
    new_cluster {
      spark_version = "15.4.x-scala2.12"
      node_type_id  = "Standard_DS3_v2"
      num_workers   = 1
    }
  }

  task {
    task_key = "bronze_ingest"
    notebook_task {
      notebook_path   = "${var.job_path_prefix}/lakehouse/src/bronze/ingest"
      base_parameters = { catalog = var.catalog_name, source = "postgres" }
    }
  }

  task {
    task_key   = "silver_build"
    depends_on { task_key = "bronze_ingest" }
    notebook_task {
      notebook_path   = "${var.job_path_prefix}/lakehouse/src/silver/transform"
      base_parameters = { catalog = var.catalog_name }
    }
  }

  task {
    task_key   = "dq_gate"
    depends_on { task_key = "silver_build" }
    notebook_task {
      notebook_path   = "${var.job_path_prefix}/lakehouse/src/quality/runner"
      base_parameters = { catalog = var.catalog_name }
    }
  }

  task {
    task_key   = "gold_build"
    depends_on { task_key = "dq_gate" }
    notebook_task {
      notebook_path   = "${var.job_path_prefix}/lakehouse/src/gold/models"
      base_parameters = { catalog = var.catalog_name }
    }
  }
}
