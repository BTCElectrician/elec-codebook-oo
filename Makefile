PYTHON ?= python3
PROFILE ?= codebook_agent/profiles/generic-reference-template.json
PDF ?= examples/synthetic-codebook/source.txt
ARTIFACTS ?= artifacts
BACKEND ?= local-artifacts
QUERY ?= synthetic branch circuit
CODEBOOK_DATABASE_URL ?= postgresql://codebook:codebook-local-only@127.0.0.1:55432/codebook_test

.DEFAULT_GOAL := help

.PHONY: help doctor caps caps-json ask plan dry ingest export search answer example smoke test test-pgvector lint leak-check check clean docker-build docker-run pgvector-up pgvector-down

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
	@$(PYTHON) -m codebook_agent plan --profile "$(PROFILE)" --pdf "$(PDF)" --backend "$(BACKEND)"

dry:
	@$(PYTHON) -m codebook_agent dry --profile "$(PROFILE)" --pdf "$(PDF)" --backend "$(BACKEND)"

ingest:
	@CODEBOOK_DATABASE_URL="$(CODEBOOK_DATABASE_URL)" $(PYTHON) -m codebook_agent ingest --apply --profile "$(PROFILE)" --pdf "$(PDF)" --artifacts "$(ARTIFACTS)" --backend "$(BACKEND)"

export:
	@$(PYTHON) -m codebook_agent export jsonl --profile "$(PROFILE)" --artifacts "$(ARTIFACTS)"

search:
	@CODEBOOK_DATABASE_URL="$(CODEBOOK_DATABASE_URL)" $(PYTHON) -m codebook_agent search --profile "$(PROFILE)" --query "$(QUERY)"

answer:
	@CODEBOOK_DATABASE_URL="$(CODEBOOK_DATABASE_URL)" $(PYTHON) -m codebook_agent answer --profile "$(PROFILE)" --query "$(QUERY)"

example:
	@$(PYTHON) examples/synthetic-codebook/generate.py

smoke:
	@$(PYTHON) -m codebook_agent smoke

test:
	@$(PYTHON) -m pytest -q

test-pgvector:
	@CODEBOOK_TEST_DATABASE_URL="$(CODEBOOK_DATABASE_URL)" $(PYTHON) -m pytest -q -m pgvector

lint:
	@$(PYTHON) -m ruff check .

leak-check:
	@$(PYTHON) scripts/leak_guard.py

check: lint test smoke leak-check
	@git diff --check

clean:
	@$(PYTHON) -m codebook_agent clean --artifacts "$(ARTIFACTS)"

docker-build:
	@docker build -t elec-codebook-oo:local .

docker-run:
	@docker compose run --rm codebook doctor

pgvector-up:
	@docker compose --profile pgvector up -d pgvector

pgvector-down:
	@docker compose --profile pgvector down -v
