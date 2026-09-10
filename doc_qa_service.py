"""HTTP entry point: POST /ask over the media team's asset, job and delivery docs."""
from __future__ import annotations

from typing import Literal

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from answer_policy import decide
from asset_library import rerank, search
from infrai_http import InfraiError

app = FastAPI(title="media-ops doc QA")


class AskRequest(BaseModel):
    question: str = Field(min_length=8, max_length=500)
    area: Literal["ingest", "processing", "delivery"] | None = None
    top_k: int = Field(default=8, ge=1, le=25)


class Citation(BaseModel):
    title: str
    doc_id: str
    score: float
    text: str


class AskResponse(BaseModel):
    status: Literal["answered", "escalated"]
    reason: str
    citations: list[Citation]


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    matches = search(request.question, request.area, request.top_k)
    passages = rerank(request.question, matches, top_k=4)
    verdict = decide(passages)
    return AskResponse(
        status=verdict.status,
        reason=verdict.reason,
        citations=[
            Citation(
                title=c.get("metadata", {}).get("title", ""),
                doc_id=c.get("metadata", {}).get("doc_id", ""),
                score=c.get("score", 0.0),
                text=c.get("metadata", {}).get("text", ""),
            )
            for c in verdict.citations
        ],
    )


@app.exception_handler(InfraiError)
def infrai_error_handler(_, exc: InfraiError) -> JSONResponse:
    status = exc.status if 400 <= exc.status < 500 else 502
    return JSONResponse(status_code=status, content={"error": exc.code, "detail": exc.message})
