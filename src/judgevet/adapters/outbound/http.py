"""HTTP outbound adapter implementation.

Examples:
    ```python
    from judgevet.adapters.outbound.http import HTTPSystemOneAdapter
    from judgevet.domain.response import SystemOneResponse

    adapter = HTTPSystemOneAdapter(api_key="your-api-key")
    try:
        response: SystemOneResponse = adapter.system_one(
            state="Your content here",
            questions={
                "q1": {
                    "type": "noul",
                    "instructions": "Is this correct?",
                }
            },
        )
        print(response)
        print(response.model)
        print(response.answers)
    finally:
        adapter.close()
    ```

See Also:
    - [judgevet.ports.SystemOnePort][]: Protocol definition
    - [judgevet.domain.errors][]: Error types
    - [judgevet.adapters.inbound.cli][]: CLI adapter
    - [judgevet.domain.response_parser][]: Response parsing

Raises:
    JevAuthError: If the API returns 401 or 403.
    JevRateLimitError: If the API returns 429 (rate limit exceeded).
    JevRequestError: If the API returns 4xx (except 401/403, 429).
    JevServiceError: If the API returns 5xx or a transport error occurs.
    JevResponseError: If the API returns 2xx with unparseable body.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Self

import httpx

from judgevet.domain.errors import (
    JevAuthError,
    JevError,
    JevRateLimitError,
    JevRequestError,
    JevResponseError,
    JevServiceError,
)
from judgevet.domain.response import SystemOneResponse
from judgevet.domain.response_parser import parse_system_one_response
from judgevet.ports import SystemOnePort


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
            response: SystemOneResponse = adapter.system_one(
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
    ) -> SystemOneResponse:
        """Call the Jev System One API via HTTP.

        Args:
            state: The content to evaluate.
            questions: Mapping of question names to question definitions.
            model: Model name override.

        Returns:
            Typed SystemOneResponse with parsed answer objects.

        Raises:
            JevAuthError: If the API returns 401 or 403.
            JevRateLimitError: If the API returns 429 (rate limit exceeded).
            JevRequestError: If the API returns 4xx (except 401/403, 429).
            JevServiceError: If the API returns 5xx or a transport error occurs.
            JevResponseError: If the API returns 2xx with unparseable body.
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
                raw = response.json()
            except ValueError as exc:
                raise JevResponseError(
                    f"Failed to parse response body: {exc}",
                    response.status_code,
                ) from exc
            return parse_system_one_response("system-one", raw)
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            if status_code == JevError.HTTP_STATUS_429_TOO_MANY_REQUESTS:
                raise JevRateLimitError(str(exc), status_code) from exc
            elif status_code in (
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
