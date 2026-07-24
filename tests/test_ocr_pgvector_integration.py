from __future__ import annotations

import os
import shutil
import uuid
from urllib.parse import urlparse

import pytest

from codebook_agent.backends.pgvector import PgVectorBackend
from codebook_agent.core import build_documents
from codebook_agent.embeddings import HashEmbeddingProvider
from tests.ocr_test_support import create_image_only_pdf


def _safe_test_database_url() -> str:
    database_url = os.getenv("CODEBOOK_TEST_DATABASE_URL", "").strip()
    if not database_url:
        pytest.skip("CODEBOOK_TEST_DATABASE_URL is not configured")
    parsed = urlparse(database_url)
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        pytest.fail("Real OCR/pgvector tests refuse non-local database hosts.")
    if "test" not in parsed.path.lower():
        pytest.fail("Real OCR/pgvector tests require a database name containing 'test'.")
    return database_url


@pytest.mark.ocr
@pytest.mark.pgvector
@pytest.mark.skipif(shutil.which("tesseract") is None, reason="Tesseract is not installed")
def test_image_only_pdf_is_ocrd_indexed_and_queryable(tmp_path):
    pytest.importorskip("pypdfium2")
    pytest.importorskip("PIL")
    pytest.importorskip("pypdf")
    database_url = _safe_test_database_url()
    schema = f"codebook_test_{uuid.uuid4().hex[:12]}"
    source = tmp_path / "synthetic-scan.pdf"
    create_image_only_pdf(source)
    profile = {
        "id": f"synthetic-scan-{uuid.uuid4().hex[:10]}",
        "title": "Synthetic Scanned Manual",
        "edition": "2026",
        "document_type": "training-manual",
        "backend": "pgvector",
        "questions": ["Authorized?"],
        "printed_page_offset": 0,
        "ocr": {
            "mode": "auto",
            "engine": "tesseract",
            "language": "eng",
            "dpi": 300,
            "page_segmentation_mode": 6,
            "min_native_characters": 20,
            "timeout_seconds": 120,
        },
    }
    documents = build_documents(profile, source)
    provider = HashEmbeddingProvider()
    backend = PgVectorBackend(database_url, schema=schema, min_pool_size=1, max_pool_size=2)
    try:
        backend.index_documents(
            profile=profile,
            documents=documents,
            embeddings=provider.embed([document.search_text for document in documents]),
            embedding_provider=provider.name,
            embedding_model=provider.model,
        )
        query = "What is the invented scan clearance?"
        results = backend.search(
            corpus_id=profile["id"],
            query=query,
            query_embedding=provider.embed([query])[0],
            limit=3,
        )

        assert results
        assert "forty-two training units" in results[0].document.content.lower()
        assert results[0].document.pdf_page_start == 1
        assert results[0].document.printed_page_start == 1
        assert results[0].document.metadata["extraction_method"] == "ocr-tesseract"
        assert "OCR confidence" in results[0].citation()
    finally:
        backend.close()
        import psycopg
        from psycopg import sql

        with psycopg.connect(database_url, autocommit=True) as connection:
            connection.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema))
            )
