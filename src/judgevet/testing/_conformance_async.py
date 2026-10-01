"""Reusable pytest conformance tests for an `AsyncSystemOnePort` provider.

`BaseAsyncProviderConformance` applies six rules of the synchronous kit to
an asynchronous provider:

- `test_port_shape`: `system_one` is callable with the port's positional and
  keyword arguments.
- `test_typed_answers_pass_policy`: `system_one` returns an awaitable, and
  awaiting it gives a `SystemOneResponse` whose answers pass
  `judgevet.policy.evaluate_policy`.
- `test_failure_raises_provider_error`: awaiting the failing port raises a
  `ProviderError` subclass.
- `test_scope_entry_yields_usable_port`, `test_scope_exit_runs_once` and
  `test_scope_propagates_body_exception`: the factory keeps the
  `async_provider_scope` lifecycle rules.

Source: https://github.com/Alberto-Codes/judgevet/issues/251.
The media rules have no asynchronous form yet.
Source: https://github.com/Alberto-Codes/judgevet/issues/252.

Each rule is an ordinary synchronous test method that drives its coroutine
with `anyio.run`. The kit adds no pytest plugin, because AnyIO's pytest plugin
and pytest-asyncio interfere when both are installed.
Source: https://anyio.readthedocs.io/en/stable/testing.html.
Source: https://github.com/agronholm/anyio/issues/328.
Source: https://github.com/Alberto-Codes/judgevet/issues/246.

The kit's fixtures are synchronous. pytest-asyncio's auto mode runs a
synchronous test that requests an asynchronous fixture, and its strict mode
refuses one.
Source: https://github.com/pytest-dev/pytest-asyncio/issues/1570.

The kit imports anyio directly, so the `conformance` extra declares it beside
pytest.
Source: https://github.com/Alberto-Codes/judgevet/issues/253#issuecomment-5904100904.

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
    - [judgevet.testing._conformance_async_scope][]: The scope rule checks
    - [judgevet.providers][]: `async_provider_scope` and the provider errors
"""

import inspect

import anyio
import pytest

from judgevet.domain.response import SystemOneResponse
from judgevet.ports import AsyncSystemOnePort
from judgevet.providers import AsyncProviderFactory, async_provider_scope
from judgevet.testing._conformance_async_scope import (
    AsyncScopeRecorder,
    body_problem,
    exit_problem,
)
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
    `async with provider_factory()` scope inside its own `anyio.run` call. The
    scope rules enter it through `async_provider_scope` and record each
    context the factory constructs.

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

    def test_scope_entry_yields_usable_port(
        self, provider_factory: AsyncProviderFactory, provider_model: str
    ) -> None:
        """Rule 4: scope entry validates the port and yields one that answers.

        Args:
            provider_factory: The provider's factory.
            provider_model: The selected model.
        """
        recorder = AsyncScopeRecorder(provider_factory)

        async def judge() -> object:
            """Enter one validated scope and await one judgment.

            Returns:
                The awaited value the port produced.
            """
            async with async_provider_scope(factory=recorder) as port:
                return await _judge(port, provider_model)

        response = anyio.run(judge)
        if not isinstance(response, SystemOneResponse):
            pytest.fail(f"The scoped port returned {type(response).__name__}.")
        exits = [context.exits for context in recorder.contexts]
        if exits != [[None]]:
            pytest.fail(f"Expected one clean exit, observed {exits}.")

    def test_scope_exit_runs_once(self, provider_factory: AsyncProviderFactory) -> None:
        """Rule 4: each scope gets its own context, and each exits exactly once.

        Args:
            provider_factory: The provider's factory.
        """
        _fail_on(anyio.run(exit_problem, provider_factory))

    def test_scope_propagates_body_exception(
        self, provider_factory: AsyncProviderFactory
    ) -> None:
        """Rule 4: a body exception reaches the caller and exits the scope once.

        The kit also enters one context directly, as `AsyncProviderFactory`
        callers may, and requires that its exit does not suppress the error.

        Args:
            provider_factory: The provider's factory.
        """
        _fail_on(anyio.run(body_problem, provider_factory))
