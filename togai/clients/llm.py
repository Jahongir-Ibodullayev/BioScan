"""LLM chat client — Groq-hosted text models.

Keeps prompts out of business logic — each caller provides its own system + user.
"""
from __future__ import annotations

import logging

from django.conf import settings

from togai.core.exceptions import ExternalServiceError

from ._http import post_json

log = logging.getLogger(__name__)

ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "llama-3.3-70b-versatile"


def chat(
    prompt: str,
    *,
    system: str = "",
    model: str = DEFAULT_MODEL,
    max_tokens: int = 600,
    temperature: float = 0.4,
) -> str:
    """Run an LLM chat completion. Returns the assistant text."""
    if not settings.GROQ_API_KEY:
        return "AI hozir mavjud emas."

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system or "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    try:
        data = post_json(
            ENDPOINT,
            payload,
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
            timeout=30,
        )
        return data["choices"][0]["message"]["content"].strip()
    except ExternalServiceError as e:
        log.warning("llm.chat upstream error: %s", e)
        return "Hozir javob bera olmadim. Qayta urinib ko'ring."
