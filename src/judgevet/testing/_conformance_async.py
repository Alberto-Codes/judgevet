"""Reusable pytest conformance tests for an `AsyncSystemOnePort` provider.

`BaseAsyncProviderConformance` applies three rules of the synchronous kit to
an asynchronous provider:

- `test_port_shape`: `system_one` is callable with the port's positional and
  keyword arguments.
- `test_typed_answers_pass_policy`: `system_one` returns an awaitable, and
  awaiting it gives a `SystemOneResponse` whose answers pass
  `judgevet.policy.evaluate_policy`.
- `test_failure_raises_provider_error`: awaiting the failing port raises a
  `ProviderError` subclass.

The scope and media rules have no asynchronous form yet.
Source: https://github.com/Alberto-Codes/judgevet/issues/251.
Source: https://github.com/Alberto-Codes/judgevet/issues/252.

Each rule is an ordinary synchronous test method that drives its coroutine
with `anyio.run`. The kit adds no pytest plugin, because AnyIO's pytest plugin
and pytest-asyncio can both claim the same asynchronous test. anyio is a
runtime dependency of httpx, so the base install carries it.
Source: https://anyio.readthedocs.io/en/stable/testing.html.
Source: https://github.com/pytest-dev/pytest-asyncio/issues/1570.
Source: https://github.com/Alberto-Codes/judgevet/issues/246.

Examples:
    ```python
    from contextlib import nullcontext

    import pytest

    from judgevet.providers import ProviderTransportError
    from judgevet.testing import AsyncFakeSystemOnePort
    from judgevet.testing.conformance import (
        VALID_ANSWERS,
        BaseAsyncProviderConformance,
    )


    class TestAsyncFakeProvider(BaseAsyncProviderConformance):
        @pytest.fixture
        def provider_factory(self):
            return lambda: nullcontext(AsyncFakeSystemOnePort(answers=VALID_ANSWERS))

        @pytest.fixture
        def failing_port(self):
            return AsyncFakeSystemOnePort(error=ProviderTransportError("offline"))
    ```

See Also:
    - [judgevet.testing.conformance][]: The synchronous kit and the public names
    - [judgevet.testing.AsyncFakeSystemOnePort][]: The offline async fake
    - [judgevet.ports.AsyncSystemOnePort][]: The protocol the rules check
    - [judgevet.providers][]: The provider errors
"""

import inspect
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

import anyio
import pytest

from judgevet.ports import AsyncSystemOnePort
from judgevet.testing._conformance_cases import (
    CONFORMANCE_MODEL,
    CONFORMANCE_QUESTIONS,
    CONFORMANCE_STATE,
    policy_problem,
)
from judgevet.testing._conformance_probes import (
    provider_error_problem,
    signature_problem,
)

AsyncProviderFactory = Callable[[], AbstractAsyncContextManager[AsyncSystemOnePort]]
"""A zero-argument callable whose async context yields an async port."""


def _fail_on(problem: str | None) -> None:
    """Fail the running test when a shared check found a problem.

    Args:
        problem: The failure message, or None when the check passed.

    Raises:
        pytest.fail.Exception: If a problem is given.
    """
    if problem is not None:
        pytest.fail(problem)


async def _judge(port: AsyncSystemOnePort, model: str) -> object:
    """Ask the kit questions with keyword arguments and await the result.

    Args:
        port: The provider port.
        model: The selected model.

    Returns:
        The awaited value the port produced.

    Raises:
        pytest.fail.Exception: If `system_one` returns a value that is not
            awaitable.
    """
    pending: object = port.system_one(
        state=CONFORMANCE_STATE, questions=CONFORMANCE_QUESTIONS, model=model
    )
    if not inspect.isawaitable(pending):
        pytest.fail(
            f"system_one returned {type(pending).__name__}, not an awaitable. "
            "Declare it async def."
        )
    return await pending


class BaseAsyncProviderConformance:
    """Conformance rules an `AsyncSystemOnePort` provider inherits in its tests.

    Name the subclass `Test...` so pytest collects it. Override the fixtures
    below as pytest fixtures on the subclass. Each rule enters one
    `async with provider_factory()` scope inside its own `anyio.run` call.

    Attributes:
        provider_factory (fixture): Required. A zero-argument callable that
            returns an async context manager yielding a working port.
        failing_port (fixture): Required. A port configured so that every
            awaited `system_one` call fails.
        provider_model (fixture): The model label the kit passes. The default
            is `CONFORMANCE_MODEL`.

    Examples:
        ```python
        class TestMyAsyncProvider(BaseAsyncProviderConformance):
            pass
        ```
    """

    @pytest.fixture
    def provider_factory(self) -> AsyncProviderFactory:
        """Fail until the provider supplies its factory.

        Raises:
            pytest.fail.Exception: Always.
        """
        pytest.fail("Override the provider_factory fixture with your factory.")

    @pytest.fixture
    def failing_port(self) -> AsyncSystemOnePort:
        """Fail until the provider supplies a port configured to fail.

        Raises:
            pytest.fail.Exception: Always.
        """
        pytest.fail("Override the failing_port fixture with a port that fails.")

    @pytest.fixture
    def provider_model(self) -> str:
        """Supply the kit's default model label.

        Returns:
            The model label.
        """
        return CONFORMANCE_MODEL

    def test_port_shape(
        self, provider_factory: AsyncProviderFactory, provider_model: str
    ) -> None:
        """Rule 1: `system_one` is callable as the port declares it.

        Args:
            provider_factory: The provider's factory.
            provider_model: The selected model.
        """

        async def check() -> str | None:
            """Enter one scope and check the yielded port's method.

            Returns:
                The signature failure message, or None.
            """
            async with provider_factory() as port:
                method = getattr(port, "system_one", None)
                return signature_problem(method, provider_model)

        _fail_on(anyio.run(check))

    def test_typed_answers_pass_policy(
        self, provider_factory: AsyncProviderFactory, provider_model: str
    ) -> None:
        """Rule 2: awaited typed answers per question kind pass the evaluator.

        A `system_one` that returns a value that is not awaitable fails this
        rule. A failure message also names every answer whose type does not
        match its question kind.

        Args:
            provider_factory: The provider's factory.
            provider_model: The selected model.
        """

        async def judge() -> object:
            """Enter one scope and await one judgment.

            Returns:
                The awaited value the port produced.
            """
            async with provider_factory() as port:
                return await _judge(port, provider_model)

        _fail_on(policy_problem(anyio.run(judge), "system_one"))

    def test_failure_raises_provider_error(
        self, failing_port: AsyncSystemOnePort, provider_model: str
    ) -> None:
        """Rule 3: an awaited failed judgment raises a `ProviderError` subclass.

        Args:
            failing_port: The port configured to fail.
            provider_model: The selected model.
        """
        with pytest.raises(Exception) as caught:
            anyio.run(_judge, failing_port, provider_model)
        _fail_on(provider_error_problem(caught.value))
