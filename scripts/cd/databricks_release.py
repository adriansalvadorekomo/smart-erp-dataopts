#!/usr/bin/env python3
"""CD release step — run the medallion job on the workspace and validate Gold.

Used by .github/workflows/cd.yml (databricks-deploy). Stdlib only.
Fails loudly on: unresolved job, unsuccessful run, or Gold outside contract.

Env (from the `databricks-prod` GitHub Environment):
    DATABRICKS_HOST, DATABRICKS_TOKEN (PAT: jobs + files + sql scopes),
    WAREHOUSE_ID (SQL warehouse for validation), LAKEHOUSE_CATALOG.

Contract mirrors docs/business-model.md §6 at full scale:
    bronze == silver.orders == silver.order_items == gold.fact_sales == 1M,
    Σ final_price == ₹9,938,876,985 ± ₹1,000.
Gold passing here is also the Phase-9 AI readiness gate (Genie/RAG grounds
on governed Gold — a green run means grounded answers stay trustworthy).
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request

JOB_NAME = "smart-erp-medallion"
EXPECTED_ROWS = 1_000_000
EXPECTED_REVENUE = 9_938_876_985
REVENUE_TOLERANCE = 1_000
POLL_SECONDS = 30
TIMEOUT_SECONDS = 30 * 60


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


def resolve_job_id() -> int:
    data = api("GET", "/api/2.1/jobs/list?limit=100")
    for job in data.get("jobs", []):
        if (job.get("settings") or {}).get("name") == JOB_NAME:
            return int(job["job_id"])
    raise SystemExit(f"job {JOB_NAME!r} not found on workspace")


def wait_run(run_id: int) -> dict:
    deadline = time.time() + TIMEOUT_SECONDS
    while True:
        run = api("GET", f"/api/2.1/jobs/runs/get?run_id={run_id}")
        state = run.get("state") or {}
        if state.get("life_cycle_state") == "TERMINATED":
            return run
        if time.time() > deadline:
            raise SystemExit(f"run {run_id} timed out after {TIMEOUT_SECONDS}s")
        time.sleep(POLL_SECONDS)


def run_statement(sql: str) -> list:
    wid = os.environ["WAREHOUSE_ID"]
    out = api("POST", "/api/2.0/sql/statements/",
              {"warehouse_id": wid, "statement": sql, "wait_timeout": "50s"})
    sid = out.get("statement_id")
    deadline = time.time() + 600
    while True:
        cur = api("GET", f"/api/2.0/sql/statements/{sid}")
        status = (cur.get("status") or {}).get("state")
        if status == "SUCCEEDED":
            return (cur.get("result") or {}).get("data_array") or []
        if status in ("FAILED", "CANCELED", "CLOSED"):
            raise SystemExit(f"validation SQL failed: {cur}")
        if time.time() > deadline:
            raise SystemExit("validation SQL timed out")
        time.sleep(10)


def main() -> int:
    for var in ("DATABRICKS_HOST", "DATABRICKS_TOKEN", "WAREHOUSE_ID"):
        if not os.environ.get(var):
            print(f"ERROR: {var} is not set", file=sys.stderr)
            return 2
    catalog = os.environ.get("LAKEHOUSE_CATALOG", "workspace")

    job_id = resolve_job_id()
    print(f"job {JOB_NAME} = {job_id}")
    run_id = api("POST", "/api/2.1/jobs/run-now", {"job_id": job_id})["run_id"]
    print(f"run {run_id} triggered — polling…")
    run = wait_run(run_id)
    result = (run.get("state") or {}).get("result_state")
    tasks = [(t.get("task_key"), ((t.get("status") or {}).get("result_state")))
             for t in run.get("tasks", [])]
    print(f"run result: {result} {tasks}")
    if result != "SUCCESS":
        return 1

    rows = run_statement(
        f"SELECT (SELECT COUNT(*) FROM {catalog}.bronze.raw_purchases),"
        f" (SELECT COUNT(*) FROM {catalog}.silver.orders),"
        f" (SELECT COUNT(*) FROM {catalog}.silver.order_items),"
        f" (SELECT COUNT(*) FROM {catalog}.gold.fact_sales),"
        f" (SELECT ROUND(SUM(final_price), 2) FROM {catalog}.gold.fact_sales)"
    )[0]
    bronze, orders, items, fact = (int(rows[i]) for i in range(4))
    revenue = float(rows[4])
    print(f"bronze={bronze:,} orders={orders:,} items={items:,} fact={fact:,}")
    print(f"revenue=₹{revenue:,.2f}")
    errors = []
    for name, got in (("bronze", bronze), ("orders", orders),
                      ("items", items), ("fact", fact)):
        if got != EXPECTED_ROWS:
            errors.append(f"{name}={got:,} != {EXPECTED_ROWS:,}")
    if abs(revenue - EXPECTED_REVENUE) > REVENUE_TOLERANCE:
        errors.append(f"revenue ₹{revenue:,.2f} outside ±₹{REVENUE_TOLERANCE:,}")
    if errors:
        print("GOLD VALIDATION FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print("GOLD VALIDATION PASSED — dashboards and AI grounding stay trustworthy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
