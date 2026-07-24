# Commands

| Command | Connections | Writes | Notes |
| --- | --- | --- | --- |
| `make doctor` | None | None | Reports optional pgvector extras and URL presence |
| `make caps-json` | None | None | Machine-readable capability contract |
| `make ask` | None | None | Profile interview questions |
| `make plan PDF=/path/book.pdf BACKEND=pgvector` | None | None | Shows deferred write target |
| `make dry PDF=/path/book.pdf BACKEND=pgvector` | None | None | Validates without connecting |
| `make ingest BACKEND=local-artifacts` | None | Local JSON | Make supplies CLI `--apply` |
| `make export` | None | Local JSONL | Requires local ingest |
| `make pgvector-up` | Local Docker | Docker volume | Starts disposable pgvector |
| `make ingest BACKEND=pgvector` | Database/provider | PostgreSQL | Atomic indexed ingest |
| `make search QUERY="..."` | Database/provider | None | Hybrid evidence retrieval |
| `make answer QUERY="..."` | Database/provider | None | Extractive grounded response |
| `make test-pgvector` | Local test database | Temporary schema | Mock-free real-service test |
| `make pgvector-down` | Local Docker | Deletes Compose volume | Disposable-service teardown |
| `make smoke` | None | Temporary directory | Local evidence contract |
| `make clean` | None | Deletes only selected `artifacts/` | Never source or `.env` |

`CODEBOOK_DATABASE_URL` selects PostgreSQL. The value is not emitted in command results. Search and
answer infer the embedding provider/model from the stored corpus contract.
