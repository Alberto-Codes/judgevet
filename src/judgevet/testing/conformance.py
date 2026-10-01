"""Reusable pytest conformance tests for a `SystemOnePort` provider.

A provider package subclasses `BaseProviderConformance` in its own test suite
and overrides fixtures that supply its implementation. Each rule is one test
method, so a failure names the rule it breaks:

- `test_port_shape`: `system_one` is callable with the port's positional and
  keyword arguments.
- `test_typed_answers_pass_policy`: the kit questions receive a
  `SystemOneResponse` whose answers pass `judgevet.policy.evaluate_policy`,
  which also requires the answer type of each question kind.
- `test_failure_raises_provider_error`: the failing port raises a
  `ProviderError` subclass.
- `test_scope_entry_yields_usable_port`, `test_scope_exit_runs_once` and
  `test_scope_propagates_body_exception`: the factory keeps the
  `provider_scope` lifecycle rules.
- `test_media_refused_without_media_support`: a port without every
  `MediaSystemOnePort` method callable exposes no partial media surface, and
  `judge_with_images` refuses it with `ProviderCapabilityError`.
- `test_media_port_refuses_undeclared_media`: `judge_with_images` refuses
  media outside the declared capabilities before any media dispatch.
- `test_media_port_judges_declared_media`: `judge_with_images` sends one
  kit-owned image of a declared type to the media port and receives a
  `SystemOneResponse` whose answers pass `evaluate_policy`. Any exception
  fails the rule.

`BaseAsyncProviderConformance` applies the shape, typed-answer, failure and
scope rules to an `AsyncSystemOnePort` provider. Its scope rules use
`judgevet.providers.async_provider_scope`. The media rules are synchronous only.
Source: https://github.com/Alberto-Codes/judgevet/issues/251.
Its `provider_factory` fixture returns a `judgevet.providers.AsyncProviderFactory`.
The synchronous fixture returns a `judgevet.providers.ProviderFactory`.

The kit needs pytest, which the `conformance` extra installs. Importing this
module without pytest raises `ImportError`. The kit needs no credentials and
no inference dependency.
Source: https://github.com/Alberto-Codes/judgevet/issues/241#issuecomment-5902293909.

Examples:
    ```python
    from contextlib import nullcontext

    import pytest

    from judgevet.providers import ProviderTransportError
    from judgevet.testing import FakeSystemOnePort
    from judgevet.testing.conformance import VALID_ANSWERS, BaseProviderConformance


    class TestFakeProvider(BaseProviderConformance):
        @pytest.fixture
        def provider_factory(self):
            return lambda: nullcontext(FakeSystemOnePort(answers=VALID_ANSWERS))

        @pytest.fixture
        def failing_port(self):
            return FakeSystemOnePort(error=ProviderTransportError("offline"))
    ```

See Also:
    - [judgevet.testing][]: The offline fakes a provider can script
    - [judgevet.testing._conformance_async][]: The asynchronous rules
    - [judgevet.providers][]: `provider_scope` and the provider errors
    - [judgevet.media][]: `judge_with_images` and its capability checks
    - [judgevet.policy][]: The evaluator that accepts typed answers
"""

from collections.abc import Iterator

try:
    import pytest
except ImportError as error:
    raise ImportError(
        "judgevet.testing.conformance needs pytest; "
        "install judgevet[conformance] to use the provider conformance kit"
    ) from error

from judgevet.domain.media import MediaCapabilities
from judgevet.domain.response import SystemOneResponse
from judgevet.media import judge_with_images
from judgevet.ports import SystemOnePort
from judgevet.ports.media import MediaSystemOnePort
from judgevet.providers import (
    AsyncProviderFactory,
    ProviderCapabilityError,
    ProviderError,
    ProviderFactory,
    provider_scope,
)
from judgevet.testing._conformance_async import BaseAsyncProviderConformance
from judgevet.testing._conformance_cases import (
    CONFORMANCE_MODEL,
    CONFORMANCE_POLICY,
    CONFORMANCE_QUESTIONS,
    CONFORMANCE_STATE,
    INVALID_ANSWERS,
    VALID_ANSWERS,
    policy_problem,
)
from judgevet.testing._conformance_probes import (
    BodyError,
    MediaProbe,
    ScopeRecorder,
    declared_evidence,
    image_evidence,
    provider_error_problem,
    signature_problem,
    undeclared_evidence,
)

