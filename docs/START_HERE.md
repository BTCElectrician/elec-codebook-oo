# Start here

```bash
python -m pip install -e '.[dev,pdf,ocr,postgres]'
make doctor
make caps-json
make ask
make smoke
make test-ocr
make pgvector-up
make test-pgvector
make pgvector-down
```

For an operator-owned source, copy `generic-reference-template.json` outside git, fill in its
identity, page mapping, and OCR policy, then run `make plan` and `make dry`. Obtain approval
immediately before `make ingest`.

Use `BACKEND=local-artifacts` for JSON/JSONL or `BACKEND=pgvector` for searchable PostgreSQL.
