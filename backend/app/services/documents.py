"""Document attachments pipeline (Phase 9): parse → chunk → embed → retrieve.

- Bytes live in a VolumeStore (Databricks UC Volume in prod, local dir for
  dev/test) — the backend never assumes Databricks credentials exist.
- Text + vectors live in public.documents / public.document_chunks.
- Embeddings are local (all-MiniLM-L6-v2, 384d, L2-normalized) via the
  already-present CPU torch; retrieval is exact brute-force cosine (right
  scale for tens/hundreds of docs — Vector Search only if that changes).
- The Databricks FM synthesis step (Phase 9 increment 2) consumes
  retrieve(); this module never calls an LLM.
"""
from __future__ import annotations

import io
import os
import time

import numpy as np
from sqlalchemy.orm import Session

from backend.app.models.entities import Document, DocumentChunk

CHUNK_WORDS = 400
CHUNK_OVERLAP = 80
MAX_CHUNKS = 2000
MAX_BYTES = 20 * 1024 * 1024
MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"

EXT_MIME = {
    ".pdf": "application/pdf",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".txt": "text/plain",
    ".csv": "text/csv",
}


class DocumentError(Exception):
    pass


# ── volume stores ──────────────────────────────────────────────────────────

class VolumeStore:
    def put(self, stored_name: str, data: bytes) -> str:
        raise NotImplementedError

    def delete(self, stored_name: str) -> None:
        raise NotImplementedError


class LocalVolumeStore(VolumeStore):
    """Dev/test store: plain directory (default keeps repo clean via gitignore)."""

    def __init__(self, root: str):
        self.root = root
        os.makedirs(root, exist_ok=True)

    def _path(self, stored_name: str) -> str:
        if "/" in stored_name or stored_name.startswith("."):
            raise DocumentError("bad stored name")
        return os.path.join(self.root, stored_name)

    def put(self, stored_name: str, data: bytes) -> str:
        with open(self._path(stored_name), "wb") as f:
            f.write(data)
        return self._path(stored_name)

    def delete(self, stored_name: str) -> None:
        try:
            os.remove(self._path(stored_name))
        except FileNotFoundError:
            pass


class DatabricksVolumeStore(VolumeStore):
    """Prod store: UC Volume via the Files API (needs DATABRICKS_HOST/TOKEN)."""

    VOLUME_DIR = "/Volumes/workspace/bronze/documents"

    def __init__(self, host: str, token: str):
        import urllib.request

        self._opener = urllib.request.build_opener()
        self._base = (host.rstrip("/"), {"Authorization": f"Bearer {token}"})

    def _request(self, method: str, path: str, data: bytes | None = None):
        import urllib.request

        host, headers = self._base
        req = urllib.request.Request(f"{host}{path}", data=data, headers=headers, method=method)
        with self._opener.open(req, timeout=300) as res:
            res.read()

    def put(self, stored_name: str, data: bytes) -> str:
        from urllib.parse import quote

        remote = f"{self.VOLUME_DIR}/{quote(stored_name)}"
        self._request("PUT", f"/api/2.0/fs/files{remote}?overwrite=true", data)
        return remote

    def delete(self, stored_name: str) -> None:
        from urllib.parse import quote

        try:
            self._request("DELETE", f"/api/2.0/fs/files{self.VOLUME_DIR}/{quote(stored_name)}")
        except Exception:
            pass  # orphan cleanup is best-effort; DB row is source of truth


def get_store(root: str | None = None) -> VolumeStore:
    host, token = os.environ.get("DATABRICKS_HOST", ""), os.environ.get("DATABRICKS_TOKEN", "")
    if host and token:
        return DatabricksVolumeStore(host, token)
    return LocalVolumeStore(root or os.environ.get("DOC_STORE_DIR", "data/documents-local"))


# ── parse + chunk (pure, unit-tested without models) ────────────────────────

def parse_bytes(filename: str, data: bytes) -> tuple[str, str]:
    """Return (mime, text). Raises DocumentError on unsupported/empty/oversize."""
    if len(data) > MAX_BYTES:
        raise DocumentError(f"file exceeds {MAX_BYTES // (1024*1024)} MB limit")
    ext = os.path.splitext(filename)[1].lower()
    mime = EXT_MIME.get(ext)
    if mime is None:
        raise DocumentError(f"unsupported type {ext!r} (pdf, md, txt, csv only)")
    if ext == ".pdf":
        from pypdf import PdfReader

        try:
            pages = PdfReader(io.BytesIO(data)).pages
        except Exception as e:
            raise DocumentError(f"unreadable PDF: {e}") from e
        text = "\n".join((p.extract_text() or "") for p in pages)
    else:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as e:
            raise DocumentError(f"not valid UTF-8: {e}") from e
    if not text.strip():
        raise DocumentError("no extractable text")
    return mime, text


