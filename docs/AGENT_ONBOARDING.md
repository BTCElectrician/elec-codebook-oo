# Agent onboarding

1. Read `AGENTS.md` and `STATUS.md`.
2. Run `make help`, `make doctor`, `make caps-json`, and `make ask`.
3. Confirm the operator may process the exact source.
4. Copy the generic metadata-only profile outside git.
5. Record edition, content ranges, printed-page offset, OCR policy, backend, and embedding choice.
6. Run `make plan` and `make dry`; explain the deferred write target.
7. For local artifacts, explain the JSON/JSONL path.
8. For pgvector, resolve `CODEBOOK_DATABASE_URL` without printing it and confirm the target is not
   production unless the operator explicitly approved it.
9. Ask for approval immediately before `ingest --apply`.
10. After indexing, run a representative `search` and verify extracted wording, both page fields, and
    extraction provenance. Treat low-confidence OCR as review-required evidence.

Never add PDFs, extracted text, page images, embeddings, database dumps, indexes, or exports to git.
The NFPA profile is a generic reference shape, not permission or bundled content.
