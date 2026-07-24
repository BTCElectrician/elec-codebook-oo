"""Agent-readable command surface for safe ingestion and grounded retrieval."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

from .answers import answer_from_results, synthesize_answer
from .backends.local import export_jsonl, write_documents, write_pages
from .core import SUPPORTED_BACKENDS, build_bundle, load_profile, plan
from .correction import CORRECTION_MODES, CorrectionConfig
from .embeddings import build_embedding_provider, resolve_embedding_selection
from .ocr import OCR_MODES
from .text_models import (
    DEFAULT_OPENAI_TEXT_MODEL,
    TEXT_MODEL_PROVIDERS,
    build_text_provider,
)

PACKAGE_ROOT = Path(__file__).resolve().parent
DEFAULT_PROFILE = PACKAGE_ROOT / "profiles" / "generic-reference-template.json"
DEFAULT_SOURCE = PACKAGE_ROOT / "data" / "synthetic_source.txt"

CAPABILITIES = {
    "schema_version": "2.2",
    "document_schema_version": "2.2",
    "page_schema_version": "1.0",
    "implemented_backends": ["local-artifacts", "pgvector"],
    "implemented_retrieval_backends": ["pgvector"],
    "implemented_embedding_providers": ["hash", "openai"],
    "implemented_ocr_engines": ["tesseract"],
    "implemented_ocr_correction_providers": ["openai"],
    "implemented_text_model_providers": ["openai"],
    "implemented_structure_recovery": ["generic-blocks", "continued-tables"],
    "implemented_answer_modes": ["extractive-grounded", "citation-validated-synthesis"],
    "candidate_backends": ["lancedb", "qdrant", "opensearch"],
    "not_implemented": [
        "azure-ai-search",
    ],
    "commands": {
        "plan": {"network": False, "writes": False, "apply_required": False},
        "dry": {"network": False, "writes": False, "apply_required": False},
        "ingest-local": {
            "network": ["text-model provider when correction is selected"],
            "writes": ["local artifact directory"],
            "apply_required": True,
        },
        "ingest-pgvector": {
            "network": [
                "configured PostgreSQL only",
                "embedding provider when selected",
                "text-model provider when correction is selected",
            ],
            "writes": ["configured PostgreSQL only"],
            "apply_required": True,
        },
        "search": {
            "network": ["configured PostgreSQL only", "embedding provider when selected"],
            "writes": False,
            "apply_required": False,
        },
        "answer": {
            "network": [
                "configured PostgreSQL only",
                "embedding provider when selected",
                "text-model provider when synthesis is selected",
            ],
            "writes": False,
            "apply_required": False,
        },
        "export": {
            "network": False,
            "writes": ["local JSONL export"],
            "apply_required": False,
        },
    },
    "data_boundary": (
        "Bring your own authorized content. Sources, artifacts, embeddings, indexes, "
        "and provider-bound text are operator-controlled derivatives and never belong in git."
    ),
}


def _json(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def _profile_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)


def _source_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--pdf",
        type=Path,
        default=DEFAULT_SOURCE,
        help="authorized source .pdf, .txt, or .md file",
    )


def _backend_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--backend", choices=sorted(SUPPORTED_BACKENDS))


def _postgres_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--schema",
        default="codebook",
        help="lowercase PostgreSQL schema name; defaults to codebook",
    )


def _embedding_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--embedding-provider", choices=["hash", "openai"])
    parser.add_argument("--embedding-model")


def _ocr_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--ocr-mode", choices=sorted(OCR_MODES))
    parser.add_argument("--ocr-language")
    parser.add_argument("--ocr-dpi", type=int)
    parser.add_argument("--ocr-page-segmentation-mode", type=int)
    parser.add_argument("--ocr-min-native-characters", type=int)
    parser.add_argument("--ocr-timeout-seconds", type=int)


def _correction_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--correction-mode", choices=sorted(CORRECTION_MODES))
    parser.add_argument("--correction-provider", choices=sorted(TEXT_MODEL_PROVIDERS))
    parser.add_argument("--correction-model")
    parser.add_argument("--correction-min-similarity", type=float)
    parser.add_argument("--correction-max-length-change-ratio", type=float)


def _retrieval_parser(sub: argparse._SubParsersAction[argparse.ArgumentParser], name: str) -> None:
    parser = sub.add_parser(name, help=f"{name} an indexed corpus with source evidence")
    _profile_arg(parser)
    _postgres_args(parser)
    parser.add_argument("--query", required=True)
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--content-type", action="append", dest="content_types")
    parser.add_argument("--json", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codebook",
        description="Backend-neutral codebook ingestion and grounded retrieval",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("help", help="show the safe command map")
    doctor = sub.add_parser("doctor", help="check local prerequisites")
    doctor.add_argument("--artifacts", type=Path, default=Path("artifacts"))
    caps = sub.add_parser("caps", help="show capability and safety contract")
    caps.add_argument("--json", action="store_true")
    ask = sub.add_parser("ask", help="print profile interview questions")
    _profile_arg(ask)
    planner = sub.add_parser("plan", help="build a no-write ingestion plan")
    _profile_arg(planner)
    _source_arg(planner)
    _backend_arg(planner)
    _postgres_args(planner)
    _embedding_args(planner)
    _ocr_args(planner)
    _correction_args(planner)
    planner.add_argument("--artifacts", type=Path, default=Path("artifacts"))
    dry = sub.add_parser("dry", help="validate the plan without writes or connections")
    _profile_arg(dry)
    _source_arg(dry)
    _backend_arg(dry)
    _postgres_args(dry)
    _embedding_args(dry)
    _ocr_args(dry)
    _correction_args(dry)
    dry.add_argument("--artifacts", type=Path, default=Path("artifacts"))
    ingest = sub.add_parser("ingest", help="ingest after explicit apply")
    _profile_arg(ingest)
    _source_arg(ingest)
    _backend_arg(ingest)
    _postgres_args(ingest)
    _embedding_args(ingest)
    _ocr_args(ingest)
    _correction_args(ingest)
    ingest.add_argument("--artifacts", type=Path, default=Path("artifacts"))
    ingest.add_argument("--apply", action="store_true", help="required to create artifacts or indexes")
    export = sub.add_parser("export", help="export local artifacts")
    export.add_argument("format", choices=["jsonl"])
    _profile_arg(export)
    export.add_argument("--artifacts", type=Path, default=Path("artifacts"))
    _retrieval_parser(sub, "search")
    _retrieval_parser(sub, "query")
    _retrieval_parser(sub, "answer")
    answer = sub.choices["answer"]
    answer.add_argument(
        "--answer-mode",
        choices=["extractive", "synthesized"],
        default="extractive",
    )
    answer.add_argument("--generation-provider", choices=sorted(TEXT_MODEL_PROVIDERS))
    answer.add_argument("--generation-model")
    answer.add_argument(
        "--plan",
        action="store_true",
        help="preview answer providers and data boundaries without connecting",
    )
    clean = sub.add_parser("clean", help="remove only the specified generated artifact directory")
    clean.add_argument("--artifacts", type=Path, default=Path("artifacts"))
    sub.add_parser("smoke", help="run the synthetic local evidence workflow")
    return parser


def _help() -> None:
    print(
        """Safe command map:
  make doctor       check Python and artifact-directory access
  make caps-json    machine-readable capability/safety contract
  make ask          profile interview questions
  make plan         no-write, no-connection plan
  make dry          no-write, no-connection validation
  make ingest       apply-gated local or pgvector ingestion
  make export       portable local JSONL export
  make test-ocr     real local OCR test on generated image-only PDF
  make search       pgvector hybrid retrieval with source evidence
  make answer       extractive answer; optional citation-validated synthesis
  make smoke        synthetic local evidence test

