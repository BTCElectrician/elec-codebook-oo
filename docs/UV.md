# Python environments

The project has no required runtime dependencies. Use any Python 3.11+ environment. For testing:

```bash
python -m pip install -e '.[dev]'
make check
```

For PDF extraction, opt in explicitly: `python -m pip install -e '.[pdf]'`. `pypdf` is optional so
the base package remains small and provider-free. A future lockfile may be added when the dependency
groups stabilize.
