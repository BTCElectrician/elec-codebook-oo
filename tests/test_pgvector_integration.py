from __future__ import annotations

import json
import os
import sys
import time
import uuid
from urllib.parse import urlparse

import pytest

from codebook_agent.answers import answer_from_results
from codebook_agent.backends.pgvector import PgVectorBackend
from codebook_agent.core import build_documents
from codebook_agent.embeddings import HashEmbeddingProvider


def _log(event: str, **data: object) -> None:
    print(
        json.dumps(
            {
                "suite": "pgvector-e2e",
                "event": event,
                "time_ns": time.time_ns(),
                "data": data,
            },
            sort_keys=True,
        ),
        file=sys.stderr,
    )


def _safe_test_database_url() -> str:
    database_url = os.getenv("CODEBOOK_TEST_DATABASE_URL", "").strip()
    if not database_url:
        pytest.skip("CODEBOOK_TEST_DATABASE_URL is not configured")
    parsed = urlparse(database_url)
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        pytest.fail("Real pgvector tests refuse non-local database hosts.")
    if "test" not in parsed.path.lower():
        pytest.fail("Real pgvector tests require a database name containing 'test'.")
    return database_url


@pytest.mark.pgvector
def test_real_pgvector_ingest_hybrid_search_and_grounded_answer(tmp_path):
    database_url = _safe_test_database_url()
    schema = f"codebook_test_{uuid.uuid4().hex[:12]}"
    source = tmp_path / "synthetic-manual.txt"
    source.write_text(
        "Synthetic Field Manual\f"
        "Article 3. Underground Training\n\n"
        "3.1 Minimum Cover\n\n"
        "For this invented exercise, the minimum training cover is twenty-four units.\f"
        "Article 4. Motors\n\n"
        "4.1 Disconnect\n\n"
        "The fictional motor disconnect is within sight.",
        encoding="utf-8",
    )
    profile = {
        "id": f"synthetic-{uuid.uuid4().hex[:10]}",
        "title": "Synthetic Field Manual",
        "edition": "2026",
        "document_type": "training-manual",
        "backend": "pgvector",
        "questions": ["Authorized?"],
        "printed_page_offset": 1,
        "content_ranges": {"main": [1, 3]},
    }
    documents = build_documents(profile, source)
    provider = HashEmbeddingProvider()
    embeddings = provider.embed([document.search_text for document in documents])
    backend = PgVectorBackend(database_url, schema=schema, min_pool_size=1, max_pool_size=2)
    _log("setup", schema=schema, documents=len(documents))
    try:
        count = backend.index_documents(
            profile=profile,
            documents=documents,
            embeddings=embeddings,
            embedding_provider=provider.name,
            embedding_model=provider.model,
        )
        _log("indexed", count=count)
        assert count == len(documents)

        query = "What is the minimum training cover underground?"
        results = backend.search(
            corpus_id=profile["id"],
            query=query,
            query_embedding=provider.embed([query])[0],
            limit=3,
        )
        _log(
            "searched",
            result_count=len(results),
            top_id=results[0].document.id if results else None,
        )
        assert results
        assert "twenty-four units" in results[0].document.content
        assert results[0].document.pdf_page_start == 2
        assert results[0].document.printed_page_start == 1
        assert results[0].text_score is not None
        assert results[0].vector_score is not None

        answer = answer_from_results(query, results[:1])
        assert "twenty-four units" in answer.text
        assert "PDF page 2" in answer.text
        assert "printed page 1" in answer.text

        config = backend.corpus_config(profile["id"])
        assert config["embedding_provider"] == "hash"
        assert config["embedding_dimensions"] == 1536

        renamed_source = tmp_path / "renamed-synthetic-manual.txt"
        renamed_source.write_bytes(source.read_bytes())
        renamed_documents = build_documents(profile, renamed_source)
        assert [document.id for document in renamed_documents] == [
            document.id for document in documents
        ]
        backend.index_documents(
            profile=profile,
            documents=renamed_documents,
            embeddings=provider.embed([document.search_text for document in renamed_documents]),
            embedding_provider=provider.name,
            embedding_model=provider.model,
        )
        renamed_results = backend.search(
            corpus_id=profile["id"],
            query=query,
            query_embedding=provider.embed([query])[0],
            limit=3,
        )
        assert renamed_results[0].document.source_name == renamed_source.name
        assert renamed_source.name in renamed_results[0].citation()

        renamed_source.write_text(
            "Synthetic Field Manual\f"
            "Article 3. Underground Training\n\n"
            "3.1 Minimum Cover\n\n"
            "The revised invented training cover is thirty units.\f"
            "Article 4. Motors\n\n"
            "4.1 Disconnect\n\n"
            "The fictional motor disconnect is within sight.",
            encoding="utf-8",
        )
        revised_documents = build_documents(profile, renamed_source)
        revised_count = backend.index_documents(
            profile=profile,
            documents=revised_documents,
            embeddings=provider.embed([document.search_text for document in revised_documents]),
            embedding_provider=provider.name,
            embedding_model=provider.model,
        )
        revised_query = "What is the revised training cover?"
        revised_results = backend.search(
            corpus_id=profile["id"],
            query=revised_query,
            query_embedding=provider.embed([revised_query])[0],
            limit=3,
        )
        assert revised_count == len(revised_documents)
        assert "thirty units" in revised_results[0].document.content
        assert all("twenty-four units" not in result.document.content for result in revised_results)
        _log("asserted", result="pass")
    finally:
        backend.close()
        import psycopg
        from psycopg import sql

        with psycopg.connect(database_url, autocommit=True) as connection:
            connection.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema)))
        _log("cleanup", schema=schema)
