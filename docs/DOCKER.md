# Docker

Docker is optional; native Python remains the primary workflow. The image excludes `.env`, PDFs,
artifacts, and local output through `.dockerignore`, and runs as a non-root user.

```bash
make docker-build
make docker-run
```

To point the read-only `/books` mount at an authorized source directory, set `CODEBOOK_SOURCE_DIR`
before invoking Compose. The container does not include a cloud publisher or an AI client.
