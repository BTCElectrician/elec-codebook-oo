# Agent operating guide

Start by reading `STATUS.md`, then run `make help`, `make doctor`, and `make caps-json`.

This repository processes only content the operator is authorized to use. Never add source PDFs,
extracted text, page images, chunks, exports, `artifacts/`, credentials, or a user's `.env` to git.

Default commands are local-only. `plan`, `dry`, `ask`, and `caps` do not write artifacts or make
network calls. `ingest` writes only to the local artifact directory and requires `--apply` at the
CLI level. `export` writes a local JSONL file. Azure, AI, and candidate vector backends are not
implemented in this release; do not imply otherwise.

For a new book, ask the questions from `make ask`, create or edit a profile, run `make plan`, then
`make dry`. Explain the exact output path and get approval before `make ingest`. Keep profiles
metadata-only: no copied book text.

Before commits, inspect `git status` and run `git diff --check`. Treat generated run output as
disposable user content, not repository input.
