# Status

## Current state

Initial OSS MVP: local profile planning, synthetic-fixture ingest, local artifact staging, and
portable JSONL export are implemented. The default path is AI-free and makes no network calls.

## Implemented

- Metadata-only profiles and agent interview questions
- Local no-write planning/dry-run
- Local text/PDF ingestion (`pypdf` is an optional PDF extra)
- Local JSON artifacts and JSONL export
- Synthetic smoke workflow and leak-focused tests

## Not implemented

- Azure publishing, OpenAI processing, local search/chat, and all candidate vector backends

## Validation

Run `make check` for the no-network test and smoke suite. Run `git diff --check` before commits.
