import json
import shlex

import pytest

from codebook_agent import cli
from codebook_agent.cli import CAPABILITIES, main
from codebook_agent.core import load_profile


def test_caps_contract_is_truthful(capsys):
    assert main(["caps", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == CAPABILITIES
    assert payload["implemented_backends"] == ["local-artifacts", "pgvector"]
    assert payload["implemented_retrieval_backends"] == ["pgvector"]
    assert "azure-ai-search" in payload["not_implemented"]
    assert "generative-answer-synthesis" not in payload["not_implemented"]
    assert payload["implemented_structure_recovery"] == [
        "generic-blocks",
        "continued-tables",
    ]


def test_configure_requires_explicit_source_authorization(tmp_path, capsys):
    source = tmp_path / "manual.txt"
    source.write_text("authorized only after operator confirmation", encoding="utf-8")

    assert main(["configure", "--source", str(source), "--json"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "--authorized" in captured.err

    assert main(["configure", "--source", str(source), "--authorizd"]) == 1
    typo = capsys.readouterr()
    assert typo.out == ""
    assert "inferred option `--authorized`" not in typo.err


def test_configure_preview_is_local_deterministic_and_write_free(tmp_path, capsys):
    source = tmp_path / "Safety Manual 2026.txt"
    source.write_text("page one\fpage two", encoding="utf-8")
    output = tmp_path / "profiles" / "safety.json"
    arguments = [
        "configure",
        "--source",
        str(source),
        "--output",
        str(output),
        "--authorized",
        "--json",
    ]

    assert main(arguments) == 0
    first = capsys.readouterr()
    assert main(arguments) == 0
    second = capsys.readouterr()

    assert first == second
    payload = json.loads(first.out)
    assert set(CAPABILITIES["output_schemas"]["profile-proposal"]["required"]) <= set(payload)
    assert payload["operation"] == "codebook-configure"
    assert payload["network"] is False
    assert payload["provider_calls"] == []
    assert payload["authorization_confirmed"] is True
    assert payload["applied"] is False
    assert payload["writes"] == []
    assert payload["inspection"]["retained_text"] is False
    assert "page one" not in first.out
    assert payload["inspection"]["page_count"] == 2
    assert "edition" not in payload["profile"]
    assessment = payload["configuration_assessment"]
    assert assessment == payload["inspection"]["configuration_assessment"]
    assert assessment["retained_text"] is False
    edition = next(
        candidate
        for candidate in assessment["inferred_candidates"]
        if candidate["field"] == "edition"
    )
    assert edition["candidate"] == "2026"
    assert edition["confidence"] == {"level": "medium", "score": 0.67}
    assert edition["profile_effect"] == "operator must explicitly set --edition"
    assert payload["profile"]["content_ranges"] == {"main": [1, 2]}
    assert payload["profile"]["ocr"]["mode"] == "off"
    assert "--apply" in payload["commands"]["apply_profile"]
    assert not output.exists()

    assert main(shlex.split(payload["commands"]["apply_profile"])[1:] + ["--json"]) == 0
    applied = json.loads(capsys.readouterr().out)
    assert applied["applied"] is True
    assert load_profile(output)["id"] == "safety-manual-2026"


def test_configure_proposes_semantic_ranges_and_page_mapping_without_applying_them(
    tmp_path, capsys
):
    source = tmp_path / "Reference 2026.txt"
    source.write_text(
        "TABLE OF CONTENTS\nprivate phrase from source\f"
        "PREFACE\nPage 1\f"
        "INSTALLATION\nPage 2\f"
        "MAINTENANCE\nPage 3\f"
        "INDEX\nPage 4",
        encoding="utf-8",
    )

    assert main(["configure", "--source", str(source), "--authorized", "--json"]) == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    candidates = {
        candidate["field"]: candidate
        for candidate in payload["configuration_assessment"]["inferred_candidates"]
    }

    assert "private phrase from source" not in captured.out
    assert candidates["edition"]["candidate"] == "2026"
    assert candidates["printed_page_offset"]["candidate"] == 1
    assert candidates["printed_page_offset"]["confidence"]["level"] == "high"
    assert candidates["content_ranges"]["candidate"] == {
        "front_matter": [[1, 1]],
        "index": [[5, 5]],
        "main": [[2, 4]],
    }
    assert payload["profile"]["content_ranges"] == {"main": [1, 5]}
    assert payload["profile"]["printed_page_offset"] is None
    assert "edition" not in payload["profile"]
    unresolved = {decision["field"]: decision["reason"] for decision in payload["unresolved_decisions"]}
    assert "candidate" in unresolved["edition"]
    assert "candidate" in unresolved["printed_page_offset"]
    assert "candidate" in unresolved["content_ranges"]


def test_configure_marks_ambiguous_page_mapping_as_low_confidence(tmp_path, capsys):
    source = tmp_path / "manual.md"
    source.write_text("ONE\nPage 1\fTWO\nPage 9\fTHREE\nPage 2", encoding="utf-8")

    assert main(["configure", "--source", str(source), "--authorized", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    mappings = [
        candidate
        for candidate in payload["configuration_assessment"]["inferred_candidates"]
        if candidate["field"] == "printed_page_offset"
    ]

    assert len(mappings) == 3
    assert {candidate["confidence"]["level"] for candidate in mappings} == {"low"}
    assert payload["profile"]["printed_page_offset"] is None


def test_configure_reports_markdown_layout_without_promoting_structure_to_source_fact(tmp_path, capsys):
    source = tmp_path / "manual.md"
    source.write_text("# Setup\n| Part | Size |\n| --- | --- |\n| A | 1 |", encoding="utf-8")

    assert main(["configure", "--source", str(source), "--authorized", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    observed = payload["configuration_assessment"]["observed_facts"]
    structure = next(
        candidate
        for candidate in payload["configuration_assessment"]["inferred_candidates"]
        if candidate["field"] == "structure"
    )

    assert observed["source_format"] == "md"
    assert observed["layout_characteristics"]["table_like_pages"] == 1
    assert structure["confidence"]["level"] == "low"
    assert "not evidence of document semantics" in structure["profile_effect"]


def test_configure_rejects_unreadable_or_unsupported_sources(tmp_path, capsys):
    binary = tmp_path / "manual.txt"
    binary.write_bytes(b"\xff\xfe")
    unsupported = tmp_path / "manual.docx"
    unsupported.write_text("not inspected", encoding="utf-8")

    assert main(["configure", "--source", str(binary), "--authorized"]) == 1
    assert "UTF-8" in capsys.readouterr().err
    assert main(["configure", "--source", str(unsupported), "--authorized"]) == 1
    assert "authorized .pdf, .txt, or .md" in capsys.readouterr().err


def test_configure_apply_writes_a_loadable_metadata_profile(tmp_path, capsys):
    source = tmp_path / "installer-manual.md"
    source.write_text("# Installation\n\nUse approved tools.", encoding="utf-8")
    output = tmp_path / "profiles" / "installer.json"

    assert (
        main(
            [
                "configure",
                "--source",
                str(source),
                "--output",
                str(output),
                "--id",
                "installer-manual",
                "--title",
                "Installer Manual",
                "--edition",
                "R2",
                "--content-range",
                "definitions:1-1",
                "--backend",
                "pgvector",
                "--embedding-provider",
                "openai",
                "--correction-mode",
                "ocr-only",
                "--correction-model",
                "synthetic-corrector",
                "--ocr-dpi",
                "400",
                "--max-chunk-chars",
                "1200",
                "--no-table-recovery",
                "--authorized",
                "--apply",
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    profile = load_profile(output)

    assert payload["writes"] == [str(output.resolve())]
    assert profile["id"] == "installer-manual"
    assert profile["title"] == "Installer Manual"
    assert profile["edition"] == "R2"
    assert profile["content_ranges"] == {"definitions": [1, 1]}
    assert profile["backend"] == "pgvector"
    assert profile["embedding"] == {
        "provider": "openai",
        "model": "text-embedding-3-small",
    }
    assert profile["correction"]["mode"] == "ocr-only"
    assert profile["correction"]["model"] == "synthetic-corrector"
    assert profile["ocr"]["dpi"] == 400
    assert profile["max_chunk_chars"] == 1200
    assert profile["structure"]["recover_tables"] is False
    assert "source" not in profile

    assert main(["plan", "--profile", str(output), "--pdf", str(source)]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["network"] is False
    assert plan["apply"]["network"] == [
        "configured PostgreSQL",
        "OpenAI embeddings API",
        "OpenAI text generation API",
    ]


def test_configure_refuses_unapproved_profile_replacement(tmp_path, capsys):
    source = tmp_path / "manual.txt"
    source.write_text("manual", encoding="utf-8")
    output = tmp_path / "manual.json"
    output.write_text('{"preserve": true}\n', encoding="utf-8")

    assert (
        main(
            [
                "configure",
                "--source",
                str(source),
                "--output",
                str(output),
                "--authorized",
                "--apply",
            ]
        )
        == 2
    )
    assert json.loads(output.read_text(encoding="utf-8")) == {"preserve": True}
    assert "--overwrite --apply" in capsys.readouterr().err

    assert (
        main(
            [
                "configure",
                "--source",
                str(source),
                "--output",
                str(output),
                "--authorized",
                "--overwrite",
                "--apply",
                "--json",
            ]
        )
        == 0
    )
    assert load_profile(output)["id"] == "manual"
    assert json.loads(capsys.readouterr().out)["applied"] is True


def test_configure_reports_scanned_pdf_ocr_need(tmp_path, capsys):
    pypdf = pytest.importorskip("pypdf")
    source = tmp_path / "scanned-reference.pdf"
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with source.open("wb") as destination:
        writer.write(destination)

    assert (
        main(
            [
                "configure",
                "--source",
                str(source),
                "--authorized",
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["inspection"]["low_text_page_ranges"] == [[1, 1]]
    assert payload["inspection"]["ocr_recommended"] is True
    assert payload["profile"]["ocr"]["mode"] == "auto"


def test_configure_finds_repeated_pdf_page_labels_without_exposing_pdf_text(tmp_path, capsys):
    pypdf = pytest.importorskip("pypdf")
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    source = tmp_path / "reference.pdf"
    writer = pypdf.PdfWriter()
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    for number in range(1, 5):
        page = writer.add_blank_page(width=200, height=200)
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
        )
        stream = DecodedStreamObject()
        stream.set_data(
            f"BT /F1 12 Tf 12 180 Td (Synthetic PDF body wording for page {number} only) Tj ET\n"
            f"BT /F1 12 Tf 12 12 Td (Page {number}) Tj ET".encode()
        )
        page[NameObject("/Contents")] = writer._add_object(stream)
    with source.open("wb") as destination:
        writer.write(destination)

    assert main(["configure", "--source", str(source), "--authorized", "--json"]) == 0
    captured = capsys.readouterr().out
    payload = json.loads(captured)
    mapping = next(
        candidate
        for candidate in payload["configuration_assessment"]["inferred_candidates"]
        if candidate["field"] == "printed_page_offset"
    )

    assert "Synthetic PDF body" not in captured
    assert payload["inspection"]["native_text_pages"] == 4
    assert mapping["candidate"] == 0
    assert mapping["confidence"]["level"] == "high"
    assert payload["profile"]["printed_page_offset"] is None


def test_configure_teaches_content_range_shape(tmp_path, capsys):
    source = tmp_path / "manual.txt"
    source.write_text("one\ftwo", encoding="utf-8")

    assert (
        main(
            [
                "configure",
                "--source",
                str(source),
                "--authorized",
                "--content-range",
                "definitions=1-2",
            ]
        )
        == 1
    )
    error = capsys.readouterr().err
    assert "--content-range TYPE:START-END" in error
    assert "definitions:12-18" in error

    assert (
        main(
            [
                "configure",
                "--source",
                str(source),
                "--authorized",
                "--content-range",
                "main:1-2",
                "--content-range",
                "definitions:2-2",
            ]
        )
        == 1
    )
    overlap = capsys.readouterr().err
    assert "overlaps main:1-2" in overlap
    assert "one explicit content type" in overlap


def test_ingest_refuses_without_apply(tmp_path, capsys):
    source = tmp_path / "book.txt"
    source.write_text("one", encoding="utf-8")
    assert main(["ingest", "--pdf", str(source)]) == 2
    assert "Refusing to write" in capsys.readouterr().err


def test_local_ingest_and_export(tmp_path):
    source = tmp_path / "book.txt"
    source.write_text("first\n\nsecond", encoding="utf-8")
    artifacts = tmp_path / "artifacts"
    assert main(["ingest", "--apply", "--pdf", str(source), "--artifacts", str(artifacts)]) == 0
    assert main(["export", "jsonl", "--artifacts", str(artifacts)]) == 0
    exported = artifacts / "local" / "generic-reference-template" / "documents.jsonl"
    rows = [json.loads(line) for line in exported.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2
    assert rows[0]["schema_version"] == "2.2"
    assert rows[0]["pdf_page_start"] == 1
    assert rows[0]["source_sha256"]
    page_rows = json.loads(
        (artifacts / "local" / "generic-reference-template" / "pages.json").read_text(
            encoding="utf-8"
        )
    )
    assert page_rows[0]["raw_text"] == "first\n\nsecond"
    assert page_rows[0]["schema_version"] == "1.0"


def test_plan_reports_effective_ocr_overrides(tmp_path, capsys):
    source = tmp_path / "book.txt"
    source.write_text("synthetic", encoding="utf-8")
    assert (
        main(
            [
                "plan",
                "--pdf",
                str(source),
                "--ocr-mode",
                "always",
                "--ocr-dpi",
                "400",
                "--ocr-page-segmentation-mode",
                "6",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["ocr"]["mode"] == "always"
    assert payload["ocr"]["dpi"] == 400
    assert payload["ocr"]["page_segmentation_mode"] == 6
    assert payload["ocr"]["network"] is False


def test_plan_reports_opt_in_correction_boundary(tmp_path, capsys):
    source = tmp_path / "book.txt"
    source.write_text("synthetic", encoding="utf-8")

    assert (
        main(
            [
                "plan",
                "--pdf",
                str(source),
                "--correction-mode",
                "ocr-only",
                "--correction-model",
                "synthetic-corrector",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["network"] is False
    assert payload["apply"]["network"] == ["OpenAI text generation API"]
    assert payload["correction"]["mode"] == "ocr-only"
    assert payload["correction"]["model"] == "synthetic-corrector"
    assert "eligible extracted page text" in payload["correction"]["data_boundary"]


def test_local_plan_reports_exact_artifact_destination(tmp_path, capsys):
    source = tmp_path / "book.txt"
    source.write_text("synthetic", encoding="utf-8")
    artifacts = tmp_path / "private-artifacts"

    assert (
        main(
            [
                "plan",
                "--pdf",
                str(source),
                "--backend",
                "local-artifacts",
                "--artifacts",
                str(artifacts),
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["network"] is False
    assert payload["apply"]["network"] is False
    assert payload["apply"]["artifact"] == str(
        (artifacts / "local" / "generic-reference-template" / "documents.json").resolve()
    )
    assert payload["apply"]["embedding"] is None


def test_pgvector_plan_reports_schema_and_external_embedding_boundary(tmp_path, capsys):
    source = tmp_path / "book.txt"
    source.write_text("synthetic", encoding="utf-8")

    assert (
        main(
            [
                "dry",
                "--pdf",
                str(source),
                "--backend",
                "pgvector",
                "--schema",
                "training_codebook",
                "--embedding-provider",
                "openai",
                "--embedding-model",
                "text-embedding-3-small",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["operation"] == "codebook-dry-run"
    assert payload["network"] is False
    assert payload["apply"]["database"] == "configured CODEBOOK_DATABASE_URL"
    assert payload["apply"]["schema"] == "training_codebook"
    assert payload["apply"]["embedding"] == {
        "data_boundary": "document search_text is sent to the selected provider",
        "external": True,
        "model": "text-embedding-3-small",
        "provider": "openai",
    }
    assert payload["apply"]["network"] == [
        "configured PostgreSQL",
        "OpenAI embeddings API",
    ]


def test_pgvector_provider_only_override_uses_new_provider_default(tmp_path, capsys):
    source = tmp_path / "book.txt"
    source.write_text("synthetic", encoding="utf-8")

    assert (
        main(
            [
                "plan",
                "--pdf",
                str(source),
                "--backend",
                "pgvector",
                "--embedding-provider",
                "openai",
            ]
        )
        == 0
    )
    embedding = json.loads(capsys.readouterr().out)["apply"]["embedding"]
    assert embedding["provider"] == "openai"
    assert embedding["model"] == "text-embedding-3-small"


def test_pgvector_provider_only_override_drops_previous_provider_model(tmp_path, capsys):
    source = tmp_path / "book.txt"
    source.write_text("synthetic", encoding="utf-8")
    profile = tmp_path / "profile.json"
    profile.write_text(
        json.dumps(
            {
                "id": "synthetic",
                "title": "Synthetic",
                "document_type": "manual",
                "backend": "pgvector",
                "questions": [],
                "embedding": {
                    "provider": "openai",
                    "model": "text-embedding-3-large",
                },
            }
        ),
        encoding="utf-8",
    )

    assert (
        main(
            [
                "plan",
                "--profile",
                str(profile),
                "--pdf",
                str(source),
                "--embedding-provider",
                "hash",
            ]
        )
        == 0
    )
    embedding = json.loads(capsys.readouterr().out)["apply"]["embedding"]
    assert embedding["provider"] == "hash"
    assert embedding["model"] == "codebook-hash-v1"


def test_local_plan_and_apply_ignore_irrelevant_embedding_overrides(tmp_path, capsys):
    source = tmp_path / "book.txt"
    source.write_text("synthetic", encoding="utf-8")
    artifacts = tmp_path / "artifacts"
    arguments = [
        "--pdf",
        str(source),
        "--backend",
        "local-artifacts",
        "--artifacts",
        str(artifacts),
        "--embedding-provider",
        "hash",
        "--embedding-model",
        "irrelevant",
    ]

    assert main(["plan", *arguments]) == 0
    assert json.loads(capsys.readouterr().out)["apply"]["embedding"] is None
    assert main(["ingest", "--apply", *arguments]) == 0
    assert json.loads(capsys.readouterr().out)["operation"] == "local-ingest"


def test_profile_with_unknown_embedding_provider_fails_before_apply(tmp_path, capsys):
    source = tmp_path / "book.txt"
    source.write_text("synthetic", encoding="utf-8")
    profile = tmp_path / "profile.json"
    profile.write_text(
        json.dumps(
            {
                "id": "synthetic",
                "title": "Synthetic",
                "document_type": "manual",
                "backend": "pgvector",
                "questions": [],
                "embedding": {"provider": "unknown"},
            }
        ),
        encoding="utf-8",
    )

    assert main(["plan", "--profile", str(profile), "--pdf", str(source)]) == 1
    assert "Unknown embedding provider" in capsys.readouterr().err


def test_pgvector_ingest_refuses_without_database_url(tmp_path, capsys, monkeypatch):
    source = tmp_path / "book.txt"
    source.write_text("one", encoding="utf-8")
    monkeypatch.delenv("CODEBOOK_DATABASE_URL", raising=False)
    assert (
        main(
            [
                "ingest",
                "--apply",
                "--backend",
                "pgvector",
                "--pdf",
                str(source),
            ]
        )
        == 3
    )
    assert "CODEBOOK_DATABASE_URL" in capsys.readouterr().err


def test_pgvector_ingest_verifies_database_before_embedding(tmp_path, capsys, monkeypatch):
    source = tmp_path / "book.txt"
    source.write_text("Synthetic searchable wording.", encoding="utf-8")
    events = []

    class FakeBackend:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return None

        def verify_connection(self):
            events.append("database")

        def index_documents(self, **kwargs):
            events.append("index")
            return len(kwargs["documents"])

    class FakeProvider:
        name = "hash"
        model = "codebook-hash-v1"

        def embed(self, texts):
            assert events == ["database"]
            events.append("embedding")
            return [[0.0] * 1536 for _ in texts]

    monkeypatch.setattr(cli, "_pgvector_backend", lambda schema: FakeBackend())
    monkeypatch.setattr(cli, "_provider_for_profile", lambda profile: FakeProvider())

    assert (
        main(
            [
                "ingest",
                "--apply",
                "--backend",
                "pgvector",
                "--pdf",
                str(source),
            ]
        )
        == 0
    )
    assert events == ["database", "embedding", "index"]
    assert json.loads(capsys.readouterr().out)["operation"] == "pgvector-ingest"


def test_synthesized_answer_plan_does_not_connect(tmp_path, capsys, monkeypatch):
    profile = tmp_path / "profile.json"
    profile.write_text(
        json.dumps(
            {
                "id": "synthetic",
                "title": "Synthetic",
                "document_type": "manual",
                "backend": "pgvector",
                "questions": [],
                "embedding": {"provider": "hash", "model": "codebook-hash-v1"},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        cli,
        "_pgvector_search",
        lambda args: (_ for _ in ()).throw(AssertionError("must not connect")),
    )

    assert (
        main(
            [
                "answer",
                "--plan",
                "--profile",
                str(profile),
                "--query",
                "synthetic question",
                "--answer-mode",
                "synthesized",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["network"] is False
    assert payload["writes"] == []
    assert payload["apply"]["answer_mode"] == "synthesized"
    assert payload["apply"]["network"] == [
        "configured PostgreSQL",
        "OpenAI text generation API",
    ]


def test_postgres_errors_are_sanitized(capsys, monkeypatch):
    class SyntheticPostgresError(Exception):
        pass

    monkeypatch.setattr(cli, "_postgres_error_types", lambda: (SyntheticPostgresError,))
    monkeypatch.setattr(
        cli,
        "command",
        lambda args: (_ for _ in ()).throw(
            SyntheticPostgresError("postgresql://user:secret@example.invalid/database")
        ),
    )

    assert main(["caps"]) == 4
    error = capsys.readouterr().err
    assert "PostgreSQL operation failed" in error
    assert "secret" not in error


def test_text_provider_errors_are_sanitized(capsys, monkeypatch):
    class SyntheticProviderError(Exception):
        pass

    monkeypatch.setattr(
        cli,
        "_text_provider_error_types",
        lambda: (SyntheticProviderError,),
    )
    monkeypatch.setattr(
        cli,
        "command",
        lambda args: (_ for _ in ()).throw(SyntheticProviderError("secret-token-value")),
    )

    assert main(["caps"]) == 4
    error = capsys.readouterr().err
    assert "Text-model provider operation failed" in error
    assert "secret-token-value" not in error


def test_internal_invariant_failures_have_a_distinct_exit(capsys, monkeypatch):
    monkeypatch.setattr(
        cli,
        "command",
        lambda args: (_ for _ in ()).throw(RuntimeError("synthetic invariant")),
    )

    assert main(["caps"]) == 5
    error = capsys.readouterr().err
    assert "internal invariant failed" in error
    assert "make check" in error


def test_filesystem_permission_failures_are_environment_errors(capsys, monkeypatch):
    monkeypatch.setattr(
        cli,
        "command",
        lambda args: (_ for _ in ()).throw(PermissionError("synthetic denied")),
    )

    assert main(["caps"]) == 3
    error = capsys.readouterr().err
    assert "filesystem permission failure" in error
    assert "codebook doctor" in error


def test_clean_refuses_other_target(tmp_path, capsys):
    target = tmp_path / "important"
    target.mkdir()
    assert main(["clean", "--artifacts", str(target)]) == 2
    assert target.exists()
    assert "Refusing" in capsys.readouterr().err
