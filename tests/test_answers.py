from codebook_agent.answers import answer_from_results
from codebook_agent.models import CodebookDocument, SearchResult


def test_extractive_answer_exposes_exact_source_and_page():
    document = CodebookDocument(
        id="doc-1",
        corpus_id="synthetic",
        source_name="manual.txt",
        source_sha256="abc",
        chunk_number=1,
        content="Use the invented training value only.",
        search_text="training value",
        content_type="main",
        pdf_page_start=7,
        pdf_page_end=7,
        printed_page_start=4,
        printed_page_end=4,
        article_number="2",
        section_number="2.1",
    )

    answer = answer_from_results(
        "What is the training value?",
        [SearchResult(document=document, score=0.5)],
    )

    assert "Use the invented training value only." in answer.text
    assert "PDF page 7" in answer.text
    assert "printed page 4" in answer.text
    assert answer.to_dict()["sources"][0]["document"]["id"] == "doc-1"
