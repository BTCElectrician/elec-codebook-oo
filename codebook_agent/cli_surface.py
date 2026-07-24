"""Side-effect-free CLI parsing, discovery, health, and intent recovery."""

from __future__ import annotations

import argparse
import difflib
import os
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .agent_contract import (
    CLI_CONTRACT_VERSION,
    COMMANDS,
    ENTRYPOINTS,
    INTERACTION_CONTRACT,
    OUTPUT_SCHEMAS,
    WORKFLOWS,
)
from .core import SUPPORTED_BACKENDS
from .correction import CORRECTION_MODES
from .embeddings import SUPPORTED_EMBEDDING_PROVIDERS
from .ocr import OCR_MODES
from .text_models import TEXT_MODEL_PROVIDERS

PACKAGE_ROOT = Path(__file__).resolve().parent
DEFAULT_PROFILE = PACKAGE_ROOT / "profiles" / "generic-reference-template.json"
DEFAULT_SOURCE = PACKAGE_ROOT / "data" / "synthetic_source.txt"


class CLIUsageError(Exception):
    """An invocation that can be corrected without changing the environment."""


class EnvironmentError(RuntimeError):
    """A missing local prerequisite or required configuration."""


class SafetyError(PermissionError):
    """A blocked operation that requires explicit operator approval."""


class AgentArgumentParser(argparse.ArgumentParser):
    """Argument parser whose failures teach the next valid command."""

    def error(self, message: str) -> None:
        raise CLIUsageError(message)


def _profile_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--profile",
        type=Path,
        default=DEFAULT_PROFILE,
        help="metadata-only JSON profile (default: bundled generic profile)",
    )


def _source_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--pdf",
        type=Path,
        default=DEFAULT_SOURCE,
        help="authorized source .pdf, .txt, or .md file",
    )


def _json_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit deterministic JSON on stdout",
    )


def _backend_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--backend",
        choices=sorted(SUPPORTED_BACKENDS),
        help="override the backend selected by the profile",
    )


def _postgres_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--schema",
        default="codebook",
        help="lowercase PostgreSQL schema name (default: codebook)",
    )


def _embedding_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--embedding-provider",
        choices=sorted(SUPPORTED_EMBEDDING_PROVIDERS),
        help="override the pgvector embedding provider",
    )
    parser.add_argument(
        "--embedding-model",
        help="override the model paired with --embedding-provider",
    )


def _ocr_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--ocr-mode",
        choices=sorted(OCR_MODES),
        help="off, automatic low-text fallback, or OCR every PDF page",
    )
    parser.add_argument("--ocr-language", help="Tesseract language code, such as eng")
    parser.add_argument("--ocr-dpi", type=int, help="local PDF render resolution")
    parser.add_argument(
        "--ocr-page-segmentation-mode",
        type=int,
        help="Tesseract page segmentation mode",
    )
    parser.add_argument(
        "--ocr-min-native-characters",
        type=int,
        help="minimum usable native characters before auto OCR",
    )
    parser.add_argument(
        "--ocr-timeout-seconds",
        type=int,
        help="per-page local Tesseract timeout",
    )


def _correction_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--correction-mode",
        choices=sorted(CORRECTION_MODES),
        help="off, OCR-derived pages only, or all extracted pages",
    )
    parser.add_argument(
        "--correction-provider",
        choices=sorted(TEXT_MODEL_PROVIDERS),
        help="explicit text-model provider for correction",
    )
    parser.add_argument("--correction-model", help="explicit correction model")
    parser.add_argument(
        "--correction-min-similarity",
        type=float,
        help="minimum raw/candidate similarity accepted by the correction gate",
    )
    parser.add_argument(
        "--correction-max-length-change-ratio",
        type=float,
        help="maximum accepted proportional length change",
    )


def _retrieval_parser(
    sub: argparse._SubParsersAction[argparse.ArgumentParser],
    name: str,
) -> None:
    parser = sub.add_parser(name, help=f"{name} an indexed corpus with source evidence")
    _profile_arg(parser)
    _postgres_args(parser)
    parser.add_argument("--query", required=True, help="ordinary-language retrieval question")
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        help="maximum ranked results (default: 5)",
    )
    parser.add_argument(
        "--content-type",
        action="append",
        dest="content_types",
        help="repeatable content-type filter",
    )
    _json_arg(parser)


