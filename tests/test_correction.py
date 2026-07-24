from codebook_agent.correction import CorrectionConfig, correct_pages
from codebook_agent.models import PageText


class FakeTextProvider:
    name = "test"
    model = "test-corrector"

    def __init__(self, output: str) -> None:
        self.output = output
        self.calls: list[tuple[str, str]] = []

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return self.output


def test_model_correction_preserves_raw_ocr_and_accepts_safe_repair():
    provider = FakeTextProvider(
        "314.23(B)(1) Install the raceway within 900 mm (3 ft) of the box."
    )
    page = PageText(
        pdf_page=7,
        printed_page=4,
        text="314.23(B)(1) lnstall the raceway within 900 mm (3 ft) of the box.",
        extraction_method="ocr-tesseract",
        extraction_confidence=0.71,
    )

    corrected = correct_pages(
        [page],
        provider=provider,
        config=CorrectionConfig(mode="ocr-only", min_similarity=0.80),
    )

    assert corrected[0].text.startswith("314.23(B)(1) Install")
    assert corrected[0].raw_text == page.text
    assert corrected[0].correction_status == "accepted"
    assert corrected[0].correction_provider == "test"
    assert corrected[0].correction_model == "test-corrector"
    assert corrected[0].correction_similarity is not None
    assert provider.calls


def test_model_correction_rejects_changed_section_number():
    provider = FakeTextProvider("314.28(B)(1) Install the raceway within 900 mm (3 ft).")
    page = PageText(
        pdf_page=1,
        text="314.23(B)(1) lnstall the raceway within 900 mm (3 ft).",
        extraction_method="ocr-tesseract",
    )

    corrected = correct_pages(
        [page],
        provider=provider,
        config=CorrectionConfig(mode="ocr-only", min_similarity=0.75),
    )

    assert corrected[0].text == page.text
    assert corrected[0].raw_text == page.text
    assert corrected[0].correction_status == "rejected"
    assert "protected_tokens_changed" in corrected[0].correction_reasons


def test_ocr_only_mode_does_not_send_native_text_to_provider():
    provider = FakeTextProvider("changed")
    page = PageText(pdf_page=1, text="Native source wording.", extraction_method="native-pdf-text")

    corrected = correct_pages(
        [page],
        provider=provider,
        config=CorrectionConfig(mode="ocr-only"),
    )

    assert corrected == [page]
    assert provider.calls == []


def test_empty_model_output_is_rejected_with_reason():
    provider = FakeTextProvider("")
    page = PageText(
        pdf_page=1,
        text="Synthetic OCR wording.",
        extraction_method="ocr-tesseract",
    )

    corrected = correct_pages(
        [page],
        provider=provider,
        config=CorrectionConfig(mode="ocr-only"),
    )

    assert corrected[0].text == page.text
    assert "empty_output" in corrected[0].correction_reasons
