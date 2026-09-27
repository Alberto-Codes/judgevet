"""Structural extension for explicitly supported image judgments.

Source: https://github.com/Alberto-Codes/judgevet/issues/203#issuecomment-5851219798.

Examples:
    ```python
    from judgevet.ports.media import MediaSystemOnePort
    from judgevet.domain.media import MediaCapabilities


    def formats(port: MediaSystemOnePort) -> MediaCapabilities:
        return port.capabilities("selected-model")
    ```

See Also:
    - [judgevet.ports][]: Existing text protocol.
    - [judgevet.media][]: Validated public dispatch.
"""

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from judgevet.domain.media import ImageEvidence, MediaCapabilities
from judgevet.domain.questions import Question
from judgevet.domain.response import SystemOneResponse
from judgevet.ports import SystemOnePort


@runtime_checkable
class MediaSystemOnePort(SystemOnePort, Protocol):
    """Provide text and image judgments without implicit media fallback.

    Attributes:
        capabilities (method): Return a static declaration for the selected model.
        system_one_media (method): Judge exact ordered evidence and bindings.
        system_one (method): Preserve the existing text operation.

    Examples:
        ```python
        def capabilities(port: MediaSystemOnePort) -> MediaCapabilities:
            return port.capabilities("selected")
        ```
    """

    def capabilities(self, model: str) -> MediaCapabilities:
        """Return static capabilities without acquisition, IO or inference.

        Args:
            model: Caller-selected model, not an inferred resolved identity.

        Returns:
            Capabilities established by the application during setup.
        """
        ...

    def system_one_media(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
        *,
        evidence: ImageEvidence,
    ) -> SystemOneResponse:
        """Judge media while preserving bytes, identities, orders and bindings.

        Args:
            state: Original caller state.
            questions: Original typed or raw question definitions.
            model: Caller-selected model.
            evidence: Immutable ordered attachment snapshot.

        Returns:
            Typed answers with provider-reported model and usage metadata.

        Raises:
            ProviderError: A declared provider failure, never a semantic answer.
        """
        ...
