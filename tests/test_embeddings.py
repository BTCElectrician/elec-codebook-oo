import math

from codebook_agent.embeddings import HashEmbeddingProvider
from codebook_agent.models import EMBEDDING_DIMENSIONS


def test_hash_embeddings_are_deterministic_normalized_and_fixed_width():
    provider = HashEmbeddingProvider()
    first, second = provider.embed(["branch circuit outlet", "branch circuit outlet"])

    assert first == second
    assert len(first) == EMBEDDING_DIMENSIONS
    assert math.isclose(sum(value * value for value in first), 1.0)


def test_hash_embeddings_preserve_token_overlap_signal():
    provider = HashEmbeddingProvider()
    query, related, unrelated = provider.embed(
        [
            "minimum cover underground raceway",
            "underground raceway minimum training cover",
            "motor ventilation disconnect",
        ]
    )

    related_score = sum(left * right for left, right in zip(query, related))
    unrelated_score = sum(left * right for left, right in zip(query, unrelated))
    assert related_score > unrelated_score
