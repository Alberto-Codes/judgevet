"""Run the provider conformance kit against the hosted adapters offline (#272).

`HTTPSystemOneAdapter` and `AsyncHTTPSystemOneAdapter` run over
`httpx.MockTransport`, a synthetic key and a loopback base URL. The kit asks
its own questions, which the contract fixtures do not name. The transport
therefore answers each request's questions in the wire shape of contract
fixture 4 and does not replay a success body verbatim. The failing ports
replay the body of contract fixture 5 as-is. The hosted adapters declare no
media methods, so the kit's text-only media rule applies to them. The kit
skips its two media-port rules, because no hosted media port exists.
`test_off_list_choice_raises_response_error` replays contract fixture 15,
because no kit rule observes the off-list Choice check through a transport
that answers on the list.
Source: https://github.com/Alberto-Codes/judgevet/issues/272#issuecomment-5921672670.
Source: https://docs.typesafe.ai/api.md.

Examples:
    ```python
    import httpx

    from judgevet.adapters.outbound.http import HTTPSystemOneAdapter
    from tests.unit.hosted_kit_support import BASE_URL, answer_questions

    with HTTPSystemOneAdapter(
        api_key="synthetic",
        base_url=BASE_URL,
        transport=httpx.MockTransport(answer_questions),
    ) as adapter:
        adapter.system_one("Synthetic state.", {"q": {"type": "noul"}}, "m")
    ```

See Also:
    - [judgevet.testing.conformance][]: The kit rules these classes inherit
    - [judgevet.adapters.outbound.http][]: The hosted adapters under test
    - [tests.unit.hosted_kit_support][]: The mock transports and adapters
"""

from collections.abc import Iterator
from contextlib import AbstractAsyncContextManager, AbstractContextManager

import anyio
import httpx
import pytest

from judgevet.adapters.outbound.http import (
    AsyncHTTPSystemOneAdapter,
    HTTPSystemOneAdapter,
)
from judgevet.domain.errors import JevResponseError
from judgevet.providers import ProviderFactory
from judgevet.testing.conformance import (
    CONFORMANCE_MODEL,
    CONFORMANCE_QUESTIONS,
    VALID_ANSWERS,
    AsyncProviderFactory,
    BaseAsyncProviderConformance,
    BaseProviderConformance,
)
from tests.contract.fixtures import get_fixture_by_name
from tests.unit.hosted_kit_support import (
    answer_questions,
    async_adapter,
    replay,
    sync_adapter,
)

pytestmark = pytest.mark.unit


def test_handler_returns_valid_answers() -> None:
    """The sync adapter parses the handler's answers back to `VALID_ANSWERS`."""
    with sync_adapter(httpx.MockTransport(answer_questions)) as adapter:
        response = adapter.system_one(
            "Synthetic state.", CONFORMANCE_QUESTIONS, CONFORMANCE_MODEL
        )
    assert dict(response.answers) == dict(VALID_ANSWERS)
    assert response.model == CONFORMANCE_MODEL


def test_off_list_choice_raises_response_error() -> None:
    """Contract fixture 15's off-list option raises `JevResponseError`."""
    fixture = get_fixture_by_name("choice_off_list")
    request = fixture["request"]
    with (
        sync_adapter(replay("choice_off_list")) as adapter,
        pytest.raises(JevResponseError) as caught,
    ):
        adapter.system_one(request["state"], request["questions"], request["model"])
    # A contract error fixture's expect tuple is (kind, error class, status).
    expected_status = fixture["expect"][2]
    assert caught.value.status_code == expected_status


class TestHostedSyncConformance(BaseProviderConformance):
    """The kit's rules against `HTTPSystemOneAdapter` over a mock transport.

    Attributes:
        provider_factory (fixture): Builds a fresh scoped adapter per call.
        failing_port (fixture): An adapter that receives fixture 5's 401.

    Examples:
        ```python
        class TestPinnedModel(TestHostedSyncConformance):
            @pytest.fixture
            def provider_model(self):
                return "jev-1.13.0"
        ```
    """

    @pytest.fixture
    def provider_factory(self) -> ProviderFactory:
        """Supply a factory whose context is a fresh hosted adapter.

        Returns:
            A zero-argument callable returning the adapter's own context.
        """

        def build() -> AbstractContextManager[HTTPSystemOneAdapter]:
            """Build one adapter over the answering transport.

            Returns:
                The adapter, which is its own context manager.
            """
            return sync_adapter(httpx.MockTransport(answer_questions))

        return build

    @pytest.fixture
    def failing_port(self) -> Iterator[HTTPSystemOneAdapter]:
        """Supply an adapter whose every call receives fixture 5's 401.

        Yields:
            The failing adapter, closed after the test.
        """
        with sync_adapter(replay("error_401")) as adapter:
            yield adapter


class TestHostedAsyncConformance(BaseAsyncProviderConformance):
    """The async kit's rules against `AsyncHTTPSystemOneAdapter`.

    Attributes:
        provider_factory (fixture): Builds a fresh async adapter per scope.
        failing_port (fixture): An adapter that receives fixture 5's 401.

    Examples:
        ```python
        class TestPinnedModel(TestHostedAsyncConformance):
            @pytest.fixture
            def provider_model(self):
                return "jev-1.13.0"
        ```
    """

    @pytest.fixture
    def provider_factory(self) -> AsyncProviderFactory:
        """Supply a factory whose async context is a fresh hosted adapter.

        Returns:
            A zero-argument callable returning the adapter's own async context.
        """

        def build() -> AbstractAsyncContextManager[AsyncHTTPSystemOneAdapter]:
            """Build one async adapter over the answering transport.

            Returns:
                The adapter, which is its own async context manager.
            """
            return async_adapter(httpx.MockTransport(answer_questions))

        return build

    @pytest.fixture
    def failing_port(self) -> Iterator[AsyncHTTPSystemOneAdapter]:
        """Supply an async adapter whose every call receives fixture 5's 401.

        Yields:
            The failing adapter, closed after the test.
        """
        adapter = async_adapter(replay("error_401"))
        yield adapter
        anyio.run(adapter.aclose)
