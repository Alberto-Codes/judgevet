"""Port protocols that the domain calls out through.

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

Attributes:
    AsyncSystemOnePort (Protocol): Async structural protocol for calling the Jev System One API.
    SystemOnePort (Protocol): Structural protocol for calling the Jev System One API.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

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
        questions: Mapping[str, Any],
        model: str,
    ) -> SystemOneResponse:
        """Call the Jev System One API.

        Args:
            state: The content to evaluate (text, JSON object, or array).
            questions: Mapping of question names to question definitions.
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
        questions: Mapping[str, Any],
        model: str,
    ) -> SystemOneResponse:
        """Call the Jev System One API.

        Args:
            state: The content to evaluate (text, JSON object, or array).
            questions: Mapping of question names to question definitions.
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
