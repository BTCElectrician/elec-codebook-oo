# Agent operating guide

This file is the canonical repository authority for every coding agent. Vendor-specific entry
files may point here; they do not replace it.

Start by reading `STATUS.md` and `docs/CODEMAP.md`, then run `make agent-json`. Use `make help`,
`make doctor`, and `make caps-json` for narrower discovery. These commands do not connect, call a
provider, or write project artifacts.

This repository processes only content the operator is authorized to use. Never add source PDFs,
extracted text, page images, chunks, exports, `artifacts/`, credentials, or a user's `.env` to git.

Default commands are local-only. `plan`, `dry`, `ask`, and `caps` do not write artifacts, connect to
PostgreSQL, or make provider calls. `ingest` requires `--apply`; it writes either the local artifact
directory or the explicitly selected pgvector database. `export` writes local JSONL. PostgreSQL/
pgvector hybrid retrieval and optional local Tesseract OCR are implemented. Model-based OCR
correction is an optional explicit provider call, generic structure/table recovery is implemented,
and generative synthesis is optional with citation validation and extractive fallback. Azure and
other candidate retrieval backends are not implemented; do not imply otherwise.

For a new book, ask the questions from `make ask`, create or edit a profile, run `make plan`, then
`make dry`. Explain the exact output path or database target and get approval before `make ingest`.
For pgvector, resolve `CODEBOOK_DATABASE_URL` without printing it and verify representative results
include source wording and page evidence. Keep profiles metadata-only: no copied book text.
Treat OCR output as uncertain evidence: preserve `ocr-tesseract` provenance and confidence, and
never silently relabel it as native source text. Model correction must preserve raw text, record
the provider/model and acceptance decision, and reject changes to protected identifiers. Synthesis
must use retrieved evidence labels and fall back to extractive output when citation validation
fails.

For code changes, use `docs/CODEMAP.md` to find the owning contract and focused tests. Keep
machine-readable data on stdout and warnings/errors on stderr. Preserve the documented exit-code
meanings and update `codebook_agent/agent_contract.py` when commands, outputs, capabilities, or
entry points change.

Before commits, inspect `git status`, run focused tests, `make check`, and `git diff --check`.
Update `STATUS.md` when current implementation truth changes. Treat generated run output as
disposable user content, not repository input.
