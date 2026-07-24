# Status

## Current state

Version 0.5.0 implements evidence-preserving ingestion, real local OCR fallback, optional
model-based OCR correction, generic structure/table recovery, and citation-validated synthesis.
Local JSON/JSONL remains the default. PostgreSQL/pgvector is the implemented searchable backend.

The repository also exposes a vendor-neutral agent contract: canonical authority/current-state/
change-map entry points, one-call machine orientation, command and output discovery, stable exit
semantics, teaching errors with safe typo recovery, preview-first cleanup, and drift-guard tests.

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
- Cross-model entry adapters that defer to one canonical `AGENTS.md`
- `agent --json`, `capabilities --json`, `schema --json`, and `robot-docs guide`
- Model-neutral conversation contract for understand/explain/change/run/verify intent
- Deterministic stdout data, stderr diagnostics, and documented exit/retry semantics
- Intent-to-owner code map and parser/contract/documentation drift guards
- Preview-first cleanup with explicit `clean --apply`
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

## Latest verified acceptance

Verified locally on 2026-07-24:

- `make check`: 86 passed, 2 real-service tests skipped by the credential-free default lane;
- real local OCR lane: passed;
- disposable pgvector lane: 2 passed, including OCR-to-retrieval;
- agent determinism, stdout/stderr separation, and non-TTY discipline: passed;
- v0.5.0 Docker wheel/image build: passed;
- packaged `agent --json` entrypoint and non-root UID 10001 runtime: passed;
- disposable pgvector container, network, and volume removed after validation.
