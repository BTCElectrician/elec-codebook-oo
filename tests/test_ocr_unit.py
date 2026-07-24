import sys
from types import ModuleType

from codebook_agent import core
from codebook_agent.ocr import OCRConfig, _parse_tesseract_tsv

TSV_HEADER = (
    "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\t"
    "width\theight\tconf\ttext\n"
)


def test_tesseract_tsv_treats_quote_as_text_not_csv_syntax():
    raw = (
        TSV_HEADER
        + '5\t1\t1\t1\t1\t1\t0\t0\t1\t1\t95\t"quoted\n'
        + "5\t1\t1\t1\t1\t2\t0\t0\t1\t1\t90\tnext\n"
    )

    text, confidence = _parse_tesseract_tsv(raw)

    assert text == '"quoted next'
    assert confidence == 0.925


def test_auto_mode_does_not_initialize_ocr_when_native_pdf_text_is_usable(
    tmp_path,
    monkeypatch,
):
    source = tmp_path / "native-text.pdf"
    source.write_bytes(b"%PDF-synthetic-test")

    class FakePage:
        @staticmethod
        def extract_text():
            return "This native PDF text is complete enough that OCR is unnecessary."

    class FakeReader:
        def __init__(self, path):
            assert path == str(source)
            self.pages = [FakePage()]

    fake_pypdf = ModuleType("pypdf")
    fake_pypdf.PdfReader = FakeReader
    monkeypatch.setitem(sys.modules, "pypdf", fake_pypdf)

    class FailIfConstructed:
        def __init__(self, config):
            raise AssertionError(f"OCR should not be initialized: {config}")

    monkeypatch.setattr(core, "TesseractOCR", FailIfConstructed)

    pages = core.extract_pages(
        source,
        ocr=OCRConfig(mode="auto", min_native_characters=20),
    )

    assert len(pages) == 1
    assert pages[0].extraction_method == "native-pdf-text"
