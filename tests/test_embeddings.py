import math
from types import SimpleNamespace

from codebook_agent.embeddings import HashEmbeddingProvider, OpenAIEmbeddingProvider
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


def test_openai_embeddings_are_batched_and_preserve_input_order():
    calls = []

    class FakeEmbeddings:
        def create(self, *, model, input, dimensions):
            calls.append(
                {
                    "model": model,
                    "input": list(input),
                    "dimensions": dimensions,
                }
            )
            return SimpleNamespace(
                data=[
                    SimpleNamespace(index=index, embedding=[float(value)])
                    for index, value in reversed(list(enumerate(input)))
                ]
            )

    provider = OpenAIEmbeddingProvider.__new__(OpenAIEmbeddingProvider)
    provider.model = "synthetic-embedding-model"
    provider.dimensions = EMBEDDING_DIMENSIONS
    provider.batch_size = 2
    provider._client = SimpleNamespace(embeddings=FakeEmbeddings())

    result = provider.embed(["1", "2", "3", "4", "5"])

    assert [call["input"] for call in calls] == [["1", "2"], ["3", "4"], ["5"]]
    assert result == [[1.0], [2.0], [3.0], [4.0], [5.0]]


def test_openai_embeddings_skip_provider_call_for_empty_input():
    class FailIfCalled:
        def create(self, **kwargs):
            raise AssertionError(f"provider should not be called: {kwargs}")

    provider = OpenAIEmbeddingProvider.__new__(OpenAIEmbeddingProvider)
    provider.model = "synthetic-embedding-model"
    provider.dimensions = EMBEDDING_DIMENSIONS
    provider.batch_size = 2
    provider._client = SimpleNamespace(embeddings=FailIfCalled())

    assert provider.embed([]) == []
