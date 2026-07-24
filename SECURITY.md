# Security policy

Do not report secrets or user book content in public issues. Do not commit `.env`, PDFs, extracted
artifacts, page images, JSONL exports, embeddings, database dumps, indexes, or provider credentials.
Planning commands instantiate no network clients. Pgvector and optional embedding operations are
explicitly selected, isolated from the base install, and preview their data destination before
apply. Pgvector ingest verifies the database before making a paid embedding request.
PDFium rendering and Tesseract OCR are local-only; temporary page bytes stay in process and are not
written by the OCR adapter.

For a security report, contact the repository owner privately through GitHub rather than attaching
reproduction material containing a source book or credential.
