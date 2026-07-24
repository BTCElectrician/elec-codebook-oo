# Agent operating guide

Start by reading `STATUS.md`, then run `make help`, `make doctor`, and `make caps-json`.

This repository processes only content the operator is authorized to use. Never add source PDFs,
extracted text, page images, chunks, exports, `artifacts/`, credentials, or a user's `.env` to git.

Default commands are local-only. `plan`, `dry`, `ask`, and `caps` do not write artifacts, connect to
PostgreSQL, or make provider calls. `ingest` requires `--apply`; it writes either the local artifact
directory or the explicitly selected pgvector database. `export` writes local JSONL. PostgreSQL/
pgvector hybrid retrieval and optional local Tesseract OCR are implemented. Azure, model-based OCR
correction, generative synthesis, and other candidate backends are not implemented; do not imply
otherwise.

For a new book, ask the questions from `make ask`, create or edit a profile, run `make plan`, then
`make dry`. Explain the exact output path or database target and get approval before `make ingest`.
For pgvector, resolve `CODEBOOK_DATABASE_URL` without printing it and verify representative results
include source wording and page evidence. Keep profiles metadata-only: no copied book text.
Treat OCR output as uncertain evidence: preserve `ocr-tesseract` provenance and confidence, and
never silently relabel it as native source text.

Before commits, inspect `git status` and run `git diff --check`. Treat generated run output as
disposable user content, not repository input.
