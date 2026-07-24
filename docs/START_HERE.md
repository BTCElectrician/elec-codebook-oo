# Start here

Install a Python 3.11+ environment and the developer extras if you intend to test:

```bash
python -m pip install -e '.[dev]'
make doctor
make caps-json
make ask
make smoke
```

For a real authorized PDF, add the optional parser with `python -m pip install -e '.[pdf]'`.
Then copy the bundled metadata-only profile, edit the book metadata, run `make plan` and `make dry`,
and obtain approval before `make ingest`. See `docs/AGENT_ONBOARDING.md` for the agent sequence.
