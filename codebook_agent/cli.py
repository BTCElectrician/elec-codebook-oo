"""Small, dependency-free command surface for safe local workflows."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Sequence

from .backends.local import export_jsonl, write_documents
from .core import extract_text, load_profile, make_documents, plan

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = ROOT / "codebook_agent" / "profiles" / "nfpa70-reference-template.json"
DEFAULT_SOURCE = ROOT / "examples" / "synthetic-codebook" / "source.txt"

CAPABILITIES = {
    "schema_version": "1.0",
    "implemented_backends": ["local-artifacts"],
    "candidate_backends": ["lancedb", "qdrant", "pgvector", "opensearch"],
    "not_implemented": ["azure-ai-search", "ai-processing", "local-search", "chat"],
    "commands": {
        "plan": {"network": False, "writes": False, "apply_required": False},
        "dry": {"network": False, "writes": False, "apply_required": False},
        "ingest": {"network": False, "writes": ["local artifact directory"], "apply_required": True},
        "export": {"network": False, "writes": ["local JSONL export"], "apply_required": False},
    },
    "data_boundary": "Bring your own authorized content. Artifacts and exports are user-content derivatives.",
}


def _json(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def _profile_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)


def _source_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--pdf", type=Path, default=DEFAULT_SOURCE, help="Source .pdf, .txt, or .md file")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codebook", description="Local-first codebook ingestion kit")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("help", help="show the safe command map")
    doctor = sub.add_parser("doctor", help="check local prerequisites")
    doctor.add_argument("--artifacts", type=Path, default=Path("artifacts"))
    caps = sub.add_parser("caps", help="show capability and safety contract")
    caps.add_argument("--json", action="store_true")
    ask = sub.add_parser("ask", help="print profile interview questions")
    _profile_arg(ask)
    planner = sub.add_parser("plan", help="build a no-write local plan")
    _profile_arg(planner)
    _source_arg(planner)
    dry = sub.add_parser("dry", help="validate the local plan without writes")
    _profile_arg(dry)
    _source_arg(dry)
    ingest = sub.add_parser("ingest", help="write local artifacts after explicit apply")
    _profile_arg(ingest)
    _source_arg(ingest)
    ingest.add_argument("--artifacts", type=Path, default=Path("artifacts"))
    ingest.add_argument("--apply", action="store_true", help="required to create local artifacts")
    export = sub.add_parser("export", help="export local artifacts")
    export.add_argument("format", choices=["jsonl"])
    _profile_arg(export)
    export.add_argument("--artifacts", type=Path, default=Path("artifacts"))
    clean = sub.add_parser("clean", help="remove only the specified generated artifact directory")
    clean.add_argument("--artifacts", type=Path, default=Path("artifacts"))
    sub.add_parser("smoke", help="run the synthetic local end-to-end workflow")
    return parser


def _help() -> None:
    print("""Safe local command map:
  make doctor       check Python and artifact-directory access
  make caps-json    machine-readable capability/safety contract
  make ask          profile interview questions
  make plan PDF=/absolute/path/book.pdf   no-write plan
  make dry          no-write validation
  make ingest       local artifact write (Make target includes --apply)
  make export       portable local JSONL export
  make smoke        synthetic end-to-end test

AI, Azure publishing, and vector/search backends are not implemented in this release.""")


def command(args: argparse.Namespace) -> int:
    if args.command == "help":
        _help()
    elif args.command == "doctor":
        parent = args.artifacts.resolve().parent
        result = {"python": sys.version.split()[0], "artifact_parent": str(parent), "writable": parent.exists() and parent.is_dir()}
        _json(result)
        return 0 if result["writable"] else 1
    elif args.command == "caps":
        _json(CAPABILITIES) if args.json else print("Implemented: local-artifacts. Candidate: lancedb, qdrant, pgvector, opensearch. No provider calls.")
    elif args.command == "ask":
        profile = load_profile(args.profile)
        for number, question in enumerate(profile["questions"], start=1):
            print(f"{number}. {question}")
    elif args.command in {"plan", "dry"}:
        result = plan(args.profile, args.pdf)
        if not result["source"]["exists"]:
            raise FileNotFoundError(f"Source not found: {args.pdf}")
        result["operation"] = "local-dry-run" if args.command == "dry" else result["operation"]
        _json(result)
    elif args.command == "ingest":
        if not args.apply:
            raise PermissionError("Refusing to write. Re-run with --apply after operator approval.")
        profile = load_profile(args.profile)
        if not args.pdf.is_file():
            raise FileNotFoundError(f"Source not found: {args.pdf}")
        destination = write_documents(args.artifacts, profile["id"], make_documents(profile, args.pdf, extract_text(args.pdf)))
        _json({"operation": "local-ingest", "network": False, "documents": len(json.loads(destination.read_text())), "artifact": str(destination)})
    elif args.command == "export":
        profile = load_profile(args.profile)
        destination = export_jsonl(args.artifacts, profile["id"])
        _json({"operation": "local-export", "network": False, "format": args.format, "artifact": str(destination)})
    elif args.command == "clean":
        if args.artifacts.resolve().name != "artifacts":
            raise ValueError("Refusing to remove a directory not named artifacts.")
        if args.artifacts.exists():
            shutil.rmtree(args.artifacts)
        print("Removed generated artifacts only.")
    elif args.command == "smoke":
        with tempfile.TemporaryDirectory(prefix="codebook-smoke-") as temp:
            root = Path(temp) / "artifacts"
            profile = load_profile(DEFAULT_PROFILE)
            destination = write_documents(root, profile["id"], make_documents(profile, DEFAULT_SOURCE, extract_text(DEFAULT_SOURCE)))
            exported = export_jsonl(root, profile["id"])
            if not destination.exists() or exported.read_text(encoding="utf-8").count("\n") != 3:
                raise RuntimeError("Synthetic smoke did not produce the expected three documents.")
            print("Synthetic smoke passed: 3 local documents exported to JSONL.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return command(build_parser().parse_args(argv))
    except (FileNotFoundError, PermissionError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
