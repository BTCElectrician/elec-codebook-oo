import json

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


def test_clean_refuses_other_target(tmp_path, capsys):
    target = tmp_path / "important"
    target.mkdir()
    assert main(["clean", "--artifacts", str(target)]) == 2
    assert target.exists()
    assert "Refusing" in capsys.readouterr().err
