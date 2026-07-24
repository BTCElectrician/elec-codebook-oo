FROM python:3.11-slim

WORKDIR /app
RUN apt-get update \
    && apt-get install --no-install-recommends --yes tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --uid 10001 codebook
COPY pyproject.toml README.md ./
COPY codebook_agent ./codebook_agent
RUN pip install --no-cache-dir '.[pdf,ocr,postgres]'
COPY --chown=codebook:codebook . .
USER codebook
ENTRYPOINT ["codebook"]
CMD ["help"]
