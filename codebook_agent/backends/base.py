"""Protocols shared by retrieval backends."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from ..models import CodebookDocument, PageText, SearchResult


class RetrievalBackend(Protocol):
    """Minimum contract for an index that can ingest and retrieve evidence."""

    def index_documents(
        self,
        *,
        profile: dict[str, object],
        documents: Sequence[CodebookDocument],
        embeddings: Sequence[Sequence[float]],
        embedding_provider: str,
        embedding_model: str,
        pages: Sequence[PageText] | None = None,
    ) -> int:
        """Atomically replace a corpus with the supplied documents."""

    def search(
        self,
        *,
        corpus_id: str,
        query: str,
        query_embedding: Sequence[float],
        limit: int,
        content_types: Sequence[str] | None = None,
    ) -> list[SearchResult]:
        """Run backend-native hybrid retrieval."""
