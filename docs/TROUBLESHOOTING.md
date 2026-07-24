# Troubleshooting

- `Source not found`: pass an absolute existing path, for example `make plan PDF=/path/book.pdf`.
- `PDF support is optional`: install the PDF extra, then rerun: `python -m pip install -e '.[pdf]'`.
- `Refusing to write`: this is the apply gate. Review the plan and obtain approval before using
  `make ingest` or adding `--apply` to the CLI.
- `No local artifacts found`: run the approved local ingest before `make export`.
- Leak guard failure: remove the tracked artifact, PDF, JSONL export, or `.env`; keep only synthetic
  text fixtures in the repository.
