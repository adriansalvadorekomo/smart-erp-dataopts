"""Document attachments (Phase 9): upload → process in background → list/get/delete/search.

POST /documents accepts pdf/md/txt/csv (≤20MB). Processing (parse/chunk/embed)
runs as a BackgroundTasks job; GET shows status uploaded → ready/failed.
POST /documents/search is the retrieval primitive the FM synthesis step
(Phase 9 increment 2) will call — grounded chunks with scores, no generation.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.core.db import get_db
from backend.app.models.entities import Document
from backend.app.services.documents import (
    delete_document,
    get_store,
    process_upload,
    retrieve,
)

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentRead(BaseModel):
    document_id: int
    filename: str
    mime_type: str
    size_bytes: int
    status: str
    error: str | None = None

    model_config = {"from_attributes": True}


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    k: int = Field(default=5, ge=1, le=20)


def _process(document_id: int, data: bytes) -> None:
    """Background worker: own session, outcome recorded on the row."""
    from backend.app.core.db import get_session_factory

    session = get_session_factory()()
    try:
        process_upload(session, document_id, data, get_store())
    finally:
        session.close()


@router.post("", response_model=DocumentRead, status_code=202)
def upload_document(file: UploadFile, background: BackgroundTasks,
                    session: Session = Depends(get_db)):
    data = file.file.read()
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="file exceeds 20 MB limit")
    from backend.app.services.documents import EXT_MIME

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in EXT_MIME:
        raise HTTPException(status_code=415, detail="pdf, md, txt, csv only")
    doc = Document(filename=file.filename or "upload", mime_type=EXT_MIME[ext],
                   size_bytes=len(data), volume_path=None, status="uploaded")
    session.add(doc)
    session.commit()
    session.refresh(doc)
    background.add_task(_process, doc.document_id, data)
    return doc


@router.get("", response_model=list[DocumentRead])
def list_documents(session: Session = Depends(get_db)):
    return session.query(Document).order_by(Document.document_id.desc()).all()


@router.get("/{document_id}", response_model=DocumentRead)
def read_document(document_id: int, session: Session = Depends(get_db)):
    doc = session.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"document {document_id} does not exist")
    return doc


@router.delete("/{document_id}", status_code=204)
def remove_document(document_id: int, session: Session = Depends(get_db)):
    from backend.app.services.orders import NotFound

    try:
        delete_document(session, document_id, get_store())
    except NotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return None


@router.post("/search")
def search_documents(payload: SearchRequest, session: Session = Depends(get_db)):
    return retrieve(session, payload.query, k=payload.k)
