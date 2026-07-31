# Start here

```bash
python -m pip install -e '.[dev,pdf,ocr,postgres]'
make agent-json
make doctor
make caps-json
make configure PDF=examples/synthetic-codebook/source.txt
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

For an operator-owned source, first confirm authorization, then run `codebook configure --source
/absolute/path/book.pdf --authorized --json`. Review the proposed metadata-only profile and
unresolved decisions; the returned `apply_profile` command writes outside git only after `--apply`.
Then run `make plan` and `make dry`. Obtain approval immediately before `make ingest`.

Use `BACKEND=local-artifacts` for JSON/JSONL or `BACKEND=pgvector` for searchable PostgreSQL.
