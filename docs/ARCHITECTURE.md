# Architecture

## Boundaries

```text
source -> native extractor -> optional OCR fallback -> CodebookDocument v2.1 -> backend -> SearchResult -> answer renderer
```

- Extraction owns source identity and page evidence.
- Profiles own operator-controlled metadata and content ranges.
- Backends own persistence and ranking, not document meaning.
- Answer renderers consume retrieved evidence and cannot mutate an index.

## Document flow

`extract_pages` emits one `PageText` per PDF page. Text and Markdown fixtures use form-feed as an
optional synthetic page boundary. PDFs first use pypdf. In `auto` mode, pages without enough native
text are rendered locally through PDFium and processed by Tesseract. `PageText` retains the
extraction method and OCR confidence. `documents_from_pages` splits paragraphs without crossing pages,
carries generic article/section context forward, applies content types from configured page ranges,
and creates deterministic IDs.

Both local JSON and pgvector receive the same `CodebookDocument` representation. The JSON `metadata`
field is the extension point for another manual; stable evidence fields change only through a schema
version.

## OCR

OCR is deliberately an extraction adapter, not an answer model. It makes no network calls.
`off`, `auto`, and `always` modes are profile/CLI controlled. Tesseract TSV output is reconstructed
into paragraphs, and mean word confidence is carried into document metadata and citations.

The synthetic OCR regression creates an image-only PDF at test time, proves pypdf sees no text,
then exercises real PDFium rendering and Tesseract. The combined integration test indexes that
result in disposable pgvector and retrieves the invented wording.

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