PostgreSQL commands read CODEBOOK_DATABASE_URL. They never print it.
The hash embedder and extractive answers are local. OpenAI embeddings, correction,
and synthesis are explicit opt-in and send only the documented text boundary."""
    )


def _database_url() -> str:
    value = os.getenv("CODEBOOK_DATABASE_URL", "").strip()
    if not value:
        raise ValueError("Set CODEBOOK_DATABASE_URL for pgvector operations.")
    return value


def _provider_for_profile(
    profile: dict[str, object],
    *,
    provider_override: str | None = None,
    model_override: str | None = None,
):
    provider_name, model = resolve_embedding_selection(
        profile,
        provider_override=provider_override,
        model_override=model_override,
    )
    return build_embedding_provider(
        provider_name,
        api_key=os.getenv("OPENAI_API_KEY"),
        model=model,
    )


def _profile_with_ocr_overrides(
    profile: dict[str, object],
    args: argparse.Namespace,
) -> dict[str, object]:
    ocr = dict(profile.get("ocr") or {})
    ocr.update(_ocr_overrides(args))
    return {**profile, "ocr": ocr}


def _profile_with_ingest_overrides(
    profile: dict[str, object],
    args: argparse.Namespace,
    *,
    backend: str,
) -> dict[str, object]:
    effective_profile = {
        **_profile_with_ocr_overrides(profile, args),
        "correction": {
            **dict(profile.get("correction") or {}),
            **_correction_overrides(args),
        },
        "backend": backend,
    }
    if backend != "pgvector":
        return effective_profile
    provider, model = resolve_embedding_selection(
        profile,
        provider_override=args.embedding_provider,
        model_override=args.embedding_model,
    )
    return {
        **effective_profile,
        "embedding": {"provider": provider, "model": model},
    }


def _ocr_overrides(args: argparse.Namespace) -> dict[str, object]:
    overrides: dict[str, object | None] = {
        "mode": getattr(args, "ocr_mode", None),
        "language": getattr(args, "ocr_language", None),
        "dpi": getattr(args, "ocr_dpi", None),
        "page_segmentation_mode": getattr(args, "ocr_page_segmentation_mode", None),
        "min_native_characters": getattr(args, "ocr_min_native_characters", None),
        "timeout_seconds": getattr(args, "ocr_timeout_seconds", None),
    }
    return {key: value for key, value in overrides.items() if value is not None}


def _correction_overrides(args: argparse.Namespace) -> dict[str, object]:
    overrides: dict[str, object | None] = {
        "mode": getattr(args, "correction_mode", None),
        "provider": getattr(args, "correction_provider", None),
        "model": getattr(args, "correction_model", None),
        "min_similarity": getattr(args, "correction_min_similarity", None),
        "max_length_change_ratio": getattr(
            args,
            "correction_max_length_change_ratio",
            None,
        ),
    }
    return {key: value for key, value in overrides.items() if value is not None}


def _correction_provider(profile: dict[str, object]):
    config = CorrectionConfig.from_profile(profile.get("correction"))
    if config.mode == "off":
        return None
    return build_text_provider(
        config.provider,
        api_key=os.getenv("OPENAI_API_KEY"),
        model=config.model,
    )


def _pgvector_backend(schema: str):
    from .backends.pgvector import PgVectorBackend

    return PgVectorBackend(_database_url(), schema=schema)


def _pgvector_search(args: argparse.Namespace):
    profile = load_profile(args.profile)
    with _pgvector_backend(args.schema) as backend:
        config = backend.corpus_config(str(profile["id"]))
        provider = build_embedding_provider(
            str(config["embedding_provider"]),
            api_key=os.getenv("OPENAI_API_KEY"),
            model=str(config["embedding_model"]),
        )
        query_vector = provider.embed([args.query])[0]
        return backend.search(
            corpus_id=str(profile["id"]),
            query=args.query,
            query_embedding=query_vector,
            limit=args.top,
            content_types=args.content_types,
        )


def command(args: argparse.Namespace) -> int:
    if args.command == "help":
        _help()
    elif args.command == "doctor":
        parent = args.artifacts.resolve().parent
        result = {
            "python": sys.version.split()[0],
            "artifact_parent": str(parent),
            "writable": parent.exists() and parent.is_dir(),
            "postgres_extra": _module_available("psycopg") and _module_available("pgvector"),
            "ocr_extra": _module_available("pypdfium2"),
            "ai_extra": _module_available("openai"),
            "tesseract": shutil.which("tesseract") is not None,
            "database_url_configured": bool(os.getenv("CODEBOOK_DATABASE_URL")),
        }
        _json(result)
        return 0 if result["writable"] else 1
    elif args.command == "caps":
        _json(CAPABILITIES) if args.json else print(
            "Implemented: local-artifacts and pgvector retrieval. "
            "Use `caps --json` for the full safety contract."
        )
    elif args.command == "ask":
        profile = load_profile(args.profile)
        for number, question in enumerate(profile["questions"], start=1):
            print(f"{number}. {question}")
    elif args.command in {"plan", "dry"}:
        result = plan(
            args.profile,
            args.pdf,
            backend=args.backend,
            ocr_overrides=_ocr_overrides(args),
            correction_overrides=_correction_overrides(args),
            artifacts=args.artifacts,
            schema=args.schema,
            embedding_provider=args.embedding_provider,
            embedding_model=args.embedding_model,
        )
        if not result["source"]["exists"]:
            raise FileNotFoundError(f"Source not found: {args.pdf}")
        result["operation"] = "codebook-dry-run" if args.command == "dry" else result["operation"]
        _json(result)
    elif args.command == "ingest":
        if not args.apply:
            raise PermissionError("Refusing to write. Re-run with --apply after operator approval.")
        profile = load_profile(args.profile)
        selected_backend = args.backend or profile["backend"]
        if not args.pdf.is_file():
            raise FileNotFoundError(f"Source not found: {args.pdf}")
        effective_profile = _profile_with_ingest_overrides(
            profile,
            args,
            backend=selected_backend,
        )
        if selected_backend == "local-artifacts":
            bundle = build_bundle(
                effective_profile,
                args.pdf,
                correction_provider=_correction_provider(effective_profile),
            )
            documents = bundle.documents
            ocr_documents = sum(
                document.metadata.get("extraction_method") == "ocr-tesseract"
                for document in documents
            )
            correction_config = CorrectionConfig.from_profile(
                effective_profile.get("correction")
            )
            accepted_corrections = sum(
                page.correction_status == "accepted" for page in bundle.pages
            )
            rejected_corrections = sum(
                page.correction_status == "rejected" for page in bundle.pages
            )
            destination = write_documents(args.artifacts, str(profile["id"]), documents)
            pages_destination = write_pages(
                args.artifacts,
                str(profile["id"]),
                bundle.pages,
            )
            _json(
                {
                    "operation": "local-ingest",
                    "network": (
                        ["OpenAI text generation API"]
                        if correction_config.mode != "off"
                        else False
                    ),
                    "documents": len(documents),
                    "ocr_documents": ocr_documents,
                    "accepted_corrections": accepted_corrections,
                    "rejected_corrections": rejected_corrections,
                    "artifact": str(destination),
                    "page_evidence": str(pages_destination),
                    "source_sha256": documents[0].source_sha256,
                }
            )
        elif selected_backend == "pgvector":
            with _pgvector_backend(args.schema) as backend:
                backend.verify_connection()
                bundle = build_bundle(
                    effective_profile,
                    args.pdf,
                    correction_provider=_correction_provider(effective_profile),
                )
                documents = bundle.documents
                ocr_documents = sum(
                    document.metadata.get("extraction_method") == "ocr-tesseract"
                    for document in documents
                )
                accepted_corrections = sum(
                    page.correction_status == "accepted" for page in bundle.pages
                )
                rejected_corrections = sum(
                    page.correction_status == "rejected" for page in bundle.pages
                )
                provider = _provider_for_profile(effective_profile)
                embeddings = provider.embed(
                    [document.search_text for document in documents]
                )
                count = backend.index_documents(
                    profile=effective_profile,
                    documents=documents,
                    embeddings=embeddings,
                    embedding_provider=provider.name,
                    embedding_model=provider.model,
                    pages=bundle.pages,
                )
            _json(
                {
                    "operation": "pgvector-ingest",
                    "database": "configured CODEBOOK_DATABASE_URL",
                    "schema": args.schema,
                    "documents": count,
                    "ocr_documents": ocr_documents,
                    "accepted_corrections": accepted_corrections,
                    "rejected_corrections": rejected_corrections,
                    "embedding_provider": provider.name,
                    "embedding_model": provider.model,
                    "source_sha256": documents[0].source_sha256,
                }
            )
        else:
            raise ValueError(f"Backend is not implemented: {selected_backend}")
    elif args.command == "export":
        profile = load_profile(args.profile)
        destination = export_jsonl(args.artifacts, str(profile["id"]))
        _json(
            {
                "operation": "local-export",
                "network": False,
                "format": args.format,
                "artifact": str(destination),
            }
        )
    elif args.command in {"search", "query"}:
        results = _pgvector_search(args)
        if args.json:
            _json({"query": args.query, "results": [result.to_dict() for result in results]})
        else:
            for number, result in enumerate(results, start=1):
                print(f"{number}. {result.document.content}\n   Source: {result.citation()}")
    elif args.command == "answer":
        if args.plan:
            profile = load_profile(args.profile)
            provider, model = resolve_embedding_selection(profile)
            synthesis_provider = args.generation_provider or "openai"
            synthesis_model = args.generation_model or DEFAULT_OPENAI_TEXT_MODEL
            _json(
                {
                    "operation": "answer-plan",
                    "network": False,
                    "writes": [],
                    "apply": {
                        "network": [
                            "configured PostgreSQL",
                            *(
                                ["OpenAI embeddings API"]
                                if provider == "openai"
                                else []
                            ),
                            *(
                                ["OpenAI text generation API"]
                                if args.answer_mode == "synthesized"
                                else []
                            ),
                        ],
                        "embedding": {"provider": provider, "model": model},
                        "answer_mode": args.answer_mode,
                        "generation": (
                            {
                                "provider": synthesis_provider,
                                "model": synthesis_model,
                                "data_boundary": (
                                    "query, retrieved passages, and source locators are sent "
                                    "to the selected text-model provider"
                                ),
                            }
                            if args.answer_mode == "synthesized"
                            else None
                        ),
                    },
                }
            )
            return 0
        results = _pgvector_search(args)
        if args.answer_mode == "synthesized":
            generation_provider = build_text_provider(
                args.generation_provider or "openai",
                api_key=os.getenv("OPENAI_API_KEY"),
                model=args.generation_model or DEFAULT_OPENAI_TEXT_MODEL,
            )
            answer = synthesize_answer(
                args.query,
                results,
                provider=generation_provider,
            )
        else:
            answer = answer_from_results(args.query, results)
        _json(answer.to_dict()) if args.json else print(answer.text)
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
            bundle = build_bundle(profile, DEFAULT_SOURCE)
            documents = bundle.documents
            destination = write_documents(root, str(profile["id"]), documents)
            pages_destination = write_pages(root, str(profile["id"]), bundle.pages)
            exported = export_jsonl(root, str(profile["id"]))
            exported_rows = [
                json.loads(line)
                for line in exported.read_text(encoding="utf-8").splitlines()
                if line
            ]
            if (
                not destination.exists()
                or not pages_destination.exists()
                or len(exported_rows) != 3
            ):
                raise RuntimeError("Synthetic smoke did not produce the expected three documents.")
            if any("pdf_page_start" not in document for document in exported_rows):
                raise RuntimeError("Synthetic smoke lost page evidence.")
            print("Synthetic smoke passed: 3 evidence-preserving documents exported to JSONL.")
    return 0


def _module_available(name: str) -> bool:
    try:
        __import__(name)
    except ImportError:
        return False
    return True


def _postgres_error_types() -> tuple[type[BaseException], ...]:
    error_types: list[type[BaseException]] = []
    try:
        import psycopg

        error_types.append(psycopg.Error)
    except ImportError:
        pass
    try:
        from psycopg_pool import PoolTimeout

        error_types.append(PoolTimeout)
    except ImportError:
        pass
    return tuple(error_types)


def _text_provider_error_types() -> tuple[type[BaseException], ...]:
    try:
        import openai

        return (openai.OpenAIError,)
    except ImportError:
        return ()


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return command(build_parser().parse_args(argv))
    except (
        FileNotFoundError,
        PermissionError,
        RuntimeError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except Exception as error:
        if isinstance(error, _postgres_error_types()):
            print(
                "error: PostgreSQL operation failed; verify the configured "
                "database, schema, and permissions.",
                file=sys.stderr,
            )
            return 2
        if isinstance(error, _text_provider_error_types()):
            print(
                "error: Text-model provider operation failed; verify the selected "
                "provider, model, credential, and service availability.",
                file=sys.stderr,
            )
            return 2
        raise


if __name__ == "__main__":
    raise SystemExit(main())
