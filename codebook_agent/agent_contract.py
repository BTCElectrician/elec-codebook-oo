"""Canonical discovery contract for humans, coding agents, and automation."""

from __future__ import annotations

from typing import Any

from . import __version__
from .core import SUPPORTED_BACKENDS
from .embeddings import SUPPORTED_EMBEDDING_PROVIDERS
from .models import DOCUMENT_SCHEMA_VERSION, PAGE_SCHEMA_VERSION
from .text_models import TEXT_MODEL_PROVIDERS

CLI_CONTRACT_VERSION = "1.1"

EXIT_CODES = {
    "0": {
        "name": "success",
        "meaning": "The requested operation completed.",
        "retry": "No retry is required.",
    },
    "1": {
        "name": "input-error",
        "meaning": "Arguments, paths, profiles, or input data need correction.",
        "retry": "Correct the reported input, then retry.",
    },
    "2": {
        "name": "safety-block",
        "meaning": "A write or destructive action lacked its explicit approval flag.",
        "retry": "Review the preview and add the reported --apply flag only after approval.",
    },
    "3": {
        "name": "environment-error",
        "meaning": "A required local executable, package, directory, or configuration is missing.",
        "retry": "Run codebook doctor, repair the reported prerequisite, then retry.",
    },
    "4": {
        "name": "upstream-failure",
        "meaning": "A configured database or provider failed.",
        "retry": "Verify the named service and its configuration without printing credentials.",
    },
    "5": {
        "name": "internal-failure",
        "meaning": "An invariant failed inside the application.",
        "retry": "Run codebook doctor and make check; report the sanitized error if it repeats.",
    },
}

ENVIRONMENT = {
    "CODEBOOK_DATABASE_URL": {
        "required_for": ["pgvector ingest", "search", "query", "answer"],
        "secret": True,
        "printed": False,
        "description": "Operator-selected PostgreSQL connection URL.",
    },
    "OPENAI_API_KEY": {
        "required_for": [
            "OpenAI embeddings",
            "OpenAI OCR correction",
            "OpenAI answer synthesis",
        ],
        "secret": True,
        "printed": False,
        "description": "Credential for explicitly selected OpenAI provider operations.",
    },
    "NO_COLOR": {
        "required_for": [],
        "secret": False,
        "printed": False,
        "description": "Accepted by convention; CLI output is unstyled with or without it.",
    },
}

