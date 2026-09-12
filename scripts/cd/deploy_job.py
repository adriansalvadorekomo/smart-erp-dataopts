#!/usr/bin/env python3
"""CD deploy step — reset the medallion job from the versioned JSON, no state.

Why not `terraform apply` here: the repo keeps Terraform stateless-local on
purpose (no remote backend; state holds secrets and never enters git), so CI
has no state to plan against — apply would try to recreate the workspace.
Terraform remains the one-time provisioning path (schemas, volume, initial
job; run by a human with local state). This script owns the EVOLVING part:
the job definition, sourced from lakehouse/workflows/smart_erp_job.json
(CI-validated task order), translated onto the live job while preserving its
deployed compute (serverless environments) untouched.

Usage:
    python3 scripts/cd/deploy_job.py [--dry-run]

Env: DATABRICKS_HOST, DATABRICKS_TOKEN (jobs scope), WAREHOUSE_ID (sql task).
Exit non-zero on any mismatch (unknown task shape, missing warehouse, …).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
JOB_JSON = os.path.join(REPO, "lakehouse", "workflows", "smart_erp_job.json")
JOB_NAME = "smart-erp-medallion"


def api(method: str, path: str, payload: dict | None = None) -> dict:
    host = os.environ["DATABRICKS_HOST"].rstrip("/")
    req = urllib.request.Request(
        f"{host}{path}",
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={
            "Authorization": f"Bearer {os.environ['DATABRICKS_TOKEN']}",
            "Content-Type": "application/json",
        },
        method=method,
    )
    with urllib.request.urlopen(req, timeout=120) as res:
        return json.load(res)


def build_settings(live: dict, contract: dict, warehouse_id: str) -> dict:
    """Merge versioned contract onto live compute (environments preserved)."""
    tasks = []
    for task in contract["tasks"]:
        key = task["task_key"]
        if "notebook_task" in task:
            nt = task["notebook_task"]
            entry: dict = {
                "task_key": key,
                "description": task.get("description", ""),
                "notebook_task": {
                    "notebook_path": nt["notebook_path"],
                    "base_parameters": nt.get("base_parameters", {}),
                },
            }
        elif "sql_task" in task:
            entry = {
                "task_key": key,
                "description": task.get("description", ""),
                "sql_task": {
                    "file": {"path": task["sql_task"]["file"]["path"]},
                    "warehouse_id": warehouse_id,
                },
            }
        else:
            raise SystemExit(f"task {key!r}: unsupported shape (need notebook_task/sql_task)")
        for dep in task.get("depends_on", []):
            entry.setdefault("depends_on", []).append({"task_key": dep["task_key"]})
        entry["environment_key"] = "serverless"
        tasks.append(entry)
    settings = {
        "name": contract.get("name", JOB_NAME),
        "description": contract.get("description", ""),
        "timeout_seconds": contract.get("timeout_seconds", 3600),
        "max_concurrent_runs": contract.get("max_concurrent_runs", 1),
        "parameters": contract.get("parameters", []),
        "tasks": tasks,
        "environments": live.get("environments", []),
        "queue": live.get("queue", {"enabled": True}),
    }
    return settings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="print the reset payload, change nothing")
    args = ap.parse_args()
    for var in ("DATABRICKS_HOST", "DATABRICKS_TOKEN", "WAREHOUSE_ID"):
        if not os.environ.get(var):
            print(f"ERROR: {var} is not set", file=sys.stderr)
            return 2

    with open(JOB_JSON, encoding="utf-8") as f:
        contract = json.load(f)
    live = api("GET", "/api/2.1/jobs/list?limit=100")
    job = next((j for j in live.get("jobs", [])
                if (j.get("settings") or {}).get("name") == JOB_NAME), None)
    if job is None:
        print(f"ERROR: job {JOB_NAME!r} missing — provision it once via "
              "infra/terraform (see docs/databricks-free-edition.md)", file=sys.stderr)
        return 1
    live_settings = api("GET", f"/api/2.1/jobs/get?job_id={job['job_id']}").get("settings", {})
    settings = build_settings(live_settings, contract, os.environ["WAREHOUSE_ID"])

    summary = [(t["task_key"], (t.get("notebook_task") or {}).get("base_parameters")
                or f"sql@{t.get('sql_task', {}).get('warehouse_id')}") for t in settings["tasks"]]
    print(f"job {job['job_id']} reset payload:")
    for key, params in summary:
        print(f"  {key}: {params}")
    if args.dry_run:
        print("(dry run — nothing changed)")
        return 0
    api("POST", "/api/2.1/jobs/reset",
        {"job_id": job["job_id"], "new_settings": settings})
    print(f"job {job['job_id']} reset applied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