def build_parser() -> argparse.ArgumentParser:
    """Build the complete CLI grammar without performing any I/O."""

    parser = AgentArgumentParser(
        prog="codebook",
        description=(
            "Evidence-preserving ingestion and grounded retrieval.\n"
            "Bare invocation and discovery commands are safe: no writes, connections, "
            "or provider calls."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "FIRST TRY\n"
            "  codebook agent --json       one-call orientation and local health\n"
            "  codebook help plan          exact help for a command\n"
            "  codebook capabilities --json\n\n"
            "SAFETY\n"
            "  ingest and destructive cleanup require explicit --apply.\n"
            "  Machine data is written to stdout; warnings and errors use stderr.\n\n"
            "EXIT CODES\n"
            "  0 success  1 input  2 safety  3 environment  4 upstream  5 internal"
        ),
    )
    parser.add_argument(
        "--robot-triage",
        action="store_true",
        help="emit the same one-call JSON packet as `codebook agent --json`",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    help_parser = sub.add_parser("help", help="show the command map or help for one command")
    help_parser.add_argument("topic", nargs="?", help="command to explain")

    agent = sub.add_parser("agent", help="one-call orientation and local health packet")
    agent.add_argument(
        "--artifacts",
        type=Path,
        default=Path("artifacts"),
        help="prospective artifact directory used only for the writable-path check",
    )
    _json_arg(agent)

    doctor = sub.add_parser("doctor", help="check local prerequisites")
    doctor.add_argument(
        "--artifacts",
        type=Path,
        default=Path("artifacts"),
        help="prospective artifact directory used only for the writable-path check",
    )
    _json_arg(doctor)

    caps = sub.add_parser(
        "caps",
        aliases=["capabilities"],
        help="show the complete capability and safety contract",
    )
    caps.set_defaults(command="caps")
    _json_arg(caps)

    ask = sub.add_parser("ask", help="print profile interview questions")
    _profile_arg(ask)
    _json_arg(ask)

    planner = sub.add_parser("plan", help="build a no-write ingestion plan")
    _profile_arg(planner)
    _source_arg(planner)
    _backend_arg(planner)
    _postgres_args(planner)
    _embedding_args(planner)
    _ocr_args(planner)
    _correction_args(planner)
    planner.add_argument(
        "--artifacts",
        type=Path,
        default=Path("artifacts"),
        help="prospective local output root included in the preview",
    )
    _json_arg(planner)

    dry = sub.add_parser("dry", help="validate the plan without writes or connections")
    _profile_arg(dry)
    _source_arg(dry)
    _backend_arg(dry)
    _postgres_args(dry)
    _embedding_args(dry)
    _ocr_args(dry)
    _correction_args(dry)
    dry.add_argument(
        "--artifacts",
        type=Path,
        default=Path("artifacts"),
        help="prospective local output root included in the validation",
    )
    _json_arg(dry)

    ingest = sub.add_parser("ingest", help="ingest after explicit apply")
    _profile_arg(ingest)
    _source_arg(ingest)
    _backend_arg(ingest)
    _postgres_args(ingest)
    _embedding_args(ingest)
    _ocr_args(ingest)
    _correction_args(ingest)
    ingest.add_argument(
        "--artifacts",
        type=Path,
        default=Path("artifacts"),
        help="local output root when local-artifacts is selected",
    )
    ingest.add_argument("--apply", action="store_true", help="required to create artifacts or indexes")
    _json_arg(ingest)

    export = sub.add_parser("export", help="export local artifacts")
    export.add_argument("format", choices=["jsonl"], help="portable export format")
    _profile_arg(export)
    export.add_argument(
        "--artifacts",
        type=Path,
        default=Path("artifacts"),
        help="local artifact root containing the prior ingest",
    )
    _json_arg(export)

    _retrieval_parser(sub, "search")
    _retrieval_parser(sub, "query")
    _retrieval_parser(sub, "answer")
    answer = sub.choices["answer"]
    answer.add_argument(
        "--answer-mode",
        choices=["extractive", "synthesized"],
        default="extractive",
        help="extract source wording or request citation-validated synthesis",
    )
    answer.add_argument(
        "--generation-provider",
        choices=sorted(TEXT_MODEL_PROVIDERS),
        help="explicit provider used only in synthesized mode",
    )
    answer.add_argument("--generation-model", help="explicit synthesis model")
    answer.add_argument(
        "--plan",
        action="store_true",
        help="preview answer providers and data boundaries without connecting",
    )

    clean = sub.add_parser("clean", help="remove only the specified generated artifact directory")
    clean.add_argument(
        "--artifacts",
        type=Path,
        default=Path("artifacts"),
        help="generated directory; its resolved name must be artifacts",
    )
    clean_mode = clean.add_mutually_exclusive_group()
    clean_mode.add_argument(
        "--plan",
        action="store_true",
        help="preview the target without deleting it (default)",
    )
    clean_mode.add_argument(
        "--apply",
        action="store_true",
        help="delete the validated generated target after approval",
    )
    _json_arg(clean)

    smoke = sub.add_parser("smoke", help="run the synthetic local evidence workflow")
    _json_arg(smoke)

    schema = sub.add_parser("schema", help="describe stable JSON output shapes")
    schema.add_argument(
        "name",
        nargs="?",
        default="all",
        choices=["all", *sorted(OUTPUT_SCHEMAS)],
    )
    _json_arg(schema)

    robot_docs = sub.add_parser("robot-docs", help="compact documentation for another agent")
    robot_sub = robot_docs.add_subparsers(dest="robot_topic")
    guide = robot_sub.add_parser("guide", help="print the paste-ready operating guide")
    _json_arg(guide)
    return parser


def _subcommand_parser(
    parser: argparse.ArgumentParser,
    topic: str,
) -> argparse.ArgumentParser | None:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action.choices.get(topic)
    return None


def render_help(topic: str | None = None) -> None:
    """Print general or command-specific help from the canonical catalog."""

    if topic:
        normalized = "caps" if topic == "capabilities" else topic
        topic_parser = _subcommand_parser(build_parser(), normalized)
        if topic_parser is None:
            matches = difflib.get_close_matches(normalized, top_level_commands(), n=1)
            hint = f" Did you mean `{matches[0]}`?" if matches else ""
            raise CLIUsageError(
                f"Unknown help topic: {topic}.{hint} Run `codebook help` to list commands."
            )
        topic_parser.print_help()
        return

    rows = [
        f"  {name:<19} {details['summary']}"
        for name, details in COMMANDS.items()
    ]
    print(
        "\n".join(
            [
                "Elec Codebook OO — safe command map",
                "",
                "First try:",
                "  codebook agent --json    one-call orientation, health, and next actions",
                "  codebook help <command>  exact flags and usage",
                "",
                "Commands:",
                *rows,
                "",
                "Canonical source workflow:",
                "  ask -> plan -> dry -> review exact target -> ingest --apply -> verify evidence",
                "",
                "Rules:",
                "  Discovery, planning, and dry-run commands do not connect or write.",
                "  Ingest and destructive cleanup require an explicit --apply.",
                "  PostgreSQL and provider credentials are read only when selected and never printed.",
                "",
                "Machine contracts:",
                "  codebook capabilities --json",
                "  codebook schema --json",
                "  codebook robot-docs guide --json",
            ]
        )
    )


def _nearest_existing_parent(path: Path) -> Path:
    candidate = path.resolve().parent
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate


def _module_available(name: str) -> bool:
    try:
        __import__(name)
    except ImportError:
        return False
    return True


def doctor_result(artifacts: Path) -> dict[str, object]:
    """Inspect local readiness without writing, connecting, or loading credentials."""

    artifact_parent = artifacts.resolve().parent
    writable_parent = _nearest_existing_parent(artifacts)
    writable = (
        writable_parent.exists()
        and writable_parent.is_dir()
        and os.access(writable_parent, os.W_OK)
    )
    return {
        "contract_version": CLI_CONTRACT_VERSION,
        "status": "ready" if writable else "blocked",
        "python": sys.version.split()[0],
        "artifact_parent": str(artifact_parent),
        "writable_parent": str(writable_parent),
        "writable": writable,
        "postgres_extra": _module_available("psycopg") and _module_available("pgvector"),
        "ocr_extra": _module_available("pypdfium2"),
        "ai_extra": _module_available("openai"),
        "tesseract": shutil.which("tesseract") is not None,
        "database_url_configured": bool(os.getenv("CODEBOOK_DATABASE_URL")),
        "next_commands": (
            ["codebook plan", "codebook smoke --json"]
            if writable
            else [
                "Choose an artifact path beneath a writable directory.",
                "codebook doctor --artifacts /writable/path/artifacts --json",
            ]
        ),
    }


def agent_triage(artifacts: Path) -> dict[str, object]:
    """Build a one-call repository/runtime orientation packet."""

    health = doctor_result(artifacts)
    recommendations = [
        "Read AGENTS.md and STATUS.md before editing.",
        "Use docs/CODEMAP.md to identify the owning contract and focused tests.",
        "Run codebook plan before any source ingestion.",
    ]
    if not health["writable"]:
        recommendations.insert(0, "Select a writable artifact destination.")
    if not health["postgres_extra"]:
        recommendations.append(
            "Install .[postgres] only if pgvector ingestion or retrieval is required."
        )
    if not health["ocr_extra"] or not health["tesseract"]:
        recommendations.append(
            "Install .[ocr] and Tesseract only if image-only PDF pages must be processed."
        )
    return {
        "contract_version": CLI_CONTRACT_VERSION,
        "package": {"name": "elec-codebook-oo", "version": __version__},
        "safe_to_run": True,
        "side_effects": {"connections": [], "writes": []},
        "health": health,
        "entrypoints": ENTRYPOINTS,
        "interaction_contract": INTERACTION_CONTRACT,
        "workflows": WORKFLOWS,
        "recommended_next_actions": recommendations,
    }


def top_level_commands() -> list[str]:
    """Return every accepted top-level command, including aliases."""

    return [
        "agent",
        "answer",
        "ask",
        "capabilities",
        "caps",
        "clean",
        "doctor",
        "dry",
        "export",
        "help",
        "ingest",
        "plan",
        "query",
        "robot-docs",
        "schema",
        "search",
        "smoke",
    ]


def _option_strings(parser: argparse.ArgumentParser) -> set[str]:
    values: set[str] = set()
    for action in parser._actions:
        values.update(action.option_strings)
        if isinstance(action, argparse._SubParsersAction):
            for child in action.choices.values():
                values.update(_option_strings(child))
    return values


def normalize_argv(
    argv: Sequence[str],
    parser: argparse.ArgumentParser,
) -> list[str]:
    """Infer only unambiguous, non-authorizing command and option typos."""

    normalized = list(argv)
    commands = top_level_commands()
    if normalized and not normalized[0].startswith("-") and normalized[0] not in commands:
        match = difflib.get_close_matches(normalized[0], commands, n=1, cutoff=0.78)
        if match:
            print(
                f"warning: inferred command `{match[0]}` from `{normalized[0]}`.",
                file=sys.stderr,
            )
            normalized[0] = match[0]
    if (
        len(normalized) > 1
        and normalized[0] == "robot-docs"
        and not normalized[1].startswith("-")
        and normalized[1] != "guide"
    ):
        match = difflib.get_close_matches(normalized[1], ["guide"], n=1, cutoff=0.7)
        if match:
            print(
                f"warning: inferred topic `guide` from `{normalized[1]}`.",
                file=sys.stderr,
            )
            normalized[1] = "guide"

    options = _option_strings(parser)
    options.discard("--apply")
    for index, value in enumerate(normalized):
        if not value.startswith("--"):
            continue
        option, separator, attached = value.partition("=")
        if option in options:
            continue
        match = difflib.get_close_matches(option, sorted(options), n=1, cutoff=0.78)
        if not match:
            continue
        replacement = match[0] + (f"={attached}" if separator else "")
        print(
            f"warning: inferred option `{match[0]}` from `{option}`.",
            file=sys.stderr,
        )
        normalized[index] = replacement
    return normalized