COMMANDS = {
    "agent": {
        "summary": "Return a one-call repository and runtime orientation packet.",
        "connections": [],
        "writes": [],
        "apply_required": False,
        "json": True,
        "example": "codebook agent --json",
    },
    "answer": {
        "summary": "Answer from indexed evidence; extractive unless synthesis is selected.",
        "connections": [
            "configured PostgreSQL",
            "embedding provider when selected",
            "text-model provider when synthesis is selected",
        ],
        "writes": [],
        "apply_required": False,
        "json": True,
        "example": 'codebook answer --profile profile.json --query "minimum cover" --json',
    },
    "ask": {
        "summary": "Return the profile interview used before processing a new source.",
        "connections": [],
        "writes": [],
        "apply_required": False,
        "json": True,
        "example": "codebook ask --profile profile.json --json",
    },
    "caps": {
        "aliases": ["capabilities"],
        "summary": "Describe implemented capabilities, boundaries, commands, and contracts.",
        "connections": [],
        "writes": [],
        "apply_required": False,
        "json": True,
        "example": "codebook capabilities --json",
    },
    "clean": {
        "summary": "Preview or apply removal of one generated directory named artifacts.",
        "connections": [],
        "writes": ["selected generated artifacts directory with --apply"],
        "apply_required": True,
        "json": True,
        "example": "codebook clean --artifacts artifacts --plan",
    },
    "configure": {
        "summary": "Inspect an authorized source and propose or write a metadata-only profile.",
        "connections": [],
        "writes": ["selected profile JSON path with --apply"],
        "apply_required": True,
        "json": True,
        "example": "codebook configure --source book.pdf --authorized --json",
    },
    "doctor": {
        "summary": "Inspect local prerequisites without connecting or writing.",
        "connections": [],
        "writes": [],
        "apply_required": False,
        "json": True,
        "example": "codebook doctor --json",
    },
    "dry": {
        "summary": "Validate an ingestion plan without clients, connections, or writes.",
        "connections": [],
        "writes": [],
        "apply_required": False,
        "json": True,
        "example": "codebook dry --profile profile.json --pdf book.pdf",
    },
    "export": {
        "summary": "Export an existing local corpus to deterministic JSONL.",
        "connections": [],
        "writes": ["local JSONL export"],
        "apply_required": False,
        "json": True,
        "example": "codebook export jsonl --profile profile.json",
    },
    "help": {
        "summary": "Show the safe command map or exact help for one command.",
        "connections": [],
        "writes": [],
        "apply_required": False,
        "json": False,
        "example": "codebook help plan",
    },
    "ingest": {
        "summary": "Apply an approved local-artifact or pgvector ingestion plan.",
        "connections": [
            "configured PostgreSQL for pgvector",
            "explicitly selected embedding or correction provider",
        ],
        "writes": ["local artifact directory or configured PostgreSQL schema"],
        "apply_required": True,
        "json": True,
        "example": "codebook ingest --apply --profile profile.json --pdf book.pdf",
    },
    "plan": {
        "summary": "Preview exact destinations, providers, and evidence without side effects.",
        "connections": [],
        "writes": [],
        "apply_required": False,
        "json": True,
        "example": "codebook plan --profile profile.json --pdf book.pdf",
    },
    "query": {
        "summary": "Compatibility alias for search.",
        "connections": ["configured PostgreSQL", "embedding provider when selected"],
        "writes": [],
        "apply_required": False,
        "json": True,
        "example": 'codebook query --profile profile.json --query "minimum cover" --json',
    },
    "robot-docs guide": {
        "summary": "Print a compact, paste-ready operating guide for another agent.",
        "connections": [],
        "writes": [],
        "apply_required": False,
        "json": True,
        "example": "codebook robot-docs guide --json",
    },
    "schema": {
        "summary": "Describe stable JSON output shapes.",
        "connections": [],
        "writes": [],
        "apply_required": False,
        "json": True,
        "example": "codebook schema --json",
    },
    "search": {
        "summary": "Retrieve ranked source evidence from pgvector.",
        "connections": ["configured PostgreSQL", "embedding provider when selected"],
        "writes": [],
        "apply_required": False,
        "json": True,
        "example": 'codebook search --profile profile.json --query "minimum cover" --json',
    },
    "smoke": {
        "summary": "Run the synthetic local workflow in a temporary directory.",
        "connections": [],
        "writes": ["temporary directory removed on exit"],
        "apply_required": False,
        "json": True,
        "example": "codebook smoke --json",
    },
}

OUTPUT_SCHEMAS: dict[str, dict[str, Any]] = {
    "agent-triage": {
        "type": "object",
        "required": [
            "contract_version",
            "package",
            "health",
            "entrypoints",
            "interaction_contract",
            "workflows",
            "recommended_next_actions",
        ],
    },
    "capabilities": {
        "type": "object",
        "required": [
            "cli_contract_version",
            "package_version",
            "implemented_backends",
            "commands",
            "exit_codes",
            "environment",
        ],
    },
    "grounded-answer": {
        "type": "object",
        "required": [
            "contract_version",
            "query",
            "mode",
            "answer",
            "sources",
            "metadata",
        ],
    },
    "doctor": {
        "type": "object",
        "required": [
            "contract_version",
            "status",
            "python",
            "writable",
            "database_url_configured",
            "next_commands",
        ],
    },
    "operation-result": {
        "type": "object",
        "required": ["operation"],
        "description": "Write commands also report concrete destinations and applied effects.",
    },
    "plan": {
        "type": "object",
        "required": [
            "operation",
            "network",
            "writes",
            "apply",
            "profile",
            "source",
            "next",
        ],
    },
    "profile-proposal": {
        "type": "object",
        "required": [
            "operation",
            "network",
            "provider_calls",
            "authorization_confirmed",
            "inspection",
            "profile",
            "profile_path",
            "applied",
            "writes",
            "unresolved_decisions",
            "commands",
            "next",
        ],
        "description": "Contains source metrics and profile metadata, never extracted text.",
    },
    "retrieval": {
        "type": "object",
        "required": ["contract_version", "query", "results"],
        "description": "Each result contains scores, a citation, and a CodebookDocument.",
    },
}

