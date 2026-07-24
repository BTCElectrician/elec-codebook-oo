# Code map

This is the shortest path from an intended change to its owning code, contract,
tests, and safety boundary. It is for humans and coding agents. The same map is
available to automation in `codebook capabilities --json`.

## Read order

1. `AGENTS.md` — authority, prohibitions, and approval rules.
2. `STATUS.md` — what is implemented now and what is not.
3. This file — where to make a change and what must remain true.
4. The focused module and tests named below.
5. `docs/ARCHITECTURE.md` when a change crosses a boundary.

For a one-call orientation packet, run:

```bash
codebook agent --json
```

## Change map

| Intent | Owning code | Focused tests | Contract that must survive |
| --- | --- | --- | --- |
| Change CLI behavior, help, JSON, errors, or safety gates | `codebook_agent/cli_surface.py`, `codebook_agent/cli.py`, `codebook_agent/agent_contract.py` | `tests/test_agent_contract.py`, `tests/test_cli.py` | Data on stdout, diagnostics on stderr; stable exit meanings; writes remain apply-gated |
| Change document or page fields | `codebook_agent/models.py`, `codebook_agent/core.py` | `tests/test_core.py`, `tests/test_ocr.py` | Raw evidence remains recoverable; stable-field changes require a schema version |
| Change extraction or page mapping | `codebook_agent/core.py`, `codebook_agent/ocr.py` | `tests/test_core.py`, `tests/test_ocr.py`, `tests/test_ocr_unit.py` | PDF and printed pages remain explicit; source SHA-256 and extraction provenance survive |
| Change OCR behavior | `codebook_agent/ocr.py` | `tests/test_ocr.py`, `tests/test_ocr_unit.py` | OCR stays local and is always labeled `ocr-tesseract` with confidence |
| Change model correction | `codebook_agent/correction.py`, `codebook_agent/text_models.py` | `tests/test_correction.py`, `tests/test_text_models.py` | Raw text, provider/model, decision, and protected identifiers remain preserved |
| Change headings, definitions, lists, or tables | `codebook_agent/structure.py` | `tests/test_structure.py` | Recovery stays deterministic and never invents missing geometry or cells |
| Change local artifacts or export | `codebook_agent/backends/local.py` | `tests/test_core.py`, `tests/test_cli.py` | Local and pgvector records share the same document contract; generated output stays out of git |
| Change pgvector storage or retrieval | `codebook_agent/backends/pgvector.py`, `codebook_agent/backends/sql/001_pgvector.sql` | `tests/test_pgvector_integration.py`, `tests/test_ocr_pgvector_integration.py` | Migration, adapter, stored corpus contract, and mock-free integration path change together |
| Change embeddings | `codebook_agent/embeddings.py` | `tests/test_embeddings.py`, `tests/test_pgvector_integration.py` | Index and query use the same provider/model; external text boundary remains explicit |
| Change answers or synthesis | `codebook_agent/answers.py`, `codebook_agent/text_models.py` | `tests/test_answers.py`, `tests/test_synthesis.py` | Extractive remains default; invalid model citations fall back to extractive evidence |
| Change public repository safety | `AGENTS.md`, `scripts/leak_guard.py`, `.gitignore`, `.dockerignore` | `tests/test_leak_guards.py` | No protected source, extract, page image, artifact, JSONL export, credential, or `.env` enters git |
| Change installation, commands, or contributor experience | `pyproject.toml`, `Makefile`, `README.md`, `docs/` | `tests/test_agent_contract.py`, `make check` | README, agent contract, CLI, and current status agree |

## Runtime flow

```text
authorized source
  -> metadata-only profile
  -> plan / dry                       no clients, connections, or writes
  -> ingest --apply
  -> native extraction
  -> optional local OCR
  -> optional explicit model correction
  -> deterministic structure recovery
  -> PageText + CodebookDocument
  -> local artifacts or pgvector
  -> SearchResult
  -> extractive answer or citation-validated synthesis
```

Ownership follows the arrows: each stage may enrich its output, but it may not
erase the evidence or authority decisions made before it.

## Change procedure

1. State the behavior to change and the invariant that must not change.
2. Read the owning module and its focused tests from the table.
3. Inspect callers with `rg`, including docs and machine contracts.
4. Make the smallest coherent change.
5. Run the focused tests.
6. Run `make check` and `git diff --check`.
7. Update `STATUS.md` when implemented state changed.

For pgvector behavior, also run the disposable real-service lane:

```bash
make pgvector-up
make test-pgvector
make pgvector-down
```

For OCR behavior, run:

```bash
make test-ocr
```

## Definition of done

A change is not complete merely because a function works. It is complete when:

- the public and credential boundaries still hold;
- the focused tests cover the behavior and failure path;
- machine-readable output remains deterministic and parseable;
- help and errors name the next valid action;
- docs and `STATUS.md` tell the same truth as the code;
- `make check` and `git diff --check` pass;
- no generated operator content is tracked.
