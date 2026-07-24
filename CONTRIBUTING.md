# Contributing

Keep changes local-first and evidence-based. Do not include source PDFs, copyrighted extracts,
artifacts, credentials, or production operational history. Before opening a change, run:

```bash
make test
make smoke
git diff --check
```

Backends are not “implemented” until they have an adapter, documented data model, tests, and a
local smoke command. Keep optional provider dependencies out of the base install.
