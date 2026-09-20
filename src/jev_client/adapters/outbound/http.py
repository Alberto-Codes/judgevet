"""HTTP outbound adapter implementation."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any, Self

import httpx

from jev_client.ports import SystemOnePort


class HTTPSystemOneAdapter(SystemOnePort):
    """HTTP implementation of the SystemOnePort using httpx.

    See: https://api.typesafe.ai/v1/systemone
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str = "jev-latest",
    ) -> None:
        """Initialize the HTTP adapter.

        Args:
            api_key: TypeSafe API key. Defaults to TYPESAFE_API_KEY env var.
            base_url: API base URL. Defaults to https://api.typesafe.ai.
            default_model: Default model to use. Defaults to jev-latest.
        """
        self._api_key = api_key or os.environ.get("TYPESAFE_API_KEY")
        if self._api_key is None:
            raise ValueError("API key must be provided or set in TYPESAFE_API_KEY")

        self._base_url = base_url or os.environ.get(
            "TYPESAFE_BASE_URL", "https://api.typesafe.ai"
        )
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
            httpx.HTTPStatusError: If the API returns an error status.
            httpx.RequestError: If the request fails.
        """
        payload = {
            "state": state,
            "questions": questions,
            "model": model or self._default_model,
        }

        response = self._client.post("/v1/systemone", json=payload)
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> Self:
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager."""
        self.close()
