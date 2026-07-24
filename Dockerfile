FROM python:3.11-slim

WORKDIR /app
RUN useradd --create-home --uid 10001 codebook
COPY pyproject.toml README.md ./
COPY codebook_agent ./codebook_agent
RUN pip install --no-cache-dir '.[pdf,postgres]'
COPY --chown=codebook:codebook . .
USER codebook
ENTRYPOINT ["codebook"]
CMD ["help"]
