"""Local-only artifact writer; it has no network client imports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import CodebookDocument


def write_documents(
    root: Path,
    profile_id: str,
    documents: list[dict[str, Any]] | list[CodebookDocument],
) -> Path:
    destination = root / "local" / profile_id / "documents.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        document.to_dict() if isinstance(document, CodebookDocument) else document
        for document in documents
    ]
    destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return destination


def export_jsonl(root: Path, profile_id: str) -> Path:
    source = root / "local" / profile_id / "documents.json"
    if not source.exists():
        raise FileNotFoundError(f"No local artifacts found; run ingest first: {source}")
    documents = json.loads(source.read_text(encoding="utf-8"))
    destination = source.with_name("documents.jsonl")
    destination.write_text(
        "".join(json.dumps(document, sort_keys=True) + "\n" for document in documents), encoding="utf-8"
    )
    return destination
