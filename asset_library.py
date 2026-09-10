"""The media team's document corpus and how it becomes a searchable collection."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from embed import EMBED_DIMENSION, embed
from infrai_http import call

COLLECTION = "media-ops-docs"


@dataclass(frozen=True)
class DocChunk:
    doc_id: str
    area: str          # "ingest" | "processing" | "delivery"
    title: str
    text: str

    @property
    def vector_id(self) -> str:
        """Stable id derived from content, so re-running ingest overwrites instead of duplicating."""
        digest = hashlib.sha256(f"{self.doc_id}:{self.text}".encode()).hexdigest()[:24]
        return f"{self.doc_id}-{digest}"


def ensure_collection() -> None:
    call(
        "/v1/vector/collection/create",
        {
            "collection": COLLECTION,
            "dimension": EMBED_DIMENSION,
            "metric": "cosine",
            "metadata": {"owner": "media-ops"},
        },
    )


def index(chunks: list[DocChunk]) -> int:
    vectors = [
        {
            "id": chunk.vector_id,
            "embedding": vector,
            "metadata": {
                "doc_id": chunk.doc_id,
                "area": chunk.area,
                "title": chunk.title,
                "text": chunk.text,
            },
        }
        for chunk, vector in zip(chunks, embed([c.text for c in chunks]))
    ]
    call("/v1/vector/upsert", {"collection": COLLECTION, "vectors": vectors})
    return len(vectors)


def search(question: str, area: str | None, top_k: int) -> list[dict]:
    payload = {
        "collection": COLLECTION,
        "embedding": embed([question])[0],
        "top_k": top_k,
        "include_metadata": True,
    }
    if area:
        payload["filter"] = {"area": area}
    return call("/v1/vector/query", payload).get("matches", [])


def rerank(question: str, matches: list[dict], top_k: int) -> list[dict]:
    if not matches:
        return []
    candidates = [m.get("metadata", {}).get("text", "") for m in matches]
    ranked = call(
        "/v1/ai/rerank",
        {"query": question, "candidates": candidates, "top_k": top_k},
    ).get("results", [])
    out = []
    for item in ranked:
        idx = item.get("index", 0)
        if 0 <= idx < len(matches):
            out.append({**matches[idx], "score": item.get("score", 0.0)})
    return out
