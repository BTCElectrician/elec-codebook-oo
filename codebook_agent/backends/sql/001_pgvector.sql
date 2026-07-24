CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS {schema}.corpora (
    id text PRIMARY KEY,
    title text NOT NULL,
    edition text,
    document_type text NOT NULL,
    source_name text NOT NULL,
    source_sha256 text NOT NULL,
    document_schema_version text NOT NULL,
    embedding_provider text NOT NULL,
    embedding_model text NOT NULL,
    embedding_dimensions integer NOT NULL CHECK (embedding_dimensions = 1536),
    metadata jsonb NOT NULL DEFAULT '{{}}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS {schema}.documents (
    id text PRIMARY KEY,
    corpus_id text NOT NULL REFERENCES {schema}.corpora(id) ON DELETE CASCADE,
    source_name text NOT NULL,
    source_sha256 text NOT NULL,
    chunk_number bigint NOT NULL,
    content text NOT NULL,
    search_text text NOT NULL,
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('simple'::regconfig, coalesce(search_text, ''))
    ) STORED,
    content_type text NOT NULL,
    pdf_page_start integer NOT NULL CHECK (pdf_page_start > 0),
    pdf_page_end integer NOT NULL CHECK (pdf_page_end >= pdf_page_start),
    printed_page_start integer,
    printed_page_end integer,
    article_number text,
    article_title text,
    section_number text,
    section_title text,
    edition text,
    document_type text,
    metadata jsonb NOT NULL DEFAULT '{{}}'::jsonb,
    document_schema_version text NOT NULL,
    content_hash text NOT NULL,
    embedding vector(1536) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (corpus_id, chunk_number)
);

CREATE INDEX IF NOT EXISTS documents_corpus_id_idx
    ON {schema}.documents (corpus_id);
CREATE INDEX IF NOT EXISTS documents_corpus_type_page_idx
    ON {schema}.documents (corpus_id, content_type, pdf_page_start);
CREATE INDEX IF NOT EXISTS documents_search_vector_idx
    ON {schema}.documents USING gin (search_vector);
CREATE INDEX IF NOT EXISTS documents_embedding_hnsw_idx
    ON {schema}.documents USING hnsw (embedding vector_cosine_ops);
