import subprocess
from pathlib import Path

from scripts.leak_guard import is_forbidden, main

ROOT = Path(__file__).resolve().parents[1]


def test_generated_derivatives_are_ignored():
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
    docker_ignored = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    for required in (".env", ".env.*", "artifacts/", "*.pdf", "*.jsonl", "output/"):
        assert required in ignored
    for required in (".env", ".env.*", "artifacts", "*.pdf", "*.jsonl", "output"):
        assert required in docker_ignored


def test_leak_guard_rejects_nested_env_files_and_page_image_directories():
    assert is_forbidden("config/.env.local")
    assert is_forbidden("docs/page_images/page-1.png")
    assert is_forbidden("exports/book.jsonl")
    assert not is_forbidden(".env.example")
    assert not is_forbidden("docs/images/original-project-logo.png")


def test_profiles_contain_no_extracted_text_fields():
    for path in (ROOT / "codebook_agent/profiles").glob("*.json"):
        profile = path.read_text(encoding="utf-8")
        for forbidden in ('"text"', '"content"', '"chunk"'):
            assert forbidden not in profile


def test_leak_guard_scans_untracked_nonignored_files(monkeypatch, capsys):
    def synthetic_ls_files(command, text):
        assert command == [
            "git",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
        ]
        assert text is True
        return "scratch/operator-source.pdf\n"

    monkeypatch.setattr(subprocess, "check_output", synthetic_ls_files)
    assert main() == 1
    assert "operator-source.pdf" in capsys.readouterr().err


def test_tracked_file_leak_guard_passes():
    result = subprocess.run(
        ["python3", "scripts/leak_guard.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
