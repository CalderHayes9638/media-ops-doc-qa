"""The one decision this service makes: answer, or route the question to a human."""
from __future__ import annotations

from dataclasses import dataclass

# A reranked passage below this score is not close enough to quote back to a creator.
MIN_SCORE = 0.45
# Ops questions get answered from at least two agreeing passages.
MIN_PASSAGES = 2


@dataclass(frozen=True)
class Verdict:
    status: str            # "answered" | "escalated"
    reason: str
    citations: list[dict]


def decide(passages: list[dict]) -> Verdict:
    strong = [p for p in passages if p.get("score", 0.0) >= MIN_SCORE]
    if len(strong) < MIN_PASSAGES:
        return Verdict(
            status="escalated",
            reason=f"only {len(strong)} passage(s) cleared {MIN_SCORE}",
            citations=strong,
        )
    return Verdict(
        status="answered",
        reason=f"{len(strong)} passages cleared {MIN_SCORE}",
        citations=strong,
    )
