"""Databricks Genie client (Phase 9): per-question veracity over Gold.

Genie writes the SQL itself against the workspace Gold tables and returns the
query + result rows — the backend relays them with the space/question cited,
so every answer stays checkable. Space setup (one-time UI step, see
docs/bi.md § Genie): create space → attach the 4 Gold marts → set
GENIE_SPACE_ID. Without it the endpoint answers 409 with setup instructions
(explicit, never silent).
"""
from __future__ import annotations

import json
import os
import time
import urllib.request

POLL_SECONDS = 5
TIMEOUT_SECONDS = 10 * 60


class GenieError(Exception):
    pass


def _api(method: str, path: str, payload: dict | None = None) -> dict:
    host = os.environ.get("DATABRICKS_HOST", "").rstrip("/")
    token = os.environ.get("DATABRICKS_TOKEN", "")
    if not host or not token:
        raise GenieError("DATABRICKS_HOST/DATABRICKS_TOKEN are not configured")
    req = urllib.request.Request(
        f"{host}{path}",
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as res:
            return json.load(res)
    except Exception as e:  # noqa: BLE001
        raise GenieError(f"Genie call failed: {type(e).__name__}: {str(e)[:200]}") from e


def space_id() -> str:
    sid = os.environ.get("GENIE_SPACE_ID", "")
    if not sid:
        raise GenieError("GENIE_SPACE_ID is not set — create the Genie Space over "
                         "Gold (docs/bi.md) and set its ID")
    return sid


TERMINAL = ("COMPLETED", "FAILED", "ERROR", "CANCELLED")
RUNNING = ("SUBMITTED", "FETCHING_METADATA", "FILTERING_CONTEXT", "ASKING_AI",
           "PENDING_WAREHOUSE", "EXECUTING_QUERY")


def ask_genie(question: str) -> dict:
    """Ask Genie; return its SQL, result rows and text (all cited)."""
    sid = space_id()
    started = _api("POST", f"/api/2.0/genie/spaces/{sid}/start-conversation",
                   {"content": question})
    cid = started.get("conversation_id")
    mid = started.get("message_id") or (started.get("message") or {}).get("message_id")
    if not cid or not mid:
        raise GenieError(f"unexpected start-conversation shape: {str(started)[:200]}")
    deadline = time.time() + TIMEOUT_SECONDS
    cur: dict = {}
    while True:
        cur = _api("GET", f"/api/2.0/genie/spaces/{sid}/conversations/{cid}/messages/{mid}")
        status = str(cur.get("status") or "").upper()
        if status in TERMINAL or status == "QUERY_RESULT_EXPIRED":
            break
        if time.time() > deadline:
            raise GenieError("Genie answer timed out")
        time.sleep(POLL_SECONDS)
    if status in ("FAILED", "ERROR", "CANCELLED"):
        raise GenieError(f"Genie could not answer: {(cur.get('error') or status)}")
    sql, rows, text = _extract(sid, cid, mid, cur, question)
    return {"answer": text or _summarize(rows), "intent": "genie",
            "sources": [{"endpoint": "Genie Space", "params": {"space_id": sid}},
                        {"endpoint": "Genie SQL", "params": {"sql": sql}}],
            "sql": sql, "rows": rows}


def _extract(sid: str, cid: str, mid: str, msg: dict, question: str) -> tuple[str, list, str]:
    """Pull (sql, rows, text) from a completed message, fetching full results."""
    sql, rows, texts = "", [], []
    echo = question.strip().lower()

    def keep(t: object) -> None:
        if isinstance(t, str) and t.strip() and t.strip().lower() != echo:
            texts.append(t.strip())
    attachments = msg.get("attachments") or []
    if isinstance(attachments, dict):
        attachments = [attachments]
    for att in attachments:
        if not isinstance(att, dict):
            continue
        q = att.get("query") or {}
        if isinstance(q, dict) and q.get("query"):
            sql = q["query"]
        elif isinstance(q, str):
            sql = q
        data = _attachment_rows(sid, cid, mid, att)
        if data:
            rows = data
        for key in ("text", "content"):
            keep(att.get(key))
    keep(msg.get("content"))
    return sql, rows, "\n".join(texts).strip()


def _attachment_rows(sid: str, cid: str, mid: str, att: dict) -> list:
    """Inline rows if present, else fetch via the query-result endpoint."""
    qr = att.get("query_result") or {}
    stmt = qr.get("statement_response") or {}
    data = (stmt.get("result") or {}).get("data_array")
    cols = [c.get("name") for c in (stmt.get("manifest") or {}).get("schema", {}).get("columns", [])]
    if data:
        return [dict(zip(cols, r)) if cols else list(r) for r in data]
    aid = att.get("attachment_id")
    if not aid:
        return []
    try:
        res = _api("GET", f"/api/2.0/genie/spaces/{sid}/conversations/{cid}"
                          f"/messages/{mid}/attachments/{aid}/query-result")
    except GenieError:
        return []
    stmt = (res.get("statement_response") or res)
    data = (stmt.get("result") or {}).get("data_array") or []
    cols = [c.get("name") for c in (stmt.get("manifest") or {}).get("schema", {}).get("columns", [])]
    return [dict(zip(cols, r)) if cols else list(r) for r in data]


def _summarize(rows: list) -> str:
    if not rows:
        return "Genie returned no rows."
    first = rows[0]
    if isinstance(first, dict):
        vals = ", ".join(f"{k}={v}" for k, v in list(first.items())[:4])
        return f"Genie returned {len(rows)} row(s). First: {vals}."
    return f"Genie returned {len(rows)} row(s). First: {first}."
