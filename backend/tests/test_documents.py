"""Document pipeline contract tests (model stubbed; one real-embedding test)."""
from __future__ import annotations

import io

import pytest

from backend.app.services import documents as docs


def test_chunking_deterministic_overlap():
    words = [f"w{i}" for i in range(1000)]
    chunks = docs.chunk_text(" ".join(words), size=400, overlap=80)
    assert len(chunks) == 4  # ceil((1000-400)/320)+1
    assert chunks[0].split()[:3] == ["w0", "w1", "w2"]
    assert chunks[1].split()[:3] == ["w320", "w321", "w322"]
    assert chunks[0].split()[-80:] == chunks[1].split()[:80]
    assert docs.chunk_text("   ") == []


def test_parse_rejects():
    with pytest.raises(docs.DocumentError):
        docs.parse_bytes("evil.exe", b"data")
    with pytest.raises(docs.DocumentError):
        docs.parse_bytes("empty.txt", b"   ")
    with pytest.raises(docs.DocumentError):
        docs.parse_bytes("big.txt", b"x" * (docs.MAX_BYTES + 1))
    mime, text = docs.parse_bytes("note.md", "# Title\nhello".encode())
    assert mime == "text/markdown" and "hello" in text


def test_upload_ready_delete_flow(client, session, tmp_path, monkeypatch):
    store = docs.LocalVolumeStore(str(tmp_path))
    monkeypatch.setattr(docs, "get_store", lambda: store)
    monkeypatch.setattr(docs, "embed_texts",
                        lambda texts: [[1.0 if "alpha" in t else 0.0,
                                        0.0 if "alpha" in t else 1.0] for t in texts])

    r = client.post("/documents", files={"file": ("report.md", io.BytesIO(
        ("alpha " + " ".join(f"w{i}" for i in range(1, 400)) + " "
         + " ".join(f"beta{i}" for i in range(400))).encode()), "text/markdown")})
    assert r.status_code == 202
    doc_id = r.json()["document_id"]

    r = client.get(f"/documents/{doc_id}")
    assert r.json()["status"] == "ready"  # TestClient runs background tasks inline

    r = client.post("/documents/search", json={"query": "alpha growth", "k": 5})
    hits = r.json()
    assert [h["chunk_index"] for h in hits] == [0, 1, 2]  # alpha chunk first

    r = client.get("/documents")
    assert any(d["document_id"] == doc_id for d in r.json())

    assert client.delete(f"/documents/{doc_id}").status_code == 204
    assert client.get(f"/documents/{doc_id}").status_code == 404
    assert client.delete("/documents/999999999").status_code == 404


def test_upload_rejects_bad_type(client):
    r = client.post("/documents", files={"file": ("x.exe", io.BytesIO(b"zz"), "application/octet-stream")})
    assert r.status_code == 415


def test_failed_status_recorded(client, session, tmp_path, monkeypatch):
    store = docs.LocalVolumeStore(str(tmp_path))
    monkeypatch.setattr(docs, "get_store", lambda: store)

    def boom(texts):
        raise RuntimeError("no model here")

    monkeypatch.setattr(docs, "embed_texts", boom)
    r = client.post("/documents", files={"file": ("ok.txt", io.BytesIO(b"hello world"), "text/plain")})
    doc_id = r.json()["document_id"]
    body = client.get(f"/documents/{doc_id}").json()
    assert body["status"] == "failed" and "no model here" in (body["error"] or "")


def test_real_embedding_smoke():
    vecs = docs.embed_texts(["hello world"])
    assert len(vecs) == 1 and len(vecs[0]) == 384
    norm = sum(x * x for x in vecs[0]) ** 0.5
    assert abs(norm - 1.0) < 1e-5
