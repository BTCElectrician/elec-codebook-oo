"""Model defaults live in one registry; nothing else may pin a stale name."""

import inspect
import json
import re
import subprocess
from pathlib import Path

from codebook_agent import model_defaults
from codebook_agent.configure import propose_profile
from codebook_agent.correction import CorrectionConfig
from codebook_agent.embeddings import (
    DEFAULT_EMBEDDING_MODELS,
    HashEmbeddingProvider,
    OpenAIEmbeddingProvider,
)
from codebook_agent.text_models import OpenAITextProvider

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = {
    model_defaults.DEFAULT_CORRECTION_MODEL,
    model_defaults.DEFAULT_SYNTHESIS_MODEL,
    model_defaults.DEFAULT_OPENAI_EMBEDDING_MODEL,
    model_defaults.HASH_EMBEDDING_MODEL,
}
MODEL_NAME = re.compile(
    r"\b(?:gpt-[0-9][\w.-]*|text-embedding-[\w-]+|claude-[a-z]+-[\w.-]+|o[134]-[\w-]+)\b"
)


def test_runtime_defaults_come_from_the_registry():
    assert CorrectionConfig().model == model_defaults.DEFAULT_CORRECTION_MODEL
    assert CorrectionConfig.from_profile({"mode": "off"}).model == (
        model_defaults.DEFAULT_CORRECTION_MODEL
    )
    assert (
        inspect.signature(OpenAITextProvider).parameters["model"].default
        == model_defaults.DEFAULT_SYNTHESIS_MODEL
    )
    assert DEFAULT_EMBEDDING_MODELS == {
        "hash": model_defaults.HASH_EMBEDDING_MODEL,
        "openai": model_defaults.DEFAULT_OPENAI_EMBEDDING_MODEL,
    }
    assert HashEmbeddingProvider().model == model_defaults.HASH_EMBEDDING_MODEL
    assert (
        inspect.signature(OpenAIEmbeddingProvider).parameters["model"].default
        == model_defaults.DEFAULT_OPENAI_EMBEDDING_MODEL
    )


def test_bundled_profiles_inherit_the_text_model_default():
    for path in (ROOT / "codebook_agent" / "profiles").glob("*.json"):
        profile = json.loads(path.read_text(encoding="utf-8"))
        assert "model" not in profile.get("correction", {}), path.name


def test_generated_profiles_pin_the_current_default():
    inspection = {"ocr_recommended": False, "page_count": 1}
    profile = propose_profile(
        inspection,
        profile_id="synthetic",
        title="Synthetic",
        edition=None,
        document_type="manual",
    )
    assert profile["correction"]["model"] == model_defaults.DEFAULT_CORRECTION_MODEL


def test_tracked_files_name_only_registry_models():
    tracked = subprocess.run(
        ["git", "ls-files", "*.md", "*.json", "*.py", "*.toml", "*.yml", "Makefile", "Dockerfile"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()
    allowed = REGISTRY | {"text-embedding-3-large"}  # an explicit alternative in tests/docs
    stale = []
    for name in tracked:
        if name.startswith("tests/test_model_defaults.py") or name == "CHANGELOG.md":
            continue
        path = ROOT / name
        if not path.is_file():
            continue
        for found in MODEL_NAME.findall(path.read_text(encoding="utf-8", errors="ignore")):
            if found not in allowed:
                stale.append(f"{name}: {found}")
    assert stale == []
