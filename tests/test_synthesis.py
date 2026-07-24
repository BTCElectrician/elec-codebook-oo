from codebook_agent.answers import synthesize_answer
from codebook_agent.models import CodebookDocument, SearchResult


class FakeTextProvider:
    name = "test"
    model = "test-synthesizer"

    def __init__(self, output: str) -> None:
        self.output = output
        self.calls: list[tuple[str, str]] = []

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return self.output


def _result() -> SearchResult:
    return SearchResult(
        document=CodebookDocument(
            id="doc-1",
            corpus_id="synthetic",
            source_name="manual.txt",
            source_sha256="abc",
            chunk_number=1,
            content="The invented training disconnect must be within sight.",
            search_text="training disconnect within sight",
            content_type="main",
            pdf_page_start=7,
            pdf_page_end=7,
            printed_page_start=4,
            printed_page_end=4,
            section_number="4.1",
        ),
        score=0.5,
    )


def test_synthesized_answer_accepts_only_known_evidence_citations():
    provider = FakeTextProvider(
        "The invented training disconnect must be within sight. [S1]"
    )

    answer = synthesize_answer(
        "Where must the disconnect be?",
        [_result()],
        provider=provider,
    )

    assert answer.mode == "synthesized"
    assert answer.metadata["citation_validation"] == "passed"
    assert answer.metadata["provider"] == "test"
    assert answer.sources[0].document.id == "doc-1"
    assert provider.calls
    assert "[S1]" in provider.calls[0][1]


def test_synthesized_answer_falls_back_when_model_uses_unknown_citation():
    provider = FakeTextProvider("The disconnect can be anywhere. [S9]")

    answer = synthesize_answer(
        "Where must the disconnect be?",
        [_result()],
        provider=provider,
    )

    assert answer.mode == "extractive"
    assert answer.metadata["requested_mode"] == "synthesized"
    assert answer.metadata["fallback_reason"] == "invalid_citations"
    assert "within sight" in answer.text


def test_synthesized_answer_falls_back_when_model_omits_citations():
    provider = FakeTextProvider("The invented training disconnect must be within sight.")

    answer = synthesize_answer(
        "Where must the disconnect be?",
        [_result()],
        provider=provider,
    )

    assert answer.mode == "extractive"
    assert answer.metadata["fallback_reason"] == "missing_citations"
