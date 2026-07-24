# Backend truth

Implemented: `local-artifacts`. It writes `documents.json` locally and exports portable JSONL.

Candidate only: LanceDB, Qdrant, pgvector, and OpenSearch. They have no adapter code in this
repository. Azure AI Search and AI processing are intentionally not implemented in v0.1. A future
backend must add code, tests, profile contract, documentation, and a smoke command before being
called implemented.
