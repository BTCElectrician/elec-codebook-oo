# Architecture

## Boundaries

```text
source -> native extractor -> optional OCR -> optional correction -> structure -> CodebookDocument v2.2 -> backend -> SearchResult -> answer
```

- Extraction owns source identity and page evidence.
- Profiles own operator-controlled metadata and content ranges.
- Backends own persistence and ranking, not document meaning.
- Answer renderers consume retrieved evidence and cannot mutate an index.

## Document flow

`extract_pages` emits one `PageText` per PDF page. Text and Markdown fixtures use form-feed as an
optional synthetic page boundary. PDFs first use pypdf. In `auto` mode, pages without enough native
text are rendered locally through PDFium and processed by Tesseract. `PageText` retains raw and
selected text, extraction/OCR provenance, and any correction decision. The structure pass labels
generic blocks and joins explicitly continued delimited tables. `documents_from_pages` carries
generic article/section context forward, applies content types, and creates deterministic IDs.

Both local JSON and pgvector receive the same `CodebookDocument` representation. Local
`pages.json` and the pgvector `pages` table preserve the raw page record independently from
retrieval chunks. The JSON `metadata` field is the extension point for another manual; stable
evidence fields change only through a schema version.

## OCR

OCR is deliberately an extraction adapter, not an answer model. It makes no network calls.
`off`, `auto`, and `always` modes are profile/CLI controlled. Tesseract TSV output is reconstructed
into paragraphs with tab-delimited, quote-neutral parsing, and mean word confidence is carried into
document metadata and citations. Auto mode constructs the OCR adapter only when at least one page
actually needs OCR.

## Model correction

Correction is off by default and provider-neutral behind a small text-generation protocol. The
current optional adapter uses OpenAI. `ocr-only` sends only Tesseract-derived page text; `all` sends
every extracted page. Protected identifiers/measurements, similarity, and length-change validators
must all pass. Accepted corrections retain `ocr-tesseract` extraction provenance and add correction
provenance. Rejected candidates leave raw text selected.

## Structure recovery

The deterministic structure adapter recognizes generic headings, definitions, notes/warnings,
lists, and body text. It normalizes delimited tables to Markdown and joins adjacent pages only when
they share an explicit table/schedule identifier. Recovered table documents carry start/end pages
and the complete source-page list.

The synthetic OCR regression creates an image-only PDF at test time, proves pypdf sees no text,
then exercises real PDFium rendering and Tesseract. The combined integration test indexes that
result in disposable pgvector and retrieves the invented wording.

## pgvector

The adapter uses a bounded Psycopg connection pool. Migrations create the vector extension and an
isolated schema, then create `corpora`, `documents`, and `pages`. Indexing upserts the corpus,
documents, and page evidence and deletes stale rows in one transaction.

Search obtains vector and full-text candidates independently, then combines their ranks with
reciprocal-rank fusion. Results are converted back into backend-neutral `SearchResult` objects.

## Answers

Extractive mode formats retrieved passages without a generation call. Synthesized mode builds an
evidence frame with `[S#]` labels and asks the selected text provider to answer only from that
frame. The validator rejects missing or unknown evidence labels and returns the extractive answer
instead.

The SQL migration is packaged at `codebook_agent/backends/sql/001_pgvector.sql`.

## Safety

Planning never constructs a database, embedding, or text-model client. It resolves the exact
artifact path or PostgreSQL schema and reports whether a selected provider would receive
`search_text`, extracted page text, or retrieved evidence. Pgvector operations require
`CODEBOOK_DATABASE_URL`; the URL is never printed. Ingest verifies PostgreSQL before a paid
provider call. Integration tests reject non-local hosts
and database names without `test`, use a unique schema, log phases as JSON lines, and remove the
schema after each run.
