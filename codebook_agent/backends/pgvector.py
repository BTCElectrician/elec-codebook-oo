"""PostgreSQL + pgvector storage and hybrid retrieval adapter."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from importlib.resources import files
from typing import Any, Self

from ..models import EMBEDDING_DIMENSIONS, CodebookDocument, SearchResult

SCHEMA_PATTERN = re.compile(r"^[a-z_][a-z0-9_]*$")
QUERY_WORD_PATTERN = re.compile(r"[a-z0-9]+(?:\.[a-z0-9]+)*")
QUESTION_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "do",
    "does",
    "for",
    "how",
    "in",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
}


def _postgres_imports() -> tuple[Any, Any, Any, Any, Any]:
    try:
        import psycopg
        from pgvector.psycopg import register_vector
        from psycopg import sql
        from psycopg.types.json import Jsonb
        from psycopg_pool import ConnectionPool
    except ImportError as error:
        raise RuntimeError(
            "PostgreSQL support is optional. Install it with: pip install '.[postgres]'"
        ) from error
    return psycopg, register_vector, sql, Jsonb, ConnectionPool


def _full_text_query(query: str) -> str:
    """Build a permissive websearch query from meaningful question terms."""

    terms = [
        term
        for term in QUERY_WORD_PATTERN.findall(query.lower())
        if term not in QUESTION_STOP_WORDS
    ]
    if not terms:
        return query
    return " OR ".join(f'"{term}"' for term in dict.fromkeys(terms))


class PgVectorBackend:
    """Atomic corpus indexing and hybrid vector/full-text retrieval."""

    def __init__(
        self,
        database_url: str,
        *,
        schema: str = "codebook",
        min_pool_size: int = 1,
        max_pool_size: int = 4,
    ) -> None:
        if not database_url:
            raise ValueError("A PostgreSQL database URL is required.")
        if not SCHEMA_PATTERN.fullmatch(schema):
            raise ValueError("Schema names must use lowercase letters, digits, and underscores.")
        _, _, _, _, connection_pool = _postgres_imports()
        self.schema = schema
        self._pool = connection_pool(
            conninfo=database_url,
            min_size=min_pool_size,
            max_size=max_pool_size,
            open=True,
            kwargs={"autocommit": False},
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()

    def close(self) -> None:
        self._pool.close()

    def ensure_schema(self) -> None:
        """Apply the idempotent schema migration."""

        _, register_vector, sql, _, _ = _postgres_imports()
        template = files("codebook_agent.backends.sql").joinpath("001_pgvector.sql").read_text(encoding="utf-8")
        migration = sql.SQL(template).format(schema=sql.Identifier(self.schema))
        with self._pool.connection() as connection, connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
            connection.commit()
            register_vector(connection)
            cursor.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(self.schema)))
            cursor.execute(migration)

    def corpus_config(self, corpus_id: str) -> dict[str, Any]:
        """Read the embedding contract required to query a corpus."""

        _, _, sql, _, _ = _postgres_imports()
        query = sql.SQL(
            """
            SELECT id, title, edition, document_type, source_name, source_sha256,
                   document_schema_version, embedding_provider, embedding_model,
                   embedding_dimensions, metadata
            FROM {}.corpora
            WHERE id = %s
            """
        ).format(sql.Identifier(self.schema))
        with self._pool.connection() as connection, connection.cursor() as cursor:
            cursor.execute(query, (corpus_id,))
            row = cursor.fetchone()
        if row is None:
            raise FileNotFoundError(f"Corpus not found in pgvector: {corpus_id}")
        keys = (
            "id",
            "title",
            "edition",
            "document_type",
            "source_name",
            "source_sha256",
            "document_schema_version",
            "embedding_provider",
            "embedding_model",
            "embedding_dimensions",
            "metadata",
        )
        return dict(zip(keys, row))

    def index_documents(
        self,
        *,
        profile: dict[str, object],
        documents: Sequence[CodebookDocument],
        embeddings: Sequence[Sequence[float]],
        embedding_provider: str,
        embedding_model: str,
    ) -> int:
        """Atomically replace one corpus, using upserts and stale-row deletion."""

        if not documents:
            raise ValueError("Refusing to index an empty corpus.")
        if len(documents) != len(embeddings):
            raise ValueError("Document and embedding counts differ.")
        if any(len(embedding) != EMBEDDING_DIMENSIONS for embedding in embeddings):
            raise ValueError(f"Every embedding must have {EMBEDDING_DIMENSIONS} dimensions.")

        self.ensure_schema()
        _, register_vector, sql, Jsonb, _ = _postgres_imports()
        corpus_id = documents[0].corpus_id
        if any(document.corpus_id != corpus_id for document in documents):
            raise ValueError("A single indexing operation cannot mix corpus IDs.")

        corpus_query = sql.SQL(
            """
            INSERT INTO {}.corpora (
                id, title, edition, document_type, source_name, source_sha256,
                document_schema_version, embedding_provider, embedding_model,
                embedding_dimensions, metadata, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
            ON CONFLICT (id) DO UPDATE SET
                title = excluded.title,
                edition = excluded.edition,
                document_type = excluded.document_type,
                source_name = excluded.source_name,
                source_sha256 = excluded.source_sha256,
                document_schema_version = excluded.document_schema_version,
                embedding_provider = excluded.embedding_provider,
                embedding_model = excluded.embedding_model,
                embedding_dimensions = excluded.embedding_dimensions,
                metadata = excluded.metadata,
                updated_at = now()
            """
        ).format(sql.Identifier(self.schema))
        document_query = sql.SQL(
            """
            INSERT INTO {}.documents (
                id, corpus_id, source_name, source_sha256, chunk_number, content,
                search_text, content_type, pdf_page_start, pdf_page_end,
                printed_page_start, printed_page_end, article_number, article_title,
                section_number, section_title, edition, document_type, metadata,
                document_schema_version, content_hash, embedding, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now()
            )
            ON CONFLICT (id) DO UPDATE SET
                content = excluded.content,
                search_text = excluded.search_text,
                content_type = excluded.content_type,
                pdf_page_start = excluded.pdf_page_start,
                pdf_page_end = excluded.pdf_page_end,
                printed_page_start = excluded.printed_page_start,
                printed_page_end = excluded.printed_page_end,
                article_number = excluded.article_number,
                article_title = excluded.article_title,
                section_number = excluded.section_number,
                section_title = excluded.section_title,
                edition = excluded.edition,
                document_type = excluded.document_type,
                metadata = excluded.metadata,
                document_schema_version = excluded.document_schema_version,
                content_hash = excluded.content_hash,
                embedding = excluded.embedding,
                updated_at = now()
            """
        ).format(sql.Identifier(self.schema))
        delete_stale_query = sql.SQL(
            "DELETE FROM {}.documents WHERE corpus_id = %s AND NOT (id = ANY(%s))"
        ).format(sql.Identifier(self.schema))

        first = documents[0]
        with self._pool.connection() as connection, connection.cursor() as cursor:
            register_vector(connection)
            cursor.execute(
                corpus_query,
                (
                    corpus_id,
                    str(profile["title"]),
                    profile.get("edition"),
                    str(profile["document_type"]),
                    first.source_name,
                    first.source_sha256,
                    first.schema_version,
                    embedding_provider,
                    embedding_model,
                    EMBEDDING_DIMENSIONS,
                    Jsonb({"profile": profile}),
                ),
            )
            rows = []
            for document, embedding in zip(documents, embeddings):
                rows.append(
                    (
                        document.id,
                        document.corpus_id,
                        document.source_name,
                        document.source_sha256,
                        document.chunk_number,
                        document.content,
                        document.search_text,
                        document.content_type,
                        document.pdf_page_start,
                        document.pdf_page_end,
                        document.printed_page_start,
                        document.printed_page_end,
                        document.article_number,
                        document.article_title,
                        document.section_number,
                        document.section_title,
                        document.edition,
                        document.document_type,
                        Jsonb(document.metadata),
                        document.schema_version,
                        hashlib.sha256(document.content.encode("utf-8")).hexdigest(),
                        list(embedding),
                    )
                )
            cursor.execute(delete_stale_query, (corpus_id, [document.id for document in documents]))
            cursor.executemany(document_query, rows)
        return len(documents)

    def search(
        self,
        *,
        corpus_id: str,
        query: str,
        query_embedding: Sequence[float],
        limit: int = 5,
        content_types: Sequence[str] | None = None,
    ) -> list[SearchResult]:
        """Fuse vector and PostgreSQL full-text ranks with reciprocal-rank fusion."""

        if not query.strip():
            raise ValueError("Search query cannot be empty.")
        if len(query_embedding) != EMBEDDING_DIMENSIONS:
            raise ValueError(f"Query embedding must have {EMBEDDING_DIMENSIONS} dimensions.")
        if limit < 1 or limit > 100:
            raise ValueError("Search limit must be between 1 and 100.")

        _, register_vector, sql, _, _ = _postgres_imports()
        type_filter = sql.SQL("")
        type_parameters: list[object] = []
        if content_types:
            type_filter = sql.SQL(" AND content_type = ANY(%s)")
            type_parameters.append(list(content_types))
        candidate_limit = max(limit * 4, 20)
        statement = sql.SQL(
            """
            WITH query_input AS (
                SELECT websearch_to_tsquery('simple'::regconfig, %s) AS query
            ),
            vector_matches AS (
                SELECT id,
                       row_number() OVER (ORDER BY embedding <=> %s::vector) AS vector_rank,
                       1 - (embedding <=> %s::vector) AS vector_score
                FROM {schema}.documents
                WHERE corpus_id = %s {type_filter}
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            ),
            text_matches AS (
                SELECT id,
                       row_number() OVER (
                           ORDER BY ts_rank_cd(search_vector, query_input.query) DESC
                       ) AS text_rank,
                       ts_rank_cd(search_vector, query_input.query) AS text_score
                FROM {schema}.documents, query_input
                WHERE corpus_id = %s
                  AND search_vector @@ query_input.query
                  {type_filter}
                ORDER BY text_score DESC
                LIMIT %s
            ),
            fused AS (
                SELECT id,
                       max(vector_rank) AS vector_rank,
                       max(vector_score) AS vector_score,
                       max(text_rank) AS text_rank,
                       max(text_score) AS text_score
                FROM (
                    SELECT id, vector_rank, vector_score, NULL::bigint AS text_rank,
                           NULL::real AS text_score
                    FROM vector_matches
                    UNION ALL
                    SELECT id, NULL::bigint, NULL::double precision, text_rank, text_score
                    FROM text_matches
                ) candidates
                GROUP BY id
            )
            SELECT d.id, d.corpus_id, d.source_name, d.source_sha256, d.chunk_number,
                   d.content, d.search_text, d.content_type, d.pdf_page_start,
                   d.pdf_page_end, d.printed_page_start, d.printed_page_end,
                   d.article_number, d.article_title, d.section_number, d.section_title,
                   d.edition, d.document_type, d.metadata, d.document_schema_version,
                   (
                       coalesce(1.0 / (60 + fused.vector_rank), 0.0)
                       + coalesce(1.0 / (60 + fused.text_rank), 0.0)
                   ) AS hybrid_score,
                   fused.vector_score,
                   fused.text_score
            FROM fused
            JOIN {schema}.documents d ON d.id = fused.id
            ORDER BY hybrid_score DESC, d.id
            LIMIT %s
            """
        ).format(
            schema=sql.Identifier(self.schema),
            type_filter=type_filter,
        )
        vector = list(query_embedding)
        parameters: list[object] = [_full_text_query(query), vector, vector, corpus_id]
        parameters.extend(type_parameters)
        parameters.extend([vector, candidate_limit, corpus_id])
        parameters.extend(type_parameters)
        parameters.extend([candidate_limit, limit])
        with self._pool.connection() as connection, connection.cursor() as cursor:
            register_vector(connection)
            cursor.execute(statement, parameters)
            rows = cursor.fetchall()

        results: list[SearchResult] = []
        for row in rows:
            document = CodebookDocument(
                id=row[0],
                corpus_id=row[1],
                source_name=row[2],
                source_sha256=row[3],
                chunk_number=row[4],
                content=row[5],
                search_text=row[6],
                content_type=row[7],
                pdf_page_start=row[8],
                pdf_page_end=row[9],
                printed_page_start=row[10],
                printed_page_end=row[11],
                article_number=row[12],
                article_title=row[13],
                section_number=row[14],
                section_title=row[15],
                edition=row[16],
                document_type=row[17],
                metadata=row[18],
                schema_version=row[19],
            )
            results.append(
                SearchResult(
                    document=document,
                    score=float(row[20]),
                    vector_score=float(row[21]) if row[21] is not None else None,
                    text_score=float(row[22]) if row[22] is not None else None,
                )
            )
        return results
