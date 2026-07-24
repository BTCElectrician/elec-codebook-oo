"""Deterministic, evidence-only answers built from retrieval results."""

from __future__ import annotations

from dataclasses import dataclass

from .models import SearchResult


@dataclass(frozen=True)
class GroundedAnswer:
    """An answer whose complete support is visible to the caller."""

    query: str
    text: str
    sources: list[SearchResult]
    mode: str = "extractive"

    def to_dict(self) -> dict[str, object]:
        return {
            "query": self.query,
            "mode": self.mode,
            "answer": self.text,
            "sources": [result.to_dict() for result in self.sources],
        }


def answer_from_results(query: str, results: list[SearchResult]) -> GroundedAnswer:
    """Return extracted wording and citations without inventing missing conclusions."""

    if not results:
        return GroundedAnswer(
            query=query,
            text="No supporting passage was found in the selected corpus.",
            sources=[],
        )

    blocks = ["The highest-ranked supporting passages are:"]
    for number, result in enumerate(results, start=1):
        blocks.append(f"\n{number}. {result.document.content}\n   Source: {result.citation()}")
    return GroundedAnswer(query=query, text="\n".join(blocks), sources=results)