__all__ = [
    "CONFORMANCE_MODEL",
    "CONFORMANCE_POLICY",
    "CONFORMANCE_QUESTIONS",
    "CONFORMANCE_STATE",
    "INVALID_ANSWERS",
    "VALID_ANSWERS",
    "AsyncProviderFactory",
    "BaseAsyncProviderConformance",
    "BaseProviderConformance",
]


_MEDIA_METHODS = ("capabilities", "system_one_media")
"""The methods `judge_with_images` requires as callables on a media port."""


def _require(condition: object, message: str) -> None:
    """Fail the running test with a message when a condition is false.

    Library modules get no pytest assertion rewriting, so the kit states each
    failure message itself.

    Args:
        condition: The value that must be true.
        message: The failure message naming the broken rule.

    Raises:
        pytest.fail.Exception: If the condition is false.
    """
    if not condition:
        pytest.fail(message)


def _media_members(port: object) -> tuple[list[str], bool]:
    """Report which media methods a port exposes and whether all are callable.

    Args:
        port: The provider port.

    Returns:
        The exposed media attribute names, and whether every media method is
        present and callable.
    """
    exposed = [name for name in _MEDIA_METHODS if hasattr(port, name)]
    complete = all(callable(getattr(port, name, None)) for name in _MEDIA_METHODS)
    return exposed, complete


def _require_policy_answers(response: object, source: str) -> None:
    """Fail unless a response carries typed answers the kit policy accepts.

    `policy_problem` holds the check, which the asynchronous kit shares.

    Args:
        response: The value the provider returned.
        source: The call that produced the response, for failure messages.

    Raises:
        pytest.fail.Exception: If the response is not a `SystemOneResponse`,
            names other questions, or carries answers the policy rejects.
    """
    problem = policy_problem(response, source)
    if problem is not None:
        pytest.fail(problem)


def _select_media_port(
    provider_port: SystemOnePort, media_port: MediaSystemOnePort | None
) -> MediaSystemOnePort:
    """Choose the media port to check and require its declaration.

    Args:
        provider_port: The provider port, used when it supports media.
        media_port: The dedicated media port, or None.

    Returns:
        The media port whose `capabilities` returned `MediaCapabilities`.

    Raises:
        pytest.skip.Exception: If the provider supplies no media port.
        pytest.fail.Exception: If the media port lacks the media methods or
            its declaration is not `MediaCapabilities`.
    """
    port = media_port if media_port is not None else provider_port
    if media_port is None and not isinstance(port, MediaSystemOnePort):
        pytest.skip("The provider supplies no media port.")
    if not isinstance(port, MediaSystemOnePort):
        pytest.fail(f"media_port {type(port).__name__} lacks MediaSystemOnePort.")
    return port


def _declared_capabilities(port: MediaSystemOnePort, model: str) -> MediaCapabilities:
    """Return a media port's declaration after checking its type.

    Args:
        port: The media port.
        model: The selected model.

    Returns:
        The declared capabilities for the model.

    Raises:
        pytest.fail.Exception: If the declaration is not `MediaCapabilities`.
    """
    capabilities = port.capabilities(model)
    if not isinstance(capabilities, MediaCapabilities):
        pytest.fail(
            f"capabilities() returned {type(capabilities).__name__}, "
            "not MediaCapabilities."
        )
    return capabilities


def _raise_in_scope(factory: ProviderFactory, body: BaseException) -> None:
    """Raise an exception inside one provider scope of a factory.

    Args:
        factory: The factory whose scope receives the exception.
        body: The exception to raise inside the scope body.

    Raises:
        BaseException: The body exception, when the scope lets it propagate.
    """
    with provider_scope(factory=factory):
        raise body


def _judge(port: SystemOnePort, model: str) -> SystemOneResponse:
    """Ask the kit questions with keyword arguments.

    Args:
        port: The provider port.
        model: The selected model.

    Returns:
        The provider's response.
    """
    return port.system_one(
        state=CONFORMANCE_STATE, questions=CONFORMANCE_QUESTIONS, model=model
    )


