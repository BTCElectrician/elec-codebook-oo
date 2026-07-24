# Architecture

## Boundaries

```text
source -> extractor -> CodebookDocument v2 -> backend -> SearchResult -> answer renderer
```

- Extraction owns source identity and page evidence.
- Profiles own operator-controlled metadata and content ranges.
- Backends own persistence and ranking, not document meaning.
- Answer renderers consume retrieved evidence and cannot mutate an index.

## Document flow

`extract_pages` emits one `PageText` per PDF page. Text and Markdown fixtures use form-feed as an
optional synthetic page boundary. `documents_from_pages` splits paragraphs without crossing pages,
carries generic article/section context forward, applies content types from configured page ranges,
and creates deterministic IDs.

Both local JSON and pgvector receive the same `CodebookDocument` representation. The JSON `metadata`
field is the extension point for another manual; stable evidence fields change only through a schema
version.

## pgvector

The adapter uses a bounded Psycopg connection pool. Migrations create the vector extension and an
isolated schema, then create `corpora` and `documents`. Indexing upserts the corpus and documents and
deletes stale documents in one transaction.

Search obtains vector and full-text candidates independently, then combines their ranks with
reciprocal-rank fusion. Results are converted back into backend-neutral `SearchResult` objects.

The SQL migration is packaged at `codebook_agent/backends/sql/001_pgvector.sql`.

## Safety

Planning never constructs a database client. Pgvector operations require `CODEBOOK_DATABASE_URL`;
the URL is never printed. Integration tests reject non-local hosts and database names without
`test`, use a unique schema, log phases as JSON lines, and remove the schema after each run.
