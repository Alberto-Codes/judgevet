"""Response types from Jev API.

The `SystemOneResponse` container holds answers with model and usage metadata.
It is a frozen dataclass with immutable fields.

Examples:
    ```python
    from judgevet.domain.answers import NoulAnswer
    from judgevet.domain.response import SystemOneResponse
    from judgevet.domain.usage import Usage

    response = SystemOneResponse(
        model="jev-latest",
        usage=Usage(input_tokens=100, output_tokens=50),
        answers={"q1": NoulAnswer(noul=0.75)},
    )
    assert response.model == "jev-latest"
    ```

See Also:
    - [judgevet.domain.answers][]: Answer types
    - [judgevet.domain.usage][]: Usage metadata
"""

from __future__ import annotations

from dataclasses import dataclass, field

from judgevet.domain.answers import Answer
from judgevet.domain.usage import Usage


@dataclass(frozen=True)
class SystemOneResponse:
    """Answers grouped by question type with model and usage metadata.

    See: https://docs.typesafe.ai/concepts/system-one

    This is a frozen dataclass: instances are immutable after construction.

    Attributes:
        model (str): The model used to answer the request.
        usage (Usage): Token usage for the request.
        answers (dict[str, Answer]): All answer objects keyed by question name.

    Examples:
        ```python
        from judgevet.domain.answers import NoulAnswer
        from judgevet.domain.usage import Usage

        response = SystemOneResponse(
            model="jev-latest",
            usage=Usage(input_tokens=100, output_tokens=50),
            answers={"q1": NoulAnswer(noul=0.75)},
        )
        assert response.model == "jev-latest"
        ```

    See Also:
        - [judgevet.domain.answers][]: Answer types
        - [judgevet.domain.usage][]: Usage metadata
    """

    model: str
    usage: Usage
    answers: dict[str, Answer] = field(default_factory=dict)
    """All answer objects keyed by question name.

    The field is always a dict (empty if no answers were provided).
    """

    def __repr__(self) -> str:
        """Return a string representation of the SystemOneResponse.

        Returns:
            A string representation including model, usage, and answers.
        """
        return (
            f"SystemOneResponse("
            f"model={self.model!r}, "
            f"usage={self.usage!r}, "
            f"answers={self.answers!r})"
        )
