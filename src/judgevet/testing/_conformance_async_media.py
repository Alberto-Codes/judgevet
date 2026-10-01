"""Observers and checks for the asynchronous media rules.

`AsyncMediaProbe` wraps an async media port, counts media dispatches and
requires `system_one_media` to return an awaitable. `refused_problem`,
`undeclared_problem` and `declared_problem` drive `async_judge_with_images`
for the three media rules. Each returns None when the provider keeps the rule,
or a failure message when it breaks it. `RuleSkipped` tells the rule to skip.
`RuleFailed` carries a failure whose cause the rule keeps.
None of these import pytest.
Source: https://github.com/Alberto-Codes/judgevet/issues/252#issuecomment-5924224316.

Examples:
    ```python
    from contextlib import nullcontext

    import anyio

    from judgevet.testing import AsyncFakeSystemOnePort
    from judgevet.testing._conformance_async_media import refused_problem

    factory = lambda: nullcontext(AsyncFakeSystemOnePort())
    assert anyio.run(refused_problem, factory, "conformance-model") is None
    ```

See Also:
    - [judgevet.testing._conformance_async][]: The rules that use these checks
    - [judgevet.testing._conformance_probes][]: The synchronous `MediaProbe`
    - [judgevet.media][]: `async_judge_with_images` and its capability checks
"""

import inspect
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from judgevet.domain.media import ImageEvidence, MediaCapabilities
from judgevet.domain.questions import Question
from judgevet.domain.response import SystemOneResponse
from judgevet.media import async_judge_with_images
from judgevet.ports.media import AsyncMediaSystemOnePort
from judgevet.providers import (
    AsyncProviderFactory,
    ProviderCapabilityError,
    ProviderError,
    async_provider_scope,
)
from judgevet.testing._conformance_cases import (
    CONFORMANCE_QUESTIONS,
    CONFORMANCE_STATE,
    policy_problem,
)
from judgevet.testing._conformance_probes import (
    MEDIA_METHODS,
    declared_evidence,
    image_evidence,
    media_members,
    undeclared_evidence,
)

MediaCheck = Callable[[AsyncMediaSystemOnePort, str], Awaitable[str | None]]
"""A check that runs against one selected async media port and model."""


class RuleSkipped(Exception):
    """Signal that a media rule does not apply to the provider.

    Examples:
        ```python
        try:
            raise RuleSkipped("The provider supplies no media port.")
        except RuleSkipped as skip:
            assert "media port" in str(skip)
        ```
    """


class RuleFailed(Exception):
    """Fail a media rule and keep the exception that broke it as the cause.

    Examples:
        ```python
        error = RuleFailed("map backend failures to a ProviderError subclass")
        assert "ProviderError" in str(error)
        ```
    """


class NotAwaitableError(Exception):
    """Signal that `system_one_media` returned a value that is not awaitable.

    Examples:
        ```python
        error = NotAwaitableError("system_one_media returned dict")
        assert "dict" in str(error)
        ```
    """


class AsyncMediaProbe:
    """Delegate every async media method and count media dispatches.

    Attributes:
        port (AsyncMediaSystemOnePort): The wrapped media port.
        media_calls (int): How many media judgments reached the port.

    Examples:
        ```python
        from judgevet.testing import AsyncFakeSystemOnePort

        probe = AsyncMediaProbe(AsyncFakeSystemOnePort())
        assert probe.media_calls == 0
        ```
    """

    def __init__(self, port: AsyncMediaSystemOnePort) -> None:
        """Wrap an async media port.

        Args:
            port: The media port to observe.
        """
        self.port = port
        self.media_calls = 0

    def capabilities(self, model: str) -> MediaCapabilities:
        """Return the wrapped port's declaration unchanged.

        Args:
            model: The selected model.

        Returns:
            The wrapped port's capabilities.
        """
        return self.port.capabilities(model)

    async def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
    ) -> SystemOneResponse:
        """Await the wrapped port's text judgment.

        Args:
            state: The content to judge.
            questions: Question names mapped to question definitions.
            model: The selected model.

        Returns:
            The wrapped port's response.
        """
        return await self.port.system_one(state, questions, model)

    async def system_one_media(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
        *,
        evidence: ImageEvidence,
    ) -> SystemOneResponse:
        """Count the media dispatch and await the wrapped port's result.

        Args:
            state: The content to judge.
            questions: Question names mapped to question definitions.
            model: The selected model.
            evidence: The ordered image evidence.

        Returns:
            The wrapped port's response.

        Raises:
            NotAwaitableError: If the wrapped method returns a value that is
                not awaitable.
        """
        self.media_calls += 1
        pending: object = self.port.system_one_media(
            state, questions, model, evidence=evidence
        )
        if not inspect.isawaitable(pending):
            raise NotAwaitableError(
                f"system_one_media returned {type(pending).__name__}, not an "
                "awaitable. Declare it async def."
            )
        return await pending


def _declaration_problem(port: object, model: str) -> str | None:
    """Describe a media port that lacks the protocol or a typed declaration.

    Args:
        port: The selected media port.
        model: The selected model.

    Returns:
        The failure message, or None when the port declares `MediaCapabilities`.
    """
    if not isinstance(port, AsyncMediaSystemOnePort):
        return f"media_port {type(port).__name__} lacks AsyncMediaSystemOnePort."
    capabilities = port.capabilities(model)
    if not isinstance(capabilities, MediaCapabilities):
        return (
            f"capabilities() returned {type(capabilities).__name__}, "
            "not MediaCapabilities."
        )
    return None


