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


def ask_genie(question: str) -> dict:
    """Ask Genie; return its SQL, result rows and text (all cited)."""
    sid = space_id()
    conv = _api("POST", f"/api/2.0/genie/spaces/{sid}/conversations", {})
    cid = conv.get("conversation_id") or conv.get("id")
    msg = _api("POST", f"/api/2.0/genie/spaces/{sid}/conversations/{cid}/messages",
               {"content": question})
    mid = msg.get("message_id") or msg.get("id")
    deadline = time.time() + TIMEOUT_SECONDS
    while True:
        cur = _api("GET", f"/api/2.0/genie/spaces/{sid}/conversations/{cid}/messages/{mid}")
        status = (cur.get("status") or cur.get("state") or "").upper()
        if status in ("SUCCEEDED", "COMPLETED", "FAILED", "ERROR", "CANCELLED"):
            break
        if time.time() > deadline:
            raise GenieError("Genie answer timed out")
        time.sleep(POLL_SECONDS)
    if status in ("FAILED", "ERROR", "CANCELLED"):
        raise GenieError(f"Genie could not answer: {(cur.get('error') or cur.get('message') or status)}")
    sql, rows, text = _extract(cur)
    return {"answer": text or _summarize(rows), "intent": "genie",
            "sources": [{"endpoint": "Genie Space", "params": {"space_id": sid}},
                        {"endpoint": "Genie SQL", "params": {"sql": sql}}],
            "sql": sql, "rows": rows}


def _extract(msg: dict) -> tuple[str, list, str]:
    """Pull (sql, rows, text) from a completed Genie message (shape-tolerant)."""
    sql, rows, texts = "", [], []
    attachments = msg.get("attachments") or msg.get("query_result") or []
    if isinstance(attachments, dict):
        attachments = [attachments]
    for att in attachments if isinstance(attachments, list) else []:
        if not isinstance(att, dict):
            continue
        q = att.get("query") or {}
        if isinstance(q, dict) and q.get("query"):
            sql = q["query"]
        data = att.get("data") or att.get("rows") or []
        if isinstance(data, list) and data:
            rows = data
        t = att.get("text") or (att.get("content") or "")
        if isinstance(t, str) and t.strip():
            texts.append(t.strip())
    content = msg.get("content")
    if isinstance(content, str) and content.strip():
        texts.append(content.strip())
    return sql, rows, "\n".join(texts).strip()


def _summarize(rows: list) -> str:
    if not rows:
        return "Genie returned no rows."
    first = rows[0]
    if isinstance(first, dict):
        vals = ", ".join(f"{k}={v}" for k, v in list(first.items())[:4])
        return f"Genie returned {len(rows)} row(s). First: {vals}."
    return f"Genie returned {len(rows)} row(s). First: {first}."
