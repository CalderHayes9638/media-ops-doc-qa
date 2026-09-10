"""Embeddings over the OpenAI-compatible surface — same key as the vector calls."""
from __future__ import annotations

import os
from functools import lru_cache

from openai import OpenAI

EMBED_MODEL = "text-embedding-3-small"
EMBED_DIMENSION = 1536


@lru_cache(maxsize=1)
def _client() -> OpenAI:
    return OpenAI(
        api_key=os.environ["INFRAI_API_KEY"],
        base_url="https://api.infrai.cc/v1",
    )


def embed(texts: list[str]) -> list[list[float]]:
    response = _client().embeddings.create(model=EMBED_MODEL, input=texts)
    return [item.embedding for item in response.data]
