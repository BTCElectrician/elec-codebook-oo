# Elec Codebook OO

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Version 0.1.0](https://img.shields.io/badge/version-0.1.0-6f42c1)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**A local-first ingestion scaffold for authorized codebooks, specifications, manuals, and other
technical references.**

Elec Codebook OO turns a local text, Markdown, or PDF source into inspectable local JSON artifacts
and portable JSONL. It grew from practical NEC/NFPA 70 workflow lessons—edition control, page-range
questions, printed-versus-PDF page numbering, and careful handling of definitions and tables—but
the project is intentionally generic and includes no NFPA content.

> **v0.1 is an alpha foundation, not a search or AI product.** Local planning, ingestion, and export
> work today. Search, chat, embeddings, vector databases, Azure publishing, and AI processing do
> not.

```bash
git clone https://github.com/BTCElectrician/elec-codebook-oo.git
cd elec-codebook-oo
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
make doctor
```

There is no supported curl installer or published package release yet. Install from source with
pip or uv, or use the optional local Docker workflow.

## TL;DR

**The problem:** Technical books are difficult to turn into a reusable local data layer without
mixing protected content into source control, hiding network calls, or jumping straight to a
provider-specific search stack.

**The solution:** Elec Codebook OO provides a small, inspectable workflow: describe an authorized
source with a metadata-only profile, preview a no-write plan, require an explicit apply step for
ingestion, and export the resulting local records as JSONL.

| Current v0.1 capability | What it provides |
| --- | --- |
| Local-first planning | `plan` and `dry` report the intended source and operation without writing artifacts or using the network |
| Explicit write gate | CLI ingestion refuses to write unless `--apply` is supplied |
| Portable output | Local `documents.json` can be exported as line-delimited JSON |
| Agent-readable contract | `caps --json` reports implemented, candidate, and unavailable capabilities |
| Content boundary | Profiles contain metadata and questions, while source text and generated derivatives stay outside git |
| Synthetic verification | The smoke workflow exercises ingest and export using invented text only |

## Quick example

The bundled synthetic source lets you inspect the workflow without supplying a real book:

```bash
make caps-json
make ask
make plan
make dry
make smoke
```

For an authorized local source, pass an absolute path:

```bash
make plan PDF=/absolute/path/to/authorized-book.pdf
make dry PDF=/absolute/path/to/authorized-book.pdf

# Only after reviewing the plan and approving the local write:
make ingest PDF=/absolute/path/to/authorized-book.pdf
make export
```

The default artifact path is
`artifacts/local/nfpa70-reference-template/documents.json`; export creates
`documents.jsonl` beside it. Both are gitignored user-content derivatives.

## What this project is building toward

The long-term idea is a generic, auditable ingestion layer for codebooks, project specifications,
equipment manuals, standards, and similar technical references. The electrical-code workflow is
the proving ground because it makes the hard requirements obvious:

- identify the exact document and edition;
- reconcile printed page numbers with file page indexes;
- distinguish main text, definitions, tables, annexes, and front matter;
- preserve source identity and provenance;
- keep operator authorization and consequential writes explicit; and
- make later retrieval backends replaceable instead of baking one provider into ingestion.

Those goals describe direction, not current functionality. v0.1 does not yet preserve page-level
evidence, run OCR, build a search index, answer questions, or publish to a cloud service.

## Design principles

1. **Capability truth over aspirational labels.** A backend is not implemented until adapter code,
   tests, a documented contract, and a smoke path exist.
2. **Plan before apply.** Read-only planning is separate from artifact creation, and the CLI makes
   the write boundary visible.
3. **Authorized content stays operator-owned.** The repository contains only synthetic text.
   Books, extracts, page images, artifacts, and exports must remain outside version control.
4. **Metadata is not source content.** Profiles describe a document and the questions needed to
   ingest it; they do not contain copied chapters or tables.
5. **Portable core, optional edges.** The base package has no runtime dependencies. PDF parsing is
   optional, and future provider integrations must remain isolated from the local path.

## How v0.1 compares

| Approach | Local by default | Explicit plan/apply split | Built-in search or chat | Typical fit |
| --- | --- | --- | --- | --- |
| **Elec Codebook OO v0.1** | Yes | Yes | No | A safe, inspectable ingestion and export foundation |
| One-off extraction script | Depends on the script | Usually no | No | A disposable conversion task |
| Hosted document assistant | No | Provider-specific | Usually yes | Fast hosted Q&A when uploading content is acceptable |
| Mature search platform | Deployment-specific | Platform-specific | Yes | A production retrieval system with operational infrastructure |

Elec Codebook OO is useful when the ingestion boundary and portable records matter more than an
immediate search UI. Choose a mature retrieval product if you need working semantic search,
ranking, access control, or chat today.

## Installation

Elec Codebook OO requires Python 3.11 or newer.

### pip from source

```bash
git clone https://github.com/BTCElectrician/elec-codebook-oo.git
cd elec-codebook-oo
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Add only the extras you need:

```bash
python -m pip install -e '.[pdf]'      # local PDF text extraction
python -m pip install -e '.[dev]'      # pytest and Ruff
python -m pip install -e '.[pdf,dev]'  # both
```

The `azure` and `ai` dependency groups reserve optional SDK dependencies for future work. Installing
them does not enable an Azure, AI, search, or chat backend.

### uv

```bash
git clone https://github.com/BTCElectrician/elec-codebook-oo.git
cd elec-codebook-oo
uv venv
source .venv/bin/activate
uv pip install -e '.[pdf,dev]'
make check
```

The project does not currently ship a uv lockfile; see [docs/UV.md](docs/UV.md).

### Docker

```bash
make docker-build
make docker-run
```

Docker is optional and local. To mount an authorized source directory read-only at `/books`, set
`CODEBOOK_SOURCE_DIR` before running Compose. See [docs/DOCKER.md](docs/DOCKER.md).

## Quick start with your own source

1. Confirm you have the right to process the document locally.
2. Copy
   [`codebook_agent/profiles/nfpa70-reference-template.json`](codebook_agent/profiles/nfpa70-reference-template.json)
   to an untracked location and replace its metadata placeholders. Do not paste source text into
   the profile.
3. Inspect the capability contract and profile questions:

   ```bash
   make caps-json
   make ask PROFILE=/absolute/path/to/profile.json
   ```

4. Preview and validate the local operation:

   ```bash
   make plan PROFILE=/absolute/path/to/profile.json PDF=/absolute/path/to/book.pdf
   make dry PROFILE=/absolute/path/to/profile.json PDF=/absolute/path/to/book.pdf
   ```

5. Review the exact source and output path. Then, and only with operator approval, write local
   artifacts and export them:

   ```bash
   make ingest PROFILE=/absolute/path/to/profile.json PDF=/absolute/path/to/book.pdf
   make export PROFILE=/absolute/path/to/profile.json
   ```

Use `ARTIFACTS=/absolute/path/to/artifacts` on both commands to override the default artifact root.

## Command reference

| Command | Network | Writes | Purpose |
| --- | --- | --- | --- |
| `make help` | No | No | Show the safe command map |
| `make doctor` | No | No | Check Python and artifact-parent access |
| `make caps-json` | No | No | Print the machine-readable capability and safety contract |
| `make ask PROFILE=/path/profile.json` | No | No | Print the metadata questions for a profile |
| `make plan PDF=/path/book.pdf` | No | No | Resolve the profile and source into a local plan |
| `make dry PDF=/path/book.pdf` | No | No | Validate the planned local workflow |
| `make ingest PDF=/path/book.pdf` | No | Local `artifacts/` | Ingest after approval; the Make target supplies the required CLI `--apply` |
| `make export` | No | Local JSONL | Export a prior local ingest |
| `make smoke` | No | Temporary directory | Exercise synthetic ingest and JSONL export |
| `make check` | No | Test caches and temporary files | Run lint, tests, smoke, leak guard, and diff checks |
| `make clean` | No | Deletes the selected `artifacts/` tree | Remove generated artifacts only; the CLI refuses other directory names |

The underlying CLI is also available after installation:

```bash
codebook --help
codebook caps --json
codebook plan --profile /path/profile.json --pdf /path/book.pdf
codebook ingest --apply --profile /path/profile.json --pdf /path/book.pdf
codebook export jsonl --profile /path/profile.json
```

See [docs/COMMANDS.md](docs/COMMANDS.md) for the compact command contract.

## Profile configuration

Profiles are JSON metadata. The only accepted backend in v0.1 is `local-artifacts`.

```json
{
  "id": "my-authorized-manual",
  "title": "My authorized manual",
  "edition": "2026",
  "document_type": "technical-manual",
  "legal_use_required": true,
  "content_ranges": {
    "front_matter": [],
    "main": [],
    "definitions": [],
    "tables": []
  },
  "printed_page_offset": null,
  "backend": "local-artifacts",
  "questions": [
    "Do you have the right to process this edition locally?",
    "What is the absolute source path?",
    "Which file pages contain the relevant content?"
  ]
}
```

Required fields and profile rules are documented in
[docs/PROFILE_SCHEMA.md](docs/PROFILE_SCHEMA.md).

## Architecture

```text
authorized .txt/.md/.pdf
          |
          |  metadata-only profile
          v
   plan / dry validation ---------------------- no writes, no network
          |
          |  explicit ingest --apply
          v
   text extraction + blank-line chunking
          |
          v
artifacts/local/<profile-id>/documents.json
          |
          |  export jsonl
          v
artifacts/local/<profile-id>/documents.jsonl
```

The base package imports no AI or cloud SDK. `local-artifacts` is the only backend with adapter
code. Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and
[docs/BACKENDS.md](docs/BACKENDS.md) before extending the pipeline.

## Repository guide

| Path | Role |
| --- | --- |
| `codebook_agent/cli.py` | CLI, capability contract, and write gate |
| `codebook_agent/core.py` | Profile loading, planning, extraction, and document shaping |
| `codebook_agent/backends/local.py` | Local JSON writer and JSONL exporter |
| `codebook_agent/profiles/` | Metadata-only profile templates |
| `examples/synthetic-codebook/` | Invented fixture used by the smoke workflow |
| `tests/` | CLI safety, local workflow, and leak-guard coverage |
| `docs/` | Command, legal, backend, Docker, profile, and agent guidance |

## Troubleshooting

### `Source not found`

Pass an absolute path to an existing `.txt`, `.md`, or `.pdf` file:

```bash
make plan PDF=/absolute/path/to/book.pdf
```

### `PDF support is optional`

Install the PDF extra in the active environment:

```bash
python -m pip install -e '.[pdf]'
```

The current parser uses `pypdf`; it does not provide OCR.

### `Refusing to write`

This is the expected apply gate. Review `plan` and `dry`, obtain operator approval, and then use
`make ingest`. If calling the CLI directly, add `--apply` explicitly.

### `No local artifacts found`

`export` requires a successful ingest for the same profile and artifact root. If you used a custom
root, pass the same value to both commands:

```bash
make ingest ARTIFACTS=/absolute/path/to/artifacts PDF=/absolute/path/to/book.pdf
make export ARTIFACTS=/absolute/path/to/artifacts
```

### Leak guard failure

Remove the tracked PDF, extract, page image, JSONL export, artifact, credential, or `.env` file.
Only invented synthetic source text belongs in this repository.

More fixes are collected in [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

## Limitations

| Capability | v0.1 status |
| --- | --- |
| Text and Markdown ingestion | Implemented |
| PDF text extraction | Optional `pypdf` extra; no OCR |
| Chunking | Blank-line splitting only |
| Page-level citations and evidence spans | Not implemented |
| Local search, ranking, or chat | Not implemented |
| Embeddings and vector database adapters | Not implemented |
| Azure AI Search or Blob publishing | Not implemented |
| AI-assisted processing | Not implemented |
| Authentication, multi-user access, or hosted service | Not implemented |

Candidate names such as LanceDB, Qdrant, pgvector, and OpenSearch appear only in the capability
contract. There is no adapter code for them. See [STATUS.md](STATUS.md) for the current handoff.

## FAQ

### Does this repository contain the NEC or NFPA 70?

No. It contains a metadata-only reference profile and invented synthetic text. It does not bundle
NFPA PDFs, code text, page images, extracted chunks, or production history.

### Can I use it with an NEC/NFPA 70 PDF?

Only if you independently have the right to process that exact document in the way you intend. This
software grants no rights to standards, manuals, books, or derivatives. Read
[docs/LEGAL.md](docs/LEGAL.md).

### Can I use it for non-electrical documents?

Yes. The current primitives are generic: a metadata profile, local text extraction, simple
chunking, local JSON, and JSONL export. Create a profile with the appropriate `document_type` and
questions.

### Do the default commands send my content anywhere?

No. The current command contract reports no network access. Planning is no-write, and ingest/export
write only to the local artifact root. Always re-check `make caps-json` after upgrading.

### Does it answer code questions or search the ingested content?

No. v0.1 produces records for a future retrieval layer; it does not provide search, citations,
chat, embeddings, or code interpretation.

### Why are AI and Azure extras listed in `pyproject.toml`?

They reserve optional SDK dependency groups for future adapters. No corresponding backend is
implemented, and installing an extra does not change that.

## About contributions

> *About Contributions:* Please don't take this the wrong way, but I do not accept outside contributions for any of my projects. I simply don't have the mental bandwidth to review anything, and it's my name on the thing, so I'm responsible for any problems it causes; thus, the risk-reward is highly asymmetric from my perspective. I'd also have to worry about other "stakeholders," which seems unwise for tools I mostly make for myself for free. Feel free to submit issues, and even PRs if you want to illustrate a proposed fix, but know I won't merge them directly. Instead, I'll have Claude or Codex review submissions via `gh` and independently decide whether and how to address them. Bug reports in particular are welcome. Sorry if this offends, but I want to avoid wasted time and hurt feelings. I understand this isn't in sync with the prevailing open-source ethos that seeks community contributions, but it's the only way I can move at this velocity and keep my sanity.

When reporting a problem, do not attach protected source content, generated derivatives,
credentials, or private operational data. See [CONTRIBUTING.md](CONTRIBUTING.md) and
[SECURITY.md](SECURITY.md).

## License

The software is available under the [MIT License](LICENSE). That license applies to this project's
code and documentation, not to any book, standard, manual, specification, PDF, or derivative you
process with it.
