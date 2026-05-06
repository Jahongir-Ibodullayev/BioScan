"""LLM chat client — OpenRouter (asosiy) yoki Groq (fallback).

Keeps prompts out of business logic — each caller provides its own system + user.
"""
from __future__ import annotations

import logging

from togai.core.exceptions import ExternalServiceError
from togai.integrations import ai_has_key, ai_provider, chat_model

from ._http import post_json

log = logging.getLogger(__name__)


def chat(
    prompt: str,
    *,
    system: str = "",
    model: str = "",
    max_tokens: int = 600,
    temperature: float = 0.4,
) -> str:
    """Run an LLM chat completion. Returns the assistant text."""
    if not ai_has_key():
        return "AI hozir mavjud emas."

    base_url, api_key, extra_headers = ai_provider()
    if not model:
        model = chat_model()

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
            f"{base_url}/chat/completions",
            payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                **extra_headers,
            },
            timeout=30,
        )
        return data["choices"][0]["message"]["content"].strip()
    except ExternalServiceError as e:
        log.warning("llm.chat upstream error: %s", e)
        return "Hozir javob berolmaadim iltimos keyinroq urini "
