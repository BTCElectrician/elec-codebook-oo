# Backend truth

| Backend | Status | Writes | Retrieval |
| --- | --- | --- | --- |
| `local-artifacts` | Implemented | Local JSON and JSONL | No |
| `pgvector` | Implemented | Configured PostgreSQL | Hybrid full-text and vector |
| LanceDB | Candidate | None | None |
| Qdrant | Candidate | None | None |
| OpenSearch | Candidate | None | None |

An implemented retrieval backend must accept `CodebookDocument` v2.2, return `SearchResult`, preserve
all evidence fields, isolate optional dependencies, document its write boundary, and pass a
real-service test.

## pgvector behavior

The pgvector adapter:

- stores a corpus-level source and embedding contract;
- stores `vector(1536)` next to native or explicitly OCR-derived evidence and JSON metadata;
- stores raw/selected page text and correction provenance separately from chunks;
- generates a `tsvector` with the `simple` configuration;
- builds GIN and HNSW indexes;
- performs atomic replacement indexing;
- supports content-type filtering; and
- fuses text and vector ranks.

Backend parity means the same query surface and evidence fields, not identical ranking scores.
