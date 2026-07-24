import hashlib

import pytest

from codebook_agent.core import documents_from_pages, extract_pages, load_profile
from codebook_agent.models import PageText


def profile(**overrides):
    base = {
        "id": "synthetic",
        "title": "Synthetic Safety Manual",
        "edition": "2026",
        "document_type": "manual",
        "backend": "local-artifacts",
        "questions": ["Authorized?"],
        "printed_page_offset": 2,
        "content_ranges": {
            "definitions": [{"start_pdf_page": 3, "end_pdf_page": 3}],
            "tables": [[4, 5]],
        },
    }
    return {**base, **overrides}


def test_text_extraction_preserves_form_feed_pages(tmp_path):
    source = tmp_path / "book.txt"
    source.write_text("front\fArticle 2. Wiring\n\n2.1 Scope\fDefinition text", encoding="utf-8")

    pages = extract_pages(source, printed_page_offset=2)

    assert [page.pdf_page for page in pages] == [1, 2, 3]
    assert [page.printed_page for page in pages] == [None, None, 1]
    assert pages[1].text.startswith("Article 2")


def test_documents_preserve_page_type_and_heading_context(tmp_path):
    source = tmp_path / "manual.txt"
    pages = [
        PageText(2, "Article 2. Wiring methods", None),
        PageText(3, "2.1 Scope\n\nDefinition text", 1),
        PageText(4, "Table A\n\nTraining row", 2),
    ]

    documents = documents_from_pages(
        profile(),
        source,
        pages,
        source_hash=hashlib.sha256(b"synthetic").hexdigest(),
    )

    assert [document.pdf_page_start for document in documents] == [2, 3, 3, 4, 4]
    assert documents[0].article_number == "2"
    assert documents[1].article_number == "2"
    assert documents[1].section_number == "2.1"
    assert documents[1].content_type == "definitions"
    assert documents[-1].content_type == "tables"
    assert documents[-1].printed_page_start == 2
    assert all(document.schema_version == "2.1" for document in documents)


def test_invalid_profile_backend_is_rejected(tmp_path):
    path = tmp_path / "profile.json"
    path.write_text(
        '{"id":"x","title":"x","document_type":"manual","backend":"qdrant","questions":[]}',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="not implemented"):
        load_profile(path)


def test_profile_id_cannot_escape_artifact_directory(tmp_path):
    path = tmp_path / "profile.json"
    path.write_text(
        '{"id":"../../outside","title":"x","document_type":"manual",'
        '"backend":"local-artifacts","questions":[]}',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="cannot contain a path separator"):
        load_profile(path)