async def _on_media_port(
    factory: AsyncProviderFactory,
    media_port: AsyncMediaSystemOnePort | None,
    model: str,
    check: MediaCheck,
) -> str | None:
    """Select the media port, check its declaration, then run one check.

    Args:
        factory: The provider's factory, whose port is used without a media port.
        media_port: The dedicated media port, or None.
        model: The selected model.
        check: The rule check to run against the selected port.

    Returns:
        The failure message, or None when the port keeps the rule.

    Raises:
        RuleSkipped: If the provider supplies no media port.
    """
    if media_port is not None:
        problem = _declaration_problem(media_port, model)
        return problem if problem is not None else await check(media_port, model)
    async with async_provider_scope(factory=factory) as port:
        if not isinstance(port, AsyncMediaSystemOnePort):
            raise RuleSkipped("The provider supplies no media port.")
        problem = _declaration_problem(port, model)
        return problem if problem is not None else await check(port, model)


async def refused_problem(factory: AsyncProviderFactory, model: str) -> str | None:
    """Check that a text-only port exposes no partial media surface.

    Args:
        factory: The provider's factory.
        model: The selected model.

    Returns:
        The failure message, or None when the port keeps the rule.

    Raises:
        RuleSkipped: If the factory's port supports media.
    """
    async with async_provider_scope(factory=factory) as port:
        exposed, complete = media_members(port)
        if complete:
            raise RuleSkipped(
                "The provider port supports media; the media-port rule checks it."
            )
        if exposed:
            return (
                f"The port exposes {exposed} but not every method of "
                f"{list(MEDIA_METHODS)} as a callable, so async_judge_with_images "
                "refuses it. Implement every media method or none."
            )
        try:
            await async_judge_with_images(
                port,
                CONFORMANCE_STATE,
                CONFORMANCE_QUESTIONS,
                model,
                evidence=image_evidence("image/png"),
            )
        except ProviderCapabilityError:
            return None
        else:
            return "async_judge_with_images accepted media from a text-only port."


async def _refuses_undeclared(port: AsyncMediaSystemOnePort, model: str) -> str | None:
    """Send undeclared media and require a refusal before media dispatch.

    Args:
        port: The selected media port.
        model: The selected model.

    Returns:
        The failure message, or None when the port keeps the rule.
    """
    probe = AsyncMediaProbe(port)
    try:
        await async_judge_with_images(
            probe,
            CONFORMANCE_STATE,
            CONFORMANCE_QUESTIONS,
            model,
            evidence=undeclared_evidence(port.capabilities(model)),
        )
    except ProviderCapabilityError:
        if probe.media_calls:
            return "The media port ran before the refusal."
        return None
    else:
        return "async_judge_with_images accepted media outside the declaration."


async def _judges_declared(port: AsyncMediaSystemOnePort, model: str) -> str | None:
    """Send one declared kit image and require typed answers.

    Args:
        port: The selected media port.
        model: The selected model.

    Returns:
        The failure message, or None when the port keeps the rule.

    Raises:
        RuleSkipped: If the declaration admits no kit image.
        RuleFailed: If the call raises an exception outside `ProviderError`,
            chained to that exception.
    """
    evidence = declared_evidence(port.capabilities(model))
    if evidence is None:
        raise RuleSkipped("The media port declares no image type the kit can send.")
    try:
        response = await async_judge_with_images(
            AsyncMediaProbe(port),
            CONFORMANCE_STATE,
            CONFORMANCE_QUESTIONS,
            model,
            evidence=evidence,
        )
    except NotAwaitableError as error:
        return str(error)
    except ProviderError as error:
        return (
            f"async_judge_with_images raised {type(error).__name__} for declared "
            f"media: {error}"
        )
    except Exception as error:
        message = (
            f"async_judge_with_images raised {type(error).__name__} for declared "
            "media; map backend failures to a judgevet.providers.ProviderError "
            "subclass."
        )
        raise RuleFailed(message) from error
    return policy_problem(response, "async_judge_with_images")


async def undeclared_problem(
    factory: AsyncProviderFactory,
    media_port: AsyncMediaSystemOnePort | None,
    model: str,
) -> str | None:
    """Check that media outside the declared capabilities is refused first.

    Args:
        factory: The provider's factory.
        media_port: The dedicated media port, or None.
        model: The selected model.

    Returns:
        The failure message, or None when the port keeps the rule.
    """
    return await _on_media_port(factory, media_port, model, _refuses_undeclared)


async def declared_problem(
    factory: AsyncProviderFactory,
    media_port: AsyncMediaSystemOnePort | None,
    model: str,
) -> str | None:
    """Check that declared media reaches the port and returns typed answers.

    Args:
        factory: The provider's factory.
        media_port: The dedicated media port, or None.
        model: The selected model.

    Returns:
        The failure message, or None when the port keeps the rule.
    """
    return await _on_media_port(factory, media_port, model, _judges_declared)
