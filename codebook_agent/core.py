"""Safe local planning, ingestion, and export primitives."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_profile(path: Path) -> dict[str, Any]:
    profile = json.loads(path.read_text(encoding="utf-8"))
    required = {"id", "title", "document_type", "backend", "questions"}
    missing = sorted(required - profile.keys())
    if missing:
        raise ValueError(f"Profile is missing required fields: {', '.join(missing)}")
    if profile["backend"] != "local-artifacts":
        raise ValueError("Only the implemented local-artifacts backend is allowed in this release.")
    return profile


def plan(profile_path: Path, source_path: Path) -> dict[str, Any]:
    profile = load_profile(profile_path)
    return {
        "operation": "local-plan",
        "network": False,
        "writes": [],
        "profile": {"id": profile["id"], "title": profile["title"], "backend": profile["backend"]},
        "source": {"path": str(source_path.resolve()), "exists": source_path.is_file()},
        "next": "Run dry for a no-write check, then request approval before ingest --apply.",
    }


def extract_text(source_path: Path) -> str:
    if source_path.suffix.lower() in {".txt", ".md"}:
        return source_path.read_text(encoding="utf-8")
    if source_path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader  # type: ignore[import-not-found]
        except ImportError as error:
            raise RuntimeError("PDF support is optional. Install it with: pip install '.[pdf]'") from error
        return "\n\n".join(page.extract_text() or "" for page in PdfReader(str(source_path)).pages)
    raise ValueError("Supported local inputs are .txt, .md, or .pdf (with the pdf extra).")


def make_documents(profile: dict[str, Any], source_path: Path, content: str) -> list[dict[str, Any]]:
    sections = [section.strip() for section in content.split("\n\n") if section.strip()]
    return [
        {
            "id": f"{profile['id']}-{number:04d}",
            "profile_id": profile["id"],
            "source_name": source_path.name,
            "chunk_number": number,
            "text": section,
            "metadata": {"document_type": profile["document_type"], "backend": "local-artifacts"},
        }
        for number, section in enumerate(sections, start=1)
    ]
