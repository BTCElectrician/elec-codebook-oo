"""Local-only artifact writer; it has no network client imports."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from ..models import CodebookDocument, PageText


def _corpus_dir(root: Path, profile_id: str) -> Path:
    return root / "local" / profile_id


def _documents_json(documents: list[dict[str, Any]] | list[CodebookDocument]) -> str:
    payload = [
        document.to_dict() if isinstance(document, CodebookDocument) else document
        for document in documents
    ]
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _pages_json(pages: list[PageText]) -> str:
    return json.dumps([page.to_dict() for page in pages], indent=2, sort_keys=True) + "\n"


def _replace_all(files: dict[Path, str]) -> None:
    """Serialize everything first, then swap each file in with an atomic rename.

    A failure while preparing any file leaves every existing artifact untouched,
    so documents and their page evidence never come from different runs.
    """

    staged: list[tuple[Path, Path]] = []
    try:
        for destination, content in files.items():
            destination.parent.mkdir(parents=True, exist_ok=True)
            handle, temporary = tempfile.mkstemp(
                prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
            )
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                stream.write(content)
            staged.append((Path(temporary), destination))
        for temporary, destination in staged:
            os.replace(temporary, destination)
    finally:
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)


def write_bundle(
    root: Path,
    profile_id: str,
    documents: list[dict[str, Any]] | list[CodebookDocument],
    pages: list[PageText],
) -> tuple[Path, Path]:
    """Write retrieval documents and their page evidence as one unit."""

    target = _corpus_dir(root, profile_id)
    documents_path = target / "documents.json"
    pages_path = target / "pages.json"
    _replace_all({documents_path: _documents_json(documents), pages_path: _pages_json(pages)})
    return documents_path, pages_path


def write_documents(
    root: Path,
    profile_id: str,
    documents: list[dict[str, Any]] | list[CodebookDocument],
) -> Path:
    destination = _corpus_dir(root, profile_id) / "documents.json"
    _replace_all({destination: _documents_json(documents)})
    return destination


def write_pages(root: Path, profile_id: str, pages: list[PageText]) -> Path:
    """Write selected and raw page evidence beside retrieval documents."""

    destination = _corpus_dir(root, profile_id) / "pages.json"
    _replace_all({destination: _pages_json(pages)})
    return destination


def export_jsonl(root: Path, profile_id: str) -> Path:
    source = _corpus_dir(root, profile_id) / "documents.json"
    if not source.exists():
        raise FileNotFoundError(f"No local artifacts found; run ingest first: {source}")
    documents = json.loads(source.read_text(encoding="utf-8"))
    destination = source.with_name("documents.jsonl")
    _replace_all(
        {destination: "".join(json.dumps(document, sort_keys=True) + "\n" for document in documents)}
    )
    return destination
