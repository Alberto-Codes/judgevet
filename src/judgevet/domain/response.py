"""Response types from Jev API.

The `SystemOneResponse` container holds answers with model and usage metadata.
Frozen instances prevent attribute reassignment. The answers dictionary and
nested answer dictionaries remain mutable. Typed accessors return fresh shallow
dictionaries containing the same answer objects.

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
    assert response.nouls["q1"].noul == 0.75
    ```

See Also:
    - [judgevet.domain.answers][]: Answer types
    - [judgevet.domain.usage][]: Usage metadata
"""

from __future__ import annotations

from dataclasses import dataclass, field

from judgevet.domain.answers import Answer, ChoiceAnswer, NoulAnswer, ScoreAnswer
from judgevet.domain.usage import Usage


@dataclass(frozen=True)
class SystemOneResponse:
    """Answers grouped by question type with model and usage metadata.

    See: https://docs.typesafe.ai/concepts/system-one

    Frozen instances prevent attribute reassignment. The original answers
    dictionary remains mutable. Each typed property filters its current contents
    into a fresh dictionary. Editing that returned mapping leaves answers
    unchanged; the answer objects and their nested dictionaries remain shared.
    Missing or wrong-variant keys raise normal KeyError when indexed.

    Attributes:
        model (str): The model used to answer the request.
        usage (Usage): Token usage for the request.
        answers (dict[str, Answer]): All answer objects keyed by question name.
        nouls (dict[str, NoulAnswer]): Current Noul answers in a fresh dictionary.
        choices (dict[str, ChoiceAnswer]): Current Choice answers in a fresh dictionary.
        scores (dict[str, ScoreAnswer]): Current Score answers in a fresh dictionary.

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

    @property
    def nouls(self) -> dict[str, NoulAnswer]:
        """Return a fresh plain dict of NoulAnswer entries from self.answers.

        Returns:
            A new dict preserving insertion order with exact NoulAnswer object references.
            Empty if no matching entries; KeyError on wrong-variant indexing.
        """
        return {k: v for k, v in self.answers.items() if isinstance(v, NoulAnswer)}

    @property
    def choices(self) -> dict[str, ChoiceAnswer]:
        """Return a fresh plain dict of ChoiceAnswer entries from self.answers.

        Returns:
            A new dict preserving insertion order with exact ChoiceAnswer object references.
            Empty if no matching entries; KeyError on wrong-variant indexing.
        """
        return {k: v for k, v in self.answers.items() if isinstance(v, ChoiceAnswer)}

    @property
    def scores(self) -> dict[str, ScoreAnswer]:
        """Return a fresh plain dict of ScoreAnswer entries from self.answers.

        Returns:
            A new dict preserving insertion order with exact ScoreAnswer object references.
            Empty if no matching entries; KeyError on wrong-variant indexing.
        """
        return {k: v for k, v in self.answers.items() if isinstance(v, ScoreAnswer)}

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
