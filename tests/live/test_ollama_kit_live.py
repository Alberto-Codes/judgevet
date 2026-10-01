"""Run the provider conformance kit against a local Ollama server (#267).

This module is the live twin of the offline kit run in
`tests/unit/test_hosted_kit_conformance.py`. `HTTPSystemOneAdapter` and
`AsyncHTTPSystemOneAdapter` call a real Ollama server with a placeholder key,
the model `nimble` and a 120 second read timeout. `JUDGEVET_OLLAMA_BASE_URL`
and `JUDGEVET_OLLAMA_MODEL` override the server and the model. The module
skips when the server does not answer `GET /api/version` within 5 seconds.
The failing ports call a closed loopback port, so they reach no server. The
hosted adapters declare no media methods, so the kit skips its two
media-port rules. A pass shows a compatible response shape, not equivalent
judgment.
Source: https://github.com/Alberto-Codes/judgevet/issues/267#issuecomment-5922075690.
Source: https://docs.ollama.com/api/systemone.

Examples:
    ```bash
    pytest -m live -p no:randomly -rsx -v tests/live/test_ollama_kit_live.py
    ```

See Also:
    - [judgevet.testing.conformance][]: The kit rules these classes inherit
    - [judgevet.adapters.outbound.http][]: The hosted adapters under test
    - [tests.unit.test_hosted_kit_conformance][]: The offline twin of this run
"""

import os
from collections.abc import Iterator
from contextlib import AbstractAsyncContextManager, AbstractContextManager

import anyio
import httpx
import pytest

from judgevet.adapters.outbound.http import (
    AsyncHTTPSystemOneAdapter,
    HTTPSystemOneAdapter,
)
from judgevet.adapters.outbound.retries import RetryPolicy
from judgevet.providers import ProviderFactory
from judgevet.testing._conformance_async import AsyncProviderFactory
from judgevet.testing.conformance import (
    BaseAsyncProviderConformance,
    BaseProviderConformance,
)

pytestmark = pytest.mark.live

PLACEHOLDER_KEY = "ollama"
"""The placeholder key. A local Ollama request needs no key."""

TIMEOUT_SECONDS = 120.0
"""The read timeout, long enough for the first model load."""

CLOSED_URL = "http://127.0.0.1:9"
"""A closed loopback port. Every call to it fails to connect."""


def _base_url() -> str:
    """Read the Ollama base URL from the environment.

    Returns:
        `JUDGEVET_OLLAMA_BASE_URL`, or `http://localhost:11434` when unset.
    """
    return os.environ.get("JUDGEVET_OLLAMA_BASE_URL", "http://localhost:11434")


def _model() -> str:
    """Read the Ollama model tag from the environment.

    Returns:
        `JUDGEVET_OLLAMA_MODEL`, or `nimble` when unset.
    """
    return os.environ.get("JUDGEVET_OLLAMA_MODEL", "nimble")


@pytest.fixture(scope="module", autouse=True)
def _require_ollama() -> None:
    """Skip the module when the Ollama server does not answer in 5 seconds."""
    url = f"{_base_url()}/api/version"
    try:
        httpx.get(url, timeout=5.0).raise_for_status()
    except httpx.HTTPError as error:
        pytest.skip(f"Ollama did not answer GET {url} within 5 seconds: {error}")


def _sync_adapter(
    base_url: str, retry: RetryPolicy | None = None
) -> HTTPSystemOneAdapter:
    """Build a sync hosted adapter with the placeholder key.

    Args:
        base_url: The server base URL.
        retry: The retry policy. None keeps the adapter default.

    Returns:
        The adapter.
    """
    return HTTPSystemOneAdapter(
        api_key=PLACEHOLDER_KEY,
        base_url=base_url,
        default_model=_model(),
        timeout_seconds=TIMEOUT_SECONDS,
        retry=retry,
    )


def _async_adapter(
    base_url: str, retry: RetryPolicy | None = None
) -> AsyncHTTPSystemOneAdapter:
    """Build an async hosted adapter with the placeholder key.

    Args:
        base_url: The server base URL.
        retry: The retry policy. None keeps the adapter default.

    Returns:
        The adapter.
    """
    return AsyncHTTPSystemOneAdapter(
        api_key=PLACEHOLDER_KEY,
        base_url=base_url,
        default_model=_model(),
        timeout_seconds=TIMEOUT_SECONDS,
        retry=retry,
    )


class TestOllamaSyncConformance(BaseProviderConformance):
    """The kit's rules against `HTTPSystemOneAdapter` and a local Ollama.

    Attributes:
        provider_factory (fixture): Builds a fresh adapter at the Ollama URL.
        failing_port (fixture): An adapter at a closed loopback port.
        provider_model (fixture): The Ollama model tag.

    Examples:
        ```python
        class TestTev1(TestOllamaSyncConformance):
            @pytest.fixture
            def provider_model(self):
                return "tev1"
        ```
    """

    @pytest.fixture
    def provider_factory(self) -> ProviderFactory:
        """Supply a factory whose context is a fresh Ollama adapter.

        Returns:
            A zero-argument callable returning the adapter's own context.
        """

        def build() -> AbstractContextManager[HTTPSystemOneAdapter]:
            """Build one adapter at the Ollama base URL.

            Returns:
                The adapter, which is its own context manager.
            """
            return _sync_adapter(_base_url())

        return build

    @pytest.fixture
    def failing_port(self) -> Iterator[HTTPSystemOneAdapter]:
        """Supply an adapter whose every call fails to connect.

        Yields:
            The failing adapter, closed after the test.
        """
        with _sync_adapter(CLOSED_URL, RetryPolicy(max_attempts=1)) as adapter:
            yield adapter

    @pytest.fixture
    def provider_model(self) -> str:
        """Supply the Ollama model tag.

        Returns:
            The model tag.
        """
        return _model()


class TestOllamaAsyncConformance(BaseAsyncProviderConformance):
    """The async kit's rules against `AsyncHTTPSystemOneAdapter` and Ollama.

    Attributes:
        provider_factory (fixture): Builds a fresh async adapter per scope.
        failing_port (fixture): An async adapter at a closed loopback port.
        provider_model (fixture): The Ollama model tag.

    Examples:
        ```python
        class TestTev1(TestOllamaAsyncConformance):
            @pytest.fixture
            def provider_model(self):
                return "tev1"
        ```
    """

    @pytest.fixture
    def provider_factory(self) -> AsyncProviderFactory:
        """Supply a factory whose async context is a fresh Ollama adapter.

        Returns:
            A zero-argument callable returning the adapter's own async context.
        """

        def build() -> AbstractAsyncContextManager[AsyncHTTPSystemOneAdapter]:
            """Build one async adapter at the Ollama base URL.

            Returns:
                The adapter, which is its own async context manager.
            """
            return _async_adapter(_base_url())

        return build

    @pytest.fixture
    def failing_port(self) -> Iterator[AsyncHTTPSystemOneAdapter]:
        """Supply an async adapter whose every call fails to connect.

        Yields:
            The failing adapter, closed after the test.
        """
        adapter = _async_adapter(CLOSED_URL, RetryPolicy(max_attempts=1))
        yield adapter
        anyio.run(adapter.aclose)

    @pytest.fixture
    def provider_model(self) -> str:
        """Supply the Ollama model tag.

        Returns:
            The model tag.
        """
        return _model()
