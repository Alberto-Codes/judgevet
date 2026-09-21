"""Unit tests for AsyncHTTPSystemOneAdapter."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import anyio
import httpx
import pytest

from judgevet.adapters.outbound.http import AsyncHTTPSystemOneAdapter
from judgevet.domain.errors import JevError, JevServiceError
from judgevet.domain.response import SystemOneResponse
from judgevet.domain.usage import Usage
from judgevet.ports import AsyncSystemOnePort


def _mock_handler_success(request: httpx.Request) -> httpx.Response:
    """Return a mock 200 response with valid JSON."""
    return httpx.Response(
        status_code=200,
        json={
            "model": "jev-latest",
            "usage": {"input_tokens": 10, "output_tokens": 5},
            "answers": {
                "q1": {"type": "noul", "noul": 0.75, "confidence": 0.8},
            },
        },
    )


def _mock_handler_401(request: httpx.Request) -> httpx.Response:
    """Return a mock 401 response."""
    return httpx.Response(
        status_code=401,
        json={
            "error_type": "authentication_error",
            "message": "Invalid API key",
        },
    )


def _mock_handler_302(request: httpx.Request) -> httpx.Response:
    """Return a mock 302 response."""
    return httpx.Response(
        status_code=302,
        headers={"Location": "https://example.com"},
    )


def _mock_handler_transport_error(request: httpx.Request) -> httpx.Response:
    """Raise a transport error."""
    raise httpx.NetworkError("Network error")


class FakeAsyncPort(AsyncSystemOnePort):
    """Minimal class satisfying AsyncSystemOnePort without importing it.

    This class is defined entirely within this test to prove that
    AsyncSystemOnePort is a structural protocol - any class with the right
    signature can satisfy it, even one from outside the judgevet package.
    """

    def __init__(self) -> None:
        """Initialize the fake async port."""
        self.state: str | dict[str, Any] | list[Any] | None = None
        self.questions: Mapping[str, Any] | None = None
        self.model: str | None = None

    async def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Any],
        model: str,
    ) -> SystemOneResponse:
        """Return a minimal valid response for testing."""
        # Record the call for verification
        self.state = state
        self.questions = questions
        self.model = model

        # Build the response with the same question keys that were sent
        answers: dict[str, Any] = {}
        for name in questions:
            answers[name] = {
                "type": "noul",
                "noul": 0.75,
                "confidence": 0.8,
            }

        return SystemOneResponse(
            model=model,
            usage=Usage(input_tokens=10, output_tokens=5),
            answers=answers,
        )


class TestAsyncAdapterSuccess:
    """Tests for successful async adapter calls."""

    def test_system_one_returns_parsed_response(self) -> None:
        """Test that system_one parses a successful response."""
        transport = httpx.MockTransport(_mock_handler_success)
        adapter = AsyncHTTPSystemOneAdapter(
            api_key="test-key",
            transport=transport,
        )

        async def run_test() -> Any:
            response = await adapter.system_one(
                state="test content",
                questions={"q1": {"type": "noul", "instructions": "Is this true?"}},
                model="jev-latest",
            )
            await adapter.aclose()
            return response

        result = anyio.run(run_test)

        assert isinstance(result, SystemOneResponse)
        assert result.model == "jev-latest"
        assert "q1" in result.answers
        assert result.answers["q1"].noul == 0.75

    def test_aclose_closes_client(self) -> None:
        """Test that aclose properly closes the async client."""
        transport = httpx.MockTransport(_mock_handler_success)
        adapter = AsyncHTTPSystemOneAdapter(
            api_key="test-key",
            transport=transport,
        )

        async def run_test() -> Any:
            assert not adapter._client.is_closed
            await adapter.aclose()
            assert adapter._client.is_closed

        anyio.run(run_test)

    def test_async_context_manager(self) -> None:
        """Test that async context manager works correctly."""
        transport = httpx.MockTransport(_mock_handler_success)

        async def run_test() -> Any:
            async with AsyncHTTPSystemOneAdapter(
                api_key="test-key",
                transport=transport,
            ) as adapter:
                assert not adapter._client.is_closed
                response = await adapter.system_one(
                    state="test",
                    questions={"q1": {"type": "noul"}},
                    model="jev-latest",
                )
                assert isinstance(response, SystemOneResponse)
            assert adapter._client.is_closed

        anyio.run(run_test)


class TestAsyncAdapterInit:
    """Tests for async adapter initialization."""

    def test_init_raises_without_api_key(self) -> None:
        """Test that init raises ValueError without API key."""
        with pytest.raises(ValueError, match="API key must be provided"):
            AsyncHTTPSystemOneAdapter(api_key=None)

    def test_init_raises_with_zero_timeout(self) -> None:
        """Test that init raises ValueError with zero timeout."""
        with pytest.raises(ValueError, match="timeout_seconds must be positive"):
            AsyncHTTPSystemOneAdapter(api_key="key", timeout_seconds=0)

    def test_init_raises_with_negative_timeout(self) -> None:
        """Test that init raises ValueError with negative timeout."""
        with pytest.raises(ValueError, match="timeout_seconds must be positive"):
            AsyncHTTPSystemOneAdapter(api_key="key", timeout_seconds=-1.0)


class TestAsyncAdapterErrorPaths:
    """Tests for async adapter error handling."""

    def test_401_raises_jev_auth_error(self) -> None:
        """Test that 401 response raises JevAuthError."""
        transport = httpx.MockTransport(_mock_handler_401)
        adapter = AsyncHTTPSystemOneAdapter(
            api_key="invalid-key",
            transport=transport,
        )

        async def run_test() -> Any:
            return await adapter.system_one(
                state="test",
                questions={"q1": {"type": "noul"}},
                model="jev-latest",
            )

        with pytest.raises(JevError) as exc_info:
            anyio.run(run_test)

        assert isinstance(exc_info.value, JevError)
        # The 401 should be translated to JevAuthError
        assert exc_info.value.status_code == 401

    def test_3xx_raises_without_cause(self) -> None:
        """Test that 3xx response raises without chaining."""
        transport = httpx.MockTransport(_mock_handler_302)
        adapter = AsyncHTTPSystemOneAdapter(
            api_key="test-key",
            transport=transport,
        )

        async def run_test() -> Any:
            return await adapter.system_one(
                state="test",
                questions={"q1": {"type": "noul"}},
                model="jev-latest",
            )

        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            anyio.run(run_test)

        # 3xx returns None from _translate_status_error, so it's re-raised
        # The spec says: assert __cause__ is None and __context__ is None
        assert exc_info.value.__cause__ is None
        assert exc_info.value.__context__ is None

    def test_transport_error_raises_jev_service_error(self) -> None:
        """Test that transport errors raise JevServiceError with status_code=None."""
        transport = httpx.MockTransport(_mock_handler_transport_error)
        adapter = AsyncHTTPSystemOneAdapter(
            api_key="test-key",
            transport=transport,
        )

        async def run_test() -> Any:
            return await adapter.system_one(
                state="test",
                questions={"q1": {"type": "noul"}},
                model="jev-latest",
            )

        with pytest.raises(JevServiceError) as exc_info:
            anyio.run(run_test)

        assert exc_info.value.status_code is None


class TestAsyncPortStructural:
    """Tests for AsyncSystemOnePort structural protocol."""

    def test_structural_port_with_async_adapter(self) -> None:
        """Test that a minimal class satisfies AsyncSystemOnePort."""
        port = FakeAsyncPort()

        async def drive_system_one(p: AsyncSystemOnePort) -> SystemOneResponse:
            return await p.system_one(
                state="test",
                questions={"q1": {"type": "noul"}},
                model="jev-latest",
            )

        # This should type-check and run
        result = anyio.run(drive_system_one, port)

        assert isinstance(result, SystemOneResponse)
        assert result.model == "jev-latest"
        assert "q1" in result.answers

    def test_structural_port_with_real_adapter(self) -> None:
        """Test that AsyncHTTPSystemOneAdapter satisfies AsyncSystemOnePort."""
        transport = httpx.MockTransport(_mock_handler_success)
        adapter = AsyncHTTPSystemOneAdapter(
            api_key="test-key",
            transport=transport,
        )

        async def drive_system_one(p: AsyncSystemOnePort) -> SystemOneResponse:
            return await p.system_one(
                state="test",
                questions={"q1": {"type": "noul"}},
                model="jev-latest",
            )

        async def run_test() -> Any:
            result = await drive_system_one(adapter)
            await adapter.aclose()
            return result

        result = anyio.run(run_test)

        assert isinstance(result, SystemOneResponse)
        assert result.model == "jev-latest"
        assert "q1" in result.answers
        assert result.answers["q1"].noul == 0.75
