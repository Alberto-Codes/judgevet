"""Structural ports for providers that take a provider-options mapping.

A provider declares that it takes options by adding a keyword-only
`provider_options` parameter to its judgment methods. judgevet forwards the
caller's mapping unchanged and never interprets its keys. A provider without
the parameter still satisfies the existing ports.
Source: https://github.com/Alberto-Codes/judgevet/issues/281.

Examples:
    ```python
    from collections.abc import Mapping
    from typing import Any

    from judgevet.domain.answers import NoulAnswer
    from judgevet.domain.questions import Question
    from judgevet.domain.response import SystemOneResponse
    from judgevet.domain.usage import Usage
    from judgevet.ports.options import ProviderOptionsSystemOnePort


    class ThresholdProvider:
        def system_one(
            self,
            state: str | dict[str, Any] | list[Any],
            questions: Mapping[str, Question | Mapping[str, Any]],
            model: str,
            *,
            provider_options: Mapping[str, object] | None = None,
        ) -> SystemOneResponse:
            return SystemOneResponse(
                model=model,
                usage=Usage(0, 0),
                answers={name: NoulAnswer(0.5) for name in questions},
            )


    port: ProviderOptionsSystemOnePort = ThresholdProvider()
    response = port.system_one(
        "state", {"q": {"type": "noul"}}, "m", provider_options={"k": 1}
    )
    assert response.receipts == {}
    ```

See Also:
    - [judgevet.ports][]: The text ports these extend.
    - [judgevet.ports.media][]: The media ports these extend.
    - [judgevet.media][]: The judge entry that forwards the options.
"""

from collections.abc import Mapping
from typing import Any, Protocol

from judgevet.domain.media import ImageEvidence
from judgevet.domain.questions import Question
from judgevet.domain.response import SystemOneResponse
from judgevet.ports import AsyncSystemOnePort, SystemOnePort
from judgevet.ports.media import AsyncMediaSystemOnePort, MediaSystemOnePort


class ProviderOptionsSystemOnePort(SystemOnePort, Protocol):
    """Take a provider-options mapping on the text judgment.

    Attributes:
        system_one (method): Judge text with optional provider options.

    Examples:
        ```python
        def judge(port: ProviderOptionsSystemOnePort):
            return port.system_one("s", {}, "m", provider_options={"k": 1})
        ```
    """

    def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
        *,
        provider_options: Mapping[str, object] | None = None,
    ) -> SystemOneResponse:
        """Judge text with an optional mapping the provider interprets.

        Args:
            state: The content to evaluate.
            questions: Mapping of question names to question definitions.
            model: Caller-selected model.
            provider_options: Provider-defined settings, or None for none.

        Returns:
            Typed answers, with any provider receipts.
        """
        ...


class AsyncProviderOptionsSystemOnePort(AsyncSystemOnePort, Protocol):
    """Take a provider-options mapping on the awaited text judgment.

    Attributes:
        system_one (method): Judge text with optional provider options.

    Examples:
        ```python
        async def judge(port: AsyncProviderOptionsSystemOnePort):
            return await port.system_one("s", {}, "m", provider_options={"k": 1})
        ```
    """

    async def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
        *,
        provider_options: Mapping[str, object] | None = None,
    ) -> SystemOneResponse:
        """Judge text with an optional mapping the provider interprets.

        Args:
            state: The content to evaluate.
            questions: Mapping of question names to question definitions.
            model: Caller-selected model.
            provider_options: Provider-defined settings, or None for none.

        Returns:
            Typed answers, with any provider receipts.
        """
        ...


class ProviderOptionsMediaSystemOnePort(MediaSystemOnePort, Protocol):
    """Take a provider-options mapping on the text and media judgments.

    Attributes:
        system_one (method): Judge text with optional provider options.
        system_one_media (method): Judge media with optional provider options.

    Examples:
        ```python
        def judge(port: ProviderOptionsMediaSystemOnePort, evidence):
            return port.system_one_media(
                "s", {}, "m", evidence=evidence, provider_options={"k": 1}
            )
        ```
    """

    def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
        *,
        provider_options: Mapping[str, object] | None = None,
    ) -> SystemOneResponse:
        """Judge text with an optional mapping the provider interprets.

        Args:
            state: The content to evaluate.
            questions: Mapping of question names to question definitions.
            model: Caller-selected model.
            provider_options: Provider-defined settings, or None for none.

        Returns:
            Typed answers, with any provider receipts.
        """
        ...

    def system_one_media(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
        *,
        evidence: ImageEvidence,
        provider_options: Mapping[str, object] | None = None,
    ) -> SystemOneResponse:
        """Judge media with an optional mapping the provider interprets.

        Args:
            state: Original caller state.
            questions: Original typed or raw question definitions.
            model: Caller-selected model.
            evidence: Immutable ordered attachment snapshot.
            provider_options: Provider-defined settings, or None for none.

        Returns:
            Typed answers, with any provider receipts.
        """
        ...


class AsyncProviderOptionsMediaSystemOnePort(AsyncMediaSystemOnePort, Protocol):
    """Take a provider-options mapping on the awaited text and media judgments.

    Attributes:
        system_one (method): Judge text with optional provider options.
        system_one_media (method): Judge media with optional provider options.

    Examples:
        ```python
        async def judge(port: AsyncProviderOptionsMediaSystemOnePort, evidence):
            return await port.system_one_media(
                "s", {}, "m", evidence=evidence, provider_options={"k": 1}
            )
        ```
    """

    async def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
        *,
        provider_options: Mapping[str, object] | None = None,
    ) -> SystemOneResponse:
        """Judge text with an optional mapping the provider interprets.

        Args:
            state: The content to evaluate.
            questions: Mapping of question names to question definitions.
            model: Caller-selected model.
            provider_options: Provider-defined settings, or None for none.

        Returns:
            Typed answers, with any provider receipts.
        """
        ...

    async def system_one_media(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
        *,
        evidence: ImageEvidence,
        provider_options: Mapping[str, object] | None = None,
    ) -> SystemOneResponse:
        """Judge media with an optional mapping the provider interprets.

        Args:
            state: Original caller state.
            questions: Original typed or raw question definitions.
            model: Caller-selected model.
            evidence: Immutable ordered attachment snapshot.
            provider_options: Provider-defined settings, or None for none.

        Returns:
            Typed answers, with any provider receipts.
        """
        ...
