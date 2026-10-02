"""Chunk identity comes from source structure, not incidental text.

Each test reproduces a misattribution shape seen in production codebook
indexes, using invented text only.
"""

import hashlib
from pathlib import Path

import pytest

from codebook_agent.core import documents_from_pages, load_profile
from codebook_agent.identity import find_page_furniture, parse_heading, split_at_headings
from codebook_agent.models import PageText, SearchResult

SOURCE = Path("manual.txt")
SOURCE_HASH = hashlib.sha256(b"synthetic").hexdigest()


def profile(**overrides):
    base = {
        "id": "synthetic",
        "title": "Synthetic Manual",
        "edition": "2026",
        "document_type": "manual",
        "backend": "local-artifacts",
        "questions": [],
    }
    return {**base, **overrides}


def build(pages, **overrides):
    return documents_from_pages(profile(**overrides), SOURCE, pages, source_hash=SOURCE_HASH)


def labels(documents):
    return [(doc.content[:24], doc.article_number, doc.section_number) for doc in documents]


def test_number_led_sentence_is_not_a_section_heading():
    documents = build(
        [
            PageText(
                1,
                "3.1 Scope\n\nThis invented rule covers frames.\n\n"
                "1.25 times the rated current is used for sizing.",
            )
        ]
    )

    assert documents[-1].content.startswith("1.25 times")
    assert documents[-1].section_number == "3.1"
    assert documents[-1].metadata["identity_source"] == "carried"


def test_prose_reference_to_an_article_does_not_change_the_article():
    documents = build(
        [
            PageText(
                1,
                "Article 3. Grounding\n\n3.1 Scope\n\n"
                "Article 4 requirements also apply where invented motors are installed.",
            )
        ]
    )

    assert documents[-1].article_number == "3"
    assert documents[-1].section_number == "3.1"


def test_new_article_does_not_inherit_the_previous_articles_section():
    documents = build(
        [
            PageText(1, "Article 3. Grounding\n\n3.1 Scope\n\nInvented grounding text."),
            PageText(2, "Article 5. Motors\n\nThe invented disconnect is within sight."),
        ]
    )

    assert labels(documents)[-2:] == [
        ("Article 5. Motors", "5", None),
        ("The invented disconnect ", "5", None),
    ]


def test_split_piece_that_begins_with_a_number_keeps_carried_identity():
    prefix = "word " * 39 + "tail"  # 199 characters, so the next token starts a new piece
    assert len(prefix) == 199
    paragraph = prefix + " 3.9 Bonding Jumper Sizing Applies Here as an invented phrase."
    documents = build([PageText(1, "3.1 Scope\n\n" + paragraph)], max_chunk_chars=200)

    continuation = documents[-1]
    assert continuation.content.startswith("3.9 Bonding")
    assert continuation.section_number == "3.1"
    assert continuation.metadata["identity_source"] == "carried"


def test_heading_inside_a_single_newline_paragraph_starts_its_own_chunk():
    # Native PDF text often has no blank lines between a heading and the prior text.
    documents = build(
        [
            PageText(
                1,
                "3.1 Scope\nThis invented rule covers frames.\n"
                "3.2 Bonding Jumpers\nInvented jumpers are copper.",
            )
        ]
    )

    assert labels(documents) == [
        ("3.1 Scope This invented ", None, "3.1"),
        ("3.2 Bonding Jumpers Inve", None, "3.2"),
    ]


def test_wrapped_cross_reference_line_is_not_a_heading():
    text = "3.1 Scope\nInvented bonding is required as specified in\n3.4 Grounding Electrode Conductors."
    assert split_at_headings(text) == [text]
    assert parse_heading("3.4 Grounding Electrode Conductors.", previous_line="specified in") is None


def test_running_headers_and_footers_are_not_identity_or_content():
    pages = [
        PageText(
            1,
            "ARTICLE 3 - GROUNDING   3.1\n3.1 Scope\nInvented grounding text begins here.\nPage 11",
        ),
        PageText(
            2,
            "3.1   ARTICLE 3 - GROUNDING\nInvented continuation text for the scope rule.\nPage 12",
        ),
        PageText(
            3,
            "ARTICLE 3 - GROUNDING   3.2\n3.2 Bonding Jumpers\nInvented jumper text.\nPage 13",
        ),
    ]
    documents = build(pages)

    assert all("ARTICLE 3 - GROUNDING" not in doc.content for doc in documents)
    assert all("Page 1" not in doc.content for doc in documents)
    continuation = next(doc for doc in documents if "continuation" in doc.content)
    assert continuation.section_number == "3.1"
    assert continuation.metadata["page_evidence"][0]["furniture_lines_removed"] == 2
    # The page evidence itself is untouched.
    assert pages[1].text.startswith("3.1   ARTICLE 3")


