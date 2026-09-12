"""Grounded Q&A over governed data (Phase 9, increment 1).

POST /ai/ask {question} → {answer, intent, sources}. Deterministic:
intents match in services/assistant.py, numbers computed live from the
stats/orders/forecast services. Unknown questions return capabilities,
never invented facts.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.core.db import get_db
from backend.app.services.assistant import ask

router = APIRouter(prefix="/ai", tags=["ai"])


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class Source(BaseModel):
    endpoint: str
    params: dict = {}
    document: str | None = None
    chunk_index: int | None = None
    score: float | None = None


def _to_sources(result: dict) -> list[Source]:
    return [Source(endpoint=s["endpoint"], params=s.get("params", {}),
                   document=s.get("document"), chunk_index=s.get("chunk_index"),
                   score=s.get("score")) for s in result["sources"]]


class AskResponse(BaseModel):
    answer: str
    intent: str
    sources: list[Source]


@router.post("/ask", response_model=AskResponse)
def ask_question(payload: AskRequest, session: Session = Depends(get_db)):
    result = ask(session, payload.question)
    return AskResponse(answer=result["answer"], intent=result["intent"],
                       sources=_to_sources(result))


class GenieResponse(BaseModel):
    answer: str
    intent: str
    sources: list[Source]
    sql: str = ""
    rows: list = []


@router.post("/ask-docs", response_model=AskResponse)
def ask_documents(payload: AskRequest, session: Session = Depends(get_db)):
    from backend.app.services.rag import FMError, ask_docs

    try:
        result = ask_docs(session, payload.question)
    except FMError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return AskResponse(answer=result["answer"], intent=result["intent"],
                       sources=_to_sources(result))


@router.post("/ask-genie", response_model=GenieResponse)
def ask_genie(payload: AskRequest):
    from backend.app.services.genie import GenieError
    from backend.app.services.genie import ask_genie as _ask_genie

    try:
        result = _ask_genie(payload.question)
    except GenieError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return GenieResponse(
        answer=result["answer"],
        intent=result["intent"],
        sources=_to_sources(result),
        sql=result.get("sql", ""),
        rows=result.get("rows", [])[:50],
    )
