# Docker

Native Python remains supported. The application image excludes `.env`, PDFs, artifacts, and
output, and runs as a non-root user.

```bash
make docker-build
make docker-run
```

The pgvector Compose profile uses:

- image `pgvector/pgvector:pg16`;
- host port `55432` by default;
- database `codebook_test`;
- a named disposable development volume; and
- a health check before tests.

```bash
make pgvector-up
make test-pgvector
make pgvector-down
```

`make pgvector-down` removes the Compose volume. Do not point the integration test at production:
its harness accepts only localhost and a database name containing `test`.

Set `CODEBOOK_SOURCE_DIR` to mount an authorized source directory read-only at `/books`. Sources and
generated derivatives remain outside the image through `.dockerignore`.
