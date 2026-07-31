# Elec Codebook OO

<div align="center">
  <img src="docs/assets/elec-codebook-oo-hero.webp" alt="Elec Codebook OO by Ohmni Oracle — open-source, local-first, source-cited codebook processing" width="100%">
</div>

[![Test](https://github.com/BTCElectrician/elec-codebook-oo/actions/workflows/ci.yml/badge.svg)](https://github.com/BTCElectrician/elec-codebook-oo/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Version 0.6.0](https://img.shields.io/badge/version-0.6.0-6f42c1)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Turn an authorized codebook, specification, or technical manual into page-cited local records or
a searchable PostgreSQL/pgvector corpus—without binding ingestion to one search vendor.**

Elec Codebook OO grew from practical NEC/NFPA 70 workflow lessons: edition control, separate PDF
and printed page numbers, article/section context, definitions, tables, and evidence a reader can
verify. The software is generic and includes no NFPA text, PDF, page image, embedding, or index.

```bash
git clone https://github.com/BTCElectrician/elec-codebook-oo.git
cd elec-codebook-oo
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[pdf,ocr,postgres]'
make doctor
```

There is no supported curl installer or published package release yet. Install from source with pip
or uv. See the [changelog](CHANGELOG.md) for version history and the
[release procedure](docs/RELEASING.md) for the future GitHub tag/release workflow.

## Built for developers and coding agents

You can point a coding agent at this repository without first teaching it the
project's private vocabulary. The repo provides three things:

- **Map:** [`AGENTS.md`](AGENTS.md) defines authority,
  [`STATUS.md`](STATUS.md) states current truth, and
  [`docs/CODEMAP.md`](docs/CODEMAP.md) maps each kind of change to its owner,
  focused tests, and invariants.
- **Motorway:** one canonical evidence flow and deterministic JSON contracts
  let an agent move quickly from intent to the relevant boundary.
- **Guarded exits:** plans show exact destinations and provider boundaries;
  writes and destructive cleanup stop at an explicit apply gate.

Start with one side-effect-free command:

```bash
make agent-json
```

It reports local health, entry points, workflows, and recommended next actions.
It also gives the receiving model a conversation contract: accept ordinary
language, lead with verified state, distinguish implemented from candidate
behavior, and offer the useful next choice—understand, explain, change, run, or
verify.

You can then tell the agent, “I have this PDF,” “I have this codebook,” or “I
have this specification.” The agent can use `codebook configure` to inspect the
authorized local source, explain what it detected, ask about what it could not
infer, and produce the exact profile, plan, and dry-run commands. It does not
silently guess page mappings, enable a provider, or ingest the document.
Use `codebook capabilities --json` for the full command/environment/exit-code
contract, `codebook schema --json` for output shapes, and
`codebook help <command>` for exact flags.

Codex/ChatGPT-style agents enter through `AGENTS.md`; Claude Code, Gemini CLI,
and GitHub Copilot receive thin adapters that point to the same authority.
Other tools can start from this README or
[`docs/AGENT_ONBOARDING.md`](docs/AGENT_ONBOARDING.md). No vendor-specific file
owns project truth.

## TL;DR

**The problem:** Basic PDF-to-text scripts discard the evidence needed for trustworthy retrieval.
They merge pages, lose printed-page mappings, flatten definitions and tables, and couple the result
to whichever database was chosen first.

**The solution:** Elec Codebook OO creates a versioned document contract before storage. Each chunk
retains source identity, PDF page, optional printed page, content type, and article/section context.
The same records can be exported as JSONL or indexed in PostgreSQL with pgvector.

For installers and tradespeople learning to code, that creates a practical teaching tool: bring an
authorized manual, inspect how it was processed, search it in ordinary language, and trace every
answer back to wording and pages you can verify. AI is optional assistance around the source—not a
replacement for the book, training, or field judgment.

| Capability | What the current worktree supports |
| --- | --- |
| Guided source setup | Local inspection reports facts plus labeled, confidence-scored candidates; it proposes a metadata-only profile and next commands |
| Evidence-preserving ingestion | Text, Markdown, native PDF text, and local OCR remain page-local |
| Real OCR fallback | Image-only or low-text PDF pages use local Tesseract with confidence metadata |
| Auditable OCR correction | Optional model repair preserves raw text and rejects changed identifiers |
| Structure recovery | Generic headings, notes, definitions, lists, and explicitly continued tables |
| Portable records | Versioned JSON and JSONL with source SHA-256 and explicit locators |
| pgvector indexing | Atomic corpus replacement with stale-record cleanup |
| Hybrid retrieval | PostgreSQL full-text search plus pgvector cosine similarity |
| Grounded answers | Extractive by default; optional synthesis must use valid evidence labels |
| Neutral profiles | Generic metadata, content ranges, page offset, backend, and embedding selection |
| Safe operations | Exact no-write apply preview and explicit `--apply` before artifacts or database writes |
| Real verification | Mock-free integration test against a disposable pgvector service |

## Quick example

The bundled source is invented and safe to use:

```bash
make agent-json
make caps-json
make configure PDF=examples/synthetic-codebook/source.txt
make plan
make dry
make ingest
make export
make smoke
```

To exercise the searchable pgvector path:

```bash
python -m pip install -e '.[dev,pdf,ocr,postgres]'
make pgvector-up
make ingest BACKEND=pgvector
make search QUERY="What does the synthetic branch circuit supply?"
make answer QUERY="What does the synthetic branch circuit supply?"
make test-pgvector
make pgvector-down
```

Example result:

```text
Article 1. A branch circuit is a circuit that supplies one or more outlets.
Source: source.txt, Article 1, PDF page 1
```

## Architecture

```text
authorized .txt / .md / .pdf
                     |
             configure --authorized
          local inspection; no retained text
          profile proposal + unresolved decisions
                     |
                     | metadata-only profile
                     v
             plan / dry validation ---------------- no writes, no connections
                     |
                     | ingest --apply
                     v
       native page extraction
                     |
             usable text? -- no --> local PDFium render
                     |                    |
                    yes             Tesseract OCR
                     |            + confidence/provenance
                     +---------+----------+
                               |
                optional model correction
              raw text retained + validators
                               |
               generic structure recovery
             headings / lists / notes / tables
                               |
        page-preserving evidence and chunking
                     |
                     v
       PageText v1.0 + CodebookDocument v2.2
       - source SHA-256
       - PDF + printed page
       - content type
       - article + section
       - raw + selected page text
       - native, OCR-derived, or model-corrected provenance
       - extraction method + OCR confidence
                     |
           +---------+----------+
           |                    |
           v                    v
 local JSON / JSONL      embedding provider
                                |
                                v
                     PostgreSQL + pgvector
                     - GIN full-text index
                     - HNSW vector index
                     - reciprocal-rank fusion
                                |
                      +---------+---------+
                      |                   |
                      v                   v
              search / query          answer
            extracted passages    extractive (default)
                                      or citation-validated synthesis
```

Ingestion owns evidence. A backend owns storage and ranking. The answer layer consumes only
backend-neutral `SearchResult` objects. This is what makes another retrieval adapter possible
without rebuilding the PDF pipeline.

## Evidence contract

Every `CodebookDocument` has:

| Field | Meaning |
| --- | --- |
| `id` | Deterministic identity derived from corpus, source hash, page, chunk, and content |
| `corpus_id` | Profile-controlled corpus name |
| `source_name` / `source_sha256` | Source locator and exact input fingerprint |
| `content` / `search_text` | Evidence wording and metadata-enriched retrieval text |
| `content_type` | `main`, `definitions`, `tables`, `annexes`, or a profile-defined type |
| `pdf_page_start/end` | One-based file-page evidence |
| `printed_page_start/end` | Optional human-visible page mapping |
| `article_*` / `section_*` | Generic heading context when detected |
| `metadata.extraction_method` | `native-text`, `native-pdf-text`, or `ocr-tesseract` |
| `metadata.extraction_confidence` | Mean Tesseract word confidence for OCR-derived text |
| `metadata.correction_*` | Model, score, and accepted/rejected correction decision |
| `metadata.raw_text_sha256` | Link from a chunk to its immutable raw page extraction |
| `metadata` | JSON extension point for another manual or downstream schema |
| `schema_version` | Contract version, currently `2.2` |

Ordinary chunks stay within a PDF page. A recovered table may span explicitly continued pages; its
document records the complete PDF/printed page range and `metadata.source_pages`.

## Native extraction and OCR

The old NFPA 70 ETL called its GPT text-correction phase “OCR cleaning,” but its extractor read the
existing PDF text layer and skipped empty pages. Elec Codebook OO v0.3 introduced the missing
capability:
real image OCR.

`ocr.mode=auto` is the default. Native PDF text is retained when it has enough alphanumeric
characters. Only pages below that threshold are rendered locally with PDFium and sent to the local
Tesseract process. `always` forces OCR for every PDF page; `off` disables it.

OCR output is evidence, not unquestionable truth. Every OCR-derived document records its engine and
mean word confidence, and human-readable citations label OCR-derived passages. No PDF page or OCR
text is sent over the network by this path.

### Optional model correction

Set `correction.mode` to `ocr-only` to send only Tesseract-derived page text to the configured text
model, or `all` to review every extracted page. The default is `off`. The corrector is deliberately
conservative:

- `pages.json` and the pgvector `pages` table retain the original extraction;
- section identifiers, numeric values, and units are protected tokens;
- similarity and maximum length-change thresholds must pass;
- accepted text remains labeled `model-corrected OCR`;
- a rejected candidate leaves the raw text selected and records every rejection reason.

This is text correction, not visual adjudication. The provider sees extracted text, not the PDF or
page image. Review low-confidence and corrected pages against the authorized source before relying
on them.

## Structure and tables

The generic structure pass labels headings, definitions, notes/warnings, lists, and body text.
Tables or schedules with delimited columns are normalized to Markdown. Adjacent pages carrying the
same `Table`/`Schedule` identifier, including `(continued)`, are joined into one page-ranged record.
No edition-specific codebook grammar is required.

This recovery is intentionally deterministic. It does not infer missing cells, read diagrams, or
invent table geometry when extraction is ambiguous.

## PostgreSQL and pgvector

The implemented pgvector adapter creates:

- `corpora`, storing the source and embedding contract;
- `documents`, storing evidence, metadata, generated `tsvector`, and `vector(1536)`;
- `pages`, storing immutable raw text, selected text, and correction provenance;
- an indexed foreign key from documents to corpora;
- a composite corpus/type/page index;
- a GIN full-text index;
- an HNSW cosine vector index.

Indexing is transactional. Records are upserted, and documents no longer present in the replacement
run are deleted in the same transaction.

Retrieval combines two candidate lists:

1. pgvector cosine similarity;
2. PostgreSQL `websearch_to_tsquery` full-text ranking.

Reciprocal-rank fusion combines the independent lexical and vector rankings.

## Answer modes

`answer` is extractive by default: it returns ranked source wording and page locators without a
generation call. `--answer-mode synthesized` is an explicit opt-in. It sends the query, retrieved
passages, and locators to the selected text model, asks it to cite evidence labels such as `[S1]`,
and validates those labels. Missing or unknown labels fail closed to the extractive answer.

Preview that boundary without connecting:

```bash
codebook answer --plan --profile /path/profile.json \
  --query "What training step comes first?" \
  --answer-mode synthesized
```

Synthesis makes retrieved wording easier to learn from; it does not make the answer authoritative,
prove that retrieval found every relevant passage, or replace the source and qualified judgment.

## Embeddings

| Provider | Status | Intended use |
| --- | --- | --- |
| `hash` | Implemented and tested | Offline tutorial, deterministic tests, plumbing verification |
| `openai` | Optional adapter | Semantic retrieval compatible with the legacy 1,536-dimension contract |

The hash provider is a signed feature-hashing representation. It is useful for exact-term and
overlap-driven local testing; it is not presented as a production semantic model. The selected
provider and model are stored with the corpus, and queries must use that same contract.

The OpenAI adapter batches document inputs while preserving result order. Pgvector ingest verifies
the configured database before making a paid embedding request. Selecting that provider is an
explicit data-boundary decision because document `search_text` is sent to the provider.

## Installation

Elec Codebook OO requires Python 3.11 or newer.

### pip

```bash
git clone https://github.com/BTCElectrician/elec-codebook-oo.git
cd elec-codebook-oo
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[pdf,ocr,postgres]'
```

Extras are isolated:

```bash
python -m pip install -e '.[pdf]'          # native text extraction with pypdf
python -m pip install -e '.[ocr]'          # PDFium rendering; also install Tesseract
python -m pip install -e '.[postgres]'     # psycopg + pgvector
python -m pip install -e '.[dev]'          # pytest + Ruff
python -m pip install -e '.[ai]'           # optional provider SDK
```

The OCR extra supplies the Python renderer. Install Tesseract separately:

```bash
brew install tesseract                 # macOS
sudo apt-get install tesseract-ocr     # Ubuntu/Debian
```

### uv

```bash
git clone https://github.com/BTCElectrician/elec-codebook-oo.git
cd elec-codebook-oo
uv venv
source .venv/bin/activate
uv pip install -e '.[dev,pdf,ocr,postgres]'
make check
```

### Docker

```bash
make docker-build
make docker-run
make pgvector-up
make test-pgvector
```

See [docs/DOCKER.md](docs/DOCKER.md) for ports, volumes, and teardown.

## Process your own authorized source

1. Confirm that you may process the exact document in the intended way.
2. Inspect the source locally and preview a metadata-only profile:

   ```bash
   codebook configure \
     --source /absolute/path/book.pdf \
     --authorized \
     --json
   ```

   This counts pages and measures native-text density. It also emits deterministic local
   candidates for an edition, printed-page offset, semantic ranges, OCR policy, and layout shape.
   Candidates include confidence and evidence counts but no extracted source text. They are not
   applied to the profile: edition, page mapping, and semantic ranges remain operator decisions.
   The command makes no network or provider call, writes nothing, identifies unresolved decisions,
   and returns an exact `apply_profile` command.

3. Discuss the edition, printed-page mapping, content ranges, OCR recommendation, and storage
   choice with your coding agent. Run the returned command after adding or changing flags as needed:

   ```bash
   codebook configure \
     --source /absolute/path/book.pdf \
     --output ~/.config/elec-codebook-oo/profiles/my-book.json \
     --id my-book-2026 \
     --title "My Authorized Book" \
     --edition 2026 \
     --content-range front_matter:1-8 \
     --content-range main:9-420 \
     --printed-page-offset 8 \
     --ocr-mode auto \
     --backend pgvector \
     --embedding-provider openai \
     --embedding-model text-embedding-3-small \
     --correction-mode off \
     --authorized \
     --apply \
     --json
   ```

   `hash` is the offline default. Selecting OpenAI embeddings creates a future provider boundary
   for document `search_text`; configuration itself still makes no provider call, and `plan` shows
   that boundary before ingestion.

4. Review the questions and plan:

   ```bash
   make ask PROFILE=~/.config/elec-codebook-oo/profiles/my-book.json
   make plan PROFILE=~/.config/elec-codebook-oo/profiles/my-book.json PDF=/absolute/path/book.pdf \
     BACKEND=pgvector SCHEMA=codebook
   make dry PROFILE=~/.config/elec-codebook-oo/profiles/my-book.json PDF=/absolute/path/book.pdf \
     BACKEND=pgvector SCHEMA=codebook
   ```

5. Start or select a non-production PostgreSQL database with pgvector.
6. Only after reviewing the target, ingest:

   ```bash
   make ingest \
     PROFILE=~/.config/elec-codebook-oo/profiles/my-book.json \
     PDF=/absolute/path/book.pdf \
     BACKEND=pgvector
   ```

7. Query it:

   ```bash
   make search PROFILE=~/.config/elec-codebook-oo/profiles/my-book.json \
     QUERY="What does Section 3.1 require?"
   make answer PROFILE=~/.config/elec-codebook-oo/profiles/my-book.json \
     QUERY="What does Section 3.1 require?"
   ```

`plan` and `dry` display the exact local artifact path or PostgreSQL schema plus the effective
embedding provider, model, and future network/data boundary. They do not read the database URL,
connect, write, or construct a provider client. PostgreSQL apply commands read
`CODEBOOK_DATABASE_URL` and never print its value. The Makefile's default URL is only for the
disposable local Compose service.

## Profile configuration

Profiles contain metadata, not source extracts:

```json
{
  "id": "authorized-manual-2026",
  "title": "Authorized Technical Manual",
  "edition": "2026",
  "document_type": "technical-manual",
  "legal_use_required": true,
  "content_ranges": {
    "front_matter": [1, 8],
    "main": [{"start_pdf_page": 9, "end_pdf_page": 420}],
    "definitions": [[421, 435]],
    "tables": [[436, 470]],
    "annexes": []
  },
  "printed_page_offset": 8,
  "max_chunk_chars": 1800,
  "ocr": {
    "mode": "auto",
    "engine": "tesseract",
    "language": "eng",
    "dpi": 300,
    "page_segmentation_mode": 3,
    "min_native_characters": 40,
    "timeout_seconds": 120
  },
  "correction": {
    "mode": "off",
    "provider": "openai",
    "model": "gpt-5.6-terra",
    "min_similarity": 0.82,
    "max_length_change_ratio": 0.2
  },
  "structure": {
    "enabled": true,
    "recover_tables": true
  },
  "backend": "pgvector",
  "embedding": {
    "provider": "hash",
    "model": "codebook-hash-v1"
  },
  "questions": [
    "Do you have the right to process this edition locally?",
    "Where is the source?"
  ]
}
```

`printed_page_offset` means `printed page = PDF page - offset`. Pages at or before the offset have
no printed-page value. Range values may be `[start, end]`, `[[start, end], ...]`, or objects with
`start_pdf_page` and `end_pdf_page`.

Read [docs/PROFILE_SCHEMA.md](docs/PROFILE_SCHEMA.md) for the complete contract.

## Command reference

| Command | Connections | Writes | Purpose |
| --- | --- | --- | --- |
| `make help` | None | None | Show the command map |
| `make agent-json` | None | None | One-call orientation, health, workflows, and next actions |
| `make robot-docs` | None | None | Paste-ready compact guide for another agent |
| `make schemas-json` | None | None | Describe stable machine-output shapes |
| `make doctor` | None | None | Check Python, optional extras, and local paths |
| `make caps-json` | None | None | Machine-readable capability and safety contract |
| `make ask` | None | None | Print profile onboarding questions |
| `make configure PDF=/path/book.pdf` | None | None | Inspect an authorized source and preview a profile outside git |
| `make plan` | None | None | Preview exact apply destination, provider boundary, and evidence contract |
| `make dry` | None | None | Validate the same apply configuration without clients or writes |
| `make ingest BACKEND=local-artifacts` | None | Local JSON | Apply-gated local ingest |
| `make export` | None | Local JSONL | Export a prior local ingest |
| `make ingest BACKEND=pgvector` | Configured database/provider | PostgreSQL | Apply-gated indexed ingest |
| `make search QUERY="..."` | Configured database/provider | None | Hybrid retrieval |
| `make answer QUERY="..."` | Configured database/provider | None | Extractive by default; optional validated synthesis |
| `make test-ocr` | Local Tesseract | Temporary generated PDF | Real image-only OCR test |
| `make smoke` | None | Temporary directory | Synthetic local evidence test |
| `make test-pgvector` | Disposable local database | Temporary test schema | Real integration test |
| `make check` | None by default | Test caches | Lint, unit tests, smoke, leak guard |
| `make clean` | None | None | Preview the resolved generated-artifact target |
| `make clean-apply` | None | Deletes selected `artifacts/` only | Apply the reviewed cleanup |

The installed CLI exposes the same controls:

```bash
codebook agent --json
codebook help plan
codebook capabilities --json
codebook schema --json
codebook caps --json
codebook configure --source /path/book.pdf --authorized --json
codebook plan --profile /path/profile.json --pdf /path/book.pdf --backend pgvector
codebook ingest --apply --profile /path/profile.json --pdf /path/book.pdf \
  --backend pgvector --ocr-mode auto --correction-mode off
codebook search --profile /path/profile.json --query "minimum cover" --json
codebook answer --profile /path/profile.json --query "minimum cover"
codebook answer --plan --profile /path/profile.json --query "minimum cover" \
  --answer-mode synthesized
codebook answer --profile /path/profile.json --query "minimum cover" \
  --answer-mode synthesized --generation-provider openai
```

## Design principles

1. **Evidence precedes vectors.** A ranking backend cannot recover page boundaries discarded during
   extraction.
2. **Behavioral parity, not provider imitation.** Every backend must return the same evidence
   contract even when its ranking algorithm differs.
3. **Plan before apply.** Configuration previews and ingestion plans do not connect to PostgreSQL,
   call a provider, or write without an explicit apply gate.
4. **Operator-owned content stays outside git.** PDFs, extracts, vectors, indexes, and exports are
   user derivatives.
5. **Capabilities are earned.** A backend is implemented only with adapter code, documentation,
   synthetic tests, and a real-service integration path.
6. **AI should teach without hiding the evidence.** Correction and explanation are useful only
   when the worker can inspect the original wording, provenance, and page.
7. **Agent navigability is part of the interface.** Authority, current state, change ownership,
   output schemas, safety gates, and the next valid action must be discoverable without guessing.

## How it compares

| Approach | Page evidence | Backend-neutral records | Search | Best fit |
| --- | --- | --- | --- | --- |
| **Elec Codebook OO v0.6.0** | Native text + local OCR, PDF + printed page | Yes | PostgreSQL hybrid | Guided, auditable BYO-document workflows |
| One-off PDF script | Often lost | Usually no | No | Disposable extraction |
| Hosted document assistant | Provider-dependent | Usually no | Hosted | Fast use when upload terms are acceptable |
| Raw pgvector tutorial | Application-defined | Application-defined | Vector only unless extended | Learning vector SQL |

## Limitations

- No protected codebook content or prebuilt index is included.
- Guided configuration supports `.pdf`, `.txt`, and `.md`; it proposes safe defaults but cannot
  infer edition, printed-page offsets, semantic page ranges, or arbitrary schemas reliably.
- OCR is word-oriented Tesseract output; complex diagrams and table geometry still require review.
- Model correction sees extracted text, not the page image, and may be rejected by safety gates.
- Printed-page mapping is profile offset-based; generic footer/header detection is not implemented.
- Heading/structure detection is generic and deterministic, not an edition-specific NEC grammar.
- Only clearly labeled, delimited continued tables are joined; arbitrary layouts are not inferred.
- `hash` embeddings are deterministic plumbing, not production semantic embeddings.
- OpenAI embeddings are optional but are not exercised by credential-free CI.
- Synthesized answers validate evidence labels but cannot prove retrieval completeness or factual
  entailment; extractive fallback remains the safety boundary.
- The pgvector schema currently standardizes on 1,536 dimensions for compatibility with the legacy
  corpus contract.
- Azure AI Search, LanceDB, Qdrant, and OpenSearch adapters are not implemented.
- There is no hosted service, authentication layer, or multi-user authorization model.

## Troubleshooting

### `Source not found`

Pass an absolute existing `.txt`, `.md`, or `.pdf` path.

### `Confirm you may process this exact source`

Confirm the source's license, ownership, access terms, or other authorization, then rerun the
preview with `--authorized`. This permits local inspection; it does not ingest or upload the source.

### `Profile already exists`

Review the existing metadata-only JSON. Choose another `--output`, or use `--overwrite --apply`
only when replacement is intended. Authorization and overwrite flags are never inferred from typos.

### `PDF support is optional`

Install the PDF extra:

```bash
python -m pip install -e '.[pdf]'
```

### `Tesseract OCR is required for this page`

Install the OCR Python extra and the local Tesseract executable:

```bash
python -m pip install -e '.[ocr]'
brew install tesseract                 # macOS
sudo apt-get install tesseract-ocr     # Ubuntu/Debian
```

Use `--ocr-mode off` only when you intentionally want native text extraction without fallback.

### `Set CODEBOOK_DATABASE_URL`

Start the disposable service with `make pgvector-up`, or configure a PostgreSQL database you are
authorized to use. Do not place a production URL in a committed file.

### `Set OPENAI_API_KEY`

Install `.[ai]`, then set the key only in your shell or approved secret manager. It is required
only when you explicitly select OpenAI embeddings, model correction, or synthesized answers.

### A correction was rejected

Inspect `pages.json` or the pgvector `pages` row. The raw extraction remains selected when protected
tokens changed, similarity was too low, or the candidate changed length too much. Adjusting a gate
should be a reviewed policy decision, not a way to force a preferred answer.

### `vector type not found`

Use a PostgreSQL service with the pgvector extension available. The adapter runs
`CREATE EXTENSION IF NOT EXISTS vector`; the database role must be allowed to create or use it.

### Search returns weak matches

Confirm the corpus was indexed with the same embedding provider now used for querying. The local
hash provider relies on token overlap. Use a real semantic embedding provider when semantic
similarity is required.

### Printed pages are missing

Set `printed_page_offset`. The formula is `printed page = PDF page - offset`.

### Leak guard failure

Remove or ignore the tracked/unignored PDF, extract, page image, JSONL, artifact, embedding dump,
or `.env`. Use invented
fixtures in tests and issues.

## FAQ

### Does this repository contain the NEC or NFPA 70?

No. The NFPA-named profile is metadata-only and optional. The default profile is generic.

### Can someone use the same PDF I use?

They bring their own independently authorized copy, create their own profile, and generate their
own local artifacts or pgvector index. This repository does not distribute the document or its
derivatives.

### Does OCR upload my PDF?

No. PDFium renders selected pages in process and Tesseract runs as a local executable. Optional
model correction sends extracted page text—not the PDF image—to the selected provider. External
embeddings and synthesized answers are separate, explicit data-boundary decisions.

### Is pgvector now implemented?

Yes. The adapter, schema migration, atomic indexing, hybrid retrieval, CLI, and mock-free
integration test are implemented.

### Is Azure required?

No. Azure is not imported or contacted by the implemented workflows.

### Does `answer` interpret the code?

By default, no: it returns ranked extracted wording and citations. Synthesized mode can explain or
combine retrieved passages, but every model citation must resolve to supplied evidence or the
command falls back to extractive output. Neither mode replaces professional judgment or proves that
a retrieved passage is sufficient for a field decision.

### Can I change the schema for another kind of manual?

Use profile-defined content types and the document `metadata` JSON object for extensions. Changing
the stable evidence fields requires a new document schema version and database migration.

### Can I drop in any document and have it configure itself perfectly?

No. `configure` supports authorized PDF, text, and Markdown sources. It can count pages, measure
native-text density, recommend local OCR, and report deterministic confidence-scored candidates for
edition, repeated printed-page labels, a few exact semantic section markers, and coarse layout
characteristics. It does not claim to understand arbitrary documents or automatically accept those
candidates. Edition, printed-page mapping, content ranges, unusual layouts, and schema changes
still require conversation and operator review.

### Do planning commands connect to PostgreSQL?

No. `configure` preview, `plan`, `dry`, `ask`, and `caps` make no network or provider calls.
Configuration preview and planning are no-write commands. Planning resolves
and displays the destination, schema, embedding contract, and future data boundary without reading
the database URL or constructing a provider client.

## About contributions

> *About Contributions:* Please don't take this the wrong way, but I do not accept outside contributions for any of my projects. I simply don't have the mental bandwidth to review anything, and it's my name on the thing, so I'm responsible for any problems it causes; thus, the risk-reward is highly asymmetric from my perspective. I'd also have to worry about other "stakeholders," which seems unwise for tools I mostly make for myself for free. Feel free to submit issues, and even PRs if you want to illustrate a proposed fix, but know I won't merge them directly. Instead, I'll have Claude or Codex review submissions via `gh` and independently decide whether and how to address them. Bug reports in particular are welcome. Sorry if this offends, but I want to avoid wasted time and hurt feelings. I understand this isn't in sync with the prevailing open-source ethos that seeks community contributions, but it's the only way I can move at this velocity and keep my sanity.

Do not attach protected source content, generated derivatives, indexes, credentials, or private
operational data to an issue or pull request. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

The code and project documentation are available under the [MIT License](LICENSE). That license
does not apply to any book, standard, manual, PDF, page image, extracted text, embedding, or index
processed with the software.

NFPA and National Electrical Code are trademarks of the National Fire Protection Association. This
project is independent and is not affiliated with, endorsed by, or sponsored by NFPA.
