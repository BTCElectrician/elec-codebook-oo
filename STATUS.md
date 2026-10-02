# Status

## Current state

Version 0.7.0 adds confidence-scored guided-configuration candidates to its local source inspection
and metadata-only profile generation, evidence-preserving ingestion, real local OCR fallback, optional
model-based OCR correction, generic structure/table recovery, and citation-validated synthesis.
Local JSON/JSONL remains the default. PostgreSQL/pgvector is the implemented searchable backend.
Unreleased on `main` (document schema 2.3): article/section identity comes only from headings that
open a chunk, repeated page-edge lines are excluded from chunks and identity, duplicate chunks are
collapsed with their other locations, document ids are local to their page span, and default model
names live in `codebook_agent/model_defaults.py`.

The repository also exposes a vendor-neutral agent contract: canonical authority/current-state/
change-map entry points, one-call machine orientation, command and output discovery, stable exit
semantics, teaching errors with safe typo recovery, preview-first cleanup, and drift-guard tests.
The guided `configure` workflow inspects authorized PDF/text/Markdown sources locally, reports page
and native-text density without returning extracted text, separates observed facts from
confidence-scored deterministic candidates, names unresolved operator decisions, proposes safe
metadata-only settings, and writes only behind `--apply`. It does not make candidates authoritative.

## Implemented

- Authorization-gated local source inspection and apply-gated metadata-only profile generation
- Deterministic profile proposal JSON with OCR readiness, observed facts, confidence/evidence-labeled
  candidates, unresolved decisions, and next commands
- Conservative local candidates for filename edition, repeated edge page labels, exact semantic
  markers, and coarse layout shape; no candidate silently changes edition, page offset, or ranges
- Generic metadata-only profile and optional NFPA reference profile
- No-write/no-connection plan and dry-run with exact apply destination and provider boundary
- Page-preserving text, Markdown, and optional pypdf extraction
- Automatic local PDFium rendering plus Tesseract OCR for low-text/image-only pages
- Per-document extraction method and OCR confidence provenance
- Immutable raw page evidence plus selected text in local JSON and pgvector
- Optional OpenAI OCR correction with protected-token, similarity, and length-change gates
- Generic heading, definition, note, list, and explicitly continued table recovery
- Heading-derived article/section identity: no identity from number-led prose, prose references,
  sentence-continuation lines, split continuations, or running headers; a new article clears the
  previous section; mid-paragraph headings start a new chunk
- Running header/footer exclusion from chunk text (`page_furniture`, default `auto`) with page
  evidence unchanged
- Duplicate-chunk collapse with `metadata.duplicate_locations` and citation mention
- Page-span-local deterministic document ids; pgvector re-ingest that tolerates moved ids and
  rejects duplicate ids or chunk numbers
- Single registry for default model names, reported by `capabilities --json`
- Atomic local write of `documents.json` and `pages.json`
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

- Universal or authoritative document understanding; inferred candidates still require operator
  confirmation before they become edition, printed-page mapping, semantic ranges, or schema choices
- Model-assisted source-configuration inference; this slice is deterministic and local-only
- Edition-specific NEC parsing or geometric diagram/table interpretation
- Part/Chapter scope inside an article; page-geometry header/footer detection
- Use of the HNSW index by the hybrid query (vector candidates are ranked exactly)
- Anthropic or other non-OpenAI text-model providers
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

Verified locally on 2026-10-02 for the unreleased schema 2.3 changes (Python 3.11, macOS):

- `make check`: 118 passed, 3 real-service tests skipped by the credential-free default lane;
- focused CLI/agent contract lane: 70 passed;
- real local OCR lane: 1 passed, 1 skipped (its pgvector half runs in the pgvector lane);
- disposable pgvector lane (pgvector 0.8.7): 3 passed, including re-ingest after chunk renumbering
  and OCR-to-retrieval;
- full suite on Python 3.13 with the disposable database: 121 passed;
- 12 of the 15 identity regression tests fail on the v0.7.0 code and pass now; the other 3 guard
  against over-correction.
