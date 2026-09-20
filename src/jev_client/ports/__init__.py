"""Port protocols that the domain calls out through."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class SystemOnePort:
    """Protocol for calling the Jev System One API."""

    def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Any],
        model: str,
    ) -> dict[str, Any]:
        """Call the Jev System One API.

        Args:
            state: The content to evaluate (text, JSON object, or array).
            questions: Mapping of question names to question definitions.
            model: Model name to use (e.g., jev-1.13.0).

        Returns:
            Raw API response dictionary.
        """
        raise NotImplementedError
