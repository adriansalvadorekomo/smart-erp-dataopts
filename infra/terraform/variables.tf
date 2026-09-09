# All infrastructure configuration is externalized — no defaults carry secrets.

variable "catalog_name" {
  description = "Unity Catalog catalog for the lakehouse. Free Edition cannot create new catalogs via API (no metastore storage root), so schemas live in the default 'workspace' catalog. Production enterprise uses a dedicated catalog (e.g. smart_erp) via LAKEHOUSE_CATALOG / TF_VAR_catalog_name."
  type        = string
  default     = "workspace"
}

variable "job_path_prefix" {
  description = "Repos path prefix where lakehouse code is checked out in the workspace."
  type        = string
  default     = "/Repos/larrymclarens@gmail.com/smart-erp"
}

variable "databricks_host" {
  description = "Workspace URL (prefer DATABRICKS_HOST env var; this is a fallback)."
  type        = string
  default     = "https://dbc-cba3c27a-ade0.cloud.databricks.com"
}

variable "workspace_id" {
  description = "Databricks workspace ID (from the workspace URL ?o= parameter). Targeting label; provider auth uses DATABRICKS_HOST + DATABRICKS_TOKEN."
  type        = string
  default     = "7474647481199325"
}

variable "environment_id" {
  description = "Cloud environment / shared resource identifier (region-scoped). Recorded for targeting; not consumed by resources yet."
  type        = string
  default     = "aws:us-east-2:82159aa2-8057-4ea2-a93d-2f3a1b373d37"
}
