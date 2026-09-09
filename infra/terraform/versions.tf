terraform {
  required_version = ">= 1.5"
  required_providers {
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.40"
    }
  }
  # NOTE: no remote backend configured for the skeleton — local state only.
  # Production: add an azurerm/s3/gcs backend block here.
}

# Auth: DATABRICKS_HOST + DATABRICKS_TOKEN from environment (never in repo).
provider "databricks" {}
