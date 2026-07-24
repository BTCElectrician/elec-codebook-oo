# Contributing

Outside contributions are not accepted for direct merge. Bug reports are welcome, and a pull
request may be useful to illustrate a proposed fix, but the maintainer will independently review
the report and decide whether and how to implement it.

Do not include source PDFs, copyrighted extracts, generated artifacts, page images, JSONL exports,
credentials, `.env` files, or private production history in an issue or pull request. Use only the
invented synthetic fixture when a reproduction needs document content.

Before sharing an illustrative change, run:

```bash
make agent-json
make check
git diff --check
```

Use `docs/CODEMAP.md` to identify the owning module, focused tests, and
invariants. If a command, output, capability, entry point, or safety gate
changes, update `codebook_agent/agent_contract.py` and its regression tests.

Backends are not “implemented” until they have an adapter, a documented data model, tests, and a
local smoke command. Keep optional provider dependencies out of the base install.