def test_running_header_guide_number_does_not_label_a_continuation():
    # A left-page banner that starts with the guide section number.
    pages = [
        PageText(1, "3.1 Scope\nInvented text.\nSYNTHETIC MANUAL 2026"),
        PageText(2, "3.4 ARTICLE 3 - GROUNDING\nInvented continuation of the scope rule.\nSYNTHETIC MANUAL 2026"),
        PageText(3, "3.4 ARTICLE 3 - GROUNDING\n3.4 Clearances\nInvented clearance text.\nSYNTHETIC MANUAL 2026"),
    ]
    continuation = next(doc for doc in build(pages) if "continuation" in doc.content)

    assert continuation.section_number == "3.1"


def test_similar_headings_on_nearby_pages_are_not_mistaken_for_furniture():
    pages = [
        PageText(1, "1.1 Scope\nInvented first chapter text."),
        PageText(2, "2.1 Scope\nInvented second chapter text."),
    ]

    assert find_page_furniture(pages) == set()
    assert [doc.section_number for doc in build(pages)] == ["1.1", "2.1"]


def test_page_furniture_can_be_disabled():
    pages = [PageText(number, f"Synthetic Manual Header\nInvented page {number} text.") for number in (1, 2)]

    assert any("Header" in doc.content for doc in build(pages, page_furniture="off"))
    assert not any("Header" in doc.content for doc in build(pages))


def test_profile_rejects_unknown_page_furniture_mode(tmp_path):
    path = tmp_path / "profile.json"
    path.write_text(
        '{"id":"x","title":"x","document_type":"manual","backend":"local-artifacts",'
        '"questions":[],"page_furniture":"sometimes"}',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="page_furniture"):
        load_profile(path)


def test_ids_do_not_shift_when_an_earlier_page_changes():
    later = PageText(2, "3.2 Bonding Jumpers\n\nInvented jumper text.")
    before = build([PageText(1, "3.1 Scope\n\nInvented text."), later])
    after = build(
        [PageText(1, "3.1 Scope\n\nInvented text.\n\nAn added invented paragraph."), later]
    )

    assert [doc.id for doc in before if doc.pdf_page_start == 2] == [
        doc.id for doc in after if doc.pdf_page_start == 2
    ]
    assert len({doc.id for doc in after}) == len(after)
    assert [doc.chunk_number for doc in after] == list(range(1, len(after) + 1))


def test_duplicated_source_page_is_indexed_once_and_cites_both_locations():
    text = "3.1 Scope\nInvented duplicated scan text that appears twice.\nMore invented text."
    documents = build([PageText(5, text), PageText(6, text)])

    assert len(documents) == 1
    assert documents[0].metadata["duplicate_locations"][0]["pdf_page_start"] == 6
    citation = SearchResult(document=documents[0], score=1.0).citation()
    assert "same text also on PDF page 6" in citation


def test_same_text_under_different_sections_is_kept():
    documents = build(
        [PageText(1, "3.1 Scope\n\nReserved.\n\n3.2 Bonding Jumpers\n\nReserved.")]
    )

    assert [(doc.content, doc.section_number) for doc in documents if doc.content == "Reserved."] == [
        ("Reserved.", "3.1"),
        ("Reserved.", "3.2"),
    ]


def test_pgvector_refuses_duplicate_ids_before_connecting():
    from dataclasses import replace

    from codebook_agent.backends.pgvector import PgVectorBackend

    documents = build([PageText(1, "3.1 Scope\n\nInvented text.\n\nMore invented text.")])
    duplicate = [documents[0], replace(documents[1], id=documents[0].id)]
    backend = object.__new__(PgVectorBackend)  # no pool: validation must happen first
    with pytest.raises(ValueError, match="duplicate document IDs"):
        backend.index_documents(
            profile=profile(),
            documents=duplicate,
            embeddings=[[0.0] * 1536] * 2,
            embedding_provider="hash",
            embedding_model="codebook-hash-v1",
        )
