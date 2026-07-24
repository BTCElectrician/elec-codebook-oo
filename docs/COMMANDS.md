# Commands

| Command | Network | Writes | Notes |
| --- | --- | --- | --- |
| `make doctor` | No | No | Local environment check |
| `make caps-json` | No | No | Capability contract for agents |
| `make ask` | No | No | Profile interview questions |
| `make plan PDF=/path/book.pdf` | No | No | Checks profile and input path |
| `make dry PDF=/path/book.pdf` | No | No | Validates planned local workflow |
| `make ingest PDF=/path/book.pdf` | No | Local `artifacts/` | Uses explicit CLI apply gate |
| `make export` | No | Local JSONL | Requires prior ingest |
| `make smoke` | No | Temporary directory | Synthetic end-to-end test |
| `make clean` | No | Deletes only `artifacts/` | Never touches source PDFs or `.env` |

At v0.1, text and Markdown inputs work in the base install. PDFs require `pip install '.[pdf]'`.
