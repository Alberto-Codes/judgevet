"""HTTP outbound adapter implementation.

Examples:
    ```python
    from jev_client.adapters.outbound.http import HTTPSystemOneAdapter

    adapter = HTTPSystemOneAdapter(api_key="your-api-key")
    try:
        response = adapter.system_one(
            state="Your content here",
            questions={
                "q1": {
                    "type": "noul",
                    "instructions": "Is this correct?",
                }
            },
        )
        print(response)
    finally:
        adapter.close()
    ```

See Also:
    - [jev_client.ports.SystemOnePort][]: Protocol definition
    - [jev_client.domain.errors][]: Error types
    - [jev_client.adapters.inbound.cli][]: CLI adapter

Raises:
    JevAuthError: If the API returns 401 or 403.
    JevRequestError: If the API returns 4xx (except 401/403).
    JevServiceError: If the API returns 5xx or a transport error occurs.
    JevResponseError: If the API returns 2xx with unparseable body.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Self

import httpx

from jev_client.domain.errors import (
    JevAuthError,
    JevError,
    JevRequestError,
    JevResponseError,
    JevServiceError,
)
from jev_client.ports import SystemOnePort


class HTTPSystemOneAdapter(SystemOnePort):
    """HTTP implementation of the SystemOnePort using httpx.

    See: https://api.typesafe.ai/v1/systemone

    Attributes:
        api_key (str | None): The TypeSafe API key.
        base_url (str): The API base URL.
        default_model (str): The default model to use.

    Examples:
        ```python
        adapter = HTTPSystemOneAdapter(api_key="your-api-key")
        try:
            response = adapter.system_one(
                state="Your content here",
                questions={"q1": {"type": "noul", "instructions": "Is this correct?"}},
            )
            print(response)
        finally:
            adapter.close()
        ```
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str = "jev-latest",
    ) -> None:
        """Initialize the HTTP adapter.

        Args:
            api_key: TypeSafe API key.
            base_url: API base URL. Defaults to https://api.typesafe.ai.
            default_model: Default model to use. Defaults to jev-latest.

        Raises:
            ValueError: If no API key is provided.
        """
        self._api_key = api_key
        if self._api_key is None:
            raise ValueError("API key must be provided")

        self._base_url = base_url or "https://api.typesafe.ai"
        self._default_model = default_model
        self._client = httpx.Client(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )

    def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Any],
        model: str | None = None,
    ) -> dict[str, Any]:
        """Call the Jev System One API via HTTP.

        Args:
            state: The content to evaluate.
            questions: Mapping of question names to question definitions.
            model: Model name override.

        Returns:
            Raw API response dictionary.

        Raises:
            JevAuthError: If the API returns 401 or 403.
            JevRequestError: If the API returns 4xx (except 401/403).
            JevServiceError: If the API returns 5xx or a transport error occurs.
            JevResponseError: If the API returns 2xx with unparseable body.

        Note:
            This method now handles response body parsing errors and raises
            JevResponseError instead of letting ValueError propagate.
        """
        payload = {
            "state": state,
            "questions": questions,
            "model": model or self._default_model,
        }

        try:
            response = self._client.post("/v1/systemone", json=payload)
            response.raise_for_status()
            try:
                return response.json()
            except ValueError as exc:
                raise JevResponseError(
                    f"Failed to parse response body: {exc}",
                    response.status_code,
                ) from exc
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            if status_code in (
                JevError.HTTP_STATUS_401_UNAUTHORIZED,
                JevError.HTTP_STATUS_403_FORBIDDEN,
            ):
                raise JevAuthError(str(exc), status_code) from exc
            elif (
                JevError.HTTP_STATUS_400_MIN
                <= status_code
                < JevError.HTTP_STATUS_500_MIN
            ):
                raise JevRequestError(str(exc), status_code) from exc
            elif status_code >= JevError.HTTP_STATUS_500_MIN:
                raise JevServiceError(str(exc), status_code) from exc
            raise
        except httpx.RequestError as exc:
            raise JevServiceError(str(exc), None) from exc

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> Self:
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager."""
        self.close()
