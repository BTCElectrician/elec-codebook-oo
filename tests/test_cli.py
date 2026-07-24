import json

from codebook_agent.cli import CAPABILITIES, main


def test_caps_contract_is_truthful(capsys):
    assert main(["caps", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == CAPABILITIES
    assert payload["implemented_backends"] == ["local-artifacts"]
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
    exported = artifacts / "local" / "nfpa70-reference-template" / "documents.jsonl"
    assert len(exported.read_text(encoding="utf-8").splitlines()) == 2


def test_clean_refuses_other_target(tmp_path, capsys):
    target = tmp_path / "important"
    target.mkdir()
    assert main(["clean", "--artifacts", str(target)]) == 2
    assert target.exists()
    assert "Refusing" in capsys.readouterr().err
