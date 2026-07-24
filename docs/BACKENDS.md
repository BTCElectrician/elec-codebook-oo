# Backend truth

| Backend | Status | Writes | Retrieval |
| --- | --- | --- | --- |
| `local-artifacts` | Implemented | Local JSON and JSONL | No |
| `pgvector` | Implemented | Configured PostgreSQL | Hybrid full-text and vector |
| `azure-ai-search` | Not implemented here | None | None |
| LanceDB | Candidate | None | None |
| Qdrant | Candidate | None | None |
| OpenSearch | Candidate | None | None |

An implemented retrieval backend must accept `CodebookDocument` v2, return `SearchResult`, preserve
all evidence fields, isolate optional dependencies, document its write boundary, and pass a
real-service test.

## pgvector behavior

The pgvector adapter:

- stores a corpus-level source and embedding contract;
- stores `vector(1536)` next to native or explicitly OCR-derived evidence and JSON metadata;
- generates a `tsvector` with the `simple` configuration;
- builds GIN and HNSW indexes;
- performs atomic replacement indexing;
- supports content-type filtering; and
- fuses text and vector ranks.

The adapter does not claim identical scores to Azure AI Search. Parity means the same query surface
and evidence fields, not proprietary-ranking equivalence.
