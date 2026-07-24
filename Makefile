PYTHON ?= python3
PROFILE ?= codebook_agent/profiles/generic-reference-template.json
PDF ?= examples/synthetic-codebook/source.txt
ARTIFACTS ?= artifacts
BACKEND ?= local-artifacts
OCR_MODE ?= auto
CORRECTION_MODE ?= off
CORRECTION_PROVIDER ?=
CORRECTION_MODEL ?=
CORRECTION_ARGS = --correction-mode "$(CORRECTION_MODE)" $(if $(CORRECTION_PROVIDER),--correction-provider "$(CORRECTION_PROVIDER)") $(if $(CORRECTION_MODEL),--correction-model "$(CORRECTION_MODEL)")
SCHEMA ?= codebook
EMBEDDING_PROVIDER ?=
EMBEDDING_MODEL ?=
EMBEDDING_ARGS = $(if $(EMBEDDING_PROVIDER),--embedding-provider "$(EMBEDDING_PROVIDER)") $(if $(EMBEDDING_MODEL),--embedding-model "$(EMBEDDING_MODEL)")
QUERY ?= synthetic branch circuit
ANSWER_MODE ?= extractive
GENERATION_PROVIDER ?=
GENERATION_MODEL ?=
GENERATION_ARGS = --answer-mode "$(ANSWER_MODE)" $(if $(GENERATION_PROVIDER),--generation-provider "$(GENERATION_PROVIDER)") $(if $(GENERATION_MODEL),--generation-model "$(GENERATION_MODEL)")
CODEBOOK_DATABASE_URL ?= postgresql://codebook:codebook-local-only@127.0.0.1:55432/codebook_test

.DEFAULT_GOAL := help

.PHONY: help agent-json robot-docs schemas-json doctor caps caps-json ask plan dry ingest export search answer example smoke test test-agent test-ocr test-pgvector lint leak-check check clean clean-apply docker-build docker-run pgvector-up pgvector-down

help:
	@$(PYTHON) -m codebook_agent help

agent-json:
	@$(PYTHON) -m codebook_agent agent --json

robot-docs:
	@$(PYTHON) -m codebook_agent robot-docs guide

schemas-json:
	@$(PYTHON) -m codebook_agent schema --json

doctor:
	@$(PYTHON) -m codebook_agent doctor --artifacts "$(ARTIFACTS)" --json

caps:
	@$(PYTHON) -m codebook_agent caps

caps-json:
	@$(PYTHON) -m codebook_agent caps --json

ask:
	@$(PYTHON) -m codebook_agent ask --profile "$(PROFILE)"

plan:
	@$(PYTHON) -m codebook_agent plan --profile "$(PROFILE)" --pdf "$(PDF)" --artifacts "$(ARTIFACTS)" --backend "$(BACKEND)" --schema "$(SCHEMA)" $(EMBEDDING_ARGS) --ocr-mode "$(OCR_MODE)" $(CORRECTION_ARGS)

dry:
	@$(PYTHON) -m codebook_agent dry --profile "$(PROFILE)" --pdf "$(PDF)" --artifacts "$(ARTIFACTS)" --backend "$(BACKEND)" --schema "$(SCHEMA)" $(EMBEDDING_ARGS) --ocr-mode "$(OCR_MODE)" $(CORRECTION_ARGS)

ingest:
	@CODEBOOK_DATABASE_URL="$(CODEBOOK_DATABASE_URL)" $(PYTHON) -m codebook_agent ingest --apply --profile "$(PROFILE)" --pdf "$(PDF)" --artifacts "$(ARTIFACTS)" --backend "$(BACKEND)" --schema "$(SCHEMA)" $(EMBEDDING_ARGS) --ocr-mode "$(OCR_MODE)" $(CORRECTION_ARGS)

export:
	@$(PYTHON) -m codebook_agent export jsonl --profile "$(PROFILE)" --artifacts "$(ARTIFACTS)"

search:
	@CODEBOOK_DATABASE_URL="$(CODEBOOK_DATABASE_URL)" $(PYTHON) -m codebook_agent search --profile "$(PROFILE)" --query "$(QUERY)"

answer:
	@CODEBOOK_DATABASE_URL="$(CODEBOOK_DATABASE_URL)" $(PYTHON) -m codebook_agent answer --profile "$(PROFILE)" --query "$(QUERY)" $(GENERATION_ARGS)

example:
	@$(PYTHON) examples/synthetic-codebook/generate.py

smoke:
	@$(PYTHON) -m codebook_agent smoke

test:
	@$(PYTHON) -m pytest -q

test-agent:
	@$(PYTHON) -m pytest -q tests/test_agent_contract.py tests/test_cli.py

test-ocr:
	@$(PYTHON) -m pytest -q -m ocr

test-pgvector:
	@CODEBOOK_TEST_DATABASE_URL="$(CODEBOOK_DATABASE_URL)" $(PYTHON) -m pytest -q -m pgvector

lint:
	@$(PYTHON) -m ruff check .

leak-check:
	@$(PYTHON) scripts/leak_guard.py

check: lint test smoke leak-check
	@git diff --check

clean:
	@$(PYTHON) -m codebook_agent clean --artifacts "$(ARTIFACTS)" --plan

clean-apply:
	@$(PYTHON) -m codebook_agent clean --artifacts "$(ARTIFACTS)" --apply

docker-build:
	@docker build -t elec-codebook-oo:local .

docker-run:
	@docker compose run --rm codebook doctor

pgvector-up:
	@docker compose --profile pgvector up -d pgvector

pgvector-down:
	@docker compose --profile pgvector down -v