CODE_MAP = {
    "cli-and-agent-contract": {
        "paths": [
            "codebook_agent/cli.py",
            "codebook_agent/cli_surface.py",
            "codebook_agent/configure.py",
            "codebook_agent/agent_contract.py",
            "tests/test_agent_contract.py",
            "tests/test_cli.py",
        ],
        "invariants": [
            "machine data stays on stdout and diagnostics stay on stderr",
            "writes retain explicit apply gates",
            "capabilities describe implemented behavior only",
        ],
    },
    "evidence-model": {
        "paths": [
            "codebook_agent/models.py",
            "codebook_agent/core.py",
            "tests/test_core.py",
        ],
        "invariants": [
            "raw page evidence remains recoverable",
            "schema changes are versioned",
            "document identifiers are deterministic",
        ],
    },
    "extraction-and-ocr": {
        "paths": [
            "codebook_agent/ocr.py",
            "codebook_agent/correction.py",
            "codebook_agent/structure.py",
            "tests/test_ocr.py",
            "tests/test_correction.py",
            "tests/test_structure.py",
        ],
        "invariants": [
            "OCR provenance is never relabeled as native text",
            "model correction preserves raw text and protected identifiers",
        ],
    },
    "persistence-and-retrieval": {
        "paths": [
            "codebook_agent/backends/local.py",
            "codebook_agent/backends/pgvector.py",
            "codebook_agent/backends/sql/001_pgvector.sql",
            "tests/test_pgvector_integration.py",
        ],
        "invariants": [
            "backends store the same CodebookDocument contract",
            "database URLs and credentials never appear in output",
        ],
    },
    "answers": {
        "paths": [
            "codebook_agent/answers.py",
            "codebook_agent/text_models.py",
            "tests/test_answers.py",
            "tests/test_synthesis.py",
        ],
        "invariants": [
            "extractive mode is the default",
            "invalid synthesis citations fall back to extractive evidence",
        ],
    },
    "public-safety": {
        "paths": [
            "AGENTS.md",
            "scripts/leak_guard.py",
            "tests/test_leak_guards.py",
        ],
        "invariants": [
            "only synthetic or metadata-only fixtures belong in git",
            "generated content and credentials remain untracked",
        ],
    },
}

ENTRYPOINTS = {
    "authority": "AGENTS.md",
    "current_state": "STATUS.md",
    "orientation": "docs/AGENT_ONBOARDING.md",
    "change_map": "docs/CODEMAP.md",
    "architecture": "docs/ARCHITECTURE.md",
    "commands": "docs/COMMANDS.md",
}

INTERACTION_CONTRACT = {
    "principle": (
        "Translate ordinary-language intent into the smallest safe, verifiable action; "
        "do not make the operator learn internal paths, IDs, or command syntax."
    ),
    "response_order": [
        "Lead with the verified outcome or current state.",
        "Distinguish implemented, optional, candidate, blocked, and not implemented behavior.",
        "Name the relevant evidence, owner, and safety boundary.",
        "Offer only useful next choices: understand, explain, change, run, or verify.",
        "Preview exact destinations and external data boundaries before consequential actions.",
    ],
    "supported_intents": {
        "understand": "Orient from authority, current state, code map, and runtime contract.",
        "explain": "Trace behavior from entry point through evidence and focused tests.",
        "change": "Find the owning contract, preserve its invariants, edit, and validate.",
        "run": "Choose the safest command that satisfies the stated outcome.",
        "verify": "Run focused, full, and real-service checks proportional to the change.",
    },
}

