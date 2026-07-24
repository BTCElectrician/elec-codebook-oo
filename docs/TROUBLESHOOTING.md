# Troubleshooting

- `Source not found`: pass an absolute existing `.txt`, `.md`, or `.pdf` path.
- `PDF support is optional`: install `.[pdf]`.
- `Tesseract OCR is required for this page`: install `.[ocr]` plus the local `tesseract` binary,
  or intentionally select `OCR_MODE=off`.
- `PostgreSQL support is optional`: install `.[postgres]`.
- `Set CODEBOOK_DATABASE_URL`: configure the approved pgvector database or run `make pgvector-up`.
- `vector type not found`: use a server with pgvector available and a role allowed to enable it.
- `Refusing to write`: review the plan and add `--apply`; Make's ingest target supplies it.
- Weak hash-provider results: use overlapping terms or select an actual semantic provider.
- Missing printed pages: configure `printed_page_offset`.
- Low OCR confidence: inspect the cited PDF page; try higher DPI or a better Tesseract page
  segmentation mode, but do not silently treat uncertain OCR as exact wording.
- `No local artifacts found`: local JSONL export requires a prior local ingest.
- Leak guard failure: remove tracked PDFs, extracts, JSONL, artifacts, page images, embeddings,
  database dumps, or `.env`.
