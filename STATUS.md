# Status

## Current state

Version 0.3 implements evidence-preserving ingestion, real local OCR fallback, and a
backend-neutral retrieval contract.
Local JSON/JSONL remains the default. PostgreSQL/pgvector is the implemented searchable backend.

## Implemented

- Generic metadata-only profile and optional NFPA reference profile
- No-write/no-connection plan and dry-run
- Page-preserving text, Markdown, and optional pypdf extraction
- Automatic local PDFium rendering plus Tesseract OCR for low-text/image-only pages
- Per-document extraction method and OCR confidence provenance
- Source SHA-256, PDF/printed pages, content types, article/section context
- Versioned `CodebookDocument` and `SearchResult` contracts
- Local JSON and JSONL
- Deterministic hash embeddings for offline plumbing/tests
- Optional OpenAI 1,536-dimension embedding adapter
- PostgreSQL migration, atomic upserts, stale cleanup, GIN full-text, HNSW vectors
- Hybrid reciprocal-rank-fusion retrieval
- Search/query CLI and deterministic evidence-grounded answers
- Mock-free disposable pgvector integration test with production guards

## Not implemented

- Edition-specific NEC parsing or multi-page table reconstruction
- Model-based OCR correction or transcription adjudication
- Generative answer synthesis
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
