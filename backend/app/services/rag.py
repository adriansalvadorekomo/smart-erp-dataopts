"""Doc-grounded Q&A (Phase 9): retrieve local chunks → synthesize via FM API.

Veracity design (the whole point): the model sees ONLY retrieved chunks, is
instructed to answer strictly from them, and the response carries the exact
chunks used. Empty retrieval → explicit unknown (never generation).
LLM: Databricks FM API (default endpoint env FM_ENDPOINT); host/token from
the standard DATABRICKS_* env (backend runtime secret, never committed).
"""
from __future__ import annotations

import json
import os
import urllib.request

from sqlalchemy.orm import Session

from backend.app.services.documents import retrieve

SYSTEM = (
    "You answer business questions using ONLY the provided document excerpts. "
    "Rules: (1) every factual claim must come from the excerpts; "
    "(2) quote or name the source document for each claim; "
    "(3) if the excerpts do not contain the answer, say exactly "
    "'I cannot answer from the attached documents.' and stop; "
    "(4) keep answers under 120 words."
)


class FMError(Exception):
    pass


def fm_chat(messages: list[dict], max_tokens: int = 512) -> str:
    """Chat completion against the FM serving endpoint. Raises FMError."""
    host = os.environ.get("DATABRICKS_HOST", "").rstrip("/")
    token = os.environ.get("DATABRICKS_TOKEN", "")
    endpoint = os.environ.get("FM_ENDPOINT", "databricks-gpt-oss-120b")
    if not host or not token:
        raise FMError("DATABRICKS_HOST/DATABRICKS_TOKEN are not configured")
    req = urllib.request.Request(
        f"{host}/serving-endpoints/{endpoint}/invocations",
        data=json.dumps({"messages": messages, "max_tokens": max_tokens}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as res:
            body = json.load(res)
    except Exception as e:  # noqa: BLE001 — surfaced cleanly
        raise FMError(f"FM call failed: {type(e).__name__}: {str(e)[:200]}") from e
    try:
        parts = (body["choices"][0]["message"]["content"] or [])
        texts = [p["text"] for p in parts if isinstance(p, dict) and p.get("type") == "text"]
        if not texts and isinstance(body["choices"][0]["message"].get("content"), str):
            texts = [body["choices"][0]["message"]["content"]]
        return "\n".join(texts).strip()
    except (KeyError, IndexError, TypeError) as e:
        raise FMError(f"unexpected FM response shape: {str(body)[:200]}") from e


def ask_docs(session: Session, question: str, k: int = 5) -> dict:
    """Grounded answer from attached documents (retrieve → synthesize → cite)."""
    hits = retrieve(session, question, k=k)
    if not hits:
        return {"answer": "I cannot answer from the attached documents.",
                "intent": "docs", "sources": []}
    context = "\n\n".join(
        f"[Excerpt {i+1} — {h['document']}, chunk {h['chunk_index']}]\n{h['content']}"
        for i, h in enumerate(hits))
    answer = fm_chat([
        {"role": "system", "content": SYSTEM},
        {"role": "user",
         "content": f"Question: {question}\n\nDocument excerpts:\n{context}"},
    ])
    return {"answer": answer, "intent": "docs",
            "sources": [{"endpoint": "POST /documents/search", "params": {"k": k},
                         "document": h["document"], "chunk_index": h["chunk_index"],
                         "score": h["score"]} for h in hits]}
