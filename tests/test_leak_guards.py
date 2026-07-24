import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_generated_derivatives_are_ignored():
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for required in (".env", "artifacts/", "*.pdf", "output/"):
        assert required in ignored


def test_profiles_contain_no_extracted_text_fields():
    for path in (ROOT / "codebook_agent/profiles").glob("*.json"):
        profile = path.read_text(encoding="utf-8")
        for forbidden in ('"text"', '"content"', '"chunk"'):
            assert forbidden not in profile


def test_tracked_file_leak_guard_passes():
    result = subprocess.run(
        ["python3", "scripts/leak_guard.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
