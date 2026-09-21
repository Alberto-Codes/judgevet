"""Usage metadata from Jev API.

Examples:
    ```python
    from judgevet.domain.usage import Usage

    usage = Usage(input_tokens=100, output_tokens=50)
    assert usage.input_tokens == 100
    ```

See Also:
    - [judgevet.domain.response][]: Response container
"""

from __future__ import annotations


class Usage:
    """Token counts for a request.

    See: https://docs.typesafe.ai/api.md

    Attributes:
        input_tokens (int | None): Number of input tokens used.
        output_tokens (int | None): Number of output tokens used.

    Examples:
        ```python
        usage = Usage(input_tokens=100, output_tokens=50)
        assert usage.input_tokens == 100
        ```

    See Also:
        - [judgevet.domain.response.SystemOneResponse][]: Response container
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
        """Return a string representation of the Usage."""
        return f"Usage(input_tokens={self.input_tokens!r}, output_tokens={self.output_tokens!r})"
