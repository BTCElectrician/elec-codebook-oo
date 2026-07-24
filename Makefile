PYTHON ?= python3
PROFILE ?= codebook_agent/profiles/nfpa70-reference-template.json
PDF ?= examples/synthetic-codebook/source.txt
ARTIFACTS ?= artifacts

.DEFAULT_GOAL := help

.PHONY: help doctor caps caps-json ask plan dry ingest export example smoke test lint check clean

help:
	@$(PYTHON) -m codebook_agent help

doctor:
	@$(PYTHON) -m codebook_agent doctor --artifacts "$(ARTIFACTS)"

caps:
	@$(PYTHON) -m codebook_agent caps

caps-json:
	@$(PYTHON) -m codebook_agent caps --json

ask:
	@$(PYTHON) -m codebook_agent ask --profile "$(PROFILE)"

plan:
	@$(PYTHON) -m codebook_agent plan --profile "$(PROFILE)" --pdf "$(PDF)"

dry:
	@$(PYTHON) -m codebook_agent dry --profile "$(PROFILE)" --pdf "$(PDF)"

ingest:
	@$(PYTHON) -m codebook_agent ingest --apply --profile "$(PROFILE)" --pdf "$(PDF)" --artifacts "$(ARTIFACTS)"

export:
	@$(PYTHON) -m codebook_agent export jsonl --profile "$(PROFILE)" --artifacts "$(ARTIFACTS)"

example:
	@$(PYTHON) examples/synthetic-codebook/generate.py

smoke:
	@$(PYTHON) -m codebook_agent smoke

test:
	@$(PYTHON) -m pytest -q

lint:
	@$(PYTHON) -m ruff check .

check: test smoke

clean:
	@$(PYTHON) -m codebook_agent clean --artifacts "$(ARTIFACTS)"