class BaseProviderConformance:
    """Conformance rules a `SystemOnePort` provider inherits in its test suite.

    Name the subclass `Test...` so pytest collects it. Override the fixtures
    below as pytest fixtures on the subclass.

    Attributes:
        provider_factory (fixture): Required. A `ProviderFactory` whose
            context yields a working port. The kit calls it once per scope.
        provider_port (fixture): A port that answers the kit questions. The
            default enters `provider_scope(factory=provider_factory)`.
        failing_port (fixture): Required. A port configured so that every
            `system_one` call fails, such as a client of an unreachable server.
        media_port (fixture): Optional. A `MediaSystemOnePort` that both media
            port rules check. It must answer the kit questions with answers
            the kit policy accepts. The default is None, and then a
            media-capable `provider_port` is used.
        provider_model (fixture): The model label the kit passes. The default
            is `CONFORMANCE_MODEL`.

    Examples:
        ```python
        class TestMyProvider(BaseProviderConformance):
            pass
        ```
    """

    @pytest.fixture
    def provider_factory(self) -> ProviderFactory:
        """Fail until the provider supplies its factory.

        Raises:
            pytest.fail.Exception: Always.
        """
        pytest.fail("Override the provider_factory fixture with your factory.")

    @pytest.fixture
    def provider_port(
        self, provider_factory: ProviderFactory
    ) -> Iterator[SystemOnePort]:
        """Enter one scope of the provider's factory.

        Args:
            provider_factory: The provider's factory.

        Yields:
            The port the factory's context yields.
        """
        with provider_scope(factory=provider_factory) as port:
            yield port

    @pytest.fixture
    def failing_port(self) -> SystemOnePort:
        """Fail until the provider supplies a port configured to fail.

        Raises:
            pytest.fail.Exception: Always.
        """
        pytest.fail("Override the failing_port fixture with a port that fails.")

    @pytest.fixture
    def media_port(self) -> MediaSystemOnePort | None:
        """Supply no dedicated media port, so the kit checks `provider_port`."""
        return None

    @pytest.fixture
    def provider_model(self) -> str:
        """Supply the kit's default model label.

        Returns:
            The model label.
        """
        return CONFORMANCE_MODEL

    def test_port_shape(
        self, provider_port: SystemOnePort, provider_model: str
    ) -> None:
        """Rule 1: `system_one` is callable as the port declares it.

        `SystemOnePort` is not a runtime-checkable protocol, so the kit checks
        the method and its signature directly. `signature_problem` holds the
        check, which the asynchronous kit shares.

        Args:
            provider_port: The provider port.
            provider_model: The selected model.
        """
        problem = signature_problem(
            getattr(provider_port, "system_one", None), provider_model
        )
        if problem is not None:
            pytest.fail(problem)

    def test_typed_answers_pass_policy(
        self, provider_port: SystemOnePort, provider_model: str
    ) -> None:
        """Rule 2: typed answers per question kind pass the public evaluator.

        `evaluate_policy` is the enforcing check, including the answer type
        each question kind requires. A failure message also names every
        answer whose type does not match its question kind. The declared-media
        rule applies the same check to a media response.

        Args:
            provider_port: The provider port.
            provider_model: The selected model.
        """
        _require_policy_answers(_judge(provider_port, provider_model), "system_one")

    def test_failure_raises_provider_error(
        self, failing_port: SystemOnePort, provider_model: str
    ) -> None:
        """Rule 3: a failed judgment raises a `ProviderError` subclass.

        `provider_error_problem` holds the message, which the asynchronous kit
        shares.

        Args:
            failing_port: The port configured to fail.
            provider_model: The selected model.
        """
        with pytest.raises(Exception) as caught:
            _judge(failing_port, provider_model)
        problem = provider_error_problem(caught.value)
        if problem is not None:
            pytest.fail(problem)

    def test_scope_entry_yields_usable_port(
        self, provider_factory: ProviderFactory, provider_model: str
    ) -> None:
        """Rule 4: scope entry validates the port and yields one that answers.

        Args:
            provider_factory: The provider's factory.
            provider_model: The selected model.
        """
        recorder = ScopeRecorder(provider_factory)
        with provider_scope(factory=recorder) as port:
            response = _judge(port, provider_model)
        _require(
            isinstance(response, SystemOneResponse),
            f"The scoped port returned {type(response).__name__}.",
        )
        exits = [context.exits for context in recorder.contexts]
        _require(exits == [[None]], f"Expected one clean exit, observed {exits}.")

    def test_scope_exit_runs_once(self, provider_factory: ProviderFactory) -> None:
        """Rule 4: each scope gets its own context, and each exits exactly once.

        Args:
            provider_factory: The provider's factory.
        """
        recorder = ScopeRecorder(provider_factory)
        for _ in range(2):
            with provider_scope(factory=recorder):
                pass
        first, second = (context.inner for context in recorder.contexts)
        _require(
            first is not second,
            "provider_factory returned one shared context for two scopes, so its "
            "cleanup runs twice on the same resource. Construct a new context.",
        )
        observed = [(c.enters, c.exits) for c in recorder.contexts]
        _require(
            observed == [(1, [None]), (1, [None])],
            f"Expected one entry and one clean exit per scope, observed {observed}.",
        )

    def test_scope_propagates_body_exception(
        self, provider_factory: ProviderFactory
    ) -> None:
        """Rule 4: a body exception reaches the caller and exits the scope once.

        The kit also enters one context directly, as `ProviderFactory`
        callers may, and requires that its exit does not suppress the error.

        Args:
            provider_factory: The provider's factory.
        """
        body = BodyError("raised inside the provider scope")
        recorder = ScopeRecorder(provider_factory)
        with pytest.raises(BodyError) as caught:
            _raise_in_scope(recorder, body)
        _require(caught.value is body, "provider_scope replaced the body exception.")
        exits = [context.exits for context in recorder.contexts]
        _require(exits == [[body]], f"Expected one exit with the error, got {exits}.")
        direct = recorder()
        direct.__enter__()
        _require(
            not direct.__exit__(BodyError, body, None),
            "The provider context suppressed a body exception. Return a false "
            "value from __exit__ so the exception propagates.",
        )

    def test_media_refused_without_media_support(
        self, provider_port: SystemOnePort, provider_model: str
    ) -> None:
        """Rule 5: a text-only port exposes no partial media surface.

        `judge_with_images` treats a port as media-capable only when every
        `MediaSystemOnePort` method is callable. A port that exposes some of
        them, or a non-callable one, fails this rule. The library would refuse
        the media support that such a port appears to offer. A
        media-capable `provider_port` skips this rule, and
        `test_media_port_refuses_undeclared_media` checks it instead.

        Args:
            provider_port: The provider port.
            provider_model: The selected model.
        """
        exposed, complete = _media_members(provider_port)
        if complete:
            pytest.skip("provider_port supports media; the media-port rule checks it.")
        _require(
            not exposed,
            f"The port exposes {exposed} but not every method of "
            f"{list(_MEDIA_METHODS)} as a callable, so judge_with_images refuses "
            "it. Implement every media method or none.",
        )
        with pytest.raises(ProviderCapabilityError):
            judge_with_images(
                provider_port,
                CONFORMANCE_STATE,
                CONFORMANCE_QUESTIONS,
                provider_model,
                evidence=image_evidence("image/png"),
            )

    def test_media_port_refuses_undeclared_media(
        self,
        provider_port: SystemOnePort,
        media_port: MediaSystemOnePort | None,
        provider_model: str,
    ) -> None:
        """Rule 5: media outside the declared capabilities is refused first.

        The rule selects the media port and checks its declaration as the
        declared-media rule does.

        Args:
            provider_port: The provider port, used when it supports media.
            media_port: The dedicated media port, or None.
            provider_model: The selected model.
        """
        port = _select_media_port(provider_port, media_port)
        capabilities = _declared_capabilities(port, provider_model)
        probe = MediaProbe(port)
        with pytest.raises(ProviderCapabilityError):
            judge_with_images(
                probe,
                CONFORMANCE_STATE,
                CONFORMANCE_QUESTIONS,
                provider_model,
                evidence=undeclared_evidence(capabilities),
            )
        _require(probe.media_calls == 0, "The media port ran before the refusal.")

    def test_media_port_judges_declared_media(
        self,
        provider_port: SystemOnePort,
        media_port: MediaSystemOnePort | None,
        provider_model: str,
    ) -> None:
        """Rule 6: declared media reaches the port and returns typed answers.

        The kit sends one kit-owned image whose MIME type and size the port
        declares for the model. The rule skips when the declaration admits no
        kit image.

        Args:
            provider_port: The provider port, used when it supports media.
            media_port: The dedicated media port, or None.
            provider_model: The selected model.

        Raises:
            pytest.fail.Exception: If `judge_with_images` raises. A message for
                an exception outside `ProviderError` names that contract.
        """
        port = _select_media_port(provider_port, media_port)
        evidence = declared_evidence(_declared_capabilities(port, provider_model))
        if evidence is None:
            pytest.skip("The media port declares no image type the kit can send.")
        try:
            response = judge_with_images(
                port,
                CONFORMANCE_STATE,
                CONFORMANCE_QUESTIONS,
                provider_model,
                evidence=evidence,
            )
        except ProviderError as error:
            pytest.fail(
                f"judge_with_images raised {type(error).__name__} for declared "
                f"media: {error}"
            )
        except Exception as error:
            message = (
                f"judge_with_images raised {type(error).__name__} for declared "
                "media; map backend failures to a judgevet.providers.ProviderError "
                "subclass."
            )
            raise pytest.fail.Exception(message) from error
        _require_policy_answers(response, "judge_with_images")
