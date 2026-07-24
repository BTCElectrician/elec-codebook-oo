# Agent onboarding

1. Read `AGENTS.md` and `STATUS.md`.
2. Run `make help`, `make doctor`, `make caps-json`, and `make ask`.
3. Confirm the operator has permission to process the source document locally.
4. Choose or create a metadata-only profile. The included NFPA 70 template is a reference shape,
   not a source of NFPA content or a configured production target.
5. Run `make plan PDF=/absolute/path/book.pdf` and `make dry`.
6. State that these commands are no-write/no-network. State that `make ingest` writes only local
   artifacts and that `make export` creates local JSONL.
7. Ask for approval immediately before ingest. Do not assume AI, Azure, or any candidate backend is approved.
