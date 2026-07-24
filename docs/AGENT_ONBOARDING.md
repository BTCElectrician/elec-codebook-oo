# Agent onboarding

Elec Codebook OO is designed to be understood, changed, run, and verified by a
coding agent without assuming a specific model or host. Repository truth has a
small hierarchy:

1. `AGENTS.md` defines authority and hard boundaries.
2. `STATUS.md` states current implemented and unimplemented behavior.
3. `docs/CODEMAP.md` maps intended changes to owners, tests, and invariants.
4. `codebook capabilities --json` describes the runtime contract.
5. Focused code and tests prove the details.

`CLAUDE.md`, `GEMINI.md`, and `.github/copilot-instructions.md` are adapters to
that same authority. README is the public front door, not a replacement for the
operating contract.

## First contact

Run:

```bash
make agent-json
```

The JSON packet reports the package version, side-effect boundary, local health,
canonical entry points, conversation contract, standard workflows, and
recommended next actions. The conversation contract tells an agent to accept
ordinary-language intent, lead with verified state, distinguish implemented
from candidate behavior, and offer a relevant understand/explain/change/run/
verify choice. The command does not connect, call a provider, or write
artifacts.

Useful follow-ups:

```bash
make help
make doctor
make caps-json
make schemas-json
make robot-docs
```

The CLI is forgiving at the discovery edge: bare `codebook` teaches the command
map, `codebook help plan` explains one command, `capabilities` aliases `caps`,
and unambiguous command or option typos are inferred with a warning on stderr.

## If the task is to understand the project

1. Read `AGENTS.md`, `STATUS.md`, and `docs/CODEMAP.md`.
2. Run `make agent-json` and `make caps-json`.
3. Read `docs/ARCHITECTURE.md` for the evidence flow.
4. Read only the module and focused tests named by the code map.
5. Distinguish implemented, optional, candidate, and not implemented behavior.

The short architectural idea is:

```text
authorized source -> preserved page evidence -> backend-neutral documents
                  -> local artifacts or pgvector -> cited retrieval -> grounded answer
```

## If the task is to change the project

1. Name the intended behavior and the invariant that must survive.
2. Find its owner and focused tests in `docs/CODEMAP.md`.
3. Search callers and documentation with `rg`.
4. Make the smallest coherent change.
5. Add a regression for success, failure, and any safety gate affected.
6. Run focused tests, then `make check` and `git diff --check`.
7. Update `STATUS.md` if the implemented state changed.

When the CLI changes, update the canonical
`codebook_agent/agent_contract.py`. Tests enforce alignment between the parser,
machine contract, Make targets, and agent entry points.

## If the task is to process a source

1. Confirm the operator may process the exact source in the intended way.
2. Run `make ask`.
3. Copy the generic metadata-only profile outside git.
4. Record edition, content ranges, printed-page offset, OCR policy, backend, and
   embedding choice.
5. Run `make plan` and `make dry`.
6. Explain the exact deferred local path or database/schema target and every
   future provider boundary.
7. Ask for approval immediately before `ingest --apply`.
8. After indexing, run a representative search and verify source wording, PDF
   and printed pages, and extraction provenance.

For pgvector, resolve `CODEBOOK_DATABASE_URL` without printing it. Confirm the
target is not production unless the operator explicitly approved it.

Treat low-confidence OCR as review-required evidence. Never silently relabel
`ocr-tesseract` text as native. A model correction must retain raw text,
provider/model, acceptance decision, and protected identifiers.

## Output and failure contract

- Deterministic JSON data goes to stdout.
- Warnings, inferred-input notices, and errors go to stderr.
- JSON output is unstyled and non-interactive.
- Exit `0` means success, `1` input error, `2` safety block, `3` environment
  error, `4` upstream failure, and `5` internal invariant failure.
- `codebook schema --json` describes stable output shapes.
- `codebook capabilities --json` describes commands, environment variables,
  data boundaries, and retry meaning.

## Hard boundary

Never add PDFs, extracted text, page images, embeddings, database dumps,
indexes, artifacts, JSONL exports, credentials, or a user's `.env` to git. The
NFPA profile is a generic metadata shape, not permission or bundled content.
