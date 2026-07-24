"""Versioned, backend-neutral document and retrieval contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

DOCUMENT_SCHEMA_VERSION = "2.2"
PAGE_SCHEMA_VERSION = "1.0"
EMBEDDING_DIMENSIONS = 1536


@dataclass(frozen=True)
class PageText:
    """Text extracted from one source page."""

    pdf_page: int
    text: str
    printed_page: int | None = None
    extraction_method: str = "native"
    extraction_confidence: float | None = None
    raw_text: str | None = None
    correction_status: str = "not-requested"
    correction_provider: str | None = None
    correction_model: str | None = None
    correction_similarity: float | None = None
    correction_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Return both selected and immutable raw extraction evidence."""

        value = asdict(self)
        value["raw_text"] = self.raw_text if self.raw_text is not None else self.text
        value["schema_version"] = PAGE_SCHEMA_VERSION
        return value


@dataclass(frozen=True)
class CodebookDocument:
    """One evidence-preserving unit presented identically to every backend."""

    id: str
    corpus_id: str
    source_name: str
    source_sha256: str
    chunk_number: int
    content: str
    search_text: str
    content_type: str
    pdf_page_start: int
    pdf_page_end: int
    printed_page_start: int | None = None
    printed_page_end: int | None = None
    article_number: str | None = None
    article_title: str | None = None
    section_number: str | None = None
    section_title: str | None = None
    edition: str | None = None
    document_type: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = DOCUMENT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Return a stable JSON-compatible representation."""

        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> CodebookDocument:
        """Load a document written by the local artifact backend."""

        return cls(**value)


@dataclass(frozen=True)
class SearchResult:
    """A backend-neutral retrieval result with explicit source evidence."""

    document: CodebookDocument
    score: float
    vector_score: float | None = None
    text_score: float | None = None

    def citation(self) -> str:
        """Build a compact, human-readable evidence locator."""

        parts: list[str] = [self.document.source_name]
        if self.document.article_number:
            parts.append(f"Article {self.document.article_number}")
        if self.document.section_number:
            parts.append(f"Section {self.document.section_number}")
        if self.document.pdf_page_end != self.document.pdf_page_start:
            parts.append(
                f"PDF pages {self.document.pdf_page_start}-{self.document.pdf_page_end}"
            )
        else:
            parts.append(f"PDF page {self.document.pdf_page_start}")
        if self.document.printed_page_start is not None:
            if (
                self.document.printed_page_end is not None
                and self.document.printed_page_end
                != self.document.printed_page_start
            ):
                parts.append(
                    "printed pages "
                    f"{self.document.printed_page_start}-"
                    f"{self.document.printed_page_end}"
                )
            else:
                parts.append(f"printed page {self.document.printed_page_start}")
        page_evidence = self.document.metadata.get("page_evidence")
        has_ocr_page = isinstance(page_evidence, list) and any(
            isinstance(value, dict)
            and value.get("extraction_method") == "ocr-tesseract"
            for value in page_evidence
        )
        if (
            self.document.metadata.get("extraction_method") == "ocr-tesseract"
            or has_ocr_page
        ):
            confidence = self.document.metadata.get("extraction_confidence")
            if isinstance(confidence, (int, float)):
                parts.append(f"OCR confidence {confidence:.0%}")
            else:
                parts.append("OCR-derived")
        has_corrected_page = isinstance(page_evidence, list) and any(
            isinstance(value, dict) and value.get("correction_status") == "accepted"
            for value in page_evidence
        )
        if (
            self.document.metadata.get("correction_status") == "accepted"
            or has_corrected_page
        ):
            parts.append(
                "model-corrected OCR"
                if (
                    self.document.metadata.get("extraction_method")
                    == "ocr-tesseract"
                    or has_ocr_page
                )
                else "model-corrected text"
            )
        return ", ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """Return a stable JSON-compatible result."""

        return {
            "score": self.score,
            "vector_score": self.vector_score,
            "text_score": self.text_score,
            "citation": self.citation(),
            "document": self.document.to_dict(),
        }
