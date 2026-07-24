# Python environments

The base install has no mandatory provider SDK. Use Python 3.11 or newer.

```bash
uv venv
source .venv/bin/activate
uv pip install -e '.[dev,pdf,ocr,postgres]'
make check
```

Extras:

- `pdf`: pypdf
- `ocr`: pypdfium2/PDFium rendering plus Pillow; local Tesseract executable required
- `postgres`: Psycopg pool and pgvector adaptation
- `ai`: optional provider SDK
- `dev`: pytest and Ruff

The repository does not commit a lockfile yet.
