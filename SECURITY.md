# Security policy

Do not report secrets or user book content in public issues. Do not commit `.env`, PDFs, extracted
artifacts, page images, JSONL exports, embeddings, database dumps, indexes, or provider credentials.
Planning commands instantiate no network clients. Pgvector, optional embeddings, OCR correction,
and synthesized answers are explicitly selected and preview their data boundary before use.
Pgvector ingest verifies the database before making a paid provider request. Correction retains raw
page text and fails closed on protected-token, similarity, or length-change violations. Synthesis
falls back to extractive passages when evidence labels are missing or invalid.
PDFium rendering and Tesseract OCR are local-only; temporary page bytes stay in process and are not
written by the OCR adapter.

For a security report, contact the repository owner privately through GitHub rather than attaching
reproduction material containing a source book or credential.
