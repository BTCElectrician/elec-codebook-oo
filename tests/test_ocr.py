import shutil

import pytest

from codebook_agent.core import build_documents, extract_pages
from codebook_agent.ocr import OCRConfig
from tests.ocr_test_support import create_image_only_pdf

pypdf = pytest.importorskip("pypdf")
pytest.importorskip("pypdfium2")
pytest.importorskip("PIL")


@pytest.mark.ocr
@pytest.mark.skipif(shutil.which("tesseract") is None, reason="Tesseract is not installed")
def test_real_tesseract_recovers_image_only_pdf_with_provenance(tmp_path):
    source = tmp_path / "synthetic-scan.pdf"
    create_image_only_pdf(source)
    assert not (pypdf.PdfReader(source).pages[0].extract_text() or "").strip()

    config = OCRConfig(
        mode="auto",
        dpi=300,
        page_segmentation_mode=6,
        min_native_characters=20,
    )
    pages = extract_pages(source, printed_page_offset=0, ocr=config)

    assert len(pages) == 1
    assert pages[0].extraction_method == "ocr-tesseract"
    assert pages[0].extraction_confidence is not None
    assert pages[0].extraction_confidence > 0.5
    assert "forty-two training units" in pages[0].text.lower()

    profile = {
        "id": "synthetic-scan",
        "title": "Synthetic Scanned Manual",
        "edition": "2026",
        "document_type": "training-manual",
        "backend": "local-artifacts",
        "questions": ["Authorized?"],
        "printed_page_offset": 0,
        "ocr": config.to_dict(),
    }
    documents = build_documents(profile, source)

    assert documents
    assert all(document.metadata["extraction_method"] == "ocr-tesseract" for document in documents)
    assert all(document.metadata["extraction_confidence"] > 0.5 for document in documents)
    assert all(document.schema_version == "2.1" for document in documents)
