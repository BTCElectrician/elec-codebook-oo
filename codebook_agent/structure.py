"""Generic, deterministic structure and multi-page table recovery."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Sequence

from .models import PageText

TABLE_TITLE = re.compile(
    r"^\s*(?:Table|Schedule)\s+(?P<id>[A-Za-z0-9.-]+)(?:\s*[-—:].*|\s+\(continued\).*)?$",
    re.IGNORECASE,
)
LIST_LINE = re.compile(r"^\s*(?:\d+[.)]|[A-Za-z][.)]|[-•])\s+")
DEFINITION = re.compile(r"^\s*[^.\n]{2,80}\.\s+\S")


@dataclass(frozen=True)
class StructuredBlock:
    text: str
    content_type: str
    pdf_page_start: int
    pdf_page_end: int
    printed_page_start: int | None
    printed_page_end: int | None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StructureConfig:
    enabled: bool = False
    recover_tables: bool = True

    @classmethod
    def from_profile(cls, value: object) -> StructureConfig:
        if value is None:
            return cls()
        if not isinstance(value, dict):
            raise ValueError("structure must be an object.")
        enabled = value.get("enabled", False)
        recover_tables = value.get("recover_tables", True)
        if not isinstance(enabled, bool) or not isinstance(recover_tables, bool):
            raise ValueError("structure enabled and recover_tables must be booleans.")
        return cls(enabled=enabled, recover_tables=recover_tables)


def _columns(line: str) -> list[str]:
    if "\t" in line:
        return [part.strip() for part in line.split("\t")]
    return [part.strip() for part in re.split(r"\s{2,}", line.strip())]


def _table_markdown(title: str, lines: list[str]) -> str:
    rows = [_columns(line) for line in lines if line.strip()]
    width = len(rows[0]) if rows else 0
    if width < 2 or any(len(row) != width for row in rows):
        return "\n".join([title, *lines]).strip()
    rendered = [f"### {title}", "", "| " + " | ".join(rows[0]) + " |"]
    rendered.append("| " + " | ".join(["---"] * width) + " |")
    rendered.extend("| " + " | ".join(row) + " |" for row in rows[1:])
    return "\n".join(rendered)


def _page_table(page: PageText) -> tuple[str, str, list[str]] | None:
    lines = [line.rstrip() for line in page.text.splitlines() if line.strip()]
    if not lines:
        return None
    match = TABLE_TITLE.match(lines[0])
    if not match:
        return None
    data_lines = lines[1:]
    if len(data_lines) < 2 or not all(len(_columns(line)) >= 2 for line in data_lines):
        return None
    return match.group("id"), lines[0], data_lines


def _kind(text: str) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) == 1 and len(text) <= 100 and not text.rstrip().endswith((".", ";")):
        return "heading"
    if text.lstrip().upper().startswith(("NOTE:", "CAUTION:", "WARNING:")):
        return "note"
    if lines and all(LIST_LINE.match(line) for line in lines):
        return "list"
    if DEFINITION.match(text):
        return "definition"
    return "body"


def recover_structure(
    profile: dict[str, object],
    pages: Sequence[PageText],
) -> list[StructuredBlock]:
    """Recover generic blocks and join explicitly continued tables across pages."""

    config = StructureConfig.from_profile(profile.get("structure"))
    if not config.enabled:
        return [
            StructuredBlock(
                text=page.text,
                content_type="main",
                pdf_page_start=page.pdf_page,
                pdf_page_end=page.pdf_page,
                printed_page_start=page.printed_page,
                printed_page_end=page.printed_page,
                metadata={"structure_kind": "page"},
            )
            for page in pages
            if page.text.strip()
        ]

    blocks: list[StructuredBlock] = []
    index = 0
    while index < len(pages):
        page = pages[index]
        table = _page_table(page) if config.recover_tables else None
        if table:
            table_id, title, rows = table
            end_page = page
            source_pages = [page.pdf_page]
            index += 1
            while index < len(pages):
                continuation = _page_table(pages[index])
                if not continuation or continuation[0].lower() != table_id.lower():
                    break
                next_rows = continuation[2]
                if rows and next_rows and _columns(rows[0]) == _columns(next_rows[0]):
                    next_rows = next_rows[1:]
                rows.extend(next_rows)
                end_page = pages[index]
                source_pages.append(end_page.pdf_page)
                index += 1
            blocks.append(
                StructuredBlock(
                    text=_table_markdown(title, rows),
                    content_type="tables",
                    pdf_page_start=page.pdf_page,
                    pdf_page_end=end_page.pdf_page,
                    printed_page_start=page.printed_page,
                    printed_page_end=end_page.printed_page,
                    metadata={
                        "structure_kind": "table",
                        "table_id": table_id,
                        "table_title": title,
                        "source_pages": source_pages,
                        "format": "markdown",
                    },
                )
            )
            continue

        for paragraph in re.split(r"\n\s*\n", page.text):
            clean = paragraph.strip()
            if clean:
                kind = _kind(clean)
                blocks.append(
                    StructuredBlock(
                        text=clean,
                        content_type=kind if kind != "body" else "main",
                        pdf_page_start=page.pdf_page,
                        pdf_page_end=page.pdf_page,
                        printed_page_start=page.printed_page,
                        printed_page_end=page.printed_page,
                        metadata={"structure_kind": kind},
                    )
                )
        index += 1
    return blocks
