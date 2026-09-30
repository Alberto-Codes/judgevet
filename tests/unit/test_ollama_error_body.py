"""Prove an Ollama `{"error": ...}` body reaches the raised message (#268).

Ollama returns error bodies as `{"error": "<string>"}` and rejects an
oversized body with 413 and `request body must not exceed 64 KiB`.
See: https://docs.ollama.com/api/systemone

Examples:
    ```bash
    uv run pytest tests/unit/test_ollama_error_body.py -q
    ```

See Also:
    - [judgevet.adapters.outbound.http][]: The adapter under test.
"""

import asyncio

import httpx
import pytest

from judgevet.adapters.outbound.http import (
    AsyncHTTPSystemOneAdapter,
    HTTPSystemOneAdapter,
)
from judgevet.domain.errors import JevRequestError

OLLAMA_413_TEXT = "request body must not exceed 64 KiB"
QUESTIONS = {"q": {"type": "noul"}}
STATE = "Synthetic state."


def reply_413(request: httpx.Request) -> httpx.Response:
    """Return Ollama's documented 413 body for every request.

    Args:
        request: The outgoing request, unused.

    Returns:
        A 413 response carrying a string `error` field.
    """
    return httpx.Response(413, json={"error": OLLAMA_413_TEXT})


@pytest.mark.unit
def test_sync_adapter_surfaces_ollama_error_text() -> None:
    """The sync adapter appends the `error` string after the httpx message."""
    adapter = HTTPSystemOneAdapter(
        api_key="synthetic", transport=httpx.MockTransport(reply_413)
    )
    with pytest.raises(JevRequestError) as caught:
        adapter.system_one(STATE, QUESTIONS, "nimble")
    assert OLLAMA_413_TEXT in str(caught.value)
    assert "413" in str(caught.value)
    assert caught.value.status_code == 413


@pytest.mark.unit
def test_async_adapter_surfaces_ollama_error_text() -> None:
    """The async adapter appends the `error` string after the httpx message."""

    async def call() -> None:
        """Run one failing judgment on a scoped async adapter."""
        async with AsyncHTTPSystemOneAdapter(
            api_key="synthetic", transport=httpx.MockTransport(reply_413)
        ) as adapter:
            await adapter.system_one(STATE, QUESTIONS, "nimble")

    with pytest.raises(JevRequestError) as caught:
        asyncio.run(call())
    assert OLLAMA_413_TEXT in str(caught.value)
    assert caught.value.status_code == 413
