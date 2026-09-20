"""Response types from Jev API.

Examples:
    ```python
    from jev_client.domain.answers import NoulAnswer
    from jev_client.domain.response import SystemOneResponse
    from jev_client.domain.usage import Usage

    response = SystemOneResponse(
        model="jev-latest",
        usage=Usage(input_tokens=100, output_tokens=50),
        answers={"q1": NoulAnswer(noul=0.75)},
    )
    assert response.model == "jev-latest"
    ```

See Also:
    - [jev_client.domain.answers][]: Answer types
    - [jev_client.domain.usage][]: Usage metadata
"""

from __future__ import annotations

from jev_client.domain.answers import Answer
from jev_client.domain.usage import Usage


class SystemOneResponse:
    """Answers grouped by question type with model and usage metadata.

    See: https://docs.typesafe.ai/concepts/system-one

    Attributes:
        model (str): The model used to answer the request.
        usage (Usage): Token usage for the request.
        answers (dict[str, Answer]): All answer objects keyed by question name.

    Examples:
        ```python
        from jev_client.domain.answers import NoulAnswer
        from jev_client.domain.usage import Usage

        response = SystemOneResponse(
            model="jev-latest",
            usage=Usage(input_tokens=100, output_tokens=50),
            answers={"q1": NoulAnswer(noul=0.75)},
        )
        assert response.model == "jev-latest"
        ```

    See Also:
        - [jev_client.domain.answers][]: Answer types
        - [jev_client.domain.usage][]: Usage metadata
    """

    __slots__ = ("answers", "model", "usage")

    def __init__(
        self,
        model: str,
        usage: Usage,
        answers: dict[str, Answer] | None = None,
    ) -> None:
        """Initialize a SystemOneResponse.

        Args:
            model: The model used to answer the request.
            usage: Token usage for the request.
            answers: All answer objects keyed by question name.
        """
        self.model = model
        self.usage = usage
        self.answers = answers if answers is not None else {}

    def __repr__(self) -> str:
        """Return a string representation of the SystemOneResponse."""
        return (
            "SystemOneResponse("
            f"model={self.model!r}, "
            f"usage={self.usage!r}, "
            f"answers={self.answers!r})"
        )
