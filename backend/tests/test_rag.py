"""RAG + Genie contract tests (external calls stubbed at the HTTP seam)."""
from __future__ import annotations

import io
import json


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self._payload).encode()


def _fm_ok(body: dict) -> _FakeResponse:
    return _FakeResponse({
        "choices": [{"message": {"content": [{"type": "text",
                                              "text": "Revenue grew on electronics per Q1 report."}]}}]
    })


def test_ask_docs_grounded_citations(client, session, tmp_path, monkeypatch):
    import backend.app.services.documents as docs
    import backend.app.services.rag as rag

    store = docs.LocalVolumeStore(str(tmp_path))
    monkeypatch.setattr(docs, "get_store", lambda: store)
    monkeypatch.setattr(docs, "embed_texts", lambda texts: [[1.0, 0.0] for _ in texts])
    monkeypatch.setattr(rag, "fm_chat", lambda messages, max_tokens=512: (
        "Electronics drove growth. [Q1 report]"
        if any("Excerpt" in m.get("content", "") for m in messages
               if isinstance(m.get("content"), str))
        else "I cannot answer from the attached documents."))

    client.post("/documents", files={"file": ("q1.md", io.BytesIO(
        b"# Q1\nElectronics revenue grew strongly this quarter"), "text/markdown")})
    r = client.post("/ai/ask-docs", json={"question": "What drove growth in Q1?"})
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "docs"
    assert "Electronics" in body["answer"]
    assert body["sources"] and body["sources"][0]["document"] == "q1.md"


def test_ask_docs_empty_unknown(client):
    r = client.post("/ai/ask-docs", json={"question": "anything at all?"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"] == "I cannot answer from the attached documents."
    assert body["sources"] == []


def test_ask_docs_fm_failure_502(client, session, tmp_path, monkeypatch):
    import backend.app.services.documents as docs
    import backend.app.services.rag as rag

    store = docs.LocalVolumeStore(str(tmp_path))
    monkeypatch.setattr(docs, "get_store", lambda: store)
    monkeypatch.setattr(docs, "embed_texts", lambda texts: [[1.0, 0.0] for _ in texts])

    def boom(messages, max_tokens=512):
        from backend.app.services.rag import FMError
        raise FMError("down")

    monkeypatch.setattr(rag, "fm_chat", boom)
    client.post("/documents", files={"file": ("q.md", io.BytesIO(b"hello world"), "text/plain")})
    r = client.post("/ai/ask-docs", json={"question": "hello?"})
    assert r.status_code == 502


def test_ask_genie_relays_sql_and_rows(client, monkeypatch):
    import backend.app.services.genie as genie

    def fake(question: str):
        assert "revenue" in question
        return {"answer": "Total revenue.", "intent": "genie",
                "sources": [{"endpoint": "Genie Space", "params": {}}],
                "sql": "SELECT SUM(final_price) FROM workspace.gold.fact_sales",
                "rows": [{"SUM(final_price)": 9938876984.9}]}

    monkeypatch.setattr(genie, "ask_genie", fake)
    r = client.post("/ai/ask-genie", json={"question": "total revenue?"})
    assert r.status_code == 200
    body = r.json()
    assert "SUM(final_price)" in body["sql"]
    assert body["rows"][0]["SUM(final_price)"] == 9938876984.9


def test_ask_genie_unconfigured_502(client, monkeypatch):
    import backend.app.services.genie as genie

    def boom(question: str):
        from backend.app.services.genie import GenieError
        raise GenieError("GENIE_SPACE_ID is not set")

    monkeypatch.setattr(genie, "ask_genie", boom)
    r = client.post("/ai/ask-genie", json={"question": "revenue?"})
    assert r.status_code == 502
    assert "GENIE_SPACE_ID" in r.json()["detail"]
