"""Shared HTTP client with timeout, retry, structured logging.

Use this instead of raw `requests.get/post` — so every outbound call
is consistent, observable, and fails gracefully.
"""
from __future__ import annotations

import logging
from typing import Any

import requests

from togai.core.exceptions import (
    UpstreamBadResponseError,
    UpstreamTimeoutError,
    UpstreamUnavailableError,
)

log = logging.getLogger(__name__)

DEFAULT_UA = "BioScan/1.0 (https://togai.uz; info@togai.uz)"
DEFAULT_TIMEOUT = 12


def get_json(url: str, *, params: dict | None = None, headers: dict | None = None,
             timeout: float = DEFAULT_TIMEOUT) -> dict:
    hdrs = {"User-Agent": DEFAULT_UA, **(headers or {})}
    try:
        r = requests.get(url, params=params, headers=hdrs, timeout=timeout)
    except requests.Timeout as e:
        log.warning("timeout %s params=%s", url, params)
        raise UpstreamTimeoutError(f"{url}: timeout") from e
    except requests.RequestException as e:
        log.warning("network fail %s: %s", url, e)
        raise UpstreamUnavailableError(f"{url}: {e}") from e

    if r.status_code == 404:
        return {}
    if r.status_code >= 500:
        raise UpstreamUnavailableError(f"{url}: {r.status_code}")
    if r.status_code >= 400:
        raise UpstreamBadResponseError(f"{url}: {r.status_code}")

    try:
        return r.json()
    except ValueError as e:
        raise UpstreamBadResponseError(f"{url}: invalid JSON") from e


def post_json(url: str, payload: dict, *, headers: dict | None = None,
              timeout: float = DEFAULT_TIMEOUT) -> dict:
    hdrs = {
        "User-Agent": DEFAULT_UA,
        "Content-Type": "application/json",
        **(headers or {}),
    }
    try:
        r = requests.post(url, json=payload, headers=hdrs, timeout=timeout)
    except requests.Timeout as e:
        raise UpstreamTimeoutError(f"{url}: timeout") from e
    except requests.RequestException as e:
        raise UpstreamUnavailableError(f"{url}: {e}") from e

    if r.status_code >= 500:
        raise UpstreamUnavailableError(f"{url}: {r.status_code}")
    if r.status_code >= 400:
        raise UpstreamBadResponseError(f"{url}: {r.status_code} — {r.text[:200]}")

    try:
        return r.json()
    except ValueError as e:
        raise UpstreamBadResponseError(f"{url}: invalid JSON") from e
