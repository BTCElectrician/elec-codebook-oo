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
SUPPORTED_EMBEDDING_PROVIDERS = {"hash", "openai"}
DEFAULT_EMBEDDING_MODELS = {
    "hash": "codebook-hash-v1",
    "openai": "text-embedding-3-small",
}
DEFAULT_OPENAI_BATCH_SIZE = 512


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
        batch_size: int = DEFAULT_OPENAI_BATCH_SIZE,
    ) -> None:
        if not api_key:
            raise ValueError("An OpenAI API key is required for the openai embedding provider.")
        if dimensions != EMBEDDING_DIMENSIONS:
            raise ValueError(f"This release requires {EMBEDDING_DIMENSIONS}-dimension embeddings.")
        if batch_size < 1:
            raise ValueError("OpenAI embedding batch_size must be positive.")
        try:
            from openai import OpenAI
        except ImportError as error:
            raise RuntimeError(
                "Install the optional AI dependencies with: pip install '.[ai]'"
            ) from error
        self.model = model
        self.dimensions = dimensions
        self.batch_size = batch_size
        self._client = OpenAI(api_key=api_key)

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        values = list(texts)
        embeddings: list[list[float]] = []
        for start in range(0, len(values), self.batch_size):
            batch = values[start : start + self.batch_size]
            response = self._client.embeddings.create(
                model=self.model,
                input=batch,
                dimensions=self.dimensions,
            )
            ordered = [
                item.embedding for item in sorted(response.data, key=lambda item: item.index)
            ]
            if len(ordered) != len(batch):
                raise RuntimeError("Embedding provider returned an unexpected result count.")
            embeddings.extend(ordered)
        return embeddings


def resolve_embedding_selection(
    profile: dict[str, object],
    *,
    provider_override: str | None = None,
    model_override: str | None = None,
) -> tuple[str, str]:
    """Resolve and validate an embedding contract without constructing a client."""

    config = profile.get("embedding")
    if config is not None and not isinstance(config, dict):
        raise TypeError("embedding must be an object.")
    configured_provider = config.get("provider") if isinstance(config, dict) else None
    configured_model = config.get("model") if isinstance(config, dict) else None
    if configured_provider is not None and not isinstance(configured_provider, str):
        raise TypeError("embedding.provider must be a string.")
    if configured_model is not None and not isinstance(configured_model, str):
        raise TypeError("embedding.model must be a string.")

    normalized_configured_provider = (
        configured_provider.strip().lower()
        if isinstance(configured_provider, str)
        else None
    )
    provider = (provider_override or configured_provider or "hash").strip().lower()
    if provider not in SUPPORTED_EMBEDDING_PROVIDERS:
        raise ValueError(
            f"Unknown embedding provider: {provider}. "
            f"Choose {', '.join(sorted(SUPPORTED_EMBEDDING_PROVIDERS))}."
        )
    if model_override:
        model = model_override
    elif provider_override and provider != normalized_configured_provider:
        model = DEFAULT_EMBEDDING_MODELS[provider]
    else:
        model = configured_model or DEFAULT_EMBEDDING_MODELS[provider]
    model = model.strip()
    if not model:
        raise ValueError("embedding.model cannot be empty.")
    if provider == "hash" and model != DEFAULT_EMBEDDING_MODELS["hash"]:
        raise ValueError(
            f"The hash provider supports only model {DEFAULT_EMBEDDING_MODELS['hash']}."
        )
    return provider, model


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
