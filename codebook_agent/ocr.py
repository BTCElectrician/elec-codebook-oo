"""Local OCR primitives with explicit provenance and no network calls."""

from __future__ import annotations

import csv
import io
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

OCR_MODES = {"off", "auto", "always"}
OCR_LANGUAGE_PATTERN = re.compile(r"^[A-Za-z0-9_.+-]+$")


@dataclass(frozen=True)
class OCRConfig:
    """Validated local OCR configuration."""

    mode: str = "auto"
    engine: str = "tesseract"
    language: str = "eng"
    dpi: int = 300
    page_segmentation_mode: int = 3
    min_native_characters: int = 40
    timeout_seconds: int = 120

    @classmethod
    def from_profile(cls, value: object) -> OCRConfig:
        if value is None:
            return cls()
        if not isinstance(value, dict):
            raise TypeError("ocr must be an object.")
        config = cls(
            mode=str(value.get("mode", "auto")).lower(),
            engine=str(value.get("engine", "tesseract")).lower(),
            language=str(value.get("language", "eng")),
            dpi=int(value.get("dpi", 300)),
            page_segmentation_mode=int(value.get("page_segmentation_mode", 3)),
            min_native_characters=int(value.get("min_native_characters", 40)),
            timeout_seconds=int(value.get("timeout_seconds", 120)),
        )
        config.validate()
        return config

    def validate(self) -> None:
        if self.mode not in OCR_MODES:
            raise ValueError(f"ocr.mode must be one of: {', '.join(sorted(OCR_MODES))}.")
        if self.engine != "tesseract":
            raise ValueError("The only implemented OCR engine is tesseract.")
        if not OCR_LANGUAGE_PATTERN.fullmatch(self.language):
            raise ValueError("ocr.language contains unsupported characters.")
        if not 150 <= self.dpi <= 600:
            raise ValueError("ocr.dpi must be between 150 and 600.")
        if not 0 <= self.page_segmentation_mode <= 13:
            raise ValueError("ocr.page_segmentation_mode must be between 0 and 13.")
        if not 0 <= self.min_native_characters <= 10_000:
            raise ValueError("ocr.min_native_characters must be between 0 and 10000.")
        if not 1 <= self.timeout_seconds <= 600:
            raise ValueError("ocr.timeout_seconds must be between 1 and 600.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "engine": self.engine,
            "language": self.language,
            "dpi": self.dpi,
            "page_segmentation_mode": self.page_segmentation_mode,
            "min_native_characters": self.min_native_characters,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True)
class OCRPageResult:
    """OCR output for one physical PDF page."""

    pdf_page: int
    text: str
    confidence: float | None
    engine: str = "tesseract"


def native_text_is_usable(text: str, *, min_characters: int) -> bool:
    """Treat alphanumeric source characters as the minimum useful text signal."""

    return sum(character.isalnum() for character in text) >= min_characters


def _parse_tesseract_tsv(raw_tsv: str) -> tuple[str, float | None]:
    """Rebuild readable lines and a mean word confidence from Tesseract TSV."""

    reader = csv.DictReader(
        io.StringIO(raw_tsv),
        delimiter="\t",
        quoting=csv.QUOTE_NONE,
    )
    paragraphs: list[list[str]] = []
    current_paragraph: tuple[str, str] | None = None
    current_line: tuple[str, str, str] | None = None
    line_words: list[str] = []
    paragraph_lines: list[str] = []
    confidences: list[float] = []

    def finish_line() -> None:
        nonlocal line_words
        if line_words:
            paragraph_lines.append(" ".join(line_words))
            line_words = []

    def finish_paragraph() -> None:
        nonlocal paragraph_lines
        finish_line()
        if paragraph_lines:
            paragraphs.append(paragraph_lines)
            paragraph_lines = []

    for row in reader:
        word = (row.get("text") or "").strip()
        if not word:
            continue
        paragraph = (row.get("block_num") or "", row.get("par_num") or "")
        line = (*paragraph, row.get("line_num") or "")
        if current_paragraph is not None and paragraph != current_paragraph:
            finish_paragraph()
            current_line = None
        elif current_line is not None and line != current_line:
            finish_line()
        current_paragraph = paragraph
        current_line = line
        line_words.append(word)
        try:
            confidence = float(row.get("conf") or -1)
        except ValueError:
            confidence = -1
        if confidence >= 0:
            confidences.append(confidence)

    finish_paragraph()
    text = "\n\n".join("\n".join(lines) for lines in paragraphs).strip()
    confidence = (sum(confidences) / len(confidences) / 100.0) if confidences else None
    return text, confidence


class TesseractOCR:
    """Render selected PDF pages and OCR them with the local Tesseract binary."""

    def __init__(self, config: OCRConfig) -> None:
        config.validate()
        binary = shutil.which("tesseract")
        if not binary:
            raise RuntimeError(
                "Tesseract OCR is required for this page. Install `tesseract` "
                "(macOS: `brew install tesseract`; Ubuntu: `apt install tesseract-ocr`) "
                "or set ocr.mode to off."
            )
        try:
            import pypdfium2  # type: ignore[import-not-found]
        except ImportError as error:
            raise RuntimeError(
                "OCR rendering support is optional. Install it with: pip install '.[ocr]'"
            ) from error
        self.config = config
        self.binary = binary
        self._pdfium = pypdfium2

    def extract_pages(self, source_path: Path, pdf_pages: list[int]) -> dict[int, OCRPageResult]:
        """OCR only the requested one-based pages."""

        if not pdf_pages:
            return {}
        results: dict[int, OCRPageResult] = {}
        document = self._pdfium.PdfDocument(source_path)
        try:
            for pdf_page in pdf_pages:
                if pdf_page < 1 or pdf_page > len(document):
                    raise ValueError(f"OCR page is outside the PDF: {pdf_page}")
                page = document[pdf_page - 1]
                bitmap = page.render(scale=self.config.dpi / 72)
                image = bitmap.to_pil()
                buffer = io.BytesIO()
                image.save(buffer, format="PNG")
                png_bytes = buffer.getvalue()
                image.close()
                bitmap.close()
                page.close()
                completed = subprocess.run(
                    [
                        self.binary,
                        "stdin",
                        "stdout",
                        "--dpi",
                        str(self.config.dpi),
                        "-l",
                        self.config.language,
                        "--psm",
                        str(self.config.page_segmentation_mode),
                        "tsv",
                    ],
                    input=png_bytes,
                    capture_output=True,
                    check=False,
                    timeout=self.config.timeout_seconds,
                )
                if completed.returncode != 0:
                    stderr = completed.stderr.decode("utf-8", errors="replace").strip()
                    raise RuntimeError(
                        f"Tesseract failed on PDF page {pdf_page} "
                        f"(exit {completed.returncode}): {stderr[-500:]}"
                    )
                text, confidence = _parse_tesseract_tsv(
                    completed.stdout.decode("utf-8", errors="replace")
                )
                results[pdf_page] = OCRPageResult(
                    pdf_page=pdf_page,
                    text=text,
                    confidence=confidence,
                )
        except subprocess.TimeoutExpired as error:
            raise RuntimeError(
                f"Tesseract exceeded {self.config.timeout_seconds}s on a PDF page."
            ) from error
        finally:
            document.close()
        return results
