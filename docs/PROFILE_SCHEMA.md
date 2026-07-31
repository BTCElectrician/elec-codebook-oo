# Profile schema

Profiles contain metadata and operator questions, never source extracts.

Generate a safe starting point without copying the template by hand:

```bash
codebook configure --source /absolute/path/book.pdf --authorized --json
```

The preview returns observed source facts, local confidence-scored candidates, the proposed profile,
unresolved decisions, and an exact `apply_profile` command. Candidates carry evidence counts but no
extracted text. They are not profile authority: the profile keeps safe defaults until the operator
explicitly supplies `--edition`, `--printed-page-offset`, or `--content-range`. The preview makes no
network or provider call. The profile is written only when that command includes `--apply`; an
existing profile also requires `--overwrite`.

`configuration_assessment` is an output-only review packet, not stored profile content. Its
`observed_facts` are measurements; its `inferred_candidates` are deterministic local suggestions
with `confidence`, evidence counts, and a `profile_effect`. The current slice can use a filename
year, repeated edge page labels, exact top-of-page `contents`/`index`/`appendix`/`annex` markers,
and coarse heading/table shape. It does not infer arbitrary document semantics, printed mappings
from body references, edition authority, or a custom schema. It does not call a model for
configuration inference; any future model-assisted path must be an explicit provider and data-boundary
plan rather than a hidden fallback.

The command accepts the same OCR, correction, and embedding overrides used by planning, plus
`--content-range`, `--printed-page-offset`, `--max-chunk-chars`, `--no-structure`, and
`--no-table-recovery`. Provider selections are recorded as future boundaries; configuration never
constructs a provider client.

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
- `ocr.mode`: `off`, `auto`, or `always`
- `ocr.engine`: `tesseract`
- `ocr.language`: installed Tesseract language, default `eng`
- `ocr.dpi`: 150-600, default 300
- `ocr.page_segmentation_mode`: Tesseract PSM 0-13, default 3
- `ocr.min_native_characters`: auto-mode threshold, default 40
- `ocr.timeout_seconds`: per-page timeout, 1-600
- `correction.mode`: `off`, `ocr-only`, or `all` (default `off`)
- `correction.provider`: currently `openai`
- `correction.model`
- `correction.min_similarity`: 0-1, default 0.82
- `correction.max_length_change_ratio`: 0-1, default 0.20
- `structure.enabled`: enable generic block recovery
- `structure.recover_tables`: join explicitly continued delimited tables
- `embedding.provider`: `hash` or `openai`
- `embedding.model`

Embedding configuration is validated during profile loading and planning without importing a
provider SDK or creating a client. The hash provider accepts only `codebook-hash-v1`; OpenAI model
names are operator-selected. Plan/dry reports whether the effective provider is external.

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

`ocr.mode=auto` keeps usable native PDF text and OCRs only pages below the configured alphanumeric
character threshold. OCR is local and records `ocr-tesseract` plus mean word confidence in every
derived document.

Correction never changes the raw page record. Accepted text remains labeled with its extraction
method plus correction provider/model; rejected candidates leave raw text selected and record the
reasons. Structure recovery is deterministic and makes no provider call.

The default is `generic-reference-template.json`. The NFPA-named profile is an optional metadata
shape only and includes no edition data, page ranges, index names, or source content.
