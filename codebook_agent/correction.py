"""Auditable model-based correction for uncertain extracted text."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from difflib import SequenceMatcher
from typing import Any, Sequence

from .models import PageText
from .text_models import DEFAULT_OPENAI_TEXT_MODEL, TEXT_MODEL_PROVIDERS, TextModelProvider

CORRECTION_MODES = {"off", "ocr-only", "all"}
PROTECTED_TOKEN = re.compile(
    r"\b\d+(?:,\d{3})*(?:\.\d+)?(?:\([A-Za-z0-9]+\))*"
    r"(?:\s*(?:V|A|W|kW|mm|cm|m|ft|in)\b)?",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CorrectionConfig:
    """Selection and acceptance policy for model correction."""

    mode: str = "off"
    provider: str = "openai"
    model: str = DEFAULT_OPENAI_TEXT_MODEL
    min_similarity: float = 0.82
    max_length_change_ratio: float = 0.20

    def __post_init__(self) -> None:
        if self.mode not in CORRECTION_MODES:
            raise ValueError(f"Unknown correction mode: {self.mode}")
        if self.provider not in TEXT_MODEL_PROVIDERS:
            raise ValueError(f"Unknown correction provider: {self.provider}")
        if not 0.0 <= self.min_similarity <= 1.0:
            raise ValueError("correction min_similarity must be between 0 and 1.")
        if not 0.0 <= self.max_length_change_ratio <= 1.0:
            raise ValueError("correction max_length_change_ratio must be between 0 and 1.")

    @classmethod
    def from_profile(cls, value: object) -> CorrectionConfig:
        if value is None:
            return cls()
        if not isinstance(value, dict):
            raise ValueError("correction must be an object.")
        return cls(
            mode=str(value.get("mode", "off")),
            provider=str(value.get("provider", "openai")),
            model=str(value.get("model", DEFAULT_OPENAI_TEXT_MODEL)),
            min_similarity=float(value.get("min_similarity", 0.82)),
            max_length_change_ratio=float(value.get("max_length_change_ratio", 0.20)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "provider": self.provider,
            "model": self.model,
            "min_similarity": self.min_similarity,
            "max_length_change_ratio": self.max_length_change_ratio,
        }


def _protected_tokens(text: str) -> tuple[str, ...]:
    return tuple(match.group(0).lower() for match in PROTECTED_TOKEN.finditer(text))


def _correct_one(
    page: PageText,
    *,
    provider: TextModelProvider,
    config: CorrectionConfig,
) -> PageText:
    raw = page.raw_text if page.raw_text is not None else page.text
    corrected = provider.generate(
        system_prompt=(
            "Repair OCR character and spacing errors in technical source text. Preserve every "
            "word, number, section identifier, unit, symbol, list marker, and line break unless "
            "it is clearly an OCR error. Do not summarize, interpret, complete, or add content. "
            "Return only the corrected text."
        ),
        user_prompt=f"PDF page {page.pdf_page}\n\n{raw}",
    ).strip()
    similarity = SequenceMatcher(None, raw, corrected).ratio()
    length_ratio = abs(len(corrected) - len(raw)) / max(len(raw), 1)
    reasons: list[str] = []
    if not corrected:
        reasons.append("empty_output")
    if _protected_tokens(raw) != _protected_tokens(corrected):
        reasons.append("protected_tokens_changed")
    if similarity < config.min_similarity:
        reasons.append("similarity_below_threshold")
    if length_ratio > config.max_length_change_ratio:
        reasons.append("length_change_above_threshold")
    accepted = not reasons
    return replace(
        page,
        text=corrected if accepted else raw,
        raw_text=raw,
        correction_status="accepted" if accepted else "rejected",
        correction_provider=provider.name,
        correction_model=provider.model,
        correction_similarity=similarity,
        correction_reasons=tuple(reasons),
    )


def correct_pages(
    pages: Sequence[PageText],
    *,
    provider: TextModelProvider,
    config: CorrectionConfig,
) -> list[PageText]:
    """Correct eligible pages while retaining raw text and rejection evidence."""

    corrected: list[PageText] = []
    for page in pages:
        eligible = config.mode == "all" or (
            config.mode == "ocr-only" and page.extraction_method == "ocr-tesseract"
        )
        corrected.append(
            _correct_one(page, provider=provider, config=config) if eligible else page
        )
    return corrected
