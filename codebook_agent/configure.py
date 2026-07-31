"""Local-only source inspection and metadata-only profile generation."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shlex
import shutil
import tempfile
import unicodedata
from pathlib import Path
from typing import Any

from .correction import CorrectionConfig
from .embeddings import resolve_embedding_selection
from .ocr import native_text_is_usable

SUPPORTED_SOURCE_SUFFIXES = {".md", ".pdf", ".txt"}
CONTENT_RANGE_PATTERN = re.compile(
    r"^(?P<name>[A-Za-z][A-Za-z0-9_-]*):(?P<start>[1-9][0-9]*)-(?P<end>[1-9][0-9]*)$"
)
EDITION_PATTERN = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
PROFILE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class MissingSourceDependencyError(RuntimeError):
    """A package required to inspect the selected source is not installed."""


class ProfileExistsError(FileExistsError):
    """A configuration write would replace an existing profile without approval."""


def _slug(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", ascii_value).strip("-._").lower()
    return (slug or "authorized-reference")[:128]


def _page_ranges(page_numbers: list[int]) -> list[list[int]]:
    if not page_numbers:
        return []
    ranges: list[list[int]] = []
    start = previous = page_numbers[0]
    for page in page_numbers[1:]:
        if page == previous + 1:
            previous = page
            continue
        ranges.append([start, previous])
        start = previous = page
    ranges.append([start, previous])
    return ranges


def inspect_source(source_path: Path, *, min_native_characters: int = 40) -> dict[str, Any]:
    """Inspect a source locally without retaining or returning extracted text."""

    source = source_path.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Source not found: {source}")
    suffix = source.suffix.lower()
    if suffix not in SUPPORTED_SOURCE_SUFFIXES:
        raise ValueError(
            f"Unsupported source type '{suffix or '[none]'}'. "
            "Use an authorized .pdf, .txt, or .md file."
        )

    if suffix in {".txt", ".md"}:
        try:
            raw_pages = source.read_text(encoding="utf-8").split("\f")
        except UnicodeDecodeError as error:
            raise ValueError(
                f"Could not read '{source.name}' as UTF-8 text. "
                "Convert it to UTF-8 or provide the original PDF, then retry."
            ) from error
        low_text_pages: list[int] = []
        native_text_pages = len(raw_pages)
    else:
        try:
            from pypdf import PdfReader  # type: ignore[import-not-found]
        except ImportError as error:
            raise MissingSourceDependencyError(
                "PDF inspection requires the pdf extra. Install with "
                "`python -m pip install 'elec-codebook-oo[pdf]'`, then retry."
            ) from error
        try:
            reader = PdfReader(str(source))
            low_text_pages = []
            native_text_pages = 0
            for number, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""
                if native_text_is_usable(text, min_characters=min_native_characters):
                    native_text_pages += 1
                else:
                    low_text_pages.append(number)
            raw_pages = [""] * len(reader.pages)
        except Exception as error:  # noqa: BLE001 - pypdf exposes several reader errors
            raise ValueError(
                f"Could not inspect PDF '{source.name}': {type(error).__name__}. "
                "Verify the file opens locally and is not locked, then retry."
            ) from error

    page_count = len(raw_pages)
    if page_count < 1:
        raise ValueError(f"Source contains no pages: {source}")
    ocr_recommended = suffix == ".pdf" and bool(low_text_pages)
    edition_match = EDITION_PATTERN.search(source.stem)
    return {
        "path": str(source),
        "format": suffix.removeprefix("."),
        "size_bytes": source.stat().st_size,
        "page_count": page_count,
        "native_text_pages": native_text_pages,
        "low_text_pages": len(low_text_pages),
        "low_text_page_ranges": _page_ranges(low_text_pages),
        "ocr_recommended": ocr_recommended,
        "ocr_ready": {
            "pypdfium2": importlib.util.find_spec("pypdfium2") is not None,
            "tesseract": shutil.which("tesseract") is not None,
        },
        "inferred_title": source.stem.replace("_", " ").strip(),
        "inferred_edition": edition_match.group(0) if edition_match else None,
        "network": False,
        "retained_text": False,
    }


def parse_content_ranges(
    specifications: list[str] | None,
    *,
    page_count: int,
) -> dict[str, object]:
    """Parse repeatable ``TYPE:START-END`` values into the profile schema."""

    if not specifications:
        return {"main": [1, page_count]}
    grouped: dict[str, list[list[int]]] = {}
    assigned: list[tuple[str, int, int]] = []
    for specification in specifications:
        match = CONTENT_RANGE_PATTERN.fullmatch(specification)
        if match is None:
            raise ValueError(
                f"Invalid content range '{specification}'. "
                "Use --content-range TYPE:START-END, for example definitions:12-18."
            )
        name = match.group("name")
        start = int(match.group("start"))
        end = int(match.group("end"))
        if end < start or end > page_count:
            raise ValueError(
                f"Content range '{specification}' is outside the inspected 1-{page_count} pages."
            )
        for existing_name, existing_start, existing_end in assigned:
            if start <= existing_end and end >= existing_start:
                raise ValueError(
                    f"Content range '{specification}' overlaps "
                    f"{existing_name}:{existing_start}-{existing_end}. "
                    "Give each PDF page one explicit content type, then retry."
                )
        assigned.append((name, start, end))
        grouped.setdefault(name, []).append([start, end])
    return {
        name: ranges[0] if len(ranges) == 1 else ranges for name, ranges in sorted(grouped.items())
    }


def default_profile_path(profile_id: str) -> Path:
    """Choose a user-owned config location rather than the repository."""

    config_root = Path(os.getenv("XDG_CONFIG_HOME", str(Path.home() / ".config"))).expanduser()
    return (config_root / "elec-codebook-oo" / "profiles" / f"{profile_id}.json").resolve()


def propose_profile(
    inspection: dict[str, Any],
    *,
    profile_id: str | None = None,
    title: str | None = None,
    edition: str | None = None,
    document_type: str = "technical-reference",
    backend: str = "local-artifacts",
    printed_page_offset: int | None = None,
    max_chunk_chars: int = 1800,
    ocr_overrides: dict[str, object] | None = None,
    correction_overrides: dict[str, object] | None = None,
    embedding_provider: str | None = None,
    embedding_model: str | None = None,
    structure_enabled: bool = True,
    recover_tables: bool = True,
    content_ranges: list[str] | None = None,
) -> dict[str, Any]:
    """Build a complete metadata-only profile from inspection and explicit answers."""

    template_path = Path(__file__).resolve().parent / "profiles" / "generic-reference-template.json"
    profile = json.loads(template_path.read_text(encoding="utf-8"))
    selected_title = (title or str(inspection["inferred_title"])).strip()
    if not selected_title:
        raise ValueError("Profile title cannot be empty. Use --title with a source title.")
    if not document_type.strip():
        raise ValueError(
            "Document type cannot be empty. Use --document-type technical-reference or another "
            "stable generic label."
        )
    selected_id = profile_id or _slug(selected_title)
    if not PROFILE_ID_PATTERN.fullmatch(selected_id):
        raise ValueError(
            "Profile id must be 1-128 letters, digits, dots, underscores, or hyphens. "
            "Use --id with a stable value such as electrical-manual-2026."
        )
    selected_edition = edition or inspection.get("inferred_edition")
    if max_chunk_chars < 200:
        raise ValueError("max_chunk_chars must be at least 200. Use --max-chunk-chars 200 or more.")
    profile.update(
        {
            "id": selected_id,
            "title": selected_title,
            "document_type": document_type.strip(),
            "content_ranges": parse_content_ranges(
                content_ranges,
                page_count=int(inspection["page_count"]),
            ),
            "printed_page_offset": printed_page_offset,
            "max_chunk_chars": max_chunk_chars,
            "backend": backend,
        }
    )
    if selected_edition is None:
        profile.pop("edition", None)
    else:
        profile["edition"] = selected_edition
    ocr = dict(profile["ocr"])
    ocr.update(ocr_overrides or {})
    if not ocr_overrides or "mode" not in ocr_overrides:
        ocr["mode"] = "auto" if inspection["ocr_recommended"] else "off"
    profile["ocr"] = ocr
    correction = dict(profile["correction"])
    correction.update(correction_overrides or {})
    CorrectionConfig.from_profile(correction)
    profile["correction"] = correction
    embedding_provider_name, embedding_model_name = resolve_embedding_selection(
        profile,
        provider_override=embedding_provider,
        model_override=embedding_model,
    )
    profile["embedding"] = {
        "provider": embedding_provider_name,
        "model": embedding_model_name,
    }
    profile["structure"] = {
        "enabled": structure_enabled,
        "recover_tables": recover_tables,
    }
    return profile


def unresolved_decisions(
    inspection: dict[str, Any],
    profile: dict[str, Any],
    *,
    explicit_content_ranges: bool,
    authorization_confirmed: bool = False,
) -> list[dict[str, str]]:
    """Name decisions that inspection cannot safely infer."""

    decisions: list[dict[str, str]] = []
    if not authorization_confirmed:
        decisions.append(
            {
                "field": "authorization",
                "question": "Are you authorized to process this exact source and its derivatives?",
                "reason": "The tool cannot determine copyright, license, contract, or access rights.",
            }
        )
    if "edition" not in profile:
        decisions.append(
            {
                "field": "edition",
                "question": "What edition or revision should citations identify?",
                "reason": "No unambiguous four-digit edition was found in the filename.",
            }
        )
    if profile.get("printed_page_offset") is None:
        decisions.append(
            {
                "field": "printed_page_offset",
                "question": "How do printed page numbers differ from PDF page numbers?",
                "reason": "Page-number mappings require operator verification.",
            }
        )
    if not explicit_content_ranges:
        decisions.append(
            {
                "field": "content_ranges",
                "question": "Should front matter, definitions, tables, or annexes use separate ranges?",
                "reason": "The safe proposal treats all pages as main content.",
            }
        )
    if inspection["ocr_recommended"]:
        decisions.append(
            {
                "field": "ocr",
                "question": "Should the reported low-text PDF pages use local Tesseract OCR?",
                "reason": "Low native-text density suggests scanned or image-heavy pages.",
            }
        )
    decisions.append(
        {
            "field": "backend",
            "question": "Keep portable local artifacts or use PostgreSQL/pgvector?",
            "reason": f"The current proposal uses {profile['backend']}.",
        }
    )
    if profile["backend"] == "pgvector":
        decisions.append(
            {
                "field": "embedding",
                "question": "Use offline hash embeddings or an explicit semantic provider?",
                "reason": (
                    "The current proposal uses "
                    f"{profile['embedding']['provider']}/{profile['embedding']['model']}."
                ),
            }
        )
    decisions.append(
        {
            "field": "correction",
            "question": "Keep model-based text correction off or explicitly enable it?",
            "reason": f"The current proposal uses correction.mode={profile['correction']['mode']}.",
        }
    )
    return decisions


def profile_commands(
    source: Path,
    output: Path,
    profile: dict[str, Any],
    *,
    overwrite: bool,
) -> dict[str, str]:
    """Return copy-pasteable commands that reproduce the proposal and preview ingestion."""

    configure = [
        "codebook",
        "configure",
        "--source",
        str(source.expanduser().resolve()),
        "--output",
        str(output.expanduser().resolve()),
        "--id",
        str(profile["id"]),
        "--title",
        str(profile["title"]),
        "--document-type",
        str(profile["document_type"]),
        "--backend",
        str(profile["backend"]),
        "--ocr-mode",
        str(profile["ocr"]["mode"]),
        "--ocr-language",
        str(profile["ocr"]["language"]),
        "--ocr-dpi",
        str(profile["ocr"]["dpi"]),
        "--ocr-page-segmentation-mode",
        str(profile["ocr"]["page_segmentation_mode"]),
        "--ocr-min-native-characters",
        str(profile["ocr"]["min_native_characters"]),
        "--ocr-timeout-seconds",
        str(profile["ocr"]["timeout_seconds"]),
        "--correction-mode",
        str(profile["correction"]["mode"]),
        "--correction-provider",
        str(profile["correction"]["provider"]),
        "--correction-model",
        str(profile["correction"]["model"]),
        "--correction-min-similarity",
        str(profile["correction"]["min_similarity"]),
        "--correction-max-length-change-ratio",
        str(profile["correction"]["max_length_change_ratio"]),
        "--embedding-provider",
        str(profile["embedding"]["provider"]),
        "--embedding-model",
        str(profile["embedding"]["model"]),
        "--max-chunk-chars",
        str(profile["max_chunk_chars"]),
        "--authorized",
        "--apply",
    ]
    if profile.get("edition") is not None:
        configure.extend(["--edition", str(profile["edition"])])
    if profile.get("printed_page_offset") is not None:
        configure.extend(["--printed-page-offset", str(profile["printed_page_offset"])])
    for name, value in sorted(dict(profile["content_ranges"]).items()):
        ranges = [value] if value and isinstance(value[0], int) else value
        for start, end in ranges:
            configure.extend(["--content-range", f"{name}:{start}-{end}"])
    if overwrite:
        configure.append("--overwrite")
    if not profile["structure"]["enabled"]:
        configure.append("--no-structure")
    if not profile["structure"]["recover_tables"]:
        configure.append("--no-table-recovery")
    profile_path = str(output.expanduser().resolve())
    source_path = str(source.expanduser().resolve())
    return {
        "apply_profile": shlex.join(configure),
        "plan": shlex.join(["codebook", "plan", "--profile", profile_path, "--pdf", source_path]),
        "dry": shlex.join(["codebook", "dry", "--profile", profile_path, "--pdf", source_path]),
    }


def write_profile(output_path: Path, profile: dict[str, Any], *, overwrite: bool) -> Path:
    """Atomically write one approved metadata-only profile."""

    destination = output_path.expanduser().resolve()
    validate_profile_path(destination)
    if destination.exists() and not overwrite:
        raise ProfileExistsError(
            f"Profile already exists: {destination}. Review it, then rerun with "
            "--overwrite --apply only if replacement is intended."
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(profile, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary:
        temporary.write(payload)
        temporary_path = Path(temporary.name)
    temporary_path.replace(destination)
    return destination


def validate_profile_path(output_path: Path) -> None:
    """Reject an output shape that cannot be consumed by the profile loader."""

    destination = output_path.expanduser().resolve()
    if destination.suffix.lower() != ".json":
        raise ValueError(
            f"Profile output must end in .json: {destination}. "
            "Choose a metadata-only JSON path and retry."
        )
