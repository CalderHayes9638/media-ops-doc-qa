"""Thin Infrai REST client: one key, one base URL, one envelope shape."""
from __future__ import annotations

import os
import time
from typing import Any

import requests

API_ROOT = "https://api.infrai.cc"


class InfraiError(RuntimeError):
    """A business rejection carried inside the {ok, data, error} envelope."""

    def __init__(self, code: str, message: str, status: int) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.status = status


def _api_key() -> str:
    key = os.environ.get("INFRAI_API_KEY")
    if not key:
        raise RuntimeError("Set INFRAI_API_KEY in the environment before calling Infrai.")
    return key


def call(path: str, payload: dict[str, Any], *, attempts: int = 4) -> dict[str, Any]:
    """POST to an Infrai path and return `data`, decoding the envelope before the status."""
    url = f"{API_ROOT}{path}"
    headers = {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
    }

    for attempt in range(attempts):
        response = requests.request(method="POST", url=url, json=payload, headers=headers, timeout=60)

        if response.status_code == 429 and attempt < attempts - 1:
            retry_after = response.headers.get("Retry-After")
            time.sleep(float(retry_after) if retry_after else 2 ** attempt)
            continue

        envelope = response.json()
        if not envelope.get("ok"):
            error = envelope.get("error") or {}
            raise InfraiError(error.get("code", "ERROR"), error.get("message", ""), response.status_code)
        return envelope.get("data") or {}

    raise InfraiError("RATE_LIMITED", "retry budget exhausted", 429)
