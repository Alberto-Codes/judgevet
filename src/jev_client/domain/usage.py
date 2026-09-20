"""Usage metadata from Jev API."""

from __future__ import annotations


class Usage:
    """Token counts for a request.

    See: https://jevaiguide.com/jev-api/
    """

    __slots__ = ("input_tokens", "output_tokens")

    def __init__(
        self,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
    ) -> None:
        """Initialize a Usage.

        Args:
            input_tokens: Number of input tokens used, or None when not reported.
            output_tokens: Number of output tokens used, or None when not reported.
        """
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens

    def __repr__(self) -> str:
        return f"Usage(input_tokens={self.input_tokens}, output_tokens={self.output_tokens})"
