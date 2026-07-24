import json

from codebook_agent import cli
from codebook_agent.cli import CAPABILITIES, main


def test_caps_contract_is_truthful(capsys):
    assert main(["caps", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == CAPABILITIES
    assert payload["implemented_backends"] == ["local-artifacts", "pgvector"]
    assert payload["implemented_retrieval_backends"] == ["pgvector"]
    assert "azure-ai-search" in payload["not_implemented"]


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
    rows = [
        json.loads(line)
        for line in exported.read_text(encoding="utf-8").splitlines()
    ]
    assert len(rows) == 2
    assert rows[0]["schema_version"] == "2.1"
    assert rows[0]["pdf_page_start"] == 1
    assert rows[0]["source_sha256"]


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


def test_pgvector_provider_only_override_drops_previous_provider_model(
    tmp_path, capsys
):
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

    assert main(["plan", "--profile", str(profile), "--pdf", str(source)]) == 2
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
        == 2
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

    assert main(["caps"]) == 2
    error = capsys.readouterr().err
    assert "PostgreSQL operation failed" in error
    assert "secret" not in error


def test_clean_refuses_other_target(tmp_path, capsys):
    target = tmp_path / "important"
    target.mkdir()
    assert main(["clean", "--artifacts", str(target)]) == 2
    assert target.exists()
    assert "Refusing" in capsys.readouterr().err
