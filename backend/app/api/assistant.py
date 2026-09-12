"""Grounded Q&A over governed data (Phase 9, increment 1).

POST /ai/ask {question} → {answer, intent, sources}. Deterministic:
intents match in services/assistant.py, numbers computed live from the
stats/orders/forecast services. Unknown questions return capabilities,
never invented facts.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
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


class AskResponse(BaseModel):
    answer: str
    intent: str
    sources: list[Source]


@router.post("/ask", response_model=AskResponse)
def ask_question(payload: AskRequest, session: Session = Depends(get_db)):
    result = ask(session, payload.question)
    return AskResponse(
        answer=result["answer"],
        intent=result["intent"],
        sources=[Source(endpoint=s["endpoint"], params=s.get("params", {}))
                 for s in result["sources"]],
    )
