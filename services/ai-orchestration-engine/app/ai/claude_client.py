"""Thin Claude API wrapper for Ask Green PM copilot — S16-03."""
from __future__ import annotations

from typing import Optional

_DEFAULT_MODEL: str = "claude-sonnet-4-6"
_MAX_TOKENS: int = 1024
_SYSTEM_PROMPT: str = (
    "You are Ask Green PM, an AI assistant for the Green PM project management platform. "
    "You synthesize project intelligence to answer questions about risks, dependencies, "
    "forecasts, vendors, readiness, and decisions. "
    "Always respond concisely and cite the nature of the evidence informing your answer. "
    "Never reveal the names of internal engine systems."
)


class ClaudeClient:
    """Async wrapper around Anthropic Messages API for Ask Green PM — S16-03."""

    def __init__(self, api_key: str, model: str = _DEFAULT_MODEL) -> None:
        self._api_key = api_key
        self._model = model

    async def complete(
        self,
        prompt: str,
        context: Optional[str] = None,
        max_tokens: int = _MAX_TOKENS,
    ) -> str:
        """Call Claude API and return the response text.

        Raises RuntimeError wrapping the upstream exception on failure.
        """
        try:
            import anthropic

            client = anthropic.AsyncAnthropic(api_key=self._api_key)
            messages = []
            if context:
                messages.append({"role": "user", "content": context})
                messages.append({"role": "assistant", "content": "Understood."})
            messages.append({"role": "user", "content": prompt})
            response = await client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                system=_SYSTEM_PROMPT,
                messages=messages,
            )
            return response.content[0].text
        except Exception as exc:
            raise RuntimeError(f"Claude API call failed: {exc}") from exc

    @property
    def model(self) -> str:
        return self._model

    @property
    def system_prompt(self) -> str:
        return _SYSTEM_PROMPT
