# Commands

| Command | Connections | Writes | Notes |
| --- | --- | --- | --- |
| `make agent-json` | None | None | One-call orientation, local health, entry points, and next actions |
| `make robot-docs` | None | None | Compact operating guide for another agent |
| `make schemas-json` | None | None | Stable machine-output shapes |
| `make doctor` | None | None | Reports pgvector, PDFium, Tesseract, and URL presence |
| `make caps-json` | None | None | Commands, capabilities, exit codes, environment, and change map |
| `make ask` | None | None | Profile interview questions |
| `make plan PDF=/path/book.pdf BACKEND=pgvector` | None | None | Shows exact schema/provider apply boundary |
| `make dry PDF=/path/book.pdf BACKEND=pgvector` | None | None | Validates the same boundary without clients |
| `make ingest BACKEND=local-artifacts` | Optional correction provider | Local JSON | Documents plus raw page evidence |
| `make export` | None | Local JSONL | Requires local ingest |
| `make pgvector-up` | Local Docker | Docker volume | Starts disposable pgvector |
| `make ingest BACKEND=pgvector` | Database/provider | PostgreSQL | Atomic indexed ingest |
| `make search QUERY="..."` | Database/provider | None | Hybrid evidence retrieval |
| `make answer QUERY="..."` | Database/provider | None | Extractive by default; optional validated synthesis |
| `make test-ocr` | Local Tesseract | Temporary image-only PDF | Real OCR regression |
| `make test-pgvector` | Local test database | Temporary schema | Mock-free real-service test |
| `make pgvector-down` | Local Docker | Deletes Compose volume | Disposable-service teardown |
| `make smoke` | None | Temporary directory | Local evidence contract |
| `make clean` | None | None | Previews the resolved generated-artifact target |
| `make clean-apply` | None | Deletes only selected `artifacts/` | Explicit apply gate; never source or `.env` |

`CODEBOOK_DATABASE_URL` selects PostgreSQL. The value is not emitted in command results. Search and
answer infer the embedding provider/model from the stored corpus contract.

The CLI supports the same discovery surface:

```bash
codebook                         # safe first-try command map
codebook agent --json            # one-call machine orientation
codebook help plan               # exact help for one command
codebook capabilities --json     # `capabilities` is an alias for `caps`
codebook schema --json
codebook robot-docs guide --json
```

Machine data is emitted on stdout; warnings and errors use stderr. Exit codes
have stable meanings: `0` success, `1` input error, `2` safety block, `3`
environment error, `4` upstream failure, and `5` internal failure. The complete
retry contract is available from `codebook capabilities --json`.

Unambiguous command and long-option typos are corrected with a warning. Unknown
or ambiguous input fails with a next-step hint and does not execute a write.

Set `OCR_MODE=off`, `auto`, or `always` on `make plan`, `make dry`, or `make ingest`. The CLI also
accepts `--ocr-language`, `--ocr-dpi`, `--ocr-page-segmentation-mode`,
`--ocr-min-native-characters`, and `--ocr-timeout-seconds`.

Set `CORRECTION_MODE=off`, `ocr-only`, or `all`. Correction defaults to `off`; enabling it requires
the `ai` extra and the explicitly selected provider credential. Planning reports exactly which
extracted text boundary would leave the process.

Set `ANSWER_MODE=synthesized` for optional generation. Use the CLI's `answer --plan` first to
preview database, embedding, and generation boundaries without connecting. `GENERATION_PROVIDER`
and `GENERATION_MODEL` override the defaults.

Set `SCHEMA`, `EMBEDDING_PROVIDER`, and `EMBEDDING_MODEL` when overriding profile values. Planning
shows the effective values and whether document `search_text` will leave the process, but it does
not connect to PostgreSQL or instantiate the provider.
