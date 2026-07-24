# Commands

| Command | Connections | Writes | Notes |
| --- | --- | --- | --- |
| `make doctor` | None | None | Reports pgvector, PDFium, Tesseract, and URL presence |
| `make caps-json` | None | None | Machine-readable capability contract |
| `make ask` | None | None | Profile interview questions |
| `make plan PDF=/path/book.pdf BACKEND=pgvector` | None | None | Shows exact schema/provider apply boundary |
| `make dry PDF=/path/book.pdf BACKEND=pgvector` | None | None | Validates the same boundary without clients |
| `make ingest BACKEND=local-artifacts` | None | Local JSON | Make supplies CLI `--apply` |
| `make export` | None | Local JSONL | Requires local ingest |
| `make pgvector-up` | Local Docker | Docker volume | Starts disposable pgvector |
| `make ingest BACKEND=pgvector` | Database/provider | PostgreSQL | Atomic indexed ingest |
| `make search QUERY="..."` | Database/provider | None | Hybrid evidence retrieval |
| `make answer QUERY="..."` | Database/provider | None | Extractive grounded response |
| `make test-ocr` | Local Tesseract | Temporary image-only PDF | Real OCR regression |
| `make test-pgvector` | Local test database | Temporary schema | Mock-free real-service test |
| `make pgvector-down` | Local Docker | Deletes Compose volume | Disposable-service teardown |
| `make smoke` | None | Temporary directory | Local evidence contract |
| `make clean` | None | Deletes only selected `artifacts/` | Never source or `.env` |

`CODEBOOK_DATABASE_URL` selects PostgreSQL. The value is not emitted in command results. Search and
answer infer the embedding provider/model from the stored corpus contract.

Set `OCR_MODE=off`, `auto`, or `always` on `make plan`, `make dry`, or `make ingest`. The CLI also
accepts `--ocr-language`, `--ocr-dpi`, `--ocr-page-segmentation-mode`,
`--ocr-min-native-characters`, and `--ocr-timeout-seconds`.

Set `SCHEMA`, `EMBEDDING_PROVIDER`, and `EMBEDDING_MODEL` when overriding profile values. Planning
shows the effective values and whether document `search_text` will leave the process, but it does
not connect to PostgreSQL or instantiate the provider.
