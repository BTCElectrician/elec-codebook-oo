"""Deterministic, evidence-only answers built from retrieval results."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .models import SearchResult
from .text_models import TextModelProvider


@dataclass(frozen=True)
class GroundedAnswer:
    """An answer whose complete support is visible to the caller."""

    query: str
    text: str
    sources: list[SearchResult]
    mode: str = "extractive"
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "query": self.query,
            "mode": self.mode,
            "answer": self.text,
            "sources": [result.to_dict() for result in self.sources],
            "metadata": self.metadata,
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


def synthesize_answer(
    query: str,
    results: list[SearchResult],
    *,
    provider: TextModelProvider,
) -> GroundedAnswer:
    """Synthesize only from supplied evidence; fail closed to exact passages."""

    fallback = answer_from_results(query, results)
    if not results:
        return fallback
    evidence = []
    for number, result in enumerate(results, start=1):
        evidence.append(
            f"[S{number}] {result.document.content}\nLocator: {result.citation()}"
        )
    generated = provider.generate(
        system_prompt=(
            "Answer only from the supplied source passages. Cite every factual sentence with "
            "one or more source labels such as [S1]. Do not use outside knowledge. If the "
            "evidence is insufficient, say so and cite the relevant evidence."
        ),
        user_prompt=f"Question: {query}\n\nEvidence:\n" + "\n\n".join(evidence),
    ).strip()
    citations = re.findall(r"\[S(\d+)\]", generated)
    metadata: dict[str, object] = {
        "requested_mode": "synthesized",
        "provider": provider.name,
        "model": provider.model,
    }
    if not citations:
        return GroundedAnswer(
            query=query,
            text=fallback.text,
            sources=results,
            metadata={**metadata, "fallback_reason": "missing_citations"},
        )
    if any(int(value) < 1 or int(value) > len(results) for value in citations):
        return GroundedAnswer(
            query=query,
            text=fallback.text,
            sources=results,
            metadata={**metadata, "fallback_reason": "invalid_citations"},
        )
    return GroundedAnswer(
        query=query,
        text=generated,
        sources=results,
        mode="synthesized",
        metadata={**metadata, "citation_validation": "passed"},
    )
