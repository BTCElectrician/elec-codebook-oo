"""Safe planning and evidence-preserving ingestion primitives."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from .backends.pgvector import validate_schema_name
from .correction import CorrectionConfig, correct_pages
from .embeddings import resolve_embedding_selection
from .identity import (
    IDENTITY_VERSION,
    IdentityState,
    find_page_furniture,
    leading_heading,
    page_furniture_mode,
    split_at_headings,
    strip_page_furniture,
)
from .models import DOCUMENT_SCHEMA_VERSION, CodebookDocument, PageText
from .ocr import OCRConfig, TesseractOCR, native_text_is_usable
from .structure import StructureConfig, recover_structure
from .text_models import TextModelProvider

SUPPORTED_BACKENDS = {"local-artifacts", "pgvector"}
PROFILE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
PARAGRAPH_PATTERN = re.compile(r"\n\s*\n")


def load_profile(path: Path) -> dict[str, Any]:
    profile = json.loads(path.read_text(encoding="utf-8"))
    required = {"id", "title", "document_type", "backend", "questions"}
    missing = sorted(required - profile.keys())
    if missing:
        raise ValueError(f"Profile is missing required fields: {', '.join(missing)}")
    if not isinstance(profile["id"], str) or not PROFILE_ID_PATTERN.fullmatch(profile["id"]):
        raise ValueError(
            "Profile id must be 1-128 letters, digits, dots, underscores, or hyphens "
            "and cannot contain a path separator."
        )
    if profile["backend"] not in SUPPORTED_BACKENDS:
        raise ValueError(
            f"Backend '{profile['backend']}' is not implemented. "
            f"Choose one of: {', '.join(sorted(SUPPORTED_BACKENDS))}."
        )
    if not isinstance(profile["questions"], list) or not all(
        isinstance(question, str) for question in profile["questions"]
    ):
        raise ValueError("Profile questions must be a list of strings.")
    offset = profile.get("printed_page_offset")
    if offset is not None and not isinstance(offset, int):
        raise ValueError("printed_page_offset must be an integer or null.")
    OCRConfig.from_profile(profile.get("ocr"))
    CorrectionConfig.from_profile(profile.get("correction"))
    StructureConfig.from_profile(profile.get("structure"))
    page_furniture_mode(profile)
    resolve_embedding_selection(profile)
    return profile


@dataclass(frozen=True)
class IngestionBundle:
    """Raw/selected page evidence and the retrieval documents derived from it."""

    pages: list[PageText]
    documents: list[CodebookDocument]


def plan(
    profile_path: Path,
    source_path: Path,
    *,
    backend: str | None = None,
    ocr_overrides: dict[str, object] | None = None,
    correction_overrides: dict[str, object] | None = None,
    artifacts: Path = Path("artifacts"),
    schema: str = "codebook",
    embedding_provider: str | None = None,
    embedding_model: str | None = None,
) -> dict[str, Any]:
    profile = load_profile(profile_path)
    selected_backend = backend or profile["backend"]
    ocr_config_value = dict(profile.get("ocr") or {})
    ocr_config_value.update(ocr_overrides or {})
    ocr_config = OCRConfig.from_profile(ocr_config_value)
    correction_value = dict(profile.get("correction") or {})
    correction_value.update(correction_overrides or {})
    correction = CorrectionConfig.from_profile(correction_value)
    if selected_backend not in SUPPORTED_BACKENDS:
        raise ValueError(
            f"Backend '{selected_backend}' is not implemented. "
            f"Choose one of: {', '.join(sorted(SUPPORTED_BACKENDS))}."
        )
    if selected_backend == "local-artifacts":
        artifact = (
            artifacts
            / "local"
            / str(profile["id"])
            / "documents.json"
        ).resolve()
        apply = {
            "backend": selected_backend,
            "network": (
                ["OpenAI text generation API"] if correction.mode != "off" else False
            ),
            "writes": [
                str(artifact),
                str(artifact.with_name("pages.json")),
            ],
            "artifact": str(artifact),
            "embedding": None,
        }
    else:
        validate_schema_name(schema)
        provider, model = resolve_embedding_selection(
            profile,
            provider_override=embedding_provider,
            model_override=embedding_model,
        )
        external = provider == "openai"
        network = ["configured PostgreSQL"]
        if external:
            network.append("OpenAI embeddings API")
        if correction.mode != "off":
            network.append("OpenAI text generation API")
        apply = {
            "backend": selected_backend,
            "network": network,
            "writes": [f"configured PostgreSQL schema: {schema}"],
            "database": "configured CODEBOOK_DATABASE_URL",
            "schema": schema,
            "embedding": {
                "provider": provider,
                "model": model,
                "external": external,
                "data_boundary": (
                    "document search_text is sent to the selected provider"
                    if external
                    else "document search_text remains local"
                ),
            },
        }
    return {
        "operation": "codebook-plan",
        "network": False,
        "writes": [],
        "apply_writes": apply["writes"],
        "apply": apply,
        "profile": {"id": profile["id"], "title": profile["title"], "backend": selected_backend},
        "source": {"path": str(source_path.resolve()), "exists": source_path.is_file()},
        "ocr": {**ocr_config.to_dict(), "network": False, "checked_during_plan": False},
        "correction": {
            **correction.to_dict(),
            "external": correction.mode != "off",
            "data_boundary": (
                "eligible extracted page text is sent to the selected text-model provider"
                if correction.mode != "off"
                else "no extracted page text is sent to a correction provider"
            ),
        },
        "document_schema_version": DOCUMENT_SCHEMA_VERSION,
        "evidence": [
            "source SHA-256",
            "PDF page",
            "printed page",
            "article",
            "section",
            "extraction method",
            "OCR confidence",
            "raw extraction SHA-256",
            "correction decision and model",
        ],
        "next": "Run dry for a no-write check, then request approval before ingest --apply.",
    }


def source_sha256(source_path: Path) -> str:
    """Hash the exact operator-owned source without retaining its bytes."""

    digest = hashlib.sha256()
    with source_path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def extract_pages(
    source_path: Path,
    *,
    printed_page_offset: int | None = None,
    ocr: OCRConfig | None = None,
) -> list[PageText]:
    """Extract source text without discarding page boundaries."""

    if source_path.suffix.lower() in {".txt", ".md"}:
        raw_pages = source_path.read_text(encoding="utf-8").split("\f")
        extraction_methods = ["native-text"] * len(raw_pages)
        extraction_confidences: list[float | None] = [None] * len(raw_pages)
    elif source_path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader  # type: ignore[import-not-found]
        except ImportError as error:
            raise RuntimeError(
                "PDF support is optional. Install it with: pip install '.[pdf]'"
            ) from error
        raw_pages = [page.extract_text() or "" for page in PdfReader(str(source_path)).pages]
        extraction_methods = ["native-pdf-text"] * len(raw_pages)
        extraction_confidences = [None] * len(raw_pages)
        ocr_config = ocr or OCRConfig(mode="off")
        if ocr_config.mode != "off":
            ocr_pages = [
                pdf_page
                for pdf_page, text in enumerate(raw_pages, start=1)
                if ocr_config.mode == "always"
                or not native_text_is_usable(
                    text,
                    min_characters=ocr_config.min_native_characters,
                )
            ]
            ocr_results = (
                TesseractOCR(ocr_config).extract_pages(source_path, ocr_pages)
                if ocr_pages
                else {}
            )
            for pdf_page, result in ocr_results.items():
                if result.text.strip():
                    raw_pages[pdf_page - 1] = result.text
                    extraction_methods[pdf_page - 1] = "ocr-tesseract"
                    extraction_confidences[pdf_page - 1] = result.confidence
    else:
        raise ValueError("Supported local inputs are .txt, .md, or .pdf (with the pdf extra).")

    pages = []
    for pdf_page, text in enumerate(raw_pages, start=1):
        printed_page = None
        if printed_page_offset is not None:
            candidate = pdf_page - printed_page_offset
            printed_page = candidate if candidate > 0 else None
        pages.append(
            PageText(
                pdf_page=pdf_page,
                printed_page=printed_page,
                text=text,
                extraction_method=extraction_methods[pdf_page - 1],
                extraction_confidence=extraction_confidences[pdf_page - 1],
            )
        )
    return pages


def extract_text(source_path: Path) -> str:
    """Compatibility helper returning page text separated by blank lines."""

    return "\n\n".join(page.text for page in extract_pages(source_path))


def _normalized_ranges(value: object) -> list[tuple[int, int]]:
    if not isinstance(value, list) or not value:
        return []
    if len(value) == 2 and all(isinstance(item, int) for item in value):
        return [(int(value[0]), int(value[1]))]

    ranges: list[tuple[int, int]] = []
    for item in value:
        if isinstance(item, list) and len(item) == 2 and all(isinstance(part, int) for part in item):
            ranges.append((item[0], item[1]))
        elif isinstance(item, dict):
            start = item.get("start_pdf_page", item.get("start"))
            end = item.get("end_pdf_page", item.get("end"))
            if isinstance(start, int) and isinstance(end, int):
                ranges.append((start, end))
    for start, end in ranges:
        if start < 1 or end < start:
            raise ValueError(f"Invalid content range: {start}-{end}")
    return ranges


def _content_type(profile: dict[str, Any], pdf_page: int) -> str:
    configured = profile.get("content_ranges")
    if isinstance(configured, dict):
        for content_type, value in configured.items():
            if any(start <= pdf_page <= end for start, end in _normalized_ranges(value)):
                return str(content_type)
    return "main"


def _split_paragraph(paragraph: str, max_chars: int) -> list[str]:
    clean = " ".join(paragraph.split())
    if len(clean) <= max_chars:
        return [clean] if clean else []
    words = clean.split()
    chunks: list[str] = []
    current: list[str] = []
    current_size = 0
    for word in words:
        extra = len(word) + (1 if current else 0)
        if current and current_size + extra > max_chars:
            chunks.append(" ".join(current))
            current = [word]
            current_size = len(word)
        else:
            current.append(word)
            current_size += extra
    if current:
        chunks.append(" ".join(current))
    return chunks


def _split_table(table: str, max_chars: int) -> list[str]:
    """Split a Markdown table on row boundaries while repeating its header."""

    clean = table.strip()
    if len(clean) <= max_chars:
        return [clean] if clean else []
    lines = clean.splitlines()
    if len(lines) < 5:
        return _split_paragraph(clean, max_chars)
    prefix = lines[:4]
    chunks: list[str] = []
    current = list(prefix)
    for row in lines[4:]:
        candidate = "\n".join([*current, row])
        if len(candidate) > max_chars and len(current) > len(prefix):
            chunks.append("\n".join(current))
            current = [*prefix, row]
        else:
            current.append(row)
    if len(current) > len(prefix):
        chunks.append("\n".join(current))
    return chunks


def _evidence_hash(page: PageText) -> str:
    return hashlib.sha256(
        (page.raw_text if page.raw_text is not None else page.text).encode()
    ).hexdigest()


@dataclass(frozen=True)
class _Block:
    """A unit of source text to chunk, with the original pages it came from."""

    text: str
    content_type: str
    pdf_page_start: int
    pdf_page_end: int
    printed_page_start: int | None
    printed_page_end: int | None
    source_pages: tuple[int, ...]
    is_table: bool = False
    metadata: dict[str, Any] | None = None


def _blocks(profile: dict[str, Any], pages: list[PageText]) -> list[_Block]:
    structure_config = profile.get("structure")
    if isinstance(structure_config, dict) and structure_config.get("enabled"):
        blocks = []
        for block in recover_structure(profile, pages):
            configured = _content_type(profile, block.pdf_page_start)
            blocks.append(
                _Block(
                    text=block.text,
                    content_type=block.content_type if block.content_type != "main" else configured,
                    pdf_page_start=block.pdf_page_start,
                    pdf_page_end=block.pdf_page_end,
                    printed_page_start=block.printed_page_start,
                    printed_page_end=block.printed_page_end,
                    source_pages=tuple(
                        block.metadata.get(
                            "source_pages",
                            range(block.pdf_page_start, block.pdf_page_end + 1),
                        )
                    ),
                    is_table=block.metadata.get("structure_kind") == "table",
                    metadata=dict(block.metadata),
                )
            )
        return blocks
    return [
        _Block(
            text=paragraph,
            content_type=_content_type(profile, page.pdf_page),
            pdf_page_start=page.pdf_page,
            pdf_page_end=page.pdf_page,
            printed_page_start=page.printed_page,
            printed_page_end=page.printed_page,
            source_pages=(page.pdf_page,),
        )
        for page in pages
        for paragraph in (part.strip() for part in PARAGRAPH_PATTERN.split(page.text))
        if paragraph
    ]


def _single_or_mixed(values: set[Any]) -> Any:
    return next(iter(values)) if len(values) == 1 else "mixed"


def documents_from_pages(
    profile: dict[str, Any],
    source_path: Path,
    pages: list[PageText],
    *,
    source_hash: str,
) -> list[CodebookDocument]:
    """Shape page-cited chunks whose identity comes from source structure.

    Article/section identity is taken only from a heading that opens a chunk and
    is otherwise carried forward in reading order (see ``identity``). Repeated
    page-edge lines (running headers/footers) are excluded from chunk text and
    identity while the page evidence keeps them. Document ids depend on the
    chunk's own page span, position within that span, and text, so a change on
    one page does not renumber every later chunk. Identical chunks with the same
    identity are indexed once and list their other locations.
    """

    max_chars = int(profile.get("max_chunk_chars", 1800))
    if max_chars < 200:
        raise ValueError("max_chunk_chars must be at least 200.")
    furniture = find_page_furniture(pages) if page_furniture_mode(profile) == "auto" else set()
    original = {page.pdf_page: page for page in pages}
    furniture_removed: dict[int, int] = {}
    chunk_pages: list[PageText] = []
    for page in pages:
        text, removed = strip_page_furniture(page.text, furniture)
        furniture_removed[page.pdf_page] = removed
        chunk_pages.append(replace(page, text=text))

    state = IdentityState()
    drafts: list[dict[str, Any]] = []
    by_key: dict[tuple[str, str | None, str | None, str], dict[str, Any]] = {}
    for block in _blocks(profile, chunk_pages):
        block_pages = [original[number] for number in block.source_pages if number in original]
        first_page = original[block.pdf_page_start]
        if block.is_table:
            pieces = [(chunk, None) for chunk in _split_table(block.text, max_chars)]
        else:
            pieces = []
            for segment in split_at_headings(block.text):
                heading = leading_heading(segment)
                for position, chunk in enumerate(_split_paragraph(segment, max_chars)):
                    # Only the piece that begins a segment can carry its heading.
                    pieces.append((chunk, heading if position == 0 else None))
        for chunk, heading in pieces:
            identity_source = state.apply(heading)
            key = (
                " ".join(chunk.split()),
                state.article_number,
                state.section_number,
                block.content_type,
            )
            location = {
                "pdf_page_start": block.pdf_page_start,
                "pdf_page_end": block.pdf_page_end,
                "printed_page_start": block.printed_page_start,
                "printed_page_end": block.printed_page_end,
            }
            if key in by_key:
                by_key[key]["duplicate_locations"].append(location)
                continue
            draft = {
                "content": chunk,
                "content_type": block.content_type,
                **location,
                "article_number": state.article_number,
                "article_title": state.article_title,
                "section_number": state.section_number,
                "section_title": state.section_title,
                "metadata": {
                    "backend": str(profile["backend"]),
                    "extraction_method": _single_or_mixed(
                        {item.extraction_method for item in block_pages}
                    ),
                    "extraction_confidence": first_page.extraction_confidence,
                    "correction_status": _single_or_mixed(
                        {item.correction_status for item in block_pages}
                    ),
                    "correction_provider": first_page.correction_provider,
                    "correction_model": first_page.correction_model,
                    "correction_similarity": first_page.correction_similarity,
                    "raw_text_sha256": _evidence_hash(first_page),
                    "identity_source": identity_source,
                    "identity_version": IDENTITY_VERSION,
                    "page_evidence": [
                        {
                            "pdf_page": item.pdf_page,
                            "extraction_method": item.extraction_method,
                            "extraction_confidence": item.extraction_confidence,
                            "correction_status": item.correction_status,
                            "correction_provider": item.correction_provider,
                            "correction_model": item.correction_model,
                            "raw_text_sha256": _evidence_hash(item),
                            "furniture_lines_removed": furniture_removed.get(item.pdf_page, 0),
                        }
                        for item in block_pages
                    ],
                    **(block.metadata or {}),
                },
                "duplicate_locations": [],
            }
            by_key[key] = draft
            drafts.append(draft)

    documents: list[CodebookDocument] = []
    span_ordinals: dict[tuple[int, int], int] = {}
    for chunk_number, draft in enumerate(drafts, start=1):
        span = (draft["pdf_page_start"], draft["pdf_page_end"])
        ordinal = span_ordinals.get(span, 0)
        span_ordinals[span] = ordinal + 1
        content = draft["content"]
        identity = f"{profile['id']}:{span[0]}:{span[1]}:{ordinal}:{content}".encode()
        metadata = dict(draft["metadata"])
        if draft["duplicate_locations"]:
            metadata["duplicate_locations"] = draft["duplicate_locations"]
        context_parts = [
            str(profile.get("title") or ""),
            str(profile.get("edition") or ""),
            draft["content_type"],
            f"Article {draft['article_number']}" if draft["article_number"] else "",
            draft["article_title"] or "",
            f"Section {draft['section_number']}" if draft["section_number"] else "",
            draft["section_title"] or "",
            content,
        ]
        documents.append(
            CodebookDocument(
                id=f"{profile['id']}-{hashlib.sha256(identity).hexdigest()[:24]}",
                corpus_id=str(profile["id"]),
                source_name=source_path.name,
                source_sha256=source_hash,
                chunk_number=chunk_number,
                content=content,
                search_text="\n".join(part for part in context_parts if part),
                content_type=draft["content_type"],
                pdf_page_start=draft["pdf_page_start"],
                pdf_page_end=draft["pdf_page_end"],
                printed_page_start=draft["printed_page_start"],
                printed_page_end=draft["printed_page_end"],
                article_number=draft["article_number"],
                article_title=draft["article_title"],
                section_number=draft["section_number"],
                section_title=draft["section_title"],
                edition=str(profile["edition"]) if profile.get("edition") is not None else None,
                document_type=str(profile["document_type"]),
                metadata=metadata,
            )
        )
    return documents


def build_bundle(
    profile: dict[str, Any],
    source_path: Path,
    *,
    correction_provider: TextModelProvider | None = None,
) -> IngestionBundle:
    """Extract, optionally correct, and shape an evidence-preserving source."""

    source_hash = source_sha256(source_path)
    pages = extract_pages(
        source_path,
        printed_page_offset=profile.get("printed_page_offset"),
        ocr=OCRConfig.from_profile(profile.get("ocr")),
    )
    correction = CorrectionConfig.from_profile(profile.get("correction"))
    if correction.mode != "off":
        if correction_provider is None:
            raise ValueError(
                "Correction is enabled but no text-model provider was supplied."
            )
        pages = correct_pages(pages, provider=correction_provider, config=correction)
    documents = documents_from_pages(profile, source_path, pages, source_hash=source_hash)
    if not documents:
        raise ValueError("No extractable text was found in the source.")
    return IngestionBundle(pages=pages, documents=documents)


def build_documents(
    profile: dict[str, Any],
    source_path: Path,
    *,
    correction_provider: TextModelProvider | None = None,
) -> list[CodebookDocument]:
    """Compatibility helper returning documents from a full ingestion bundle."""

    return build_bundle(
        profile,
        source_path,
        correction_provider=correction_provider,
    ).documents


def make_documents(profile: dict[str, Any], source_path: Path, content: str) -> list[dict[str, Any]]:
    """Compatibility wrapper for callers that already hold single-page text."""

    source_hash = hashlib.sha256(content.encode()).hexdigest()
    return [
        document.to_dict()
        for document in documents_from_pages(
            profile,
            source_path,
            [PageText(pdf_page=1, printed_page=1, text=content)],
            source_hash=source_hash,
        )
    ]
