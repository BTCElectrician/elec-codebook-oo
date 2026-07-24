# Status

## Current state

Version 0.4.0 implements evidence-preserving ingestion, real local OCR fallback, optional
model-based OCR correction, generic structure/table recovery, and citation-validated synthesis.
Local JSON/JSONL remains the default. PostgreSQL/pgvector is the implemented searchable backend.

## Implemented

- Generic metadata-only profile and optional NFPA reference profile
- No-write/no-connection plan and dry-run with exact apply destination and provider boundary
- Page-preserving text, Markdown, and optional pypdf extraction
- Automatic local PDFium rendering plus Tesseract OCR for low-text/image-only pages
- Per-document extraction method and OCR confidence provenance
- Immutable raw page evidence plus selected text in local JSON and pgvector
- Optional OpenAI OCR correction with protected-token, similarity, and length-change gates
- Generic heading, definition, note, list, and explicitly continued table recovery
- Source SHA-256, PDF/printed pages, content types, article/section context
- Versioned `CodebookDocument` and `SearchResult` contracts
- Local JSON and JSONL
- Deterministic hash embeddings for offline plumbing/tests
- Optional batched OpenAI 1,536-dimension embedding adapter
- PostgreSQL migration, atomic upserts, stale cleanup, GIN full-text, HNSW vectors
- Hybrid reciprocal-rank-fusion retrieval
- Search/query CLI, deterministic extractive answers, and optional citation-validated synthesis
- No-connection `answer --plan` for provider/data-boundary review
- Mock-free disposable pgvector integration test with production guards
- Quote-safe Tesseract TSV parsing and same-content source-rename provenance refresh

## Not implemented

- Edition-specific NEC parsing or geometric diagram/table interpretation
- Visual model transcription adjudication
- Azure AI Search, LanceDB, Qdrant, or OpenSearch adapters
- Hosted service, authentication, or multi-user access control

## Validation

Default:

```bash
make check
git diff --check
```

Real pgvector:

```bash
make pgvector-up
make test-pgvector
make pgvector-down
```
