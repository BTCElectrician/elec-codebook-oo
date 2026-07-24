"""Provider-neutral text generation used by optional correction and synthesis."""

from __future__ import annotations

from typing import Protocol

DEFAULT_OPENAI_TEXT_MODEL = "gpt-5.6-terra"
TEXT_MODEL_PROVIDERS = {"openai"}


class TextModelProvider(Protocol):
    """Small boundary that keeps correction and synthesis provider-neutral."""

    name: str
    model: str

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        """Return plain text generated from the supplied instructions."""


class OpenAITextProvider:
    """OpenAI Responses API adapter, imported only after explicit opt-in."""

    name = "openai"

    def __init__(self, *, api_key: str | None, model: str = DEFAULT_OPENAI_TEXT_MODEL) -> None:
        if not api_key:
            raise ValueError("Set OPENAI_API_KEY to use OpenAI text generation.")
        try:
            from openai import OpenAI
        except ImportError as error:
            raise RuntimeError("Install the AI extra with: pip install '.[ai]'") from error
        self.model = model
        self._client = OpenAI(api_key=api_key)

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        response = self._client.responses.create(
            model=self.model,
            instructions=system_prompt,
            input=user_prompt,
        )
        output = str(response.output_text or "").strip()
        if not output:
            raise RuntimeError("The text model returned no text.")
        return output


def build_text_provider(
    provider: str,
    *,
    api_key: str | None,
    model: str | None = None,
) -> TextModelProvider:
    """Construct an explicitly selected text provider."""

    if provider != "openai":
        raise ValueError(f"Unknown text-model provider: {provider}")
    return OpenAITextProvider(
        api_key=api_key,
        model=model or DEFAULT_OPENAI_TEXT_MODEL,
    )
