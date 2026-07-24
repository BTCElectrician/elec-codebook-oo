import hashlib

from codebook_agent.core import documents_from_pages
from codebook_agent.models import PageText
from codebook_agent.structure import recover_structure


def _profile() -> dict[str, object]:
    return {
        "id": "synthetic",
        "title": "Synthetic Installer Manual",
        "edition": "2026",
        "document_type": "manual",
        "backend": "local-artifacts",
        "questions": [],
        "max_chunk_chars": 1800,
        "structure": {
            "enabled": True,
            "recover_tables": True,
        },
    }


def test_multi_page_table_is_recovered_with_page_range_and_markdown():
    pages = [
        PageText(
            pdf_page=10,
            printed_page=7,
            text=(
                "Table 4 — Synthetic Motor Ratings\n"
                "Motor\tVoltage\tCurrent\n"
                "M1\t480 V\t10 A\n"
                "M2\t480 V\t12 A"
            ),
        ),
        PageText(
            pdf_page=11,
            printed_page=8,
            text=(
                "Table 4 (continued)\n"
                "Motor\tVoltage\tCurrent\n"
                "M3\t480 V\t14 A"
            ),
        ),
    ]

    blocks = recover_structure(_profile(), pages)

    assert len(blocks) == 1
    assert blocks[0].content_type == "tables"
    assert blocks[0].pdf_page_start == 10
    assert blocks[0].pdf_page_end == 11
    assert blocks[0].metadata["table_id"] == "4"
    assert blocks[0].metadata["source_pages"] == [10, 11]
    assert "| Motor | Voltage | Current |" in blocks[0].text
    assert "| M3 | 480 V | 14 A |" in blocks[0].text

    documents = documents_from_pages(
        _profile(),
        source_path=__import__("pathlib").Path("manual.txt"),
        pages=pages,
        source_hash=hashlib.sha256(b"synthetic").hexdigest(),
    )
    assert len(documents) == 1
    assert documents[0].pdf_page_start == 10
    assert documents[0].pdf_page_end == 11
    assert documents[0].metadata["structure_kind"] == "table"
    assert "\n| Motor | Voltage | Current |\n" in documents[0].content
    assert [
        item["pdf_page"] for item in documents[0].metadata["page_evidence"]
    ] == [10, 11]


def test_generic_blocks_label_notes_lists_and_definitions():
    pages = [
        PageText(
            pdf_page=1,
            text=(
                "Definitions\n\n"
                "Qualified Person. A synthetic person with demonstrated training.\n\n"
                "NOTE: Verify the invented value before use.\n\n"
                "1. First training step\n2. Second training step"
            ),
        )
    ]

    blocks = recover_structure(_profile(), pages)
    kinds = [block.metadata["structure_kind"] for block in blocks]

    assert "heading" in kinds
    assert "definition" in kinds
    assert "note" in kinds
    assert "list" in kinds
