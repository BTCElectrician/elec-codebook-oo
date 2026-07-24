# Start here

```bash
python -m pip install -e '.[dev,pdf,ocr,postgres]'
make agent-json
make doctor
make caps-json
make ask
make smoke
make test-ocr
make pgvector-up
make test-pgvector
make pgvector-down
```

If you are a coding agent, read `AGENTS.md`, `STATUS.md`, and
`docs/CODEMAP.md` before editing. `make agent-json` is safe to run without
credentials: it performs no connections, provider calls, or artifact writes.

For an operator-owned source, copy `generic-reference-template.json` outside git, fill in its
identity, page mapping, and OCR policy, then run `make plan` and `make dry`. Obtain approval
immediately before `make ingest`.

Use `BACKEND=local-artifacts` for JSON/JSONL or `BACKEND=pgvector` for searchable PostgreSQL.