def chunk_text(text: str, size: int = CHUNK_WORDS, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Deterministic word-window chunking (overlap keeps boundary context)."""
    words = text.split()
    if not words:
        return []
    step = max(size - overlap, 1)
    return [" ".join(words[i:i + size]) for i in range(0, len(words), step)][:MAX_CHUNKS]


# ── embed + retrieve ───────────────────────────────────────────────────────

_embedder = None


def _get_embedder():
    global _embedder
    if _embedder is None:
        import torch
        from transformers import AutoModel, AutoTokenizer

        tok = AutoTokenizer.from_pretrained(MODEL_ID)
        mdl = AutoModel.from_pretrained(MODEL_ID)
        mdl.eval()
        _embedder = (tok, mdl, torch)
    return _embedder


def embed_texts(texts: list[str]) -> list[list[float]]:
    """L2-normalized MiniLM embeddings (module-level seam for tests to stub)."""
    import backend.app.services.documents as mod

    return mod._embed_real(texts)


def _embed_real(texts: list[str]) -> list[list[float]]:
    tok, mdl, torch = _get_embedder()
    out: list[list[float]] = []
    for i in range(0, len(texts), 32):
        enc = tok(texts[i:i + 32], padding=True, truncation=True,
                  max_length=512, return_tensors="pt")
        with torch.no_grad():
            hidden = mdl(**enc).last_hidden_state
            mask = enc["attention_mask"].unsqueeze(-1).float()
            vec = (hidden * mask).sum(1) / mask.sum(1).clamp(min=1e-9)
            vec = vec / vec.norm(dim=1, keepdim=True).clamp(min=1e-12)
        out.extend(vec.tolist())
    return out


def process_upload(session: Session, document_id: int, data: bytes,
                   store: VolumeStore, actor: str = "api") -> Document:
    """Fill a pending row: volume put → parse → chunk → embed. Outcome is
    always recorded (ready/failed); never half-written without a status."""
    from backend.app.models.entities import AuditLog
    from backend.app.services.orders import NotFound

    doc = session.get(Document, document_id)
    if doc is None:
        raise NotFound(f"document {document_id} does not exist")
    try:
        mime, text = parse_bytes(doc.filename, data)
        chunks = chunk_text(text)
        safe = "".join(c if c.isalnum() or c in "._-" else "_"
                       for c in os.path.basename(doc.filename))
        stored = f"{int(time.time() * 1000)}_{safe}"
        doc.volume_path = store.put(stored, data)
        doc.mime_type = mime
        vectors = embed_texts(chunks)
        for idx, (content, vec) in enumerate(zip(chunks, vectors)):
            session.add(DocumentChunk(document_id=doc.document_id, chunk_index=idx,
                                      content=content, embedding=[float(x) for x in vec]))
        doc.status, doc.error = "ready", None
    except Exception as e:  # noqa: BLE001 — recorded, not raised
        doc.status, doc.error = "failed", f"{type(e).__name__}: {str(e)[:300]}"
        chunks = []
    session.add(AuditLog(table_name="documents", row_pk=str(doc.document_id),
                         action="insert",
                         details={"filename": doc.filename,
                                  "chunks": len(chunks), "status": doc.status},
                         actor=actor))
    session.commit()
    session.refresh(doc)
    return doc


def retrieve(session: Session, query: str, k: int = 5) -> list[dict]:
    """Top-k chunks by cosine (embeddings are L2-normalized → dot product)."""
    rows = session.query(DocumentChunk, Document.filename).join(
        Document, Document.document_id == DocumentChunk.document_id).filter(
        Document.status == "ready", DocumentChunk.embedding.isnot(None)).all()
    if not rows or not query.strip():
        return []
    q = np.array(embed_texts([query])[0], dtype=float)
    scored = []
    for chunk, filename in rows:
        v = np.array(chunk.embedding, dtype=float)
        if v.shape != q.shape:
            continue
        scored.append((float(q @ v), chunk, filename))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [{"document": fn, "chunk_index": c.chunk_index,
             "content": c.content, "score": round(s, 4)}
            for s, c, fn in scored[: max(k, 1)]]


def delete_document(session: Session, document_id: int, store: VolumeStore) -> None:
    doc = session.get(Document, document_id)
    if doc is None:
        from backend.app.services.orders import NotFound

        raise NotFound(f"document {document_id} does not exist")
    if doc.volume_path:
        store.delete(doc.volume_path.rsplit("/", 1)[-1])
    session.delete(doc)  # chunks cascade
    session.commit()
