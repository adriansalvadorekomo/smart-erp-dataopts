"""CD pipeline contract tests — pure logic, no network, no daemon.

Covers what CI can verify without credentials: Gold validation math,
job-definition translation, workflow/compose file sanity, entrypoint syntax.
The daemon-requiring proof (build + smoke + workspace run) happens on
workflow_dispatch / tags in .github/workflows/cd.yml.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_validate_gold_pass_and_fail():
    import sys

    sys.path.insert(0, str(REPO / "scripts" / "cd"))
    from databricks_release import validate_gold

    assert validate_gold(1_000_000, 1_000_000, 1_000_000, 1_000_000, 9_938_876_984.90) == []
    assert validate_gold(1_000_000, 1_000_000, 1_000_000, 1_000_000, 9_938_876_985.0) == []
    bad = validate_gold(10_000, 1_000_000, 1_000_000, 1_000_000, 99_000_000.0)
    assert len(bad) == 2  # one count + revenue
    assert any("bronze" in e for e in bad) and any("revenue" in e for e in bad)


def test_deploy_job_translation_matches_contract():
    import sys

    sys.path.insert(0, str(REPO / "scripts" / "cd"))
    from deploy_job import build_settings

    contract = json.loads((REPO / "lakehouse" / "workflows" / "smart_erp_job.json").read_text())
    live = {"environments": [{"environment_key": "serverless"}],
            "queue": {"enabled": True}}
    settings = build_settings(live, contract, "wh-123")
    assert [t["task_key"] for t in settings["tasks"]] == [
        "bronze_ingest", "silver_build", "dq_gate", "gold_build", "sql_refresh"]
    bronze = settings["tasks"][0]["notebook_task"]["base_parameters"]
    assert "source_file" in bronze and "source" not in bronze  # the drift stays fixed
    sql = settings["tasks"][-1]["sql_task"]
    assert sql["warehouse_id"] == "wh-123"
    assert settings["environments"] == live["environments"]  # compute preserved


def test_cd_workflow_files_parse():
    import yaml

    cd = yaml.safe_load((REPO / ".github" / "workflows" / "cd.yml").read_text())
    assert set(cd["jobs"]) == {"images", "smoke", "databricks-deploy"}
    assert cd["jobs"]["smoke"]["needs"] == "images"
    assert cd["jobs"]["databricks-deploy"]["needs"] == "smoke"
    compose = yaml.safe_load((REPO / "infra" / "docker-compose.yml").read_text())
    assert set(compose["services"]) == {"postgres", "backend", "frontend"}
    assert compose["services"]["backend"]["depends_on"]["postgres"]["condition"] == "service_healthy"
    assert compose["services"]["frontend"]["depends_on"]["backend"]["condition"] == "service_healthy"


def test_entrypoint_syntax():
    entry = REPO / "backend" / "docker-entrypoint.sh"
    assert entry.stat().st_mode & 0o111, "entrypoint must stay executable"
    r = subprocess.run(["sh", "-n", str(entry)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
