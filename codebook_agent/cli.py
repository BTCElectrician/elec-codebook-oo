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

from .agent_contract import (
    CLI_CONTRACT_VERSION,
    OUTPUT_SCHEMAS,
    agent_guide,
    capabilities,
)
from .answers import answer_from_results, synthesize_answer
from .backends.local import export_jsonl, write_documents, write_pages
from .cli_surface import (
    DEFAULT_PROFILE,
    DEFAULT_SOURCE,
    CLIUsageError,
    EnvironmentError,
    SafetyError,
    agent_triage,
    build_parser,
    doctor_result,
    normalize_argv,
    render_help,
)
from .core import build_bundle, load_profile, plan
from .correction import CorrectionConfig
from .embeddings import build_embedding_provider, resolve_embedding_selection
from .text_models import (
    DEFAULT_OPENAI_TEXT_MODEL,
    build_text_provider,
)

EXIT_SUCCESS = 0
EXIT_INPUT = 1
EXIT_SAFETY = 2
EXIT_ENVIRONMENT = 3
EXIT_UPSTREAM = 4
EXIT_INTERNAL = 5

CAPABILITIES = capabilities()


def _json(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def _database_url() -> str:
    value = os.getenv("CODEBOOK_DATABASE_URL", "").strip()
    if not value:
        raise EnvironmentError(
            "CODEBOOK_DATABASE_URL is required for pgvector operations. "
            "Start the disposable service with `make pgvector-up` or configure an "
            "authorized database, then retry."
        )
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
    if args.robot_triage and args.command is not None:
        raise CLIUsageError(
            "--robot-triage cannot be combined with a command. "
            "Run `codebook --robot-triage` by itself."
        )
    if args.robot_triage:
        _json(agent_triage(Path("artifacts")))
    elif args.command is None:
        render_help()
    elif args.command == "help":
        render_help(args.topic)
    elif args.command == "agent":
        _json(agent_triage(args.artifacts))
    elif args.command == "doctor":
        result = doctor_result(args.artifacts)
        _json(result)
        return EXIT_SUCCESS if result["writable"] else EXIT_ENVIRONMENT
    elif args.command == "caps":
        _json(CAPABILITIES) if args.json else print(
            "Implemented: local-artifacts and pgvector retrieval.\n"
            "Inspect: `codebook capabilities --json`\n"
            "Orient an agent: `codebook agent --json`"
        )
    elif args.command == "ask":
        profile = load_profile(args.profile)
        if args.json:
            _json(
                {
                    "contract_version": CLI_CONTRACT_VERSION,
                    "profile": {
                        "id": profile["id"],
                        "title": profile["title"],
                    },
                    "questions": profile["questions"],
                    "next": "Answer these questions in a metadata-only profile, then run plan.",
                }
            )
        else:
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
        result["contract_version"] = CLI_CONTRACT_VERSION
        _json(result)
    elif args.command == "ingest":
        if not args.apply:
            raise SafetyError(
                "Refusing to write: ingest is apply-gated. Review `codebook plan` "
                "and `codebook dry`, "
                "obtain operator approval, then add --apply to the same ingest command."
            )
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
                    "contract_version": CLI_CONTRACT_VERSION,
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
                    "contract_version": CLI_CONTRACT_VERSION,
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
                "contract_version": CLI_CONTRACT_VERSION,
                "operation": "local-export",
                "network": False,
                "format": args.format,
                "artifact": str(destination),
            }
        )
    elif args.command in {"search", "query"}:
        results = _pgvector_search(args)
        if args.json:
            _json(
                {
                    "contract_version": CLI_CONTRACT_VERSION,
                    "query": args.query,
                    "results": [result.to_dict() for result in results],
                }
            )
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
                    "contract_version": CLI_CONTRACT_VERSION,
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
        if args.json:
            _json(
                {
                    "contract_version": CLI_CONTRACT_VERSION,
                    **answer.to_dict(),
                }
            )
        else:
            print(answer.text)
    elif args.command == "clean":
        if args.artifacts.resolve().name != "artifacts":
            raise SafetyError(
                "Refusing cleanup: the resolved directory name must be `artifacts`. "
                "Choose that generated target and preview it with `codebook clean --plan`."
            )
        target = args.artifacts.resolve()
        existed = target.exists()
        if args.apply and existed:
            shutil.rmtree(target)
        _json(
            {
                "contract_version": CLI_CONTRACT_VERSION,
                "operation": "clean",
                "network": False,
                "target": str(target),
                "existed": existed,
                "applied": bool(args.apply),
                "writes": [str(target)] if args.apply and existed else [],
                "next": (
                    "Generated artifacts were removed."
                    if args.apply
                    else "Review the target, then rerun with --apply to remove it."
                ),
            }
        )
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
            result = {
                "contract_version": CLI_CONTRACT_VERSION,
                "operation": "synthetic-smoke",
                "status": "passed",
                "documents": len(exported_rows),
                "page_evidence": True,
                "connections": [],
                "persistent_writes": [],
            }
            if args.json:
                _json(result)
            else:
                print("Synthetic smoke passed: 3 evidence-preserving documents exported to JSONL.")
    elif args.command == "schema":
        selected = (
            OUTPUT_SCHEMAS
            if args.name == "all"
            else {args.name: OUTPUT_SCHEMAS[args.name]}
        )
        _json(
            {
                "contract_version": CLI_CONTRACT_VERSION,
                "schemas": selected,
            }
        )
    elif args.command == "robot-docs":
        if args.robot_topic != "guide":
            raise CLIUsageError(
                "robot-docs needs a topic. Run `codebook robot-docs guide`."
            )
        if args.json:
            _json(
                {
                    "contract_version": CLI_CONTRACT_VERSION,
                    "guide": agent_guide(),
                }
            )
        else:
            print(agent_guide(), end="")
    return EXIT_SUCCESS


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
    parser = build_parser()
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    try:
        normalized_argv = normalize_argv(raw_argv, parser)
        return command(parser.parse_args(normalized_argv))
    except SystemExit as error:
        return int(error.code or 0)
    except CLIUsageError as error:
        print(f"error: {error}", file=sys.stderr)
        print("next: run `codebook help` or `codebook agent --json`.", file=sys.stderr)
        return EXIT_INPUT
    except SafetyError as error:
        print(f"error: {error}", file=sys.stderr)
        print(
            "next: review the exact plan and proceed only with explicit operator approval.",
            file=sys.stderr,
        )
        return EXIT_SAFETY
    except EnvironmentError as error:
        print(f"error: {error}", file=sys.stderr)
        print("next: run `codebook doctor --json`.", file=sys.stderr)
        return EXIT_ENVIRONMENT
    except (FileNotFoundError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        print("next: correct the reported input, then retry the same command.", file=sys.stderr)
        return EXIT_INPUT
    except PermissionError as error:
        print(f"error: filesystem permission failure: {error}", file=sys.stderr)
        print("next: run `codebook doctor --json` and select a writable target.", file=sys.stderr)
        return EXIT_ENVIRONMENT
    except RuntimeError as error:
        print(f"error: internal invariant failed: {error}", file=sys.stderr)
        print("next: run `make check`; report this failure if it repeats.", file=sys.stderr)
        return EXIT_INTERNAL
    except Exception as error:  # noqa: BLE001 - provider errors have optional runtime types
        if isinstance(error, _postgres_error_types()):
            print(
                "error: PostgreSQL operation failed; verify the configured "
                "database, schema, and permissions.",
                file=sys.stderr,
            )
            print("next: run `codebook doctor --json`, then retry.", file=sys.stderr)
            return EXIT_UPSTREAM
        if isinstance(error, _text_provider_error_types()):
            print(
                "error: Text-model provider operation failed; verify the selected "
                "provider, model, credential, and service availability.",
                file=sys.stderr,
            )
            print("next: verify the provider configuration, then retry.", file=sys.stderr)
            return EXIT_UPSTREAM
        print(
            f"error: unexpected internal failure ({type(error).__name__}).",
            file=sys.stderr,
        )
        print("next: run `make check`; report this failure if it repeats.", file=sys.stderr)
        return EXIT_INTERNAL


if __name__ == "__main__":
    raise SystemExit(main())
