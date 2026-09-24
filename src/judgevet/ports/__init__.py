"""Ports for judgment calls and caller-owned state transformation.

Examples:
    ```python
    from judgevet.ports import SystemOnePort
    from judgevet.domain.questions import Noul
    from judgevet.domain.response import SystemOneResponse


    def call_api(port: SystemOnePort) -> SystemOneResponse:
        return port.system_one(
            state="content",
            questions={"q1": Noul(instructions="Question?")},
            model="jev-latest",
        )
    ```

See Also:
    - [judgevet.adapters.outbound.http][]: HTTP adapter implementation

Attributes:
    AsyncSystemOnePort (Protocol): Async structural protocol for calling the Jev System One API.
    SystemOnePort (Protocol): Structural protocol for calling the Jev System One API.
    StateRedactor (Protocol): Synchronous state transformation before HTTP serialization.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from judgevet.domain.questions import Question
from judgevet.domain.response import SystemOneResponse


class SystemOnePort(Protocol):
    """Protocol for calling the Jev System One API.

    Attributes:
        system_one (method): Method to call the Jev System One API.

    Examples:
        ```python
        from judgevet.ports import SystemOnePort
        from judgevet.domain.response import SystemOneResponse


        def call_api(port: SystemOnePort) -> SystemOneResponse:
            return port.system_one(
                state="content",
                questions={"q1": {"type": "noul"}},
                model="jev-latest",
            )
        ```

    See Also:
        - [judgevet.adapters.outbound.http][]: HTTP adapter implementation
    """

    def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
    ) -> SystemOneResponse:
        """Call the Jev System One API.

        Args:
            state: The content to evaluate (text, JSON object, or array).
            questions: Mapping of question names to question definitions.
                Both Question objects and raw dicts are accepted; mixed mappings
                are allowed. Question objects are converted to their wire format.
            model: Model name to use (e.g., jev-1.13.0).

        Returns:
            Typed SystemOneResponse.

        Example:
            ```python
            port: SystemOnePort
            response = port.system_one(
                state="content",
                questions={"q1": {"type": "noul"}},
                model="jev-latest",
            )
            ```
        """
        ...


class AsyncSystemOnePort(Protocol):
    """Protocol for calling the Jev System One API asynchronously.

    Attributes:
        system_one (method): Method to call the Jev System One API.

    Examples:
        ```python
        from judgevet.ports import AsyncSystemOnePort
        from judgevet.domain.response import SystemOneResponse


        async def call_api(port: AsyncSystemOnePort) -> SystemOneResponse:
            return await port.system_one(
                state="content",
                questions={"q1": {"type": "noul"}},
                model="jev-latest",
            )
        ```

    See Also:
        - [judgevet.adapters.outbound.http][]: HTTP adapter implementation
        - [judgevet.ports.SystemOnePort][]: Sync protocol definition
    """

    async def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
    ) -> SystemOneResponse:
        """Call the Jev System One API.

        Args:
            state: The content to evaluate (text, JSON object, or array).
            questions: Mapping of question names to question definitions.
                Both Question objects and raw dicts are accepted; mixed mappings
                are allowed. Question objects are converted to their wire format.
            model: Model name to use (e.g., jev-1.13.0).

        Returns:
            Typed SystemOneResponse.

        Example:
            ```python
            port: AsyncSystemOnePort
            response = await port.system_one(
                state="content",
                questions={"q1": {"type": "noul"}},
                model="jev-latest",
            )
            ```
        """
        ...


class StateRedactor(Protocol):
    """Transform caller-owned state through a synchronous structural callback.

    The HTTP adapters pass a deep copy of JSON state and serialize the returned
    state once per logical call. The same callback runs in sync and async clients.
    Applications own detection rules, callback IO and concurrency safety.

    Attributes:
        redact (method): Transform copied state before serialization.

    Examples:
        ```python
        from typing import Any


        class ReplaceState:
            def redact(self, state: str | dict[str, Any] | list[Any]) -> str:
                return "caller-selected replacement"


        redactor: StateRedactor = ReplaceState()
        assert redactor.redact("synthetic") == "caller-selected replacement"
        ```

    See Also:
        - [judgevet.adapters.outbound.request_body][]: Copy and serialization boundary.
    """

    def redact(
        self, state: str | dict[str, Any] | list[Any]
    ) -> str | dict[str, Any] | list[Any]:
        """Return replacement state without receiving questions or transport metadata.

        Args:
            state: A private copy of the logical call's text, dictionary or list.

        Returns:
            A JSON-serializable string, dictionary or list chosen by the caller.

        Raises:
            Exception: Caller-defined failures propagate before any transmission.
        """
        ...
