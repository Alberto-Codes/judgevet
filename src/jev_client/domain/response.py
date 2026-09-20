"""Response types from Jev API."""

from __future__ import annotations

from jev_client.domain.answers import Answer
from jev_client.domain.usage import Usage


class SystemOneResponse:
    """Answers grouped by question type with model and usage metadata.

    See: https://docs.typesafe.ai/concepts/system-one
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
        return f"SystemOneResponse(model={self.model!r}, usage={self.usage}, answers={self.answers})"
