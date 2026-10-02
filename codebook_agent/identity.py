"""Chunk identity derived from source structure, not from incidental text.

A chunk's article and section come only from a structural heading that begins
the chunk, or are carried forward from the most recent such heading. These are
deliberately *not* identity sources:

- running page headers and footers (page furniture repeated at the page edges),
- cross-references and quantities that happen to begin a line or a split chunk
  ("Article 4 requirements also apply", "1.25 times the rating"),
- the second and later pieces of a paragraph that was split for length.

When a higher-level heading (an article) starts, lower-level context (the
section) is cleared so a new article never inherits the previous article's
section.

The rules are generic shapes, never specific document numbers. They are a
deterministic baseline for text-layer sources; they do not use page geometry.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise

from .models import PageText

IDENTITY_VERSION = "heading-structure-v1"
PAGE_FURNITURE_MODES = {"auto", "off"}

_NUMBER = r"\d+(?:\.\d+)+(?:\([A-Za-z0-9]+\))*"
SECTION_LINE = re.compile(rf"^(?P<number>{_NUMBER})(?:\s+(?P<rest>\S.*))?$")
ARTICLE_LINE = re.compile(
    r"^article\s+(?P<number>(?=[A-Za-z0-9.-]*\d)[A-Za-z0-9]+(?:[.-][A-Za-z0-9]+)*|[IVXLC]+\b)"
    r"(?P<separator>\s*[-–—:]\s*|\.\s*|\s+|$)(?P<rest>.*)$",
    re.IGNORECASE,
)
ARTICLE_REFERENCE = re.compile(r"\barticle\s+\S*\d", re.IGNORECASE)
TITLE_END = re.compile(r"[.;:](?:\s|$)")
WORD = re.compile(r"[A-Za-z][A-Za-z'’-]*")
# A line ending with one of these continues a sentence, so the next line is not a heading.
CONTINUING_LINE = re.compile(
    r"(?:\b(?:a|an|and|as|at|by|for|from|in|of|on|or|per|see|the|to|under|with)|[,(-])\s*$",
    re.IGNORECASE,
)
MINOR_WORDS = {
    "a", "an", "and", "as", "at", "by", "for", "from", "in", "into", "of", "on", "or",
    "per", "the", "to", "with", "without",
}
MAX_TITLE_CHARS = 160
EDGE_LINES = 2
MAX_FURNITURE_CHARS = 120
FURNITURE_WINDOW = 2
TABLE_TITLE = re.compile(r"^\s*(?:Table|Schedule)\s+[A-Za-z0-9.-]+", re.IGNORECASE)


@dataclass(frozen=True)
class Heading:
    """A structural heading found at the start of a block of text."""

    level: str  # "article" or "section"
    number: str
    title: str | None


def _title_like(text: str) -> bool:
    """True for a heading title: short, capitalized, and not a sentence."""

    clean = text.strip()
    if not clean or len(clean) > MAX_TITLE_CHARS or not clean[0].isupper():
        return False
    significant = [word for word in WORD.findall(clean) if word.lower() not in MINOR_WORDS]
    if not significant:
        return False
    capitalized = sum(1 for word in significant if word[0].isupper())
    return capitalized / len(significant) >= 0.7


def _title_segment(rest: str) -> str:
    match = TITLE_END.search(rest)
    return (rest[: match.start()] if match else rest).strip()


def parse_heading(
    line: str,
    *,
    previous_line: str | None = None,
    next_line: str | None = None,
) -> Heading | None:
    """Return the heading that starts ``line``, or None for ordinary text."""

    text = " ".join(line.split())
    if not text:
        return None
    if previous_line is not None and CONTINUING_LINE.search(previous_line.strip()):
        return None
    following = " ".join((next_line or "").split())

    article = ARTICLE_LINE.match(text)
    if article:
        rest = article.group("rest").strip()
        separator = article.group("separator").strip()
        if not rest:
            title = following if following and _title_like(following) else None
            return Heading("article", article.group("number"), title)
        title = _title_segment(rest)
        if separator:
            # "Article 3. Grounding" / "Article 3 - Grounding": an explicit heading form.
            return Heading("article", article.group("number"), title if _title_like(title) else None)
        if _title_like(title):
            return Heading("article", article.group("number"), title)
        return None

    section = SECTION_LINE.match(text)
    if section:
        rest = section.group("rest")
        if rest is None:
            if following and len(following) <= 80 and _title_like(following):
                return Heading("section", section.group("number"), following)
            return None
        title = _title_segment(rest)
        if _title_like(title) and not ARTICLE_REFERENCE.search(title):
            return Heading("section", section.group("number"), title)
    return None


def split_at_headings(text: str) -> list[str]:
    """Split a block so every structural heading line starts its own segment."""

    lines = text.splitlines()
    segments: list[list[str]] = []
    current: list[str] = []
    for index, line in enumerate(lines):
        if current and line.strip():
            previous = next((item for item in reversed(current) if item.strip()), None)
            following = next((item for item in lines[index + 1 :] if item.strip()), None)
            if parse_heading(line, previous_line=previous, next_line=following):
                segments.append(current)
                current = []
        current.append(line)
    if current:
        segments.append(current)
    return [joined for segment in segments if (joined := "\n".join(segment).strip())]


def leading_heading(text: str) -> Heading | None:
    """Return the heading that opens a block, considering only its first line."""

    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return None
    return parse_heading(lines[0], next_line=lines[1] if len(lines) > 1 else None)


@dataclass
class IdentityState:
    """Article/section context carried forward in reading order."""

    article_number: str | None = None
    article_title: str | None = None
    section_number: str | None = None
    section_title: str | None = None

    def apply(self, heading: Heading | None) -> str:
        """Update context from a block-opening heading; return the identity source."""

        if heading is None:
            return "carried" if self.article_number or self.section_number else "none"
        if heading.level == "article":
            self.article_number = heading.number
            self.article_title = heading.title
            # A new article never inherits the previous article's section.
            self.section_number = None
            self.section_title = None
        else:
            self.section_number = heading.number
            self.section_title = heading.title
        return "heading"


def _normalize_edge_line(line: str) -> str:
    """Drop page numbers and guide numbers so left/right running heads compare equal."""

    return " ".join(re.sub(r"[\d.()-]*\d[\d.()-]*", " ", line.lower()).split())


def _edge_candidates(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    edges = lines[:EDGE_LINES] + lines[EDGE_LINES:][-EDGE_LINES:]
    return [
        line
        for line in edges
        if len(line) <= MAX_FURNITURE_CHARS
        and not TABLE_TITLE.match(line)
        and not _tabular(line)
    ]


def _tabular(line: str) -> bool:
    """Table rows (tab- or wide-space-delimited, 3+ cells) repeat by design."""

    return "\t" in line or len(re.split(r"\s{2,}", line.strip())) >= 3


def find_page_furniture(pages: Sequence[PageText]) -> set[str]:
    """Find running headers/footers: edge lines repeated on nearby pages.

    A line is furniture when its form without numbers appears among the first
    or last two lines of pages no more than two pages apart. A line that would
    also parse as a heading needs stronger evidence, so a real heading is not
    discarded by coincidence: the identical line on nearby pages, or the same
    multi-word pattern on at least three pages. Table titles and table rows are
    never furniture because table continuation depends on them.
    """

    seen: dict[str, dict[int, set[str]]] = {}
    page_texts: set[str] = set()
    for page in pages:
        whole = " ".join(page.text.split())
        if whole in page_texts:
            continue  # a duplicated page is not evidence that its lines are furniture
        page_texts.add(whole)
        for line in _edge_candidates(page.text):
            seen.setdefault(_normalize_edge_line(line), {}).setdefault(page.pdf_page, set()).add(line)

    furniture: set[str] = set()
    for by_page in seen.values():
        numbers = sorted(by_page)
        nearby = [
            (earlier, later)
            for earlier, later in pairwise(numbers)
            if later - earlier <= FURNITURE_WINDOW
        ]
        if not nearby:
            continue
        sample = next(iter(by_page[numbers[0]]))
        if parse_heading(sample):
            identical = any(by_page[earlier] & by_page[later] for earlier, later in nearby)
            core_words = WORD.findall(re.sub(r"\d+(?:\.\d+)*", " ", sample))
            if not identical and (len(numbers) < 3 or len(core_words) < 2):
                continue
        for lines in by_page.values():
            furniture.update(lines)
    return furniture


def strip_page_furniture(text: str, furniture: set[str]) -> tuple[str, int]:
    """Remove furniture lines from the page edges only; return text and count."""

    if not furniture:
        return text, 0
    lines = text.splitlines()
    content = [index for index, line in enumerate(lines) if line.strip()]
    edge_indexes = set(content[:EDGE_LINES]) | set(content[EDGE_LINES:][-EDGE_LINES:])
    removed = {index for index in edge_indexes if lines[index].strip() in furniture}
    kept = [line for index, line in enumerate(lines) if index not in removed]
    return "\n".join(kept), len(removed)


def page_furniture_mode(profile: dict[str, object]) -> str:
    """Validate and return the profile's page-furniture policy (default ``auto``)."""

    value = profile.get("page_furniture", "auto")
    if not isinstance(value, str) or value not in PAGE_FURNITURE_MODES:
        raise ValueError(
            "page_furniture must be one of: " + ", ".join(sorted(PAGE_FURNITURE_MODES)) + "."
        )
    return value
