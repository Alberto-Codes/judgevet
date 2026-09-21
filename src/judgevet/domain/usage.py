"""Usage metadata from Jev API.

This is a frozen dataclass with optional token counts and validation in
`__post_init__` to ensure non-negative values.

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

from dataclasses import dataclass


@dataclass(frozen=True)
class Usage:
    """Token counts for a request.

    See: https://docs.typesafe.ai/api.md

    This is a frozen dataclass. Values must be non-negative if provided.

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

    input_tokens: int | None = None
    output_tokens: int | None = None

    def __post_init__(self) -> None:
        """Validate token counts.

        Raises:
            TypeError: If a token count is not int (bool rejected).
            ValueError: If a token count is negative.
        """
        if self.input_tokens is not None:
            if not isinstance(self.input_tokens, int) or isinstance(
                self.input_tokens, bool
            ):
                raise TypeError(
                    f"input_tokens must be int or None, got "
                    f"{type(self.input_tokens).__name__}"
                )
            if self.input_tokens < 0:
                raise ValueError(
                    f"input_tokens must be non-negative, got {self.input_tokens}"
                )
        if self.output_tokens is not None:
            if not isinstance(self.output_tokens, int) or isinstance(
                self.output_tokens, bool
            ):
                raise TypeError(
                    f"output_tokens must be int or None, got "
                    f"{type(self.output_tokens).__name__}"
                )
            if self.output_tokens < 0:
                raise ValueError(
                    f"output_tokens must be non-negative, got {self.output_tokens}"
                )
