# Profile schema

Profiles contain metadata and operator questions, never source extracts.

Required:

- `id`: 1-128 letters, digits, dots, underscores, or hyphens
- `title`
- `document_type`
- `backend`: `local-artifacts` or `pgvector`
- `questions`: list of strings

Optional:

- `edition`
- `legal_use_required`
- `content_ranges`
- `printed_page_offset`
- `max_chunk_chars` (minimum 200, default 1800)
- `embedding.provider`: `hash` or `openai`
- `embedding.model`

`content_ranges` maps type names to page ranges. Supported shapes are:

```json
{
  "main": [10, 400],
  "definitions": [[401, 410], [520, 525]],
  "tables": [
    {"start_pdf_page": 411, "end_pdf_page": 519}
  ]
}
```

Unmatched pages use `main`. Type names are extensible.

`printed_page_offset` follows:

```text
printed page = PDF page - printed_page_offset
```

Use `null` when no mapping is known. Non-positive results remain null.

The default is `generic-reference-template.json`. The NFPA-named profile is an optional metadata
shape only and includes no edition data, page ranges, index names, or source content.
