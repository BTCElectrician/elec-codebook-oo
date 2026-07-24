# Python environments

The base install has no mandatory provider SDK. Use Python 3.11 or newer.

```bash
uv venv
source .venv/bin/activate
uv pip install -e '.[dev,pdf,postgres]'
make check
```

Extras:

- `pdf`: pypdf
- `postgres`: Psycopg pool and pgvector adaptation
- `ai`: optional provider SDK
- `azure`: reserved SDK dependencies; no Azure adapter is implemented
- `dev`: pytest and Ruff

The repository does not commit a lockfile yet.
