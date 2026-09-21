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
    SystemOnePort (class): Protocol for calling the Jev System One API.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from judgevet.domain.response import SystemOneResponse


class SystemOnePort:
    """Protocol for calling the Jev System One API.

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

        Raises:
            NotImplementedError: If not implemented in a subclass.
        """
        raise NotImplementedError
