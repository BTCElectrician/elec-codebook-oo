# Elec Codebook OO

A local-first, agent-guided kit for turning an authorized codebook, specbook, manual, or technical
PDF into local artifacts and portable JSONL. It is rooted in the operational lessons of electrical
codebook workflows without including NFPA content, production history, PDFs, chunks, images, or
cloud exports.

You bring content you have the right to process. Planning and the default ingest never call an AI
provider or cloud service. Current v0.1 writes only local artifacts; Azure, AI processing, search,
chat, and vector backends are deliberately not implemented yet.

## Quick start

```bash
make doctor
make caps-json
make ask
make plan PDF=/absolute/path/to/authorized-book.pdf
make dry PDF=/absolute/path/to/authorized-book.pdf
make smoke
```

For PDF ingestion, install the permissively licensed optional parser: `pip install '.[pdf]'`.
Then, after reviewing the plan and approving a local write:

```bash
make ingest PDF=/absolute/path/to/authorized-book.pdf
make export
```

Artifacts are written under `artifacts/local/<profile-id>/` and are gitignored.

## Agent workflow

Read [AGENTS.md](AGENTS.md), run `make caps-json`, then `make ask`. Select or edit a metadata-only
profile, run `make plan` and `make dry`, explain the exact local write, and obtain approval before
ingest. See [docs/AGENT_ONBOARDING.md](docs/AGENT_ONBOARDING.md).

## Safety and boundaries

- Do not add user books, extracted content, artifacts, images, JSONL exports, secrets, or `.env` files to git.
- `plan`, `dry`, `ask`, and `caps` are no-write/no-network commands.
- CLI `ingest` fails unless `--apply` is supplied; the Make target includes it only for the approved local path.
- Local artifact files are user-content derivatives, not safe-to-publish fixtures.

Read [docs/LEGAL.md](docs/LEGAL.md), [docs/COMMANDS.md](docs/COMMANDS.md), and
[docs/BACKENDS.md](docs/BACKENDS.md) before extending the kit.
