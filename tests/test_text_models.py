from types import SimpleNamespace

from codebook_agent.text_models import OpenAITextProvider


class FakeResponses:
    def __init__(self) -> None:
        self.arguments = {}

    def create(self, **kwargs):
        self.arguments = kwargs
        return SimpleNamespace(output_text="  corrected output  ")


def test_openai_adapter_uses_responses_contract_and_plain_output_text():
    responses = FakeResponses()
    provider = object.__new__(OpenAITextProvider)
    provider.model = "synthetic-model"
    provider._client = SimpleNamespace(responses=responses)

    output = provider.generate(
        system_prompt="Preserve the source.",
        user_prompt="Synthetic input.",
    )

    assert output == "corrected output"
    assert responses.arguments == {
        "model": "synthetic-model",
        "instructions": "Preserve the source.",
        "input": "Synthetic input.",
    }