WORKFLOWS = {
    "understand": [
        "codebook agent --json",
        "codebook capabilities --json",
        "codebook robot-docs guide",
    ],
    "change": [
        "Read AGENTS.md, STATUS.md, and docs/CODEMAP.md.",
        "Inspect the named contract and its focused tests.",
        "Make the smallest coherent change.",
        "Run focused tests, make check, and git diff --check.",
    ],
    "new-source": [
        "Confirm the operator is authorized to process the exact source.",
        "codebook configure --source /path/book.pdf --authorized --json",
        "Review unresolved decisions and rerun the returned apply_profile command.",
        "codebook plan --profile /path/profile.json --pdf /path/book.pdf",
        "codebook dry --profile /path/profile.json --pdf /path/book.pdf",
        "Review the exact destination and request operator approval.",
        "codebook ingest --apply --profile /path/profile.json --pdf /path/book.pdf",
    ],
}


def capabilities() -> dict[str, Any]:
    """Return the stable, side-effect-free capability and safety contract."""

    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "cli_contract_version": CLI_CONTRACT_VERSION,
        "package": "elec-codebook-oo",
        "package_version": __version__,
        "document_schema_version": DOCUMENT_SCHEMA_VERSION,
        "page_schema_version": PAGE_SCHEMA_VERSION,
        "implemented_backends": sorted(SUPPORTED_BACKENDS),
        "implemented_source_formats": ["md", "pdf", "txt"],
        "implemented_configuration": [
            "local-source-inspection",
            "metadata-only-profile-proposal",
            "apply-gated-profile-write",
        ],
        "implemented_retrieval_backends": ["pgvector"],
        "implemented_embedding_providers": sorted(SUPPORTED_EMBEDDING_PROVIDERS),
        "implemented_ocr_engines": ["tesseract"],
        "implemented_ocr_correction_providers": sorted(TEXT_MODEL_PROVIDERS),
        "implemented_text_model_providers": sorted(TEXT_MODEL_PROVIDERS),
        "implemented_structure_recovery": ["generic-blocks", "continued-tables"],
        "implemented_answer_modes": [
            "extractive-grounded",
            "citation-validated-synthesis",
        ],
        "candidate_backends": ["lancedb", "qdrant", "opensearch"],
        "not_implemented": ["azure-ai-search"],
        "commands": COMMANDS,
        "output_schemas": OUTPUT_SCHEMAS,
        "exit_codes": EXIT_CODES,
        "environment": ENVIRONMENT,
        "entrypoints": ENTRYPOINTS,
        "interaction_contract": INTERACTION_CONTRACT,
        "code_map": CODE_MAP,
        "data_boundary": (
            "Bring your own authorized content. Sources, artifacts, embeddings, indexes, "
            "and provider-bound text are operator-controlled derivatives and never belong in git."
        ),
    }


def agent_guide() -> str:
    """Return a compact guide suitable for a human or another coding agent."""

    return """Elec Codebook OO agent guide

Purpose
  Build page-cited records or a pgvector corpus from operator-authorized sources.

Start
  1. Read AGENTS.md and STATUS.md.
  2. Run: codebook agent --json
  3. Use docs/CODEMAP.md to find the owning contract and focused tests.

Safe discovery
  codebook capabilities --json
  codebook schema --json
  codebook help <command>
  make doctor

Conversation contract
  Accept ordinary-language intent.
  Lead with verified current state and distinguish implemented from candidate behavior.
  Offer the relevant next choice: understand, explain, change, run, or verify.
  Preview exact destinations and external data boundaries before consequential actions.

Source workflow
  configure -> plan -> dry -> review exact target -> ingest --apply -> verify evidence

Configure a new source
  1. Confirm the operator is authorized to process the exact source.
  2. Run: codebook configure --source /path/book.pdf --authorized --json
  3. Discuss unresolved decisions, then run the returned apply_profile command.
  Configuration is local-only, returns no extracted text, and calls no provider.

Hard boundaries
  Never commit source PDFs, extracts, page images, artifacts, JSONL exports, credentials, or .env.
  Never print CODEBOOK_DATABASE_URL or OPENAI_API_KEY.
  Preserve raw OCR evidence and provenance.
  Do not imply candidate backends are implemented.
  Do not write or delete without the command's explicit --apply gate.

Before handoff
  Run focused tests, make check, git diff --check, and update STATUS.md when state changes.
"""
