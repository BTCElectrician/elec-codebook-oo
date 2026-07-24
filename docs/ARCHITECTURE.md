# Architecture

```text
authorized source -> metadata-only profile -> plan/dry (no write) -> ingest --apply
                                                               -> local documents.json -> JSONL export
```

The base package imports no cloud or AI SDK. The `local-artifacts` backend is the only implemented
backend. Profiles carry document metadata and questions, never source extracts. Generated artifacts
are intentionally outside version-control input.
