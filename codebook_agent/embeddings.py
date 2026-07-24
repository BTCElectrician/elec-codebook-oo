"""Embedding providers isolated from ingestion and storage backends."""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise
from typing import Protocol

from .models import EMBEDDING_DIMENSIONS

TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:\.[a-z0-9]+)*")


class EmbeddingProvider(Protocol):
    """Provider contract used for both indexing and queries."""

    name: str
    model: str
    dimensions: int

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed texts in order."""


@dataclass(frozen=True)
class HashEmbeddingProvider:
    """Deterministic, dependency-free embedding for tutorials and tests.

    This is a signed feature-hashing representation, not a substitute for a
    semantic model. It makes the complete pgvector path locally testable.
    """

    dimensions: int = EMBEDDING_DIMENSIONS
    name: str = "hash"
    model: str = "codebook-hash-v1"

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = TOKEN_PATTERN.findall(text.lower())
        features = tokens + [f"{left}::{right}" for left, right in pairwise(tokens)]
        for feature in features:
            digest = hashlib.sha256(feature.encode("utf-8")).digest()
            index = int.from_bytes(digest[:8], "big") % self.dimensions
            sign = 1.0 if digest[8] & 1 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm:
            return [value / norm for value in vector]
        return vector


class OpenAIEmbeddingProvider:
    """Optional OpenAI embedding provider matching the legacy 1,536-D contract."""

    name = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "text-embedding-3-small",
        dimensions: int = EMBEDDING_DIMENSIONS,
    ) -> None:
        if not api_key:
            raise ValueError("An OpenAI API key is required for the openai embedding provider.")
        if dimensions != EMBEDDING_DIMENSIONS:
            raise ValueError(f"This release requires {EMBEDDING_DIMENSIONS}-dimension embeddings.")
        try:
            from openai import OpenAI
        except ImportError as error:
            raise RuntimeError("Install the optional AI dependencies with: pip install '.[ai]'") from error
        self.model = model
        self.dimensions = dimensions
        self._client = OpenAI(api_key=api_key)

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        response = self._client.embeddings.create(
            model=self.model,
            input=list(texts),
            dimensions=self.dimensions,
        )
        return [item.embedding for item in sorted(response.data, key=lambda item: item.index)]


def build_embedding_provider(
    name: str,
    *,
    api_key: str | None = None,
    model: str | None = None,
) -> EmbeddingProvider:
    """Resolve a named provider without importing optional SDKs prematurely."""

    normalized = name.strip().lower()
    if normalized == "hash":
        return HashEmbeddingProvider()
    if normalized == "openai":
        return OpenAIEmbeddingProvider(
            api_key=api_key or "",
            model=model or "text-embedding-3-small",
        )
    raise ValueError(f"Unknown embedding provider: {name}. Choose hash or openai.")
