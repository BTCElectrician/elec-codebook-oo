# Start here

```bash
python -m pip install -e '.[dev,pdf,postgres]'
make doctor
make caps-json
make ask
make smoke
make pgvector-up
make test-pgvector
make pgvector-down
```

For an operator-owned source, copy `generic-reference-template.json` outside git, fill in its
identity and page mapping, then run `make plan` and `make dry`. Obtain approval immediately before
`make ingest`.

Use `BACKEND=local-artifacts` for JSON/JSONL or `BACKEND=pgvector` for searchable PostgreSQL.
